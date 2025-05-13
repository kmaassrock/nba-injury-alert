"""
Base fetcher classes for the NBA Injury Alert system.
"""
import hashlib
import json
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import httpx

from ..utils.config import settings
from ..utils.errors import FetcherError
from ..utils.logging import logger, setup_logger

# Create a logger for the fetcher module
fetcher_logger = setup_logger("nba_injury_alert.fetcher")


class BaseFetcher(ABC):
    """Base class for data fetchers."""
    
    def __init__(self, timeout: Optional[float] = None, max_retries: Optional[int] = None):
        """
        Initialize the fetcher.
        
        Args:
            timeout: Request timeout in seconds.
            max_retries: Maximum number of retries for failed requests.
        """
        self.timeout = timeout or settings.fetcher.timeout_seconds
        self.max_retries = max_retries or settings.fetcher.max_retries
        self.logger = fetcher_logger
    
    @abstractmethod
    async def fetch(self) -> Dict[str, Any]:
        """
        Fetch data from the source.
        
        Returns:
            The fetched data.
        
        Raises:
            FetcherError: If the fetch operation fails.
        """
        pass
    
    @staticmethod
    def generate_hash(data: Union[str, Dict[str, Any], List[Any]]) -> str:
        """
        Generate a hash for the given data.
        
        Args:
            data: The data to hash.
        
        Returns:
            The hash as a hexadecimal string.
        """
        if isinstance(data, (dict, list)):
            data = json.dumps(data, sort_keys=True)
        
        return hashlib.sha256(data.encode("utf-8")).hexdigest()


class HttpFetcher(BaseFetcher):
    """Base class for HTTP-based fetchers."""
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None
    ):
        """
        Initialize the HTTP fetcher.
        
        Args:
            base_url: Base URL for API requests.
            headers: HTTP headers to include in requests.
            timeout: Request timeout in seconds.
            max_retries: Maximum number of retries for failed requests.
        """
        super().__init__(timeout=timeout, max_retries=max_retries)
        self.base_url = base_url
        self.headers = headers or {}
    
    async def _make_request(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        retry_count: int = 0
    ) -> httpx.Response:
        """
        Make an HTTP request.
        
        Args:
            method: HTTP method (GET, POST, etc.).
            url: URL to request.
            params: Query parameters.
            data: Form data.
            json_data: JSON data.
            headers: HTTP headers.
            retry_count: Current retry count.
        
        Returns:
            The HTTP response.
        
        Raises:
            FetcherError: If the request fails after all retries.
        """
        if not url.startswith(("http://", "https://")):
            if not self.base_url:
                raise FetcherError("No base URL provided for relative URL")
            url = f"{self.base_url.rstrip('/')}/{url.lstrip('/')}"
        
        merged_headers = {**self.headers, **(headers or {})}
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    params=params,
                    data=data,
                    json=json_data,
                    headers=merged_headers
                )
                
                # Check for rate limiting
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", "60"))
                    self.logger.warning(f"Rate limited. Retry after {retry_after} seconds.")
                    raise FetcherError(
                        "Rate limited by the API",
                        status_code=429,
                        retry_after=retry_after
                    )
                
                # Check for other error status codes
                if response.status_code >= 400:
                    self.logger.error(f"HTTP error: {response.status_code} - {response.text}")
                    if retry_count < self.max_retries:
                        retry_count += 1
                        self.logger.info(f"Retrying request ({retry_count}/{self.max_retries})...")
                        return await self._make_request(
                            method, url, params, data, json_data, headers, retry_count
                        )
                    
                    raise FetcherError(
                        f"HTTP error: {response.status_code}",
                        status_code=response.status_code,
                        details={"response": response.text}
                    )
                
                return response
                
        except httpx.TimeoutException:
            self.logger.error(f"Request timed out: {url}")
            if retry_count < self.max_retries:
                retry_count += 1
                self.logger.info(f"Retrying request ({retry_count}/{self.max_retries})...")
                return await self._make_request(
                    method, url, params, data, json_data, headers, retry_count
                )
            
            raise FetcherError("Request timed out after retries")
            
        except httpx.RequestError as e:
            self.logger.error(f"Request error: {str(e)}")
            if retry_count < self.max_retries:
                retry_count += 1
                self.logger.info(f"Retrying request ({retry_count}/{self.max_retries})...")
                return await self._make_request(
                    method, url, params, data, json_data, headers, retry_count
                )
            
            raise FetcherError(f"Request error: {str(e)}")
