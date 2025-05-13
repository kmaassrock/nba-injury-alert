"""
Logging configuration for the NBA Injury Alert system.
"""
import logging
import sys
from typing import Optional

from .config import settings


def setup_logger(name: str, level: Optional[int] = None) -> logging.Logger:
    """
    Set up a logger with the specified name and level.
    
    Args:
        name: The name of the logger.
        level: The logging level. If None, uses DEBUG for development and INFO for production.
    
    Returns:
        A configured logger instance.
    """
    if level is None:
        level = logging.DEBUG if settings.debug else logging.INFO
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Remove existing handlers to avoid duplicates
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(console_handler)
    
    return logger


# Create default logger for the application
logger = setup_logger("nba_injury_alert")
