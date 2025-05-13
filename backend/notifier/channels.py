"""
Notification channel implementations for the NBA Injury Alert system.
"""
import asyncio
import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import aiosmtplib
from fastapi import WebSocket

from ..utils.config import settings
from ..utils.errors import NotifierError
from .base import BaseNotifier, NotificationFormatter


class EmailNotifier(BaseNotifier):
    """Email notification channel."""
    
    def __init__(
        self,
        smtp_server: Optional[str] = None,
        smtp_port: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        from_address: Optional[str] = None
    ):
        """
        Initialize the email notifier.
        
        Args:
            smtp_server: SMTP server address.
            smtp_port: SMTP server port.
            username: SMTP username.
            password: SMTP password.
            from_address: Sender email address.
        """
        super().__init__()
        self.smtp_server = smtp_server or settings.notification.email_smtp_server
        self.smtp_port = smtp_port or settings.notification.email_smtp_port
        self.username = username or settings.notification.email_smtp_username
        self.password = password or settings.notification.email_smtp_password
        self.from_address = from_address or settings.notification.email_from_address
    
    async def send_notification(
        self, 
        recipient: str, 
        subject: str, 
        message: str, 
        html_message: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Send an email notification.
        
        Args:
            recipient: Recipient email address.
            subject: Email subject.
            message: Plain text message.
            html_message: HTML message (optional).
            **kwargs: Additional parameters.
        
        Returns:
            Dictionary with the notification result.
        
        Raises:
            NotifierError: If the email fails to send.
        """
        self.logger.info(f"Sending email to {recipient}: {subject}")
        
        try:
            # Create message
            email_message = MIMEMultipart("alternative")
            email_message["Subject"] = subject
            email_message["From"] = self.from_address
            email_message["To"] = recipient
            
            # Attach plain text part
            email_message.attach(MIMEText(message, "plain"))
            
            # Attach HTML part if provided
            if html_message:
                email_message.attach(MIMEText(html_message, "html"))
            
            # Send the email
            await aiosmtplib.send(
                email_message,
                hostname=self.smtp_server,
                port=self.smtp_port,
                username=self.username,
                password=self.password,
                use_tls=True
            )
            
            self.logger.info(f"Email sent successfully to {recipient}")
            
            return {
                "success": True,
                "recipient": recipient,
                "subject": subject,
                "channel": "email"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to send email to {recipient}: {str(e)}")
            raise NotifierError(f"Failed to send email: {str(e)}")
    
    async def send_batch(
        self, 
        notifications: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Send a batch of email notifications.
        
        Args:
            notifications: List of notification dictionaries.
        
        Returns:
            List of notification results.
        
        Raises:
            NotifierError: If the batch operation fails.
        """
        self.logger.info(f"Sending batch of {len(notifications)} emails")
        
        results = []
        
        for notification in notifications:
            try:
                result = await self.send_notification(
                    recipient=notification["recipient"],
                    subject=notification["subject"],
                    message=notification["message"],
                    html_message=notification.get("html_message"),
                    **{k: v for k, v in notification.items() if k not in ["recipient", "subject", "message", "html_message"]}
                )
                results.append(result)
            except Exception as e:
                self.logger.error(f"Error sending email to {notification['recipient']}: {str(e)}")
                results.append({
                    "success": False,
                    "recipient": notification["recipient"],
                    "subject": notification["subject"],
                    "channel": "email",
                    "error": str(e)
                })
        
        return results


class WebSocketNotifier(BaseNotifier):
    """WebSocket notification channel."""
    
    def __init__(self):
        """Initialize the WebSocket notifier."""
        super().__init__()
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str) -> None:
        """
        Connect a WebSocket client.
        
        Args:
            websocket: The WebSocket connection.
            client_id: The client identifier.
        """
        await websocket.accept()
        self.active_connections[client_id] = websocket
        self.logger.info(f"WebSocket client {client_id} connected")
    
    def disconnect(self, client_id: str) -> None:
        """
        Disconnect a WebSocket client.
        
        Args:
            client_id: The client identifier.
        """
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            self.logger.info(f"WebSocket client {client_id} disconnected")
    
    async def send_notification(
        self, 
        recipient: str, 
        subject: str, 
        message: str, 
        data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Send a WebSocket notification.
        
        Args:
            recipient: Client ID to send to.
            subject: Notification subject.
            message: Notification message.
            data: Additional data to include.
            **kwargs: Additional parameters.
        
        Returns:
            Dictionary with the notification result.
        
        Raises:
            NotifierError: If the notification fails.
        """
        self.logger.info(f"Sending WebSocket notification to {recipient}: {subject}")
        
        if recipient not in self.active_connections:
            error_msg = f"WebSocket client {recipient} not connected"
            self.logger.error(error_msg)
            raise NotifierError(error_msg)
        
        try:
            notification_data = {
                "type": "notification",
                "subject": subject,
                "message": message
            }
            
            if data:
                notification_data["data"] = data
            
            await self.active_connections[recipient].send_json(notification_data)
            
            self.logger.info(f"WebSocket notification sent successfully to {recipient}")
            
            return {
                "success": True,
                "recipient": recipient,
                "subject": subject,
                "channel": "websocket"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to send WebSocket notification to {recipient}: {str(e)}")
            raise NotifierError(f"Failed to send WebSocket notification: {str(e)}")
    
    async def broadcast(
        self, 
        subject: str, 
        message: str, 
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Broadcast a notification to all connected clients.
        
        Args:
            subject: Notification subject.
            message: Notification message.
            data: Additional data to include.
        
        Returns:
            Dictionary with the broadcast result.
        """
        self.logger.info(f"Broadcasting WebSocket notification to {len(self.active_connections)} clients: {subject}")
        
        notification_data = {
            "type": "notification",
            "subject": subject,
            "message": message
        }
        
        if data:
            notification_data["data"] = data
        
        successful = 0
        failed = 0
        
        for client_id, websocket in list(self.active_connections.items()):
            try:
                await websocket.send_json(notification_data)
                successful += 1
            except Exception as e:
                self.logger.error(f"Failed to send to client {client_id}: {str(e)}")
                failed += 1
                # Remove the failed connection
                self.disconnect(client_id)
        
        self.logger.info(f"Broadcast complete: {successful} successful, {failed} failed")
        
        return {
            "success": True,
            "total_clients": len(self.active_connections) + failed,
            "successful": successful,
            "failed": failed,
            "subject": subject,
            "channel": "websocket"
        }
    
    async def send_batch(
        self, 
        notifications: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Send a batch of WebSocket notifications.
        
        Args:
            notifications: List of notification dictionaries.
        
        Returns:
            List of notification results.
        
        Raises:
            NotifierError: If the batch operation fails.
        """
        self.logger.info(f"Sending batch of {len(notifications)} WebSocket notifications")
        
        results = []
        
        for notification in notifications:
            try:
                result = await self.send_notification(
                    recipient=notification["recipient"],
                    subject=notification["subject"],
                    message=notification["message"],
                    data=notification.get("data"),
                    **{k: v for k, v in notification.items() if k not in ["recipient", "subject", "message", "data"]}
                )
                results.append(result)
            except Exception as e:
                self.logger.error(f"Error sending WebSocket notification to {notification['recipient']}: {str(e)}")
                results.append({
                    "success": False,
                    "recipient": notification["recipient"],
                    "subject": notification["subject"],
                    "channel": "websocket",
                    "error": str(e)
                })
        
        return results


class PushNotifier(BaseNotifier):
    """Push notification channel (placeholder implementation)."""
    
    async def send_notification(
        self, 
        recipient: str, 
        subject: str, 
        message: str, 
        **kwargs
    ) -> Dict[str, Any]:
        """
        Send a push notification.
        
        Args:
            recipient: Device token or user ID.
            subject: Notification title.
            message: Notification body.
            **kwargs: Additional parameters.
        
        Returns:
            Dictionary with the notification result.
        
        Raises:
            NotifierError: If the notification fails.
        """
        self.logger.info(f"Sending push notification to {recipient}: {subject}")
        
        # This is a placeholder implementation
        # In a real implementation, this would use a push notification service
        self.logger.info(f"Push notification would be sent to {recipient}")
        
        return {
            "success": True,
            "recipient": recipient,
            "subject": subject,
            "channel": "push"
        }
    
    async def send_batch(
        self, 
        notifications: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Send a batch of push notifications.
        
        Args:
            notifications: List of notification dictionaries.
        
        Returns:
            List of notification results.
        
        Raises:
            NotifierError: If the batch operation fails.
        """
        self.logger.info(f"Sending batch of {len(notifications)} push notifications")
        
        results = []
        
        for notification in notifications:
            try:
                result = await self.send_notification(
                    recipient=notification["recipient"],
                    subject=notification["subject"],
                    message=notification["message"],
                    **{k: v for k, v in notification.items() if k not in ["recipient", "subject", "message"]}
                )
                results.append(result)
            except Exception as e:
                self.logger.error(f"Error sending push notification to {notification['recipient']}: {str(e)}")
                results.append({
                    "success": False,
                    "recipient": notification["recipient"],
                    "subject": notification["subject"],
                    "channel": "push",
                    "error": str(e)
                })
        
        return results
