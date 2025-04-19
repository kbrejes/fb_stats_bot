"""
Role-based access control utilities.
"""
import logging
from functools import wraps
from typing import Callable, Any, Optional, Union

from aiogram.types import Message, CallbackQuery

from src.storage.database import get_session
from src.storage.models import User, UserRole

logger = logging.getLogger(__name__)

def check_user_role(user_id: int, required_role: UserRole) -> bool:
    """
    Check if a user has a specific role or higher.
    
    Args:
        user_id: Telegram user ID.
        required_role: Required role for the operation.
        
    Returns:
        True if the user has the required role, False otherwise.
    """
    session = get_session()
    try:
        user = session.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            logger.warning(f"User {user_id} not found in database")
            return False
            
        user_role = user.get_role()
        
        # Check role hierarchy
        if required_role == UserRole.ADMIN:
            return user_role == UserRole.ADMIN
        elif required_role == UserRole.TARGETOLOGIST:
            return user_role in [UserRole.ADMIN, UserRole.TARGETOLOGIST]
        elif required_role == UserRole.PARTNER:
            # All roles can access partner functionality
            return True
        else:
            logger.error(f"Unknown role: {required_role}")
            return False
    except Exception as e:
        logger.error(f"Error checking user role: {e}")
        return False
    finally:
        session.close()
        
def admin_required(func: Callable) -> Callable:
    """
    Decorator to check if a user has ADMIN role.
    For message handlers.
    
    Args:
        func: The function to decorate.
        
    Returns:
        Decorated function.
    """
    @wraps(func)
    async def wrapper(message: Message, *args: Any, **kwargs: Any) -> Any:
        if not message.from_user:
            await message.answer("Ошибка: пользователь не найден.")
            return None
            
        user_id = message.from_user.id
        if check_user_role(user_id, UserRole.ADMIN):
            return await func(message, *args, **kwargs)
        else:
            await message.answer("У вас нет прав администратора для выполнения этой операции.")
            return None
    return wrapper

def targetologist_required(func: Callable) -> Callable:
    """
    Decorator to check if a user has TARGETOLOGIST or ADMIN role.
    For message handlers.
    
    Args:
        func: The function to decorate.
        
    Returns:
        Decorated function.
    """
    @wraps(func)
    async def wrapper(message: Message, *args: Any, **kwargs: Any) -> Any:
        if not message.from_user:
            await message.answer("Ошибка: пользователь не найден.")
            return None
            
        user_id = message.from_user.id
        if check_user_role(user_id, UserRole.TARGETOLOGIST):
            return await func(message, *args, **kwargs)
        else:
            await message.answer("У вас нет прав таргетолога для выполнения этой операции.")
            return None
    return wrapper

def callback_admin_required(func: Callable) -> Callable:
    """
    Decorator to check if a user has ADMIN role.
    For callback query handlers.
    
    Args:
        func: The function to decorate.
        
    Returns:
        Decorated function.
    """
    @wraps(func)
    async def wrapper(callback: CallbackQuery, *args: Any, **kwargs: Any) -> Any:
        if not callback.from_user:
            await callback.answer("Ошибка: пользователь не найден.")
            return None
            
        user_id = callback.from_user.id
        if check_user_role(user_id, UserRole.ADMIN):
            return await func(callback, *args, **kwargs)
        else:
            await callback.answer("У вас нет прав администратора для выполнения этой операции.")
            return None
    return wrapper

def callback_targetologist_required(func: Callable) -> Callable:
    """
    Decorator to check if a user has TARGETOLOGIST or ADMIN role.
    For callback query handlers.
    
    Args:
        func: The function to decorate.
        
    Returns:
        Decorated function.
    """
    @wraps(func)
    async def wrapper(callback: CallbackQuery, *args: Any, **kwargs: Any) -> Any:
        if not callback.from_user:
            await callback.answer("Ошибка: пользователь не найден.")
            return None
            
        user_id = callback.from_user.id
        if check_user_role(user_id, UserRole.TARGETOLOGIST):
            return await func(callback, *args, **kwargs)
        else:
            await callback.answer("У вас нет прав таргетолога для выполнения этой операции.")
            return None
    return wrapper 