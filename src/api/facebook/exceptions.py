"""
Exception classes for Facebook API client.
"""
from typing import Dict, Optional


class FacebookAdsApiError(Exception):
    """Exception raised for Facebook API errors."""
    def __init__(self, message: str, code: Optional[str] = None, data: Optional[Dict] = None):
        self.message = message
        self.code = code
        self.data = data or {}
        super().__init__(self.message) 