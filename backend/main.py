"""
Main entry point for the NBA Injury Alert system.
"""
import os
import sys
import uvicorn

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.api import app
from backend.utils.config import settings
from backend.utils.logging import logger


def main():
    """Run the NBA Injury Alert API server."""
    logger.info(f"Starting NBA Injury Alert API on {settings.api.host}:{settings.api.port}")
    
    uvicorn.run(
        "backend.api:app",
        host=settings.api.host,
        port=settings.api.port,
        reload=settings.debug,
        log_level="info" if settings.debug else "error"
    )


if __name__ == "__main__":
    main()
