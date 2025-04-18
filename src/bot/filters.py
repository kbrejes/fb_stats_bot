"""
Custom filters for the Telegram bot.
These filters can be used to check various conditions before command handlers are executed.
"""
import logging
from typing import Union, Dict, Any, Optional, Callable, Awaitable

from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery, User
from aiogram.fsm.context import FSMContext

from src.storage.database import get_session
from src.storage.models import User as UserModel, Account
from src.utils.constants import ADMIN_IDS

logger = logging.getLogger(__name__)

class AuthFilter(BaseFilter):
    """
    Filter that checks if a user is authenticated with a Facebook account.
    """
    async def __call__(self, update: Union[Message, CallbackQuery]) -> bool:
        user = update.from_user
        if not user:
            return False
            
        session = get_session()
        try:
            db_user = session.query(UserModel).filter(UserModel.telegram_id == user.id).first()
            if not db_user:
                # User not in database
                return False
                
            # Check if user has a valid Facebook token
            has_token = db_user.fb_access_token is not None
            
            if not has_token and isinstance(update, Message):
                await update.answer("Пожалуйста, авторизуйтесь с помощью команды /start")
                
            return has_token
        except Exception as e:
            logger.error(f"Error in AuthFilter: {e}")
            return False
        finally:
            session.close()

class AdminFilter(BaseFilter):
    """
    Filter that checks if a user is an admin.
    """
    async def __call__(self, update: Union[Message, CallbackQuery]) -> bool:
        user = update.from_user
        if not user:
            return False
            
        is_admin = user.id in ADMIN_IDS
        
        if not is_admin and isinstance(update, Message):
            await update.answer("У вас нет прав для выполнения этой команды.")
            
        return is_admin

class HasAccountFilter(BaseFilter):
    """
    Filter that checks if a user has a selected account.
    """
    async def __call__(self, update: Union[Message, CallbackQuery]) -> Dict[str, Any]:
        user = update.from_user
        if not user:
            return False
            
        session = get_session()
        try:
            # Get user from database
            db_user = session.query(UserModel).filter(UserModel.telegram_id == user.id).first()
            if not db_user:
                return False
                
            # Find primary account or any account
            account = session.query(Account).filter(
                Account.telegram_id == user.id,
                Account.is_primary == True
            ).first()
            
            if not account:
                # Try to get any account
                account = session.query(Account).filter(
                    Account.telegram_id == user.id
                ).first()
            
            if not account and isinstance(update, Message):
                await update.answer("У вас нет выбранного аккаунта. Используйте команду /accounts для выбора аккаунта.")
                return False
                
            return {"account": account} if account else False
        except Exception as e:
            logger.error(f"Error in HasAccountFilter: {e}")
            return False
        finally:
            session.close()

class StateFilter(BaseFilter):
    """
    Filter that checks if a user is in a specific state.
    """
    def __init__(self, state: Optional[str] = None):
        self.state = state
        
    async def __call__(self, update: Union[Message, CallbackQuery], state: FSMContext) -> bool:
        if not self.state:
            return True
            
        current_state = await state.get_state()
        return current_state == self.state

class AccountCallbackFilter(BaseFilter):
    """
    Filter for account callback data.
    Extracts account_id from callback data in format 'account:account_id'.
    """
    async def __call__(self, callback: CallbackQuery) -> Dict[str, Any]:
        if not callback.data:
            return False
            
        if callback.data.startswith('account:'):
            parts = callback.data.split(':')
            if len(parts) == 2:
                return {'account_id': parts[1]}
        
        return False

class DatePresetCallbackFilter(BaseFilter):
    """
    Filter for date preset callback data.
    Extracts preset from callback data in format 'date:preset'.
    """
    async def __call__(self, callback: CallbackQuery) -> Dict[str, Any]:
        if not callback.data:
            return False
            
        if callback.data.startswith('date:'):
            parts = callback.data.split(':')
            if len(parts) == 2:
                return {'preset': parts[1]}
        
        return False 