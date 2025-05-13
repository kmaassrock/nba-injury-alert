"""
Main FastAPI application for the NBA Injury Alert system.
"""
import asyncio
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from ..models.database import get_db, init_db
from ..notifier.channels import WebSocketNotifier
from ..utils.config import settings
from ..utils.logging import logger

# Create the FastAPI application
app = FastAPI(
    title="NBA Injury Alert API",
    description="API for the NBA Injury Alert system",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create WebSocket notifier
websocket_notifier = WebSocketNotifier()


@app.on_event("startup")
async def startup_event():
    """Initialize the application on startup."""
    logger.info("Starting NBA Injury Alert API")
    
    # Initialize the database
    init_db()
    
    # Start background tasks
    asyncio.create_task(background_tasks())


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown."""
    logger.info("Shutting down NBA Injury Alert API")


async def background_tasks():
    """Run background tasks."""
    logger.info("Starting background tasks")
    
    # Import here to avoid circular imports
    from ..fetcher.nba import NBAInjuryPoller
    from ..processor.injury import InjuryReportProcessor
    from ..notifier.service import notification_service
    
    # Create fetcher, processor, and poller
    processor = InjuryReportProcessor()
    poller = NBAInjuryPoller()
    
    # Define callback for new reports
    async def on_new_report(report_data):
        try:
            # Process the report
            processed = await processor.process(report_data)
            
            # Get the previous report for comparison
            with get_db() as db:
                from ..models.injury import InjuryReport
                previous_report = db.query(InjuryReport).order_by(
                    InjuryReport.report_date.desc()
                ).offset(1).first()
                
                if previous_report:
                    # Get the previous processed data
                    previous_data = {
                        "report_id": previous_report.id,
                        "player_statuses": []  # This would need to be populated from the database
                    }
                    
                    # Compute the diff
                    diff = await processor.compute_diff(processed, previous_data)
                    
                    # Send notifications for changes
                    if diff.get("changes"):
                        await notification_service.process_status_changes(diff["changes"])
        
        except Exception as e:
            logger.error(f"Error processing new report: {str(e)}")
    
    # Start polling for injury reports
    await poller.start_polling(callback=on_new_report)


@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """
    WebSocket endpoint for real-time notifications.
    
    Args:
        websocket: The WebSocket connection.
        client_id: The client identifier.
    """
    await websocket_notifier.connect(websocket, client_id)
    try:
        while True:
            # Wait for messages from the client
            data = await websocket.receive_text()
            # Echo the message back (for testing)
            await websocket.send_text(f"Message received: {data}")
    except WebSocketDisconnect:
        websocket_notifier.disconnect(client_id)


# Import and include API routers
from .routers import injuries, players, users

app.include_router(injuries.router, prefix="/api/injuries", tags=["injuries"])
app.include_router(players.router, prefix="/api/players", tags=["players"])
app.include_router(users.router, prefix="/api/users", tags=["users"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Welcome to the NBA Injury Alert API"}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
