"""
Notification service for the NBA Injury Alert system.
"""
from datetime import datetime, time
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from sqlalchemy import and_, or_

from ..models.database import db_session
from ..models.injury import StatusChange
from ..models.user import User, NotificationSetting
from ..utils.config import settings
from ..utils.errors import NotifierError
from ..utils.logging import logger
from .base import NotificationFormatter
from .channels import EmailNotifier, WebSocketNotifier, PushNotifier


class NotificationService:
    """Service for managing and sending notifications."""
    
    def __init__(self):
        """Initialize the notification service."""
        self.email_notifier = EmailNotifier() if settings.notification.email_enabled else None
        self.push_notifier = PushNotifier() if settings.notification.push_enabled else None
        self.websocket_notifier = WebSocketNotifier() if settings.notification.websocket_enabled else None
        self.logger = logger
    
    async def process_status_changes(self, changes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Process status changes and send notifications.
        
        Args:
            changes: List of status change dictionaries.
        
        Returns:
            Dictionary with notification results.
        """
        self.logger.info(f"Processing {len(changes)} status changes for notifications")
        
        # Get the list of status changes that need notifications
        with db_session() as session:
            change_ids = [change["id"] for change in changes]
            db_changes = session.query(StatusChange).filter(
                StatusChange.id.in_(change_ids),
                StatusChange.notification_sent == False
            ).all()
            
            if not db_changes:
                self.logger.info("No status changes require notifications")
                return {"success": True, "notifications_sent": 0}
            
            self.logger.info(f"Found {len(db_changes)} status changes requiring notifications")
            
            # Get the users who should receive notifications
            notifications_to_send = []
            
            for change in db_changes:
                # Get users who have notification settings for this player or team
                users = session.query(User).join(
                    NotificationSetting,
                    and_(
                        NotificationSetting.user_id == User.id,
                        or_(
                            NotificationSetting.player_id == change.player_id,
                            NotificationSetting.team == change.player.team
                        )
                    )
                ).filter(
                    User.is_active == True
                ).all()
                
                self.logger.info(f"Found {len(users)} users to notify about player {change.player.name}")
                
                # Prepare notifications for each user
                for user in users:
                    # Check if user is in quiet hours
                    if self._is_in_quiet_hours(user):
                        self.logger.info(f"User {user.email} is in quiet hours, skipping notification")
                        continue
                    
                    # Get notification settings for this player/team
                    notification_setting = next(
                        (
                            ns for ns in user.notification_settings
                            if ns.player_id == change.player_id or ns.team == change.player.team
                        ),
                        None
                    )
                    
                    # If no specific setting, use user's default preferences
                    if notification_setting:
                        email_enabled = notification_setting.email_enabled
                        push_enabled = notification_setting.push_enabled
                        web_enabled = notification_setting.web_enabled
                    else:
                        email_enabled = user.email_notifications
                        push_enabled = user.push_notifications
                        web_enabled = user.web_notifications
                    
                    # Format the notification
                    formatted = NotificationFormatter.format_injury_change(
                        player_name=change.player.name,
                        team=change.player.team,
                        old_status=change.old_status,
                        new_status=change.new_status,
                        reason=None,  # Add reason if available
                        details=None  # Add details if available
                    )
                    
                    html_formatted = NotificationFormatter.format_html_injury_change(
                        player_name=change.player.name,
                        team=change.player.team,
                        old_status=change.old_status,
                        new_status=change.new_status,
                        reason=None,  # Add reason if available
                        details=None,  # Add details if available
                        rank=change.player.current_rank
                    )
                    
                    # Add to notifications list based on user preferences
                    if email_enabled and self.email_notifier:
                        notifications_to_send.append({
                            "channel": "email",
                            "recipient": user.email,
                            "subject": formatted["subject"],
                            "message": formatted["message"],
                            "html_message": html_formatted,
                            "user_id": user.id,
                            "change_id": change.id
                        })
                    
                    if push_enabled and self.push_notifier:
                        notifications_to_send.append({
                            "channel": "push",
                            "recipient": user.id,  # Using user ID as recipient for push
                            "subject": formatted["subject"],
                            "message": formatted["message"],
                            "user_id": user.id,
                            "change_id": change.id
                        })
                    
                    if web_enabled and self.websocket_notifier:
                        # For WebSocket, we'll broadcast to all connected clients
                        # and let the frontend filter based on user ID
                        notifications_to_send.append({
                            "channel": "websocket",
                            "recipient": str(user.id),  # Using user ID as recipient for WebSocket
                            "subject": formatted["subject"],
                            "message": formatted["message"],
                            "data": {
                                "html": html_formatted,
                                "player_id": change.player_id,
                                "team": change.player.team,
                                "old_status": change.old_status,
                                "new_status": change.new_status,
                                "change_id": change.id
                            },
                            "user_id": user.id,
                            "change_id": change.id
                        })
            
            # Send the notifications
            results = await self._send_notifications(notifications_to_send)
            
            # Mark the status changes as notified
            for change in db_changes:
                change.notification_sent = True
                change.notification_date = datetime.now()
            
            session.commit()
            
            return {
                "success": True,
                "notifications_sent": len(results),
                "results": results
            }
    
    async def _send_notifications(self, notifications: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Send notifications through appropriate channels.
        
        Args:
            notifications: List of notification dictionaries.
        
        Returns:
            List of notification results.
        """
        results = []
        
        # Group notifications by channel
        email_notifications = []
        push_notifications = []
        websocket_notifications = []
        
        for notification in notifications:
            channel = notification["channel"]
            if channel == "email":
                email_notifications.append(notification)
            elif channel == "push":
                push_notifications.append(notification)
            elif channel == "websocket":
                websocket_notifications.append(notification)
        
        # Send email notifications
        if email_notifications and self.email_notifier:
            try:
                email_results = await self.email_notifier.send_batch(email_notifications)
                results.extend(email_results)
            except Exception as e:
                self.logger.error(f"Error sending email notifications: {str(e)}")
        
        # Send push notifications
        if push_notifications and self.push_notifier:
            try:
                push_results = await self.push_notifier.send_batch(push_notifications)
                results.extend(push_results)
            except Exception as e:
                self.logger.error(f"Error sending push notifications: {str(e)}")
        
        # Send WebSocket notifications
        if websocket_notifications and self.websocket_notifier:
            try:
                websocket_results = await self.websocket_notifier.send_batch(websocket_notifications)
                results.extend(websocket_results)
            except Exception as e:
                self.logger.error(f"Error sending WebSocket notifications: {str(e)}")
        
        return results
    
    def _is_in_quiet_hours(self, user: User) -> bool:
        """
        Check if the current time is within the user's quiet hours.
        
        Args:
            user: The user to check.
        
        Returns:
            True if in quiet hours, False otherwise.
        """
        if not user.quiet_hours_start or not user.quiet_hours_end:
            return False
        
        try:
            # Parse quiet hours
            start_hour, start_minute = map(int, user.quiet_hours_start.split(":"))
            end_hour, end_minute = map(int, user.quiet_hours_end.split(":"))
            
            start_time = time(start_hour, start_minute)
            end_time = time(end_hour, end_minute)
            
            # Get current time
            now = datetime.now().time()
            
            # Check if current time is in quiet hours
            if start_time <= end_time:
                # Simple case: quiet hours within the same day
                return start_time <= now <= end_time
            else:
                # Complex case: quiet hours span midnight
                return now >= start_time or now <= end_time
                
        except (ValueError, AttributeError):
            # If there's an error parsing the quiet hours, assume not in quiet hours
            return False


# Global notification service instance
notification_service = NotificationService()
