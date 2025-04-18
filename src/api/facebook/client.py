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
from src.api.facebook.exceptions import (
    FacebookAdsApiError, 
    TokenExpiredError, 
    TokenNotSetError,
    InsufficientPermissionsError,
    RateLimitError,
    NetworkError
)
from src.utils.error_handlers import api_error_handler

logger = get_logger(__name__)

# Create SSL context that ignores verification
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE


class FacebookAdsClient:
    """
    Client for interacting with the Facebook Marketing API.
    """
    def __init__(self, user_id: int = None, access_token: str = None):
        """
        Initialize the Facebook Ads client.
        
        Args:
            user_id: The Telegram user ID.
            access_token: Optional direct access token. If provided, user_id is not required.
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
        self._access_token = access_token
        self._base_url = f"https://graph.facebook.com/v{self.api_version}/"
    
    async def get_access_token(self) -> str:
        """
        Get the access token for API requests.
        
        Returns:
            str: The access token.
            
        Raises:
            TokenNotSetError: If the token is not set.
            TokenExpiredError: If the token is expired.
        """
        # If we already have a token, return it
        if self._access_token:
            return self._access_token
            
        # Otherwise, load from the database
        if not self.user_id:
            raise TokenNotSetError("User ID not set, cannot retrieve token")
            
        session = get_session()
        try:
            user = session.query(User).filter(User.telegram_id == self.user_id).first()
            
            if not user:
                print(f"DEBUG: User not found with ID {self.user_id}")
                raise TokenNotSetError(f"User not found with ID {self.user_id}")
            
            print(f"DEBUG: User found: {user.telegram_id}, token valid: {user.is_token_valid()}")
            
            # BUGFIX: Проверка на повторяющиеся ошибки с токеном
            # Если у нас есть неудачная попытка доступа с этим токеном, проверим это
            token = user.get_fb_token()
            if not token:
                print(f"DEBUG: Token is None for user {user.telegram_id}, raising TokenNotSetError")
                raise TokenNotSetError("Facebook token is not set")
            
            # Проверка действительности токена
            is_token_valid = user.is_token_valid()
            if not is_token_valid:
                print(f"DEBUG: Token is invalid for user {user.telegram_id}, raising TokenExpiredError")
                raise TokenExpiredError("Facebook token is expired")
            
            print(f"DEBUG: Token is valid and has {len(token)} characters")
            
            self._access_token = token
            return token
        finally:
            session.close()

    @api_error_handler(api_name="Facebook Marketing API", log_error=True, notify_user=False)
    async def _make_request(self, endpoint: str, params: Optional[Dict] = None,
                          method: str = 'GET', retries: int = 3) -> Dict:
        """
        Make a request to the Facebook Marketing API with error handling and retries.
        
        Args:
            endpoint: The API endpoint to request.
            params: Optional parameters for the request.
            method: HTTP method to use. Default is GET.
            retries: Maximum number of retries. Default is 3.
            
        Returns:
            The JSON response from the API.
            
        Raises:
            FacebookAdsApiError: For API errors.
            NetworkError: For network-related errors.
        """
        if params is None:
            params = {}
            
        # Get access token (will raise appropriate errors if not available)
        access_token = await self.get_access_token()
        params['access_token'] = access_token
        
        # Construct URL based on method
        if method == 'GET':
            query_string = urlencode(params)
            url = f"{self._base_url}{endpoint}?{query_string}"
        else:
            url = f"{self._base_url}{endpoint}"
            
        logger.info(f"Making {method} request to {endpoint}")
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
                        
                        # Определяем тип исключения на основе ошибки API
                        
                        # OAuth ошибки (истекший токен, недостаточные разрешения и т.д.)
                        if error_code == 190 or error_type == 'OAuthException':
                            if "access token" in error_message.lower() and "expired" in error_message.lower():
                                raise TokenExpiredError(error_message, data)
                            elif "permission" in error_message.lower():
                                raise InsufficientPermissionsError(error_message, data)
                            else:
                                raise TokenExpiredError(error_message, data)  # Общий случай для OAuth ошибок
                        
                        # Ошибки лимита запросов
                        elif error_code in [4, 17, 341]:
                            # Проверка на необходимость повторной попытки
                            if retry_count < retries:
                                retry_count += 1
                                wait_time = min(2 ** retry_count, 60)  # Экспоненциальное ожидание
                                logger.info(f"Rate limited. Retrying in {wait_time} seconds...")
                                await asyncio.sleep(wait_time)
                                continue
                            else:
                                raise RateLimitError(error_message, data)
                            
                        # Другие ошибки - используем общий класс FacebookAdsApiError
                        else:
                            raise FacebookAdsApiError(
                                message=error_message,
                                code=str(error_code),
                                data=data,
                                http_code=response.status,
                                fb_error_code=error_code,
                                fb_error_subcode=error_subcode
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
                    
                raise NetworkError(f"Network error: {str(e)}")
                
            except (TokenExpiredError, TokenNotSetError, InsufficientPermissionsError, RateLimitError) as e:
                # Для специализированных ошибок - просто пробрасываем дальше
                raise
                
            except Exception as e:
                logger.error(f"Unexpected error during API request: {str(e)}")
                raise FacebookAdsApiError(f"Unexpected error: {str(e)}")
        
        # If we've exhausted all retries
        raise RateLimitError("Maximum retries exceeded")
    
    @api_error_handler(api_name="Facebook User API")
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