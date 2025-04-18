"""
Insights and analytics methods for Facebook Marketing API.
"""
from typing import Dict, List, Optional

from config.settings import DATE_PRESETS
from src.storage.database import get_session
from src.storage.models import Cache
from src.utils.logger import get_logger
from src.api.facebook.exceptions import FacebookAdsApiError

logger = get_logger(__name__)


class InsightsMixin:
    """
    Mixin class for insights and analytics-related methods.
    To be used with FacebookAdsClient.
    """
    
    async def get_insights(self, object_id: str, date_preset: str = 'last_7d',
                         fields: Optional[List[str]] = None, 
                         level: str = 'campaign') -> List[Dict]:
        """
        Get insights (statistics) for an object.
        
        Args:
            object_id: The object ID (ad account, campaign, ad set, or ad).
            date_preset: The date range preset.
            fields: List of insight fields to return.
            level: The level of insight data (account, campaign, adset, ad).
            
        Returns:
            List of insights.
        """
        # Map our internal date preset keys to Facebook's values
        facebook_date_preset = DATE_PRESETS.get(date_preset)
        if not facebook_date_preset:
            logger.warning(f"Invalid date preset '{date_preset}', defaulting to 'last_7_days'")
            date_preset = 'last_7d'
            facebook_date_preset = DATE_PRESETS.get(date_preset)
            
        if not fields:
            # Расширенный набор полей для получения подробной информации о кастомных конверсиях
            fields = [
                'impressions', 'clicks', 'reach', 'spend', 'cpm', 'cpc', 'ctr',
                'actions', 'conversions', 'cost_per_action_type', 'cost_per_conversion',
                'conversion_values', 'action_values', 'purchase_roas',
                'cost_per_inline_link_click', 'cost_per_unique_click', 
                'cost_per_15_sec_video_view', 'unique_actions',
                'video_p25_watched_actions', 'video_p50_watched_actions', 
                'video_p75_watched_actions', 'video_p100_watched_actions'
            ]
            
        cache_key = f"insights:{self.user_id}:{object_id}:{date_preset}:{level}"
        
        # Try to get from cache first
        session = get_session()
        try:
            cached_data = Cache.get(session, cache_key)
            if cached_data:
                return cached_data
                
            # If not in cache, fetch from API
            params = {
                'fields': ','.join(fields),
                'level': level,
                'date_preset': facebook_date_preset,  # Use the mapped value
                'time_increment': 'all_days'  # Получать агрегированные данные без разделения по дням
            }
            
            print(f"DEBUG: Insights request params: {params}")
            
            data = await self._make_request(f"{object_id}/insights", params)
            
            insights = data.get('data', [])
            
            # Проверяем, есть ли кастомные конверсии, и если да, запрашиваем информацию о них
            has_custom_conversions = False
            for insight in insights:
                if 'conversions' in insight:
                    for conv in insight.get('conversions', []):
                        if 'action_type' in conv and conv['action_type'].startswith('offsite_conversion.fb_pixel_custom.'):
                            has_custom_conversions = True
                            break
                
                if has_custom_conversions:
                    break
            
            # Cache the result for 10 minutes (insights change frequently)
            Cache.set(session, cache_key, insights, 600)
            
            return insights
        except Exception as e:
            logger.error(f"Error getting insights for {object_id}: {str(e)}")
            if isinstance(e, FacebookAdsApiError):
                logger.error(f"Facebook API Error Code: {e.code}")
            raise
        finally:
            session.close()
            
    async def get_account_insights(self, account_id: str, date_preset: str = 'last_7d') -> List[Dict]:
        """
        Get insights for an ad account.
        
        Args:
            account_id: The ad account ID.
            date_preset: The date range preset.
            
        Returns:
            Account insights.
        """
        return await self.get_insights(account_id, date_preset, level='account')
        
    async def get_campaign_insights(self, campaign_id: str, date_preset: str = 'last_7d') -> List[Dict]:
        """
        Get insights for a campaign.
        
        Args:
            campaign_id: The campaign ID.
            date_preset: The date range preset.
            
        Returns:
            Campaign insights.
        """
        return await self.get_insights(campaign_id, date_preset, level='campaign')
        
    async def get_adset_insights(self, adset_id: str, date_preset: str = 'last_7d') -> List[Dict]:
        """
        Get insights for an ad set.
        
        Args:
            adset_id: The ad set ID.
            date_preset: The date range preset.
            
        Returns:
            Ad set insights.
        """
        return await self.get_insights(adset_id, date_preset, level='adset')
        
    async def get_ad_insights(self, ad_id: str, date_preset: str = 'last_7d') -> List[Dict]:
        """
        Get insights for an ad.
        
        Args:
            ad_id: The ad ID.
            date_preset: The date range preset.
            
        Returns:
            Ad insights.
        """
        return await self.get_insights(ad_id, date_preset, level='ad') 