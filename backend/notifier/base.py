"""
Base notifier classes for the NBA Injury Alert system.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from ..utils.errors import NotifierError
from ..utils.logging import logger, setup_logger

# Create a logger for the notifier module
notifier_logger = setup_logger("nba_injury_alert.notifier")


class BaseNotifier(ABC):
    """Base class for notifiers."""
    
    def __init__(self):
        """Initialize the notifier."""
        self.logger = notifier_logger
    
    @abstractmethod
    async def send_notification(
        self, 
        recipient: str, 
        subject: str, 
        message: str, 
        **kwargs
    ) -> Dict[str, Any]:
        """
        Send a notification.
        
        Args:
            recipient: The recipient of the notification.
            subject: The subject of the notification.
            message: The message content.
            **kwargs: Additional notification parameters.
        
        Returns:
            A dictionary with the notification result.
        
        Raises:
            NotifierError: If the notification fails.
        """
        pass
    
    @abstractmethod
    async def send_batch(
        self, 
        notifications: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Send a batch of notifications.
        
        Args:
            notifications: List of notification dictionaries.
        
        Returns:
            List of notification results.
        
        Raises:
            NotifierError: If the batch operation fails.
        """
        pass


class NotificationFormatter:
    """Utility class for formatting notifications."""
    
    @staticmethod
    def format_injury_change(
        player_name: str,
        team: str,
        old_status: Optional[str],
        new_status: str,
        reason: Optional[str] = None,
        details: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Format an injury status change notification.
        
        Args:
            player_name: Name of the player.
            team: Team of the player.
            old_status: Previous injury status.
            new_status: New injury status.
            reason: Reason for the status.
            details: Additional details.
        
        Returns:
            Dictionary with formatted subject and message.
        """
        # Format the subject
        if old_status is None:
            subject = f"{player_name} ({team}) added to injury report: {new_status}"
        elif new_status == "ACTIVE":
            subject = f"{player_name} ({team}) removed from injury report"
        else:
            subject = f"{player_name} ({team}) status change: {old_status} → {new_status}"
        
        # Format the message
        message_parts = [
            f"Player: {player_name}",
            f"Team: {team}",
        ]
        
        if old_status is None:
            message_parts.append(f"Status: {new_status}")
        else:
            message_parts.append(f"Previous Status: {old_status}")
            message_parts.append(f"New Status: {new_status}")
        
        if reason:
            message_parts.append(f"Reason: {reason}")
        
        if details:
            message_parts.append(f"Details: {details}")
        
        message = "\n".join(message_parts)
        
        return {
            "subject": subject,
            "message": message
        }
    
    @staticmethod
    def format_html_injury_change(
        player_name: str,
        team: str,
        old_status: Optional[str],
        new_status: str,
        reason: Optional[str] = None,
        details: Optional[str] = None,
        rank: Optional[int] = None
    ) -> str:
        """
        Format an injury status change as HTML.
        
        Args:
            player_name: Name of the player.
            team: Team of the player.
            old_status: Previous injury status.
            new_status: New injury status.
            reason: Reason for the status.
            details: Additional details.
            rank: Player's rank.
        
        Returns:
            HTML formatted message.
        """
        # Determine status change type
        if old_status is None:
            status_text = f"<span class='status new'>{new_status}</span>"
            change_type = "added"
        elif new_status == "ACTIVE":
            status_text = "<span class='status active'>ACTIVE</span>"
            change_type = "removed"
        else:
            status_text = f"<span class='status old'>{old_status}</span> → <span class='status new'>{new_status}</span>"
            change_type = "changed"
        
        # Format the HTML
        html = f"""
        <div class="injury-alert {change_type}">
            <div class="player-info">
                <h3>{player_name}</h3>
                <div class="team">{team}</div>
                {f'<div class="rank">Rank: {rank}</div>' if rank else ''}
            </div>
            <div class="status-info">
                <div class="status-change">{status_text}</div>
                {f'<div class="reason">{reason}</div>' if reason else ''}
                {f'<div class="details">{details}</div>' if details else ''}
            </div>
        </div>
        """
        
        return html
