"""
User models for the NBA Injury Alert system.
"""
from typing import List, Optional, Set

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Table
from sqlalchemy.orm import relationship

from .base import BaseModel


# Association table for user-team favorites
user_team_favorites = Table(
    "user_team_favorites",
    BaseModel.metadata,
    Column("user_id", Integer, ForeignKey("user.id"), primary_key=True),
    Column("team_id", Integer, ForeignKey("team.id"), primary_key=True)
)

# Association table for user-player favorites
user_player_favorites = Table(
    "user_player_favorites",
    BaseModel.metadata,
    Column("user_id", Integer, ForeignKey("user.id"), primary_key=True),
    Column("player_id", Integer, ForeignKey("player.id"), primary_key=True)
)


class User(BaseModel):
    """User model."""
    
    # User information
    email = Column(String, nullable=False, unique=True, index=True)
    username = Column(String, nullable=True, unique=True, index=True)
    hashed_password = Column(String, nullable=True)
    
    # OAuth information
    oauth_provider = Column(String, nullable=True)
    oauth_id = Column(String, nullable=True, index=True)
    
    # Account status
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    
    # Notification preferences
    email_notifications = Column(Boolean, default=True, nullable=False)
    push_notifications = Column(Boolean, default=False, nullable=False)
    web_notifications = Column(Boolean, default=True, nullable=False)
    
    # Quiet hours (stored as 24-hour format strings, e.g., "22:00")
    quiet_hours_start = Column(String, nullable=True)
    quiet_hours_end = Column(String, nullable=True)
    
    # Relationships
    favorite_teams = relationship("Team", secondary=user_team_favorites, back_populates="users")
    favorite_players = relationship("Player", secondary=user_player_favorites, back_populates="users")
    notification_settings = relationship("NotificationSetting", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        """String representation of the user."""
        return f"<User(id={self.id}, email='{self.email}')>"


class NotificationSetting(BaseModel):
    """User notification settings for specific players or teams."""
    
    # User relationship
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False, index=True)
    user = relationship("User", back_populates="notification_settings")
    
    # What this setting applies to
    player_id = Column(Integer, ForeignKey("player.id"), nullable=True, index=True)
    team = Column(String, nullable=True, index=True)
    
    # Notification channels
    email_enabled = Column(Boolean, default=True, nullable=False)
    push_enabled = Column(Boolean, default=True, nullable=False)
    web_enabled = Column(Boolean, default=True, nullable=False)
    
    # Minimum importance to trigger notification (1-5, where 1 is most important)
    min_importance = Column(Integer, default=3, nullable=False)
    
    def __repr__(self) -> str:
        """String representation of the notification setting."""
        target = f"player_id={self.player_id}" if self.player_id else f"team='{self.team}'"
        return f"<NotificationSetting(id={self.id}, user_id={self.user_id}, {target})>"


class Team(BaseModel):
    """NBA team model."""
    
    # Team information
    name = Column(String, nullable=False, unique=True, index=True)
    abbreviation = Column(String, nullable=False, unique=True, index=True)
    city = Column(String, nullable=False)
    conference = Column(String, nullable=False, index=True)
    division = Column(String, nullable=False, index=True)
    
    # Relationships
    users = relationship("User", secondary=user_team_favorites, back_populates="favorite_teams")
    
    def __repr__(self) -> str:
        """String representation of the team."""
        return f"<Team(id={self.id}, name='{self.name}', abbreviation='{self.abbreviation}')>"
