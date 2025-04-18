"""
Ad-related methods for Facebook Marketing API.
"""
from typing import Dict, List

from src.storage.database import get_session
from src.storage.models import Cache
from src.utils.logger import get_logger
from src.api.facebook.exceptions import FacebookAdsApiError

logger = get_logger(__name__)


class AdMixin:
    """
    Mixin class for ad-related methods.
    To be used with FacebookAdsClient.
    """
    
    async def get_ads(self, campaign_id: str, limit: int = 100) -> List[Dict]:
        """
        Get ads for a campaign.
        
        Args:
            campaign_id: The campaign ID.
            limit: Maximum number of ads to return.
            
        Returns:
            List of ads.
        """
        cache_key = f"ads:{self.user_id}:{campaign_id}"
        
        # Try to get from cache first
        session = get_session()
        try:
            cached_data = Cache.get(session, cache_key)
            if cached_data:
                return cached_data
                
            # If not in cache, fetch from API
            fields = 'id,name,status,adset_id,creative{id,name,thumbnail_url},preview_shareable_link'
            data = await self._make_request(f"{campaign_id}/ads", {
                'fields': fields,
                'limit': limit
            })
            
            ads = data.get('data', [])
            
            # Process and cache the result for 30 minutes
            processed_ads = []
            for ad in ads:
                creative = ad.get('creative', {})
                processed_ads.append({
                    'id': ad.get('id'),
                    'name': ad.get('name'),
                    'status': ad.get('status'),
                    'adset_id': ad.get('adset_id'),
                    'creative_id': creative.get('id') if creative else None,
                    'creative_name': creative.get('name') if creative else None,
                    'thumbnail_url': creative.get('thumbnail_url') if creative else None,
                    'preview_link': ad.get('preview_shareable_link')
                })
            
            Cache.set(session, cache_key, processed_ads, 1800)
            
            return processed_ads
        finally:
            session.close() 