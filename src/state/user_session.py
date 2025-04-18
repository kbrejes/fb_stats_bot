"""
Module for handling user state and session management.
"""
import json
import logging
from typing import Dict, Any, Optional, Union, List
from datetime import datetime

from sqlalchemy.orm import Session

from src.storage.database import get_session
from src.storage.models import User
from src.utils.bot_helpers import fix_user_id

logger = logging.getLogger(__name__)


class UserSession:
    """
    Central class for managing user state and session data.
    Provides a unified interface for working with user context.
    """
    
    def __init__(self, user_id: int):
        """
        Initialize a user session.
        
        Args:
            user_id: Telegram user ID
        """
        self.user_id = user_id
        self._context_cache = None
        self._user_cache = None
    
    @classmethod
    async def get_session(cls, user_id: int) -> 'UserSession':
        """
        Get a user session with fixed ID handling.
        
        Args:
            user_id: Raw user ID from Telegram
            
        Returns:
            UserSession instance with properly fixed user_id
        """
        fixed_id = await fix_user_id(user_id)
        return cls(fixed_id)
    
    def _get_db_session(self) -> Session:
        """
        Get a database session.
        
        Returns:
            SQLAlchemy session
        """
        return get_session()
    
    def _get_user(self, session: Optional[Session] = None) -> Optional[User]:
        """
        Get the user from database.
        
        Args:
            session: Optional SQLAlchemy session
            
        Returns:
            User model or None if not found
        """
        if self._user_cache:
            return self._user_cache
            
        own_session = False
        if not session:
            session = self._get_db_session()
            own_session = True
            
        try:
            user = session.query(User).filter_by(telegram_id=self.user_id).first()
            if not user:
                logger.warning(f"User {self.user_id} not found in database")
                return None
                
            # Cache the user object
            self._user_cache = user
            return user
        except Exception as e:
            logger.error(f"Error getting user {self.user_id}: {str(e)}")
            return None
        finally:
            if own_session:
                session.close()
    
    def get_context(self) -> Dict[str, Any]:
        """
        Get the user's context data.
        
        Returns:
            Dictionary with user context or empty dict if not found
        """
        if self._context_cache is not None:
            return self._context_cache
            
        session = self._get_db_session()
        try:
            user = self._get_user(session)
            if not user:
                return {}
                
            context = user.get_context()
            self._context_cache = context
            return context
        finally:
            session.close()
    
    def set_context(self, data: Dict[str, Any], merge: bool = True) -> bool:
        """
        Set or update the user's context data.
        
        Args:
            data: Context data to set
            merge: If True, merge with existing context; if False, replace it
            
        Returns:
            True if successful, False otherwise
        """
        session = self._get_db_session()
        try:
            user = self._get_user(session)
            if not user:
                logger.error(f"Cannot set context: user {self.user_id} not found")
                return False
                
            if merge:
                current = user.get_context()
                current.update(data)
                user.set_context(current)
                self._context_cache = current
            else:
                user.set_context(data)
                self._context_cache = data
                
            session.commit()
            return True
        except Exception as e:
            logger.error(f"Error setting context for user {self.user_id}: {str(e)}")
            session.rollback()
            return False
        finally:
            session.close()
    
    def clear_context(self) -> bool:
        """
        Clear the user's context data.
        
        Returns:
            True if successful, False otherwise
        """
        return self.set_context({}, merge=False)
    
    def get_value(self, key: str, default: Any = None) -> Any:
        """
        Get a specific value from the user's context.
        
        Args:
            key: The key to lookup
            default: Default value if key not found
            
        Returns:
            The value for the key or default if not found
        """
        context = self.get_context()
        return context.get(key, default)
    
    def set_value(self, key: str, value: Any) -> bool:
        """
        Set a specific key-value in the user's context.
        
        Args:
            key: The key to set
            value: The value to set
            
        Returns:
            True if successful, False otherwise
        """
        return self.set_context({key: value})
    
    def remove_value(self, key: str) -> bool:
        """
        Remove a specific key from the user's context.
        
        Args:
            key: The key to remove
            
        Returns:
            True if successful, False otherwise
        """
        context = self.get_context()
        if key not in context:
            return True
            
        context.pop(key, None)
        return self.set_context(context, merge=False)
    
    def set_current_account(self, account_id: str) -> bool:
        """
        Set the current account ID for the user.
        
        Args:
            account_id: The Facebook ad account ID
            
        Returns:
            True if successful, False otherwise
        """
        return self.set_value("current_account_id", account_id)
    
    def get_current_account(self) -> Optional[str]:
        """
        Get the current account ID for the user.
        
        Returns:
            Account ID or None if not set
        """
        return self.get_value("current_account_id")
    
    def set_current_campaign(self, campaign_id: str) -> bool:
        """
        Set the current campaign ID for the user.
        
        Args:
            campaign_id: The campaign ID
            
        Returns:
            True if successful, False otherwise
        """
        return self.set_value("current_campaign_id", campaign_id)
    
    def get_current_campaign(self) -> Optional[str]:
        """
        Get the current campaign ID for the user.
        
        Returns:
            Campaign ID or None if not set
        """
        return self.get_value("current_campaign_id")
    
    def set_current_ad_set(self, ad_set_id: str) -> bool:
        """
        Set the current ad set ID for the user.
        
        Args:
            ad_set_id: The ad set ID
            
        Returns:
            True if successful, False otherwise
        """
        return self.set_value("current_ad_set_id", ad_set_id)
    
    def get_current_ad_set(self) -> Optional[str]:
        """
        Get the current ad set ID for the user.
        
        Returns:
            Ad set ID or None if not set
        """
        return self.get_value("current_ad_set_id")
    
    def is_token_valid(self) -> bool:
        """
        Check if the user has a valid Facebook access token.
        
        Returns:
            True if token is valid, False otherwise
        """
        session = self._get_db_session()
        try:
            user = self._get_user(session)
            if not user:
                return False
                
            return user.is_token_valid()
        finally:
            session.close()
    
    def get_last_command(self) -> Optional[str]:
        """
        Get the user's last executed command.
        
        Returns:
            Command string or None if not set
        """
        session = self._get_db_session()
        try:
            user = self._get_user(session)
            if not user:
                return None
                
            return user.last_command
        finally:
            session.close()
    
    def set_last_command(self, command: str) -> bool:
        """
        Set the user's last executed command.
        
        Args:
            command: The command string
            
        Returns:
            True if successful, False otherwise
        """
        session = self._get_db_session()
        try:
            user = self._get_user(session)
            if not user:
                return False
                
            user.last_command = command
            session.commit()
            return True
        except Exception as e:
            logger.error(f"Error setting last command for user {self.user_id}: {str(e)}")
            session.rollback()
            return False
        finally:
            session.close()
    
    def get_language(self) -> str:
        """
        Get the user's preferred language.
        
        Returns:
            Language code (default: 'ru')
        """
        session = self._get_db_session()
        try:
            user = self._get_user(session)
            if not user:
                return 'ru'  # Default language
                
            return user.language or 'ru'
        finally:
            session.close()
    
    def set_language(self, language: str) -> bool:
        """
        Set the user's preferred language.
        
        Args:
            language: Language code ('ru', 'en', etc.)
            
        Returns:
            True if successful, False otherwise
        """
        session = self._get_db_session()
        try:
            user = self._get_user(session)
            if not user:
                return False
                
            user.language = language
            session.commit()
            return True
        except Exception as e:
            logger.error(f"Error setting language for user {self.user_id}: {str(e)}")
            session.rollback()
            return False
        finally:
            session.close()
    
    def clear_cache(self) -> None:
        """
        Clear the internal cache.
        """
        self._context_cache = None
        self._user_cache = None 