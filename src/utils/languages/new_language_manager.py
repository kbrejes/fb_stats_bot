"""
Language manager for the Telegram bot (Compatibility Layer).
This file is kept for backward compatibility and uses the new localization system.
"""
import logging
import warnings
from typing import Dict, Any, Optional

from src.utils.localization import (
    get_text as new_get_text,
    get_language as new_get_language,
    set_language as new_set_language,
    get_available_languages,
    get_language_name
)
from src.storage.database import get_session
from src.storage.models import User

logger = logging.getLogger(__name__)

# Warning message for compatibility layer
COMPATIBILITY_WARNING = (
    "Using deprecated language_manager module. "
    "Please update your code to use src.utils.localization instead."
)

# Supported languages
SUPPORTED_LANGUAGES = get_available_languages()
DEFAULT_LANGUAGE = "ru"

# User language settings cache
_user_languages: Dict[int, str] = {}

def get_language(user_id: int) -> str:
    """
    Get the user's preferred language (Compatibility function).
    
    Args:
        user_id: The user's Telegram ID.
        
    Returns:
        The user's language code ('ru' or 'en').
    """
    warnings.warn(COMPATIBILITY_WARNING, DeprecationWarning, stacklevel=2)
    return new_get_language(user_id)

def set_language(user_id: int, language: str) -> bool:
    """
    Set the user's preferred language (Compatibility function).
    
    Args:
        user_id: The user's Telegram ID.
        language: The language code ('ru' or 'en').
        
    Returns:
        True if successful, False otherwise.
    """
    warnings.warn(COMPATIBILITY_WARNING, DeprecationWarning, stacklevel=2)
    return new_set_language(user_id, language)

def get_text(key: str, language: str, **kwargs) -> str:
    """
    Get translated text for a key (Compatibility function).
    
    Args:
        key: The translation key.
        language: The language code.
        **kwargs: Formatting arguments.
        
    Returns:
        The translated text.
    """
    warnings.warn(COMPATIBILITY_WARNING, DeprecationWarning, stacklevel=2)
    return new_get_text(key, lang=language, **kwargs)

# Функция для исправления ID пользователя
def fix_user_id(user_id: int) -> int:
    """
    Fix user ID for the bot ID issue.
    
    Args:
        user_id: The Telegram user ID.
        
    Returns:
        Fixed user ID.
    """
    # Проверяем на бота
    if user_id == 8113924050 or str(user_id) == "8113924050":
        session = get_session()
        try:
            user = session.query(User).filter(User.telegram_id != 8113924050).first()
            if user:
                return user.telegram_id
        except Exception as e:
            logger.error(f"Error finding alternative user: {str(e)}")
        finally:
            session.close()
    return user_id 