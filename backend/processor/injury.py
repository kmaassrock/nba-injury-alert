"""
Injury report processor for the NBA Injury Alert system.
"""
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from sqlalchemy.orm import Session

from ..models.database import db_session
from ..models.injury import InjuryReport, InjuryStatus, StatusChange
from ..models.player import Player
from ..utils.errors import ProcessorError
from .base import DiffProcessor


class InjuryReportProcessor(DiffProcessor):
    """Processor for NBA injury reports."""
    
    def __init__(self, top_players_only: bool = True):
        """
        Initialize the injury report processor.
        
        Args:
            top_players_only: Whether to process only top-ranked players.
        """
        super().__init__()
        self.top_players_only = top_players_only
    
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process an injury report.
        
        Args:
            data: The injury report data from the fetcher.
        
        Returns:
            The processed data with extracted player statuses.
        
        Raises:
            ProcessorError: If the processing operation fails.
        """
        self.logger.info("Processing injury report...")
        
        try:
            # Extract the report data
            report_data = data.get("data", {})
            report_id = data.get("report_id")
            
            if not report_data:
                raise ProcessorError("No report data to process")
            
            if not report_id:
                raise ProcessorError("No report ID provided")
            
            # Parse the injury data
            player_statuses = self._extract_player_statuses(report_data)
            
            # Filter for top players if needed
            if self.top_players_only:
                player_statuses = self._filter_top_players(player_statuses)
            
            # Store the player statuses in the database
            stored_statuses = await self._store_player_statuses(player_statuses, report_id)
            
            return {
                "report_id": report_id,
                "player_statuses": stored_statuses,
                "total_players": len(player_statuses),
                "top_players": len(stored_statuses) if self.top_players_only else None
            }
            
        except Exception as e:
            self.logger.error(f"Error processing injury report: {str(e)}")
            raise ProcessorError(f"Failed to process injury report: {str(e)}")
    
    async def compute_diff(
        self, 
        current_data: Dict[str, Any], 
        previous_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Compute the difference between current and previous injury reports.
        
        Args:
            current_data: The current injury report data.
            previous_data: The previous injury report data.
        
        Returns:
            The differences between the reports.
        
        Raises:
            ProcessorError: If the diff operation fails.
        """
        self.logger.info("Computing diff between injury reports...")
        
        try:
            # Extract player statuses from both reports
            current_statuses = current_data.get("player_statuses", [])
            previous_statuses = previous_data.get("player_statuses", [])
            
            # Group statuses by player for easier comparison
            current_by_player = {status["player_id"]: status for status in current_statuses}
            previous_by_player = {status["player_id"]: status for status in previous_statuses}
            
            # Find players with status changes
            changes = []
            
            # Check for status changes in players present in both reports
            for player_id, current_status in current_by_player.items():
                if player_id in previous_by_player:
                    prev_status = previous_by_player[player_id]
                    if current_status["status"] != prev_status["status"]:
                        changes.append({
                            "player_id": player_id,
                            "player_name": current_status["player_name"],
                            "team": current_status["team"],
                            "old_status": prev_status["status"],
                            "new_status": current_status["status"],
                            "reason": current_status.get("reason"),
                            "details": current_status.get("details"),
                            "rank": current_status.get("rank")
                        })
            
            # Check for new players in the injury report
            for player_id, current_status in current_by_player.items():
                if player_id not in previous_by_player:
                    changes.append({
                        "player_id": player_id,
                        "player_name": current_status["player_name"],
                        "team": current_status["team"],
                        "old_status": None,
                        "new_status": current_status["status"],
                        "reason": current_status.get("reason"),
                        "details": current_status.get("details"),
                        "rank": current_status.get("rank")
                    })
            
            # Check for players removed from the injury report
            for player_id, prev_status in previous_by_player.items():
                if player_id not in current_by_player:
                    changes.append({
                        "player_id": player_id,
                        "player_name": prev_status["player_name"],
                        "team": prev_status["team"],
                        "old_status": prev_status["status"],
                        "new_status": "ACTIVE",  # Assuming removal means player is now active
                        "reason": None,
                        "details": None,
                        "rank": prev_status.get("rank")
                    })
            
            # Store the changes in the database
            stored_changes = await self._store_status_changes(
                changes, 
                current_data.get("report_id")
            )
            
            return {
                "changes": stored_changes,
                "total_changes": len(stored_changes),
                "current_report_id": current_data.get("report_id"),
                "previous_report_id": previous_data.get("report_id")
            }
            
        except Exception as e:
            self.logger.error(f"Error computing diff between injury reports: {str(e)}")
            raise ProcessorError(f"Failed to compute diff: {str(e)}")
    
    def _extract_player_statuses(self, report_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract player statuses from the injury report data.
        
        Args:
            report_data: The raw injury report data.
        
        Returns:
            List of player status dictionaries.
        """
        # This is a placeholder implementation
        # In a real implementation, this would parse the NBA API response format
        # For now, we'll assume the report_data already contains a list of player statuses
        player_statuses = []
        
        # Example parsing logic (adjust based on actual NBA API response format)
        if "players" in report_data:
            for player_data in report_data["players"]:
                player_statuses.append({
                    "player_id": player_data.get("personId"),
                    "player_name": player_data.get("name"),
                    "team": player_data.get("teamName"),
                    "status": player_data.get("status"),
                    "reason": player_data.get("reason"),
                    "details": player_data.get("details"),
                    "game_date": player_data.get("gameDate"),
                    "opponent": player_data.get("opponent")
                })
        
        return player_statuses
    
    def _filter_top_players(self, player_statuses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter the player statuses to include only top-ranked players.
        
        Args:
            player_statuses: List of player status dictionaries.
        
        Returns:
            Filtered list of player status dictionaries.
        """
        # Get the list of top players from the database
        with db_session() as session:
            top_players = session.query(Player).filter(Player.is_top_100 == True).all()
            top_player_ids = {str(player.nba_id) for player in top_players}
        
        # Filter the player statuses
        filtered_statuses = []
        for status in player_statuses:
            player_id = str(status.get("player_id"))
            if player_id in top_player_ids:
                # Get the player's rank
                for player in top_players:
                    if str(player.nba_id) == player_id:
                        status["rank"] = player.current_rank
                        break
                filtered_statuses.append(status)
        
        return filtered_statuses
    
    async def _store_player_statuses(
        self, 
        player_statuses: List[Dict[str, Any]], 
        report_id: int
    ) -> List[Dict[str, Any]]:
        """
        Store player statuses in the database.
        
        Args:
            player_statuses: List of player status dictionaries.
            report_id: ID of the injury report.
        
        Returns:
            List of stored player status dictionaries.
        """
        stored_statuses = []
        
        with db_session() as session:
            # Get the report
            report = session.query(InjuryReport).filter_by(id=report_id).first()
            if not report:
                raise ProcessorError(f"Report with ID {report_id} not found")
            
            # Process each player status
            for status_data in player_statuses:
                player_id = status_data.get("player_id")
                
                # Get or create the player
                player = self._get_or_create_player(session, status_data)
                
                # Create the injury status
                injury_status = InjuryStatus(
                    status=status_data.get("status"),
                    reason=status_data.get("reason"),
                    details=status_data.get("details"),
                    game_date=status_data.get("game_date"),
                    opponent=status_data.get("opponent"),
                    player_id=player.id,
                    report_id=report_id
                )
                
                session.add(injury_status)
                session.flush()  # Flush to get the ID
                
                # Add the stored status to the result
                stored_status = status_data.copy()
                stored_status["id"] = injury_status.id
                stored_status["player_db_id"] = player.id
                stored_statuses.append(stored_status)
        
        return stored_statuses
    
    async def _store_status_changes(
        self, 
        changes: List[Dict[str, Any]], 
        report_id: int
    ) -> List[Dict[str, Any]]:
        """
        Store status changes in the database.
        
        Args:
            changes: List of status change dictionaries.
            report_id: ID of the current injury report.
        
        Returns:
            List of stored status change dictionaries.
        """
        stored_changes = []
        
        with db_session() as session:
            # Process each status change
            for change_data in changes:
                player_id = change_data.get("player_id")
                
                # Get the player
                player = session.query(Player).filter_by(nba_id=player_id).first()
                if not player:
                    # Create a minimal player record if not found
                    player = Player(
                        name=change_data.get("player_name"),
                        team=change_data.get("team"),
                        nba_id=player_id,
                        current_rank=change_data.get("rank"),
                        is_top_100=change_data.get("rank") is not None and change_data.get("rank") <= 100
                    )
                    session.add(player)
                    session.flush()  # Flush to get the ID
                
                # Create the status change
                status_change = StatusChange(
                    player_id=player.id,
                    old_status=change_data.get("old_status"),
                    new_status=change_data.get("new_status"),
                    change_date=datetime.now(),
                    report_id=report_id,
                    notification_sent=False
                )
                
                session.add(status_change)
                session.flush()  # Flush to get the ID
                
                # Add the stored change to the result
                stored_change = change_data.copy()
                stored_change["id"] = status_change.id
                stored_change["player_db_id"] = player.id
                stored_changes.append(stored_change)
        
        return stored_changes
    
    def _get_or_create_player(self, session: Session, player_data: Dict[str, Any]) -> Player:
        """
        Get an existing player or create a new one.
        
        Args:
            session: Database session.
            player_data: Player data dictionary.
        
        Returns:
            Player instance.
        """
        player_id = player_data.get("player_id")
        
        # Try to find the player by NBA ID
        player = session.query(Player).filter_by(nba_id=player_id).first()
        
        if not player:
            # Create a new player
            player = Player(
                name=player_data.get("player_name"),
                team=player_data.get("team"),
                nba_id=player_id,
                current_rank=player_data.get("rank"),
                is_top_100=player_data.get("rank") is not None and player_data.get("rank") <= 100
            )
            session.add(player)
            session.flush()  # Flush to get the ID
        
        return player
