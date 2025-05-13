"""
Database connection and session management for the NBA Injury Alert system.
"""
import contextlib
from typing import Any, Callable, ContextManager, Iterator, Optional, TypeVar

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

from ..utils.config import settings
from ..utils.logging import logger

# Create database engine
engine = create_engine(
    settings.database.connection_string,
    echo=settings.debug,
    pool_pre_ping=True
)

# Create sessionmaker
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Type variable for database functions
T = TypeVar("T")


def get_db() -> Iterator[Session]:
    """
    Get a database session.
    
    Yields:
        A SQLAlchemy session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextlib.contextmanager
def db_session() -> ContextManager[Session]:
    """
    Context manager for database sessions.
    
    Yields:
        A SQLAlchemy session.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Database error: {str(e)}")
        raise
    finally:
        db.close()


def with_db_session(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator to provide a database session to a function.
    
    Args:
        func: The function to decorate.
    
    Returns:
        The decorated function.
    """
    def wrapper(*args: Any, **kwargs: Any) -> T:
        with db_session() as session:
            return func(*args, session=session, **kwargs)
    return wrapper


def init_db() -> None:
    """
    Initialize the database by creating all tables.
    """
    # Import all models to ensure they are registered with the Base metadata
    from .base import Base
    from .player import Player, PlayerRanking
    from .injury import InjuryReport, InjuryStatus, StatusChange
    from .user import User, NotificationSetting, Team
    
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully.")
