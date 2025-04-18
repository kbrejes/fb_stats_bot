"""
Campaign-related methods for Facebook Marketing API.
"""
import json
import asyncio
from typing import Dict, List

from src.storage.database import get_session
from src.storage.models import Cache
from src.utils.logger import get_logger
from src.api.facebook.exceptions import FacebookAdsApiError

logger = get_logger(__name__)


class CampaignMixin:
    """
    Mixin class for campaign-related methods.
    To be used with FacebookAdsClient.
    """
    
    async def get_campaigns(self, account_id: str, limit: int = 100) -> List[Dict]:
        """
        Get campaigns for an ad account.
        
        Args:
            account_id: The ad account ID.
            limit: Maximum number of campaigns to return.
            
        Returns:
            List of campaigns.
        """
        print(f"DEBUG: get_campaigns called for account {account_id}, user {self.user_id}")
        cache_key = f"campaigns:{self.user_id}:{account_id}"
        
        # Try to get from cache first
        session = get_session()
        try:
            print(f"DEBUG: Checking cache for campaigns")
            cached_data = Cache.get(session, cache_key)
            if cached_data:
                print(f"DEBUG: Found {len(cached_data)} campaigns in cache")
                return cached_data
                
            # If not in cache, fetch from API
            print(f"DEBUG: No cache found, fetching from API")
            fields = 'id,name,status,objective,start_time,stop_time,daily_budget,lifetime_budget,budget_remaining'
            print(f"DEBUG: Making API request for campaigns with fields: {fields}")
            
            max_retries = 2
            retry_count = 0
            campaign_result = []
            
            while retry_count <= max_retries:
                try:
                    # BUGFIX: Добавляем дополнительную обработку для account_id
                    # Убеждаемся, что account_id имеет правильный формат (act_XXXXXX)
                    if not account_id.startswith('act_'):
                        account_id = f"act_{account_id}"
                        print(f"DEBUG: Fixed account_id format to {account_id}")
                    
                    # BUGFIX: Попытка сделать запрос с явным указанием account_id и access_token
                    data = await self._make_request(f"{account_id}/campaigns", {
                        'fields': fields,
                        'limit': limit
                    })
                    
                    print(f"DEBUG: API request successful")
                    
                    # Проверяем, что у нас есть данные в ответе
                    if 'data' not in data:
                        print(f"DEBUG: No 'data' field in API response: {json.dumps(data)}")
                        if retry_count < max_retries:
                            retry_count += 1
                            await asyncio.sleep(1)
                            print(f"DEBUG: Retrying request ({retry_count}/{max_retries})")
                            continue
                        else:
                            # Если исчерпаны все попытки, возвращаем пустой список
                            print(f"DEBUG: No data found after {max_retries} retries")
                            return []
                    
                    campaigns = data.get('data', [])
                    break  # Успешно получены данные, выходим из цикла
                    
                except FacebookAdsApiError as e:
                    print(f"DEBUG: Facebook API error in get_campaigns: {e.message} (code: {e.code})")
                    
                    # Если ошибка связана с токеном, не пытаемся повторить
                    if e.code == "TOKEN_EXPIRED" or e.code == "TOKEN_NOT_SET" or e.code == "USER_NOT_FOUND":
                        raise
                    
                    # Для других ошибок можем попробовать еще раз
                    if retry_count < max_retries:
                        retry_count += 1
                        await asyncio.sleep(2)  # Немного подождем перед повторной попыткой
                        print(f"DEBUG: Retrying request ({retry_count}/{max_retries})")
                        continue
                    else:
                        raise  # Если исчерпаны все попытки, пробрасываем ошибку дальше
            
            print(f"DEBUG: Retrieved {len(campaigns)} campaigns from API")
            
            # Process and cache the result for 30 minutes
            processed_campaigns = [
                {
                    'id': campaign.get('id'),
                    'name': campaign.get('name'),
                    'status': campaign.get('status'),
                    'objective': campaign.get('objective'),
                    'start_time': campaign.get('start_time'),
                    'stop_time': campaign.get('stop_time'),
                    'daily_budget': campaign.get('daily_budget'),
                    'lifetime_budget': campaign.get('lifetime_budget'),
                    'budget_remaining': campaign.get('budget_remaining')
                }
                for campaign in campaigns
            ]
            
            print(f"DEBUG: Caching {len(processed_campaigns)} campaigns for 30 minutes")
            try:
                Cache.set(session, cache_key, processed_campaigns, 1800)
                print(f"DEBUG: Successfully cached campaigns")
            except Exception as cache_error:
                print(f"DEBUG: Error caching campaigns: {str(cache_error)}")
            
            return processed_campaigns
        except Exception as e:
            print(f"DEBUG: Unexpected error in get_campaigns: {str(e)}")
            raise
        finally:
            session.close() 