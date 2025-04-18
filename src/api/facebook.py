"""
Facebook Marketing API client for backward compatibility.

This module exists to maintain backward compatibility with existing code.
All functionality has been moved to the facebook package.
"""
from src.api.facebook import FacebookAdsClient, FacebookAdsApiError

# Re-export for backward compatibility
__all__ = [
    'FacebookAdsClient',
    'FacebookAdsApiError',
] 