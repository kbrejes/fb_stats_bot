"""
Facebook Marketing API client modules.
"""
from src.api.facebook.exceptions import FacebookAdsApiError
from src.api.facebook.client import FacebookAdsClient as BaseClient
from src.api.facebook.account import AccountMixin
from src.api.facebook.campaign import CampaignMixin
from src.api.facebook.adset import AdSetMixin
from src.api.facebook.ad import AdMixin
from src.api.facebook.insights import InsightsMixin


# Create combined client class with all mixins
class FacebookAdsClient(BaseClient, AccountMixin, CampaignMixin, AdSetMixin, AdMixin, InsightsMixin):
    """
    Complete Facebook Marketing API client that combines all functionality.
    """
    pass


# Export classes for backward compatibility
__all__ = [
    'FacebookAdsClient',
    'FacebookAdsApiError',
] 