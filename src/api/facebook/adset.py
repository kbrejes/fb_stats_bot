"""
Ad Set-related methods for Facebook Marketing API.
"""
from typing import Dict, List

from src.storage.database import get_session
from src.storage.models import Cache
from src.utils.logger import get_logger
from src.api.facebook.exceptions import FacebookAdsApiError

logger = get_logger(__name__)


class AdSetMixin:
    """
    Mixin class for ad set-related methods.
    To be used with FacebookAdsClient.
    """
    
    async def get_adsets(self, campaign_id: str, limit: int = 100) -> List[Dict]:
        """
        Get ad sets for a campaign.
        
        Args:
            campaign_id: The campaign ID.
            limit: Maximum number of ad sets to return.
            
        Returns:
            List of ad sets.
        """
        cache_key = f"adsets:{self.user_id}:{campaign_id}"
        
        # Try to get from cache first
        session = get_session()
        try:
            cached_data = Cache.get(session, cache_key)
            if cached_data:
                return cached_data
                
            # If not in cache, fetch from API
            fields = 'id,name,status,targeting,optimization_goal,bid_amount,billing_event,daily_budget,lifetime_budget'
            data = await self._make_request(f"{campaign_id}/adsets", {
                'fields': fields,
                'limit': limit
            })
            
            adsets = data.get('data', [])
            
            # Process and cache the result for 30 minutes
            processed_adsets = [
                {
                    'id': adset.get('id'),
                    'name': adset.get('name'),
                    'status': adset.get('status'),
                    'optimization_goal': adset.get('optimization_goal'),
                    'bid_amount': adset.get('bid_amount'),
                    'billing_event': adset.get('billing_event'),
                    'daily_budget': adset.get('daily_budget'),
                    'lifetime_budget': adset.get('lifetime_budget')
                }
                for adset in adsets
            ]
            
            Cache.set(session, cache_key, processed_adsets, 1800)
            
            return processed_adsets
        finally:
            session.close() 