"""
Account-related methods for Facebook Marketing API client.
"""
from typing import Dict, List, Any, Optional, Tuple
import json

from src.storage.database import get_session
from src.storage.models import Cache, Account
from src.utils.logger import get_logger
from src.api.facebook.exceptions import (
    FacebookAdsApiError, 
    TokenExpiredError, 
    TokenNotSetError
)
from src.utils.error_handlers import api_error_handler, handle_exceptions
from src.api.interfaces import AccountServiceInterface
from src.bot.types import AccountData

logger = get_logger(__name__)


class AccountMixin:
    """
    Mixin for account-related operations.
    Provides methods for interacting with Facebook ad accounts.
    Implements AccountServiceInterface.
    """
    
    @api_error_handler(api_name="Facebook Accounts API")
    async def get_ad_accounts(self) -> List[Dict[str, Any]]:
        """
        Get all ad accounts available to the user.
        
        Returns:
            List of ad account objects.
        """
        # Try to get from cache first
        cache_key = f"ad_accounts:{self.user_id}"
        
        session = get_session()
        try:
            cached_data = Cache.get(session, cache_key)
            if cached_data:
                logger.info(f"Returning cached accounts for user {self.user_id}")
                return cached_data
                
            # If not in cache, fetch from API
            response = await self._make_request('me/adaccounts', {
                'fields': 'id,name,account_id,account_status,amount_spent,balance,currency'
            })
            
            accounts = response.get('data', [])
            
            # Format and save accounts to database
            formatted_accounts: List[Dict[str, Any]] = []
            for acc in accounts:
                account_id = acc.get('id', '').replace('act_', '')
                name = acc.get('name', 'Unnamed Account')
                
                # Skip accounts with missing details
                if not account_id:
                    continue
                    
                formatted_accounts.append({
                    'id': f"act_{account_id}",
                    'account_id': account_id,
                    'name': name,
                    'status': acc.get('account_status', 0),
                    'currency': acc.get('currency', 'USD'),
                    'spent': acc.get('amount_spent', 0),
                    'balance': acc.get('balance', 0)
                })
                
                # Save/update account in database
                try:
                    account = session.query(Account).filter(Account.account_id == account_id).first()
                    if not account:
                        account = Account(account_id=account_id, name=name, user_id=self.user_id)
                        session.add(account)
                    else:
                        account.name = name
                    session.commit()
                except Exception as e:
                    logger.error(f"Error saving account to database: {str(e)}")
                    session.rollback()
            
            # Cache for 24 hours
            Cache.set(session, cache_key, formatted_accounts, 86400)
            
            logger.info(f"Retrieved {len(formatted_accounts)} accounts for user {self.user_id}")
            return formatted_accounts
        finally:
            session.close()
            
    @handle_exceptions(log_error=True, notify_user=True)
    async def get_accounts(self) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """
        Get the user's ad accounts with error handling for callbacks.
        
        Returns:
            Tuple of (accounts list, error message or None).
        """
        try:
            accounts = await self.get_ad_accounts()
            return accounts, None
        except TokenExpiredError:
            return [], "Your Facebook access token has expired. Please use /auth to authenticate again."
        except TokenNotSetError:
            return [], "You are not authenticated with Facebook. Please use /auth to authenticate."
        except FacebookAdsApiError as e:
            logger.error(f"Facebook API error: {str(e)}")
            return [], f"Facebook API error: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return [], f"Unexpected error occurred while getting accounts. Please try again later." 