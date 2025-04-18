"""
Base client for Facebook Marketing API.
"""
import json
import aiohttp
import asyncio
import ssl
from typing import Dict, List, Any, Optional, Union, Tuple
from urllib.parse import urlencode

from config.settings import FB_API_VERSION
from src.storage.database import get_session
from src.storage.models import User, Account, Cache
from src.utils.logger import get_logger
from src.api.facebook.exceptions import FacebookAdsApiError

logger = get_logger(__name__)

# Create SSL context that ignores verification
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE


class FacebookAdsClient:
    """
    Client for interacting with the Facebook Marketing API.
    """
    def __init__(self, user_id: int):
        """
        Initialize the Facebook Ads client.
        
        Args:
            user_id: The Telegram user ID.
        """
        print(f"DEBUG: Initializing FacebookAdsClient with user_id: {user_id}")
        
        # Fix for the issue where bot's ID is used instead of user's ID
        # Make sure we're not using Bot ID (8113924050 in this case)
        if user_id == 8113924050 or str(user_id) == "8113924050":
            from src.storage.database import get_session
            from src.storage.models import User
            
            # Try to find a valid user in the database
            session = get_session()
            try:
                # Get the first user with a valid token
                user = session.query(User).filter(User.telegram_id != 8113924050).first()
                if user:
                    print(f"DEBUG: Replacing bot ID with user ID: {user.telegram_id}")
                    user_id = user.telegram_id
            except Exception as e:
                print(f"DEBUG: Error finding alternative user: {str(e)}")
            finally:
                session.close()
        
        self.user_id = user_id
        self.api_version = FB_API_VERSION
        self.base_url = f"https://graph.facebook.com/{self.api_version}"
        
        # We'll load the token when needed
        self._access_token = None
        
    async def _get_access_token(self) -> str:
        """
        Get the user's access token from the database.
        
        Returns:
            The access token.
            
        Raises:
            FacebookAdsApiError: If no valid token is found.
        """
        if self._access_token:
            return self._access_token
            
        session = get_session()
        try:
            print(f"DEBUG: Looking for user with ID {self.user_id}")
            user = session.query(User).filter_by(telegram_id=self.user_id).first()
            
            if not user:
                print(f"DEBUG: User with ID {self.user_id} not found in database!")
                
                # Попытка создать пользователя на лету
                try:
                    print(f"DEBUG: Attempting to create user with ID {self.user_id}")
                    user = User(
                        telegram_id=self.user_id,
                        first_name="Auto-created user"
                    )
                    session.add(user)
                    session.commit()
                    print(f"DEBUG: Successfully created user with ID {self.user_id}")
                except Exception as e:
                    print(f"DEBUG: Failed to create user: {str(e)}")
                    raise FacebookAdsApiError("User not found and could not be created", "USER_NOT_FOUND")
                    
                # Повторная попытка получить пользователя
                user = session.query(User).filter_by(telegram_id=self.user_id).first()
                if not user:
                    print(f"DEBUG: User with ID {self.user_id} still not found after creation attempt!")
                    raise FacebookAdsApiError("User not found", "USER_NOT_FOUND")
            
            print(f"DEBUG: User found: {user.telegram_id}, token valid: {user.is_token_valid()}")
            
            # BUGFIX: Проверка на повторяющиеся ошибки с токеном
            # Если у нас есть неудачная попытка доступа с этим токеном, проверим это
            token = user.get_fb_token()
            if not token:
                print(f"DEBUG: Token is None for user {user.telegram_id}, raising TOKEN_NOT_SET")
                raise FacebookAdsApiError("Facebook token is not set", "TOKEN_NOT_SET")
            
            # Проверка действительности токена
            is_token_valid = user.is_token_valid()
            if not is_token_valid:
                print(f"DEBUG: Token is invalid for user {user.telegram_id}, raising TOKEN_EXPIRED")
                raise FacebookAdsApiError("Facebook token is expired or not set", "TOKEN_EXPIRED")
            
            print(f"DEBUG: Token is valid and has {len(token)} characters")
            
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
                # Using a ClientSession with SSL verification disabled
                connector = aiohttp.TCPConnector(ssl=ssl_context)
                async with aiohttp.ClientSession(connector=connector) as session:
                    if method == 'GET':
                        async with session.get(url) as response:
                            data = await response.json()
                    elif method == 'POST':
                        async with session.post(url, data=params) as response:
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
                            
                        # Другие ошибки - пробрасываем исключение
                        raise FacebookAdsApiError(
                            error_message,
                            internal_error_code,
                            data
                        )
                    
                    # Если ошибок нет - возвращаем данные
                    return data
                    
            except aiohttp.ClientError as e:
                logger.error(f"HTTP error during API request: {str(e)}")
                print(f"DEBUG: HTTP client error: {str(e)}")
                
                # Retry for network errors
                if retry_count < retries:
                    retry_count += 1
                    wait_time = min(2 ** retry_count, 60)
                    logger.info(f"Network error. Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                    continue
                    
                raise FacebookAdsApiError(f"Network error: {str(e)}", "NETWORK_ERROR")
                
            except Exception as e:
                logger.error(f"Unexpected error during API request: {str(e)}")
                raise FacebookAdsApiError(f"Unexpected error: {str(e)}")
        
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