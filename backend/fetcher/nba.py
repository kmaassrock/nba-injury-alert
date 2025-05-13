"""
NBA-specific fetcher for injury reports.
"""
import asyncio
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union

from ..models.database import db_session
from ..models.injury import InjuryReport
from ..utils.config import settings
from ..utils.errors import FetcherError
from .base import HttpFetcher


class NBAInjuryFetcher(HttpFetcher):
    """Fetcher for NBA injury reports."""
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None
    ):
        """
        Initialize the NBA injury fetcher.
        
        Args:
            base_url: Base URL for the NBA API.
            headers: HTTP headers to include in requests.
            timeout: Request timeout in seconds.
            max_retries: Maximum number of retries for failed requests.
        """
        base_url = base_url or settings.fetcher.nba_api_base_url
        
        # Set default headers to mimic a browser request
        default_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.nba.com/",
            "Origin": "https://www.nba.com"
        }
        
        headers = {**default_headers, **(headers or {})}
        
        super().__init__(
            base_url=base_url,
            headers=headers,
            timeout=timeout,
            max_retries=max_retries
        )
    
    async def fetch(self) -> Dict[str, Any]:
        """
        Fetch the latest NBA injury report.
        
        Returns:
            The injury report data.
        
        Raises:
            FetcherError: If the fetch operation fails.
        """
        self.logger.info("Fetching NBA injury report...")
        
        try:
            response = await self._make_request(
                method="GET",
                url=settings.fetcher.injury_report_endpoint
            )
            
            data = response.json()
            
            # Generate a hash for the report
            report_hash = self.generate_hash(data)
            
            # Check if this report already exists in the database
            with db_session() as session:
                existing_report = session.query(InjuryReport).filter_by(report_hash=report_hash).first()
                
                if existing_report:
                    self.logger.info(f"Report with hash {report_hash} already exists in the database.")
                    return {"data": data, "hash": report_hash, "is_new": False}
            
            # Store the report in the database
            report_date = datetime.now()
            report = InjuryReport(
                report_date=report_date,
                source_url=f"{self.base_url}{settings.fetcher.injury_report_endpoint}",
                report_hash=report_hash,
                raw_content=json.dumps(data)
            )
            
            with db_session() as session:
                session.add(report)
                session.commit()
                self.logger.info(f"Stored new injury report with ID {report.id} and hash {report_hash}.")
            
            return {"data": data, "hash": report_hash, "is_new": True, "report_id": report.id}
            
        except Exception as e:
            self.logger.error(f"Error fetching NBA injury report: {str(e)}")
            raise FetcherError(f"Failed to fetch NBA injury report: {str(e)}")


class NBAInjuryPoller:
    """Poller for NBA injury reports."""
    
    def __init__(
        self,
        poll_interval: Optional[float] = None,
        fetcher: Optional[NBAInjuryFetcher] = None
    ):
        """
        Initialize the NBA injury poller.
        
        Args:
            poll_interval: Interval between poll attempts in seconds.
            fetcher: NBA injury fetcher instance.
        """
        self.poll_interval = poll_interval or settings.fetcher.poll_interval_seconds
        self.fetcher = fetcher or NBAInjuryFetcher()
        self.logger = self.fetcher.logger
        self._running = False
        self._last_report_time = None
    
    async def poll_once(self) -> Dict[str, Any]:
        """
        Poll for the latest NBA injury report once.
        
        Returns:
            The injury report data.
        """
        return await self.fetcher.fetch()
    
    async def start_polling(self, callback=None) -> None:
        """
        Start polling for NBA injury reports.
        
        Args:
            callback: Function to call with new reports.
        """
        self._running = True
        self.logger.info(f"Starting NBA injury report polling with interval {self.poll_interval} seconds...")
        
        while self._running:
            try:
                result = await self.poll_once()
                
                if result.get("is_new", False) and callback:
                    await callback(result)
                
                self._last_report_time = datetime.now()
                
            except FetcherError as e:
                self.logger.error(f"Error during polling: {str(e)}")
                
                # If rate limited, wait for the specified time
                if hasattr(e, "retry_after") and e.retry_after:
                    self.logger.info(f"Rate limited. Waiting for {e.retry_after} seconds...")
                    await asyncio.sleep(e.retry_after)
                    continue
            
            # Wait for the next poll interval
            await asyncio.sleep(self.poll_interval)
    
    def stop_polling(self) -> None:
        """Stop polling for NBA injury reports."""
        self._running = False
        self.logger.info("Stopped NBA injury report polling.")


async def poll_for_new_report(hour: int = None, minute: int = 30) -> Dict[str, Any]:
    """
    Poll for a new NBA injury report at the specified time.
    
    Args:
        hour: Hour to start polling (None for current hour).
        minute: Minute to start polling.
    
    Returns:
        The new injury report data.
    """
    fetcher = NBAInjuryFetcher()
    poller = NBAInjuryPoller(fetcher=fetcher)
    
    # Determine the target time
    now = datetime.now()
    if hour is None:
        target_time = now.replace(minute=minute, second=0, microsecond=0)
    else:
        target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    
    # If the target time is in the past, move to the next hour
    if target_time < now:
        target_time += timedelta(hours=1)
    
    # Wait until the target time
    wait_seconds = (target_time - now).total_seconds()
    if wait_seconds > 0:
        fetcher.logger.info(f"Waiting until {target_time.strftime('%H:%M:%S')} to start polling...")
        await asyncio.sleep(wait_seconds)
    
    # Poll until a new report is found
    fetcher.logger.info("Starting to poll for new injury report...")
    while True:
        try:
            result = await poller.poll_once()
            if result.get("is_new", False):
                fetcher.logger.info("Found new injury report!")
                return result
        except Exception as e:
            fetcher.logger.error(f"Error polling for new report: {str(e)}")
        
        # Wait before the next poll
        await asyncio.sleep(poller.poll_interval)
