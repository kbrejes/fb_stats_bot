"""
Account-related methods for Facebook Marketing API.
"""
from typing import Dict, List, Optional, Tuple

from src.storage.database import get_session
from src.storage.models import Cache
from src.utils.logger import get_logger
from src.api.facebook.exceptions import FacebookAdsApiError

logger = get_logger(__name__)


class AccountMixin:
    """
    Mixin class for account-related methods.
    To be used with FacebookAdsClient.
    """
    
    async def get_ad_accounts(self) -> List[Dict]:
        """
        Get the user's ad accounts.
        
        Returns:
            List of ad accounts.
        """
        # Try to get from cache first
        cache_key = f"ad_accounts:{self.user_id}"
        
        session = get_session()
        try:
            cached_data = Cache.get(session, cache_key)
            if cached_data:
                print(f"DEBUG: Using cached ad accounts for user {self.user_id}")
                return cached_data
        except Exception as e:
            logger.error(f"Error checking cache for ad accounts: {str(e)}")
        finally:
            session.close()
        
        try:
            # Get all accounts the user has access to
            print(f"DEBUG: Fetching ad accounts for user {self.user_id}")
            response = await self._make_request('me/adaccounts', {
                'fields': 'id,name,account_status,amount_spent,balance,currency,timezone_name,business_country_code'
            })
            
            if 'data' in response:
                accounts = response['data']
                print(f"DEBUG: Found {len(accounts)} ad accounts for user {self.user_id}")
                
                # Cache the results
                try:
                    session = get_session()
                    Cache.set(session, cache_key, accounts, 300)  # Cache for 5 minutes
                except Exception as e:
                    logger.error(f"Error caching ad accounts: {str(e)}")
                finally:
                    session.close()
                    
                return accounts
            else:
                print(f"DEBUG: No ad accounts data found for user {self.user_id}")
                return []
                
        except FacebookAdsApiError as e:
            logger.error(f"Error getting ad accounts: {e.message}")
            raise
            
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