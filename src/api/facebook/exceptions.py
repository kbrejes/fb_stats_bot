"""
Exception classes for Facebook API client.
"""
from typing import Dict, Optional, Any

from src.utils.error_handlers import FacebookAPIError


class FacebookAdsApiError(FacebookAPIError):
    """
    Exception raised for Facebook API errors.
    
    Extends the core FacebookAPIError class from the error_handlers module
    but maintains backward compatibility with existing error handling code.
    """
    def __init__(
        self, 
        message: str, 
        code: Optional[str] = None, 
        data: Optional[Dict] = None, 
        http_code: Optional[int] = None,
        fb_error_code: Optional[int] = None,
        fb_error_subcode: Optional[int] = None
    ):
        # Store original properties for backward compatibility
        self.message = message
        self.code = code
        self.data = data or {}
        
        # Initialize parent class with appropriate values
        super().__init__(
            message=message,
            error_code=code,
            details=data
        )
        
        # Set Facebook specific properties
        self.fb_error_code = fb_error_code
        self.fb_error_subcode = fb_error_subcode
        self.http_code = http_code


# Common Facebook API error codes
class TokenExpiredError(FacebookAdsApiError):
    """Raised when the access token has expired."""
    def __init__(self, message: str = "Access token has expired", data: Optional[Dict] = None):
        super().__init__(
            message=message,
            code="TOKEN_EXPIRED",
            data=data
        )


class InsufficientPermissionsError(FacebookAdsApiError):
    """Raised when the access token doesn't have required permissions."""
    def __init__(self, message: str = "Insufficient permissions", data: Optional[Dict] = None):
        super().__init__(
            message=message,
            code="INSUFFICIENT_PERMISSIONS",
            data=data
        )


class RateLimitError(FacebookAdsApiError):
    """Raised when API rate limit is exceeded."""
    def __init__(self, message: str = "Rate limit exceeded", data: Optional[Dict] = None):
        super().__init__(
            message=message,
            code="RATE_LIMIT",
            data=data
        )


class TokenNotSetError(FacebookAdsApiError):
    """Raised when no token is available."""
    def __init__(self, message: str = "Facebook token is not set", data: Optional[Dict] = None):
        super().__init__(
            message=message,
            code="TOKEN_NOT_SET",
            data=data
        )


class NetworkError(FacebookAdsApiError):
    """Raised when a network error occurs."""
    def __init__(self, message: str = "Network error occurred", data: Optional[Dict] = None):
        super().__init__(
            message=message,
            code="NETWORK_ERROR",
            data=data
        ) 