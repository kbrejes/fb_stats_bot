"""
Facebook Marketing API client to interact with ads data.
"""
import json
import aiohttp
import asyncio
import ssl
from typing import Dict, List, Any, Optional, Union, Tuple
from urllib.parse import urlencode
from datetime import datetime

from config.settings import FB_API_VERSION, DATE_PRESETS
from src.storage.database import get_session
from src.storage.models import User, Account, Cache
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Create SSL context that ignores verification
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

class FacebookAdsApiError(Exception):
    """Exception raised for Facebook API errors."""
    def __init__(self, message: str, code: Optional[str] = None, data: Optional[Dict] = None):
        self.message = message
        self.code = code
        self.data = data or {}
        super().__init__(self.message)


class FacebookAdsClient:
    """
    Client for interacting with the Facebook Marketing API.
    Always uses owner's token for API requests, but respects user's permissions.
    """
    def __init__(self, user_id: int):
        """
        Initialize the Facebook Ads client.
        
        Args:
            user_id: The Telegram user ID.
        """
        print(f"DEBUG: Initializing FacebookAdsClient with user_id: {user_id}")
        
        self.user_id = user_id
        self.api_version = FB_API_VERSION
        self.base_url = f"https://graph.facebook.com/{self.api_version}"
        
        # We'll load the token when needed
        self._access_token = None
        self._owner_id = None
        self._session = None
        
    async def __aenter__(self):
        """Async context manager entry."""
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        self._session = aiohttp.ClientSession(connector=connector)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._session:
            await self._session.close()
        
    async def _get_owner_id(self, session) -> Optional[int]:
        """
        Get the owner's ID from the database.
        
        Args:
            session: The database session.
            
        Returns:
            The owner's Telegram ID or None if not found.
        """
        if self._owner_id:
            return self._owner_id
            
        owner = session.query(User).filter_by(role="owner").first()
        if owner:
            self._owner_id = owner.telegram_id
            return self._owner_id
        return None
        
    async def _get_access_token(self) -> str:
        """
        Get the access token from the database.
        Always returns owner's token for all users.
        
        Returns:
            The access token.
            
        Raises:
            FacebookAdsApiError: If no valid token is found.
        """
        if self._access_token:
            return self._access_token
            
        session = get_session()
        try:
            # Всегда получаем owner'а
            owner = session.query(User).filter_by(role="owner").first()
            if not owner:
                print(f"DEBUG: Owner not found in database!")
                raise FacebookAdsApiError("Owner not found", "OWNER_NOT_FOUND")
                
            print(f"DEBUG: Owner found, getting token")
            
            token = owner.get_fb_token()
            if not token:
                print(f"DEBUG: Owner's token not found")
                raise FacebookAdsApiError("Owner's token not found", "TOKEN_NOT_FOUND")
                
            print(f"DEBUG: Using owner's token for user {self.user_id}")
            self._access_token = token
            return token
                
        finally:
            session.close()
            
    async def _make_request(self, endpoint: str, params: Optional[Dict] = None,
                          method: str = 'GET', retries: int = 3) -> Dict:
        """
        Make a request to the Facebook Marketing API.
        
        Args:
            endpoint: The API endpoint.
            params: The query parameters.
            method: The HTTP method to use.
            retries: Number of retries for failed requests.
            
        Returns:
            The API response data.
            
        Raises:
            FacebookAdsApiError: If the request fails.
        """
        if not self._session:
            await self.__aenter__()
            
        token = await self._get_access_token()
        params = params or {}
        params['access_token'] = token
        
        url = f"{self.base_url}/{endpoint}"
        
        if method == 'GET':
            url = f"{url}?{urlencode(params)}"
            params = None
        
        # Маскируем токен в URL для отладочных сообщений
        debug_url = url.replace(token, 'REDACTED_TOKEN')
        print(f"DEBUG: Making API request to: {debug_url}")
        
        retry_count = 0
        while retry_count < retries:
            try:
                if method == 'GET':
                    async with self._session.get(url) as response:
                        data = await response.json()
                elif method == 'POST':
                    async with self._session.post(url, data=params) as response:
                        data = await response.json()
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                # Проверка на наличие ошибок в ответе
                if 'error' in data:
                    error = data['error']
                    error_message = error.get('message', 'Unknown error')
                    error_type = error.get('type', 'Unknown')
                    error_code = error.get('code', 0)
                    error_subcode = error.get('error_subcode', 0)
                    
                    logger.error(f"Facebook API error: {error_message} (code: {error_code}, type: {error_type}, subcode: {error_subcode})")
                    print(f"DEBUG: API error details: {json.dumps(error, indent=2)}")
                    
                    # Определяем внутренний код ошибки для нашего приложения
                    internal_error_code = None
                    
                    # OAuth ошибки (истекший токен, недостаточные разрешения и т.д.)
                    if error_code == 190 or error_type == 'OAuthException':
                        if "access token" in error_message.lower() and "expired" in error_message.lower():
                            internal_error_code = "TOKEN_EXPIRED"
                        elif "permission" in error_message.lower():
                            internal_error_code = "INSUFFICIENT_PERMISSIONS"
                        else:
                            internal_error_code = "TOKEN_EXPIRED"  # Общий случай для OAuth ошибок
                        print(f"DEBUG: OAuth error detected: {error_message}. Setting internal_error_code to {internal_error_code}")
                    
                    # Ошибки доступа к бизнес-аккаунту
                    elif error_code == 200:
                        internal_error_code = "ACCESS_DENIED"
                    
                    # Ошибки лимита запросов
                    elif error_code in [4, 17, 341]:
                        internal_error_code = "RATE_LIMIT"
                    
                    # Прочие ошибки API
                    else:
                        internal_error_code = str(error_code)
                    
                    # Проверка на необходимость повторной попытки
                    if internal_error_code == "RATE_LIMIT" and retry_count < retries:
                        retry_count += 1
                        wait_time = min(2 ** retry_count, 60)  # Экспоненциальное ожидание
                        logger.info(f"Rate limited. Retrying in {wait_time} seconds...")
                        await asyncio.sleep(wait_time)
                        continue
                        
                    raise FacebookAdsApiError(error_message, internal_error_code, error)
                
                return data
                
            except aiohttp.ClientError as e:
                logger.error(f"HTTP error during API request: {str(e)}")
                if retry_count < retries - 1:
                    retry_count += 1
                    await asyncio.sleep(1)
                    continue
                raise FacebookAdsApiError(f"HTTP error: {str(e)}", "HTTP_ERROR")
        
        # If we've exhausted all retries
        raise FacebookAdsApiError("Maximum retries exceeded")
    
    async def get_user_info(self) -> Dict:
        """
        Get information about the current user.
        
        Returns:
            User information.
        """
        # Simple endpoint to test if the token is working
        cache_key = f"user_info:{self.user_id}"
        
        # Try to get from cache first
        session = get_session()
        try:
            cached_data = Cache.get(session, cache_key)
            if cached_data:
                return cached_data
                
            # If not in cache, fetch from API
            data = await self._make_request('me', {'fields': 'id,name,email'})
            
            # Cache the result for 1 hour
            Cache.set(session, cache_key, data, 3600)
            
            return data
        finally:
            session.close()
    
    async def get_ad_accounts(self) -> List[Dict[str, Any]]:
        """
        Get available ad accounts.
        
        Returns:
            List of ad account data dictionaries.
        """
        print(f"DEBUG: Fetching ad accounts for user {self.user_id}")
        
        session = get_session()
        try:
            # Сначала определяем роль пользователя
            user = session.query(User).filter_by(telegram_id=self.user_id).first()
            if not user:
                raise FacebookAdsApiError("User not found", "USER_NOT_FOUND")
            
            # Для всех пользователей используем токен owner'а
            owner = session.query(User).filter_by(role="owner").first()
            if not owner:
                raise FacebookAdsApiError("Owner not found", "OWNER_NOT_FOUND")
            
            # Проверяем валидность токена owner'а
            is_valid = owner.is_token_valid()
            print(f"DEBUG: Owner's token validation - Current time: {datetime.utcnow().isoformat()}, "
                  f"Expires: {owner.token_expires_at.isoformat() if owner.token_expires_at else None}, "
                  f"Valid: {is_valid}")
            
            if not is_valid:
                raise FacebookAdsApiError("Owner's token expired", "TOKEN_EXPIRED")
            
            # Получаем токен owner'а
            token = owner.get_fb_token()
            if not token:
                raise FacebookAdsApiError("Owner's token not found", "TOKEN_NOT_FOUND")
            
            print(f"DEBUG: Using owner's token for user {self.user_id}")
            print(f"DEBUG: Token is valid and has {len(token)} characters")
            
            # Make the API request
            url = f"{self.base_url}/me/adaccounts"
            params = {
                'fields': 'id,name,account_status,amount_spent,balance,currency,timezone_name,business_country_code',
                'access_token': token
            }
            
            print(f"DEBUG: Making API request to: {url}?fields={params['fields']}&access_token=REDACTED_TOKEN")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        error_data = await response.json()
                        error_message = error_data.get('error', {}).get('message', 'Unknown error')
                        raise FacebookAdsApiError(f"Failed to get ad accounts: {error_message}", "API_ERROR")
                    
                    data = await response.json()
                    accounts = data.get('data', [])
                    print(f"DEBUG: Found {len(accounts)} ad accounts for user {self.user_id}")
                    return accounts
        finally:
            session.close()
            
    async def get_accounts(self) -> Tuple[List[Dict], Optional[str]]:
        """
        Get the user's ad accounts with error handling for callbacks.
        
        Returns:
            Tuple of (accounts list, error message or None).
        """
        try:
            accounts = await self.get_ad_accounts()
            return accounts, None
        except FacebookAdsApiError as e:
            logger.error(f"Error getting accounts: {e.message} (code: {e.code})")
            if e.code == "TOKEN_EXPIRED":
                return [], "Your access token has expired. Please use /auth to authenticate again."
            elif e.code == "USER_NOT_FOUND":
                return [], "User not found. Please use /start to initialize the bot."
            elif e.code == "TOKEN_NOT_SET":
                return [], "You are not authenticated with Facebook. Please use /auth to authenticate."
            else:
                return [], f"Facebook API error: {e.message}"
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return [], f"Unexpected error: {str(e)}"
    
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
            
    async def get_insights(
        self,
        object_id: str,
        date_preset: Optional[str] = 'last_7d',
        fields: Optional[List[str]] = None,
        level: str = 'campaign',
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict]:
        """
        Get insights (statistics) for an object.
        
        Args:
            object_id: The object ID (ad account, campaign, ad set, or ad).
            date_preset: The date range preset. Если указаны start_date и end_date, игнорируется.
            fields: List of insight fields to return.
            level: The level of insight data (account, campaign, adset, ad).
            start_date: Начальная дата для кастомного периода
            end_date: Конечная дата для кастомного периода
            
        Returns:
            List of insights.
        """
        # Определяем параметры дат
        if start_date and end_date:
            date_params = {
                'time_range': {
                    'since': start_date.strftime('%Y-%m-%d'),
                    'until': end_date.strftime('%Y-%m-%d')
                }
            }
        else:
            # Map our internal date preset keys to Facebook's values
            facebook_date_preset = DATE_PRESETS.get(date_preset)
            if not facebook_date_preset:
                logger.warning(f"Invalid date preset '{date_preset}', defaulting to 'last_7_days'")
                date_preset = 'last_7d'
                facebook_date_preset = DATE_PRESETS.get(date_preset)
            date_params = {'date_preset': facebook_date_preset}
            
        if not fields:
            # Расширенный набор полей для получения подробной информации о кастомных конверсиях
            fields = [
                'impressions', 'clicks', 'reach', 'spend', 'cpm', 'cpc', 'ctr',
                'actions', 'conversions', 'cost_per_action_type', 'cost_per_conversion',
                'conversion_values', 'action_values', 'purchase_roas',
                'cost_per_inline_link_click', 'cost_per_unique_click', 
                'cost_per_15_sec_video_view', 'unique_actions',
                'video_p25_watched_actions', 'video_p50_watched_actions', 
                'video_p75_watched_actions', 'video_p100_watched_actions',
                'date_start', 'date_stop'  # Добавляем поля для дат
            ]
            
        cache_key = f"insights:{self.user_id}:{object_id}:{date_preset}:{level}"
        if start_date and end_date:
            cache_key = f"insights:{self.user_id}:{object_id}:{start_date.strftime('%Y-%m-%d')}_{end_date.strftime('%Y-%m-%d')}:{level}"
        
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
                'time_increment': 1  # Получаем данные по дням для правильных дат
            }
            params.update(date_params)
            
            print(f"DEBUG: Insights request params: {params}")
            
            data = await self._make_request(f"{object_id}/insights", params)
            
            insights = data.get('data', [])
            
            # Если получили данные по дням, агрегируем их
            if insights:
                aggregated_insight = {
                    'date_start': insights[0].get('date_start'),
                    'date_stop': insights[-1].get('date_stop'),
                    'impressions': sum(float(i.get('impressions', 0)) for i in insights),
                    'clicks': sum(float(i.get('clicks', 0)) for i in insights),
                    'reach': sum(float(i.get('reach', 0)) for i in insights),
                    'spend': sum(float(i.get('spend', 0)) for i in insights),
                    'conversions': [],
                    'cost_per_action_type': []
                }
                
                # Агрегируем конверсии и их стоимость
                conversion_values = {}
                cost_per_action = {}
                
                for insight in insights:
                    for conv in insight.get('conversions', []):
                        action_type = conv.get('action_type')
                        if action_type and action_type.startswith('offsite_conversion.fb_pixel_custom'):
                            if action_type not in conversion_values:
                                conversion_values[action_type] = 0
                            conversion_values[action_type] += float(conv.get('value', 0))
                    
                    for cost in insight.get('cost_per_action_type', []):
                        action_type = cost.get('action_type')
                        if action_type and action_type.startswith('offsite_conversion.fb_pixel_custom'):
                            values = [float(cost.get('value', 0)) for cost in insight.get('cost_per_action_type', [])
                                    if cost.get('action_type') == action_type]
                            if values:
                                if action_type not in cost_per_action:
                                    cost_per_action[action_type] = []
                                cost_per_action[action_type].extend(values)
                
                # Добавляем агрегированные конверсии
                for action_type, value in conversion_values.items():
                    aggregated_insight['conversions'].append({
                        'action_type': action_type,
                        'value': value
                    })
                
                # Добавляем агрегированные стоимости конверсий (среднее значение)
                for action_type, values in cost_per_action.items():
                    if values:
                        avg_cost = sum(values) / len(values)
                        aggregated_insight['cost_per_action_type'].append({
                            'action_type': action_type,
                            'value': avg_cost
                        })
                
                insights = [aggregated_insight]
            
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
            
    async def get_account_insights(
        self,
        account_id: str,
        date_preset: Optional[str] = 'last_7d',
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict]:
        """
        Get insights for an ad account.
        
        Args:
            account_id: The ad account ID.
            date_preset: The date range preset.
            start_date: Начальная дата для кастомного периода
            end_date: Конечная дата для кастомного периода
            
        Returns:
            Account insights.
        """
        return await self.get_insights(
            account_id,
            date_preset=date_preset,
            level='account',
            start_date=start_date,
            end_date=end_date
        )
        
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