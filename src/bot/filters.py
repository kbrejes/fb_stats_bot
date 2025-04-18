"""
Custom filters for the Facebook Ads Telegram Bot.
Used for filtering callback queries and messages based on their data.
"""
import re
from typing import Dict, Any, Union, Optional, Callable

from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message

class AccountCallbackFilter(BaseFilter):
    """
    Filter for callbacks with account data.
    Extracts account_id from account-related callbacks.
    """
    async def __call__(self, callback: CallbackQuery) -> Union[bool, Dict[str, str]]:
        # Match patterns like "account:123456789" or "account_menu:123456789"
        if not callback.data:
            return False
            
        account_patterns = [
            r"^account:(\w+)",  # account:account_id
            r"^menu:account:(\w+)",  # menu:account:account_id
            r"^account_campaigns_stats:(\w+)",  # account_campaigns_stats:account_id
        ]
        
        for pattern in account_patterns:
            match = re.match(pattern, callback.data)
            if match:
                return {"account_id": match.group(1)}
        
        return False


class DatePresetCallbackFilter(BaseFilter):
    """
    Filter for callbacks with date preset data.
    Extracts account_id and date_preset from date preset callbacks.
    """
    async def __call__(self, callback: CallbackQuery) -> Union[bool, Dict[str, str]]:
        # Match pattern like "date_preset:account_id:date_preset"
        if not callback.data:
            return False
            
        match = re.match(r"^date_preset:(\w+):(\w+)", callback.data)
        if match:
            return {
                "account_id": match.group(1),
                "date_preset": match.group(2)
            }
        
        return False


class AuthFilter(BaseFilter):
    """
    Filter that checks if the user is authenticated with a Facebook account.
    """
    async def __call__(self, message: Message) -> bool:
        from src.storage.database import get_session
        from src.storage.models import User
        
        user_id = message.from_user.id
        
        # Fix for the issue where bot ID might be used
        from src.utils.bot_helpers import fix_user_id
        user_id = await fix_user_id(user_id)
        
        session = get_session()
        try:
            user = session.query(User).filter_by(telegram_id=user_id).first()
            return user is not None and user.is_token_valid()
        except Exception:
            return False
        finally:
            session.close()


class AdminFilter(BaseFilter):
    """
    Filter that checks if the user is an admin.
    """
    async def __call__(self, message: Message) -> bool:
        from config.settings import ADMIN_IDS
        
        user_id = message.from_user.id
        return user_id in ADMIN_IDS


class HasAccountFilter(BaseFilter):
    """
    Filter that checks if the user has a selected account.
    """
    async def __call__(self, message: Message) -> bool:
        from src.storage.database import get_session
        from src.storage.models import User
        
        user_id = message.from_user.id
        
        # Fix for the issue where bot ID might be used
        from src.utils.bot_helpers import fix_user_id
        user_id = await fix_user_id(user_id)
        
        session = get_session()
        try:
            user = session.query(User).filter_by(telegram_id=user_id).first()
            if not user:
                return False
                
            context = user.get_context()
            return context is not None and "current_account_id" in context
        except Exception:
            return False
        finally:
            session.close() 