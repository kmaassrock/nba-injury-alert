"""
API endpoints for injury data.
"""
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from ...models.database import get_db
from ...models.injury import InjuryReport, InjuryStatus, StatusChange
from ...models.player import Player
from ...utils.errors import ResourceNotFoundError

router = APIRouter()


@router.get("/reports")
async def get_injury_reports(
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """
    Get a list of injury reports.
    
    Args:
        skip: Number of reports to skip.
        limit: Maximum number of reports to return.
        db: Database session.
    
    Returns:
        List of injury reports.
    """
    reports = db.query(InjuryReport).order_by(
        desc(InjuryReport.report_date)
    ).offset(skip).limit(limit).all()
    
    return {
        "reports": [
            {
                "id": report.id,
                "report_date": report.report_date,
                "source_url": report.source_url,
                "report_hash": report.report_hash
            }
            for report in reports
        ],
        "total": db.query(InjuryReport).count(),
        "skip": skip,
        "limit": limit
    }


@router.get("/reports/{report_id}")
async def get_injury_report(
    report_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a specific injury report.
    
    Args:
        report_id: ID of the report.
        db: Database session.
    
    Returns:
        The injury report.
    
    Raises:
        HTTPException: If the report is not found.
    """
    report = db.query(InjuryReport).filter(InjuryReport.id == report_id).first()
    
    if not report:
        raise HTTPException(status_code=404, detail=f"Report with ID {report_id} not found")
    
    # Get the statuses for this report
    statuses = db.query(InjuryStatus).filter(
        InjuryStatus.report_id == report_id
    ).all()
    
    return {
        "id": report.id,
        "report_date": report.report_date,
        "source_url": report.source_url,
        "report_hash": report.report_hash,
        "statuses": [
            {
                "id": status.id,
                "player_id": status.player_id,
                "player_name": status.player.name,
                "team": status.player.team,
                "status": status.status,
                "reason": status.reason,
                "details": status.details,
                "game_date": status.game_date,
                "opponent": status.opponent,
                "is_status_change": status.is_status_change,
                "previous_status": status.previous_status
            }
            for status in statuses
        ]
    }


@router.get("/changes")
async def get_status_changes(
    days: int = 1,
    top_players_only: bool = True,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """
    Get recent status changes.
    
    Args:
        days: Number of days to look back.
        top_players_only: Whether to include only top-ranked players.
        skip: Number of changes to skip.
        limit: Maximum number of changes to return.
        db: Database session.
    
    Returns:
        List of status changes.
    """
    # Calculate the cutoff date
    cutoff_date = datetime.now() - timedelta(days=days)
    
    # Build the query
    query = db.query(StatusChange).filter(
        StatusChange.change_date >= cutoff_date
    )
    
    if top_players_only:
        query = query.join(Player).filter(Player.is_top_100 == True)
    
    # Get the total count
    total = query.count()
    
    # Get the paginated results
    changes = query.order_by(
        desc(StatusChange.change_date)
    ).offset(skip).limit(limit).all()
    
    return {
        "changes": [
            {
                "id": change.id,
                "player_id": change.player_id,
                "player_name": change.player.name,
                "team": change.player.team,
                "old_status": change.old_status,
                "new_status": change.new_status,
                "change_date": change.change_date,
                "report_id": change.report_id,
                "notification_sent": change.notification_sent,
                "notification_date": change.notification_date,
                "rank": change.player.current_rank
            }
            for change in changes
        ],
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.get("/players/{player_id}/history")
async def get_player_injury_history(
    player_id: int,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """
    Get injury history for a specific player.
    
    Args:
        player_id: ID of the player.
        limit: Maximum number of status changes to return.
        db: Database session.
    
    Returns:
        The player's injury history.
    
    Raises:
        HTTPException: If the player is not found.
    """
    player = db.query(Player).filter(Player.id == player_id).first()
    
    if not player:
        raise HTTPException(status_code=404, detail=f"Player with ID {player_id} not found")
    
    # Get the player's status changes
    changes = db.query(StatusChange).filter(
        StatusChange.player_id == player_id
    ).order_by(
        desc(StatusChange.change_date)
    ).limit(limit).all()
    
    # Get the player's current status
    current_status = db.query(InjuryStatus).filter(
        InjuryStatus.player_id == player_id
    ).order_by(
        desc(InjuryStatus.created_at)
    ).first()
    
    return {
        "player": {
            "id": player.id,
            "name": player.name,
            "team": player.team,
            "position": player.position,
            "jersey_number": player.jersey_number,
            "current_rank": player.current_rank,
            "is_top_100": player.is_top_100
        },
        "current_status": {
            "status": current_status.status if current_status else "ACTIVE",
            "reason": current_status.reason if current_status else None,
            "details": current_status.details if current_status else None,
            "game_date": current_status.game_date if current_status else None,
            "opponent": current_status.opponent if current_status else None,
            "report_id": current_status.report_id if current_status else None,
            "updated_at": current_status.updated_at if current_status else None
        } if current_status else None,
        "history": [
            {
                "id": change.id,
                "old_status": change.old_status,
                "new_status": change.new_status,
                "change_date": change.change_date,
                "report_id": change.report_id
            }
            for change in changes
        ]
    }
