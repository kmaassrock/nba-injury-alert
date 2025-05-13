"""
API endpoints for player data.
"""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from ...models.database import get_db
from ...models.player import Player, PlayerRanking
from ...models.injury import InjuryStatus
from ...utils.errors import ResourceNotFoundError

router = APIRouter()


@router.get("/")
async def get_players(
    team: Optional[str] = None,
    is_top_100: Optional[bool] = None,
    has_injury: Optional[bool] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    Get a list of players.
    
    Args:
        team: Filter by team.
        is_top_100: Filter by top 100 status.
        has_injury: Filter by injury status.
        skip: Number of players to skip.
        limit: Maximum number of players to return.
        db: Database session.
    
    Returns:
        List of players.
    """
    # Build the query
    query = db.query(Player)
    
    # Apply filters
    if team:
        query = query.filter(Player.team == team)
    
    if is_top_100 is not None:
        query = query.filter(Player.is_top_100 == is_top_100)
    
    if has_injury is not None:
        # This is a more complex filter that requires a subquery
        if has_injury:
            # Get players with a recent injury status
            latest_statuses = db.query(
                InjuryStatus.player_id,
                func.max(InjuryStatus.created_at).label("latest_date")
            ).group_by(InjuryStatus.player_id).subquery()
            
            query = query.join(
                latest_statuses,
                Player.id == latest_statuses.c.player_id
            )
        else:
            # Get players without a recent injury status
            injured_player_ids = db.query(InjuryStatus.player_id).distinct().subquery()
            query = query.filter(~Player.id.in_(injured_player_ids))
    
    # Get the total count
    total = query.count()
    
    # Apply pagination
    players = query.order_by(
        Player.current_rank.asc() if is_top_100 else Player.name.asc()
    ).offset(skip).limit(limit).all()
    
    return {
        "players": [
            {
                "id": player.id,
                "name": player.name,
                "team": player.team,
                "position": player.position,
                "jersey_number": player.jersey_number,
                "current_rank": player.current_rank,
                "is_top_100": player.is_top_100,
                "nba_id": player.nba_id,
                "espn_id": player.espn_id
            }
            for player in players
        ],
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.get("/top100")
async def get_top_players(
    db: Session = Depends(get_db)
):
    """
    Get the top 100 players.
    
    Args:
        db: Database session.
    
    Returns:
        List of top 100 players.
    """
    players = db.query(Player).filter(
        Player.is_top_100 == True
    ).order_by(
        Player.current_rank.asc()
    ).all()
    
    return {
        "players": [
            {
                "id": player.id,
                "name": player.name,
                "team": player.team,
                "position": player.position,
                "jersey_number": player.jersey_number,
                "current_rank": player.current_rank,
                "is_top_100": player.is_top_100,
                "nba_id": player.nba_id,
                "espn_id": player.espn_id
            }
            for player in players
        ],
        "total": len(players)
    }


@router.get("/teams")
async def get_teams(
    db: Session = Depends(get_db)
):
    """
    Get a list of all NBA teams.
    
    Args:
        db: Database session.
    
    Returns:
        List of teams.
    """
    # Get distinct teams from the player table
    teams = db.query(Player.team).distinct().order_by(Player.team).all()
    
    return {
        "teams": [team[0] for team in teams]
    }


@router.get("/{player_id}")
async def get_player(
    player_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a specific player.
    
    Args:
        player_id: ID of the player.
        db: Database session.
    
    Returns:
        The player.
    
    Raises:
        HTTPException: If the player is not found.
    """
    player = db.query(Player).filter(Player.id == player_id).first()
    
    if not player:
        raise HTTPException(status_code=404, detail=f"Player with ID {player_id} not found")
    
    # Get the player's current status
    current_status = db.query(InjuryStatus).filter(
        InjuryStatus.player_id == player_id
    ).order_by(
        desc(InjuryStatus.created_at)
    ).first()
    
    return {
        "id": player.id,
        "name": player.name,
        "team": player.team,
        "position": player.position,
        "jersey_number": player.jersey_number,
        "current_rank": player.current_rank,
        "is_top_100": player.is_top_100,
        "nba_id": player.nba_id,
        "espn_id": player.espn_id,
        "current_status": {
            "status": current_status.status,
            "reason": current_status.reason,
            "details": current_status.details,
            "game_date": current_status.game_date,
            "opponent": current_status.opponent,
            "report_id": current_status.report_id,
            "updated_at": current_status.updated_at
        } if current_status else None
    }


@router.get("/search/{query}")
async def search_players(
    query: str,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """
    Search for players by name.
    
    Args:
        query: Search query.
        limit: Maximum number of results to return.
        db: Database session.
    
    Returns:
        List of matching players.
    """
    # Search for players by name
    players = db.query(Player).filter(
        Player.name.ilike(f"%{query}%")
    ).order_by(
        Player.current_rank.asc() if query else Player.name.asc()
    ).limit(limit).all()
    
    return {
        "players": [
            {
                "id": player.id,
                "name": player.name,
                "team": player.team,
                "position": player.position,
                "jersey_number": player.jersey_number,
                "current_rank": player.current_rank,
                "is_top_100": player.is_top_100,
                "nba_id": player.nba_id,
                "espn_id": player.espn_id
            }
            for player in players
        ],
        "total": len(players),
        "query": query
    }
