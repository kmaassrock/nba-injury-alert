"""
Injury models for the NBA Injury Alert system.
"""
from typing import List, Optional

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from .base import BaseModel


class InjuryReport(BaseModel):
    """NBA injury report snapshot model."""
    
    # Report metadata
    report_date = Column(DateTime, nullable=False, index=True)
    source_url = Column(String, nullable=True)
    report_hash = Column(String, nullable=False, unique=True, index=True)
    
    # Raw report data
    raw_content = Column(Text, nullable=False)
    
    # Relationships
    statuses = relationship("InjuryStatus", back_populates="report", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        """String representation of the injury report."""
        return f"<InjuryReport(id={self.id}, report_date='{self.report_date}')>"


class InjuryStatus(BaseModel):
    """Player injury status model."""
    
    # Status information
    status = Column(String, nullable=False, index=True)
    reason = Column(String, nullable=True)
    details = Column(Text, nullable=True)
    
    # Game information
    game_date = Column(DateTime, nullable=True, index=True)
    opponent = Column(String, nullable=True)
    
    # Foreign keys
    player_id = Column(Integer, ForeignKey("player.id"), nullable=False, index=True)
    report_id = Column(Integer, ForeignKey("injury_report.id"), nullable=False, index=True)
    
    # Relationships
    player = relationship("Player", back_populates="injury_statuses")
    report = relationship("InjuryReport", back_populates="statuses")
    
    # Status change tracking
    is_status_change = Column(Boolean, default=False, nullable=False, index=True)
    previous_status = Column(String, nullable=True)
    
    def __repr__(self) -> str:
        """String representation of the injury status."""
        return f"<InjuryStatus(id={self.id}, player_id={self.player_id}, status='{self.status}')>"


class StatusChange(BaseModel):
    """Record of player status changes."""
    
    # Change information
    player_id = Column(Integer, ForeignKey("player.id"), nullable=False, index=True)
    old_status = Column(String, nullable=True)
    new_status = Column(String, nullable=False)
    change_date = Column(DateTime, nullable=False, index=True)
    
    # Report information
    report_id = Column(Integer, ForeignKey("injury_report.id"), nullable=False)
    
    # Notification tracking
    notification_sent = Column(Boolean, default=False, nullable=False)
    notification_date = Column(DateTime, nullable=True)
    
    # Relationships
    player = relationship("Player")
    report = relationship("InjuryReport")
    
    def __repr__(self) -> str:
        """String representation of the status change."""
        return (
            f"<StatusChange(id={self.id}, player_id={self.player_id}, "
            f"old_status='{self.old_status}', new_status='{self.new_status}')>"
        )
