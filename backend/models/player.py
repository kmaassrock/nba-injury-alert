"""
Player models for the NBA Injury Alert system.
"""
from typing import List, Optional

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Table
from sqlalchemy.orm import relationship

from .base import BaseModel


class Player(BaseModel):
    """NBA player model."""
    
    # Basic player information
    name = Column(String, nullable=False, index=True)
    team = Column(String, nullable=False, index=True)
    position = Column(String, nullable=True)
    jersey_number = Column(String, nullable=True)
    
    # Player ranking information
    current_rank = Column(Integer, nullable=True, index=True)
    is_top_100 = Column(Boolean, default=False, nullable=False, index=True)
    
    # External identifiers
    nba_id = Column(String, nullable=True, unique=True, index=True)
    espn_id = Column(String, nullable=True, unique=True)
    
    # Relationships
    injury_statuses = relationship("InjuryStatus", back_populates="player", cascade="all, delete-orphan")
    users = relationship("User", secondary="user_player_favorites", back_populates="favorite_players")
    
    def __repr__(self) -> str:
        """String representation of the player."""
        return f"<Player(id={self.id}, name='{self.name}', team='{self.team}', rank={self.current_rank})>"


class PlayerRanking(BaseModel):
    """Player ranking snapshot model."""
    
    # Ranking information
    rank = Column(Integer, nullable=False, index=True)
    player_id = Column(Integer, ForeignKey("player.id"), nullable=False, index=True)
    source = Column(String, nullable=False, index=True)
    ranking_date = Column(String, nullable=False, index=True)
    
    # Relationships
    player = relationship("Player")
    
    def __repr__(self) -> str:
        """String representation of the player ranking."""
        return f"<PlayerRanking(id={self.id}, player_id={self.player_id}, rank={self.rank}, source='{self.source}')>"
