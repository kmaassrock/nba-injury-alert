"""
Error handling utilities for the NBA Injury Alert system.
"""
from typing import Any, Dict, List, Optional, Union

from .logging import logger


class BaseAppError(Exception):
    """Base exception class for application errors."""
    
    def __init__(
        self, 
        message: str, 
        status_code: int = 500, 
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the exception.
        
        Args:
            message: Error message.
            status_code: HTTP status code.
            details: Additional error details.
        """
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)
        
        # Log the error
        logger.error(
            f"Error {self.__class__.__name__} ({status_code}): {message}",
            extra={"details": self.details}
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the error to a dictionary representation."""
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "status_code": self.status_code,
            "details": self.details
        }


class FetcherError(BaseAppError):
    """Error raised during data fetching operations."""
    
    def __init__(
        self, 
        message: str, 
        status_code: int = 500, 
        details: Optional[Dict[str, Any]] = None,
        retry_after: Optional[int] = None
    ):
        """
        Initialize the exception.
        
        Args:
            message: Error message.
            status_code: HTTP status code.
            details: Additional error details.
            retry_after: Seconds to wait before retrying.
        """
        self.retry_after = retry_after
        details = details or {}
        if retry_after is not None:
            details["retry_after"] = retry_after
        super().__init__(message, status_code, details)


class ProcessorError(BaseAppError):
    """Error raised during data processing operations."""
    pass


class NotifierError(BaseAppError):
    """Error raised during notification operations."""
    pass


class DatabaseError(BaseAppError):
    """Error raised during database operations."""
    pass


class ValidationError(BaseAppError):
    """Error raised during data validation."""
    
    def __init__(
        self, 
        message: str, 
        field_errors: Optional[Dict[str, List[str]]] = None,
        status_code: int = 400
    ):
        """
        Initialize the exception.
        
        Args:
            message: Error message.
            field_errors: Dictionary mapping field names to error messages.
            status_code: HTTP status code.
        """
        details = {"field_errors": field_errors or {}}
        super().__init__(message, status_code, details)


class AuthenticationError(BaseAppError):
    """Error raised during authentication."""
    
    def __init__(
        self, 
        message: str = "Authentication failed", 
        status_code: int = 401,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the exception.
        
        Args:
            message: Error message.
            status_code: HTTP status code.
            details: Additional error details.
        """
        super().__init__(message, status_code, details)


class AuthorizationError(BaseAppError):
    """Error raised during authorization."""
    
    def __init__(
        self, 
        message: str = "Not authorized", 
        status_code: int = 403,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the exception.
        
        Args:
            message: Error message.
            status_code: HTTP status code.
            details: Additional error details.
        """
        super().__init__(message, status_code, details)


class ResourceNotFoundError(BaseAppError):
    """Error raised when a resource is not found."""
    
    def __init__(
        self, 
        message: str = "Resource not found", 
        resource_type: Optional[str] = None,
        resource_id: Optional[Union[str, int]] = None,
        status_code: int = 404
    ):
        """
        Initialize the exception.
        
        Args:
            message: Error message.
            resource_type: Type of resource that was not found.
            resource_id: ID of resource that was not found.
            status_code: HTTP status code.
        """
        details = {}
        if resource_type:
            details["resource_type"] = resource_type
        if resource_id:
            details["resource_id"] = resource_id
        super().__init__(message, status_code, details)
