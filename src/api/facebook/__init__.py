"""
Facebook Marketing API client modules.
"""
from typing import Type, Union, Protocol

from src.api.facebook.exceptions import (
    FacebookAdsApiError,
    TokenExpiredError, 
    TokenNotSetError,
    InsufficientPermissionsError,
    RateLimitError,
    NetworkError
)
from src.api.facebook.client import FacebookAdsClient as BaseClient
from src.api.facebook.account import AccountMixin
from src.api.facebook.campaign import CampaignMixin
from src.api.facebook.adset import AdSetMixin
from src.api.facebook.ad import AdMixin
from src.api.facebook.insights import InsightsMixin
from src.api.interfaces import (
    FacebookAdsClientInterface,
    AccountServiceInterface,
    CampaignServiceInterface,
    AdServiceInterface,
    InsightServiceInterface
)


# Create combined client class with all mixins
class FacebookAdsClient(BaseClient, AccountMixin, CampaignMixin, AdSetMixin, AdMixin, InsightsMixin):
    """
    Complete Facebook Marketing API client that combines all functionality.
    
    This class implements:
    - FacebookAdsClientInterface: Core API functionality
    - AccountServiceInterface: Account-related operations
    - CampaignServiceInterface: Campaign-related operations
    - AdServiceInterface: Ad-related operations
    - InsightServiceInterface: Insights-related operations
    """
    pass


# Define a custom Protocol that combines all interfaces
class CombinedClientInterface(FacebookAdsClientInterface, AccountServiceInterface, 
                            CampaignServiceInterface, AdServiceInterface, 
                            InsightServiceInterface, Protocol):
    """Interface that combines all specific interfaces for the Facebook Ads API client."""
    pass


# Export classes for backward compatibility
__all__ = [
    'FacebookAdsClient',
    'FacebookAdsApiError',
    'TokenExpiredError',
    'TokenNotSetError',
    'InsufficientPermissionsError',
    'RateLimitError',
    'NetworkError',
    'CombinedClientInterface'
] 