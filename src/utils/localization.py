"""
Localization manager for the Telegram bot.
Handles translations and language settings using JSON files.
"""
import os
import json
import logging
from typing import Dict, Any, Optional, List

from src.storage.database import get_session
from src.storage.models import User

logger = logging.getLogger(__name__)

# Прототип для поддерживаемых языков, будет обновлен после инициализации менеджера
SUPPORTED_LANGUAGES = ["ru", "en"]

class LocalizationManager:
    """
    Class that manages translations and language settings.
    
    This class provides methods to:
    - Load translations from JSON files
    - Get translations for specific keys
    - Set and get user language preferences
    """
    
    def __init__(self):
        """Initialize the localization manager."""
        self.translations: Dict[str, Dict[str, Dict[str, str]]] = {}
        self.metadata: Dict[str, Any] = {}
        self.available_languages: List[str] = []
        self.default_language: str = "ru"
        self.language_names: Dict[str, str] = {}
        self.categories: List[str] = []
        
        # User language cache for quick access
        self._user_languages: Dict[int, str] = {}
        
        # Load translations and metadata
        self.load_metadata()
        self.load_translations()
    
    def load_metadata(self) -> None:
        """Load metadata about available languages and categories."""
        try:
            metadata_path = os.path.join("src", "locales", "index.json")
            with open(metadata_path, 'r', encoding='utf-8') as f:
                self.metadata = json.load(f)
                
            self.available_languages = self.metadata.get("available_languages", ["ru", "en"])
            self.default_language = self.metadata.get("default_language", "ru")
            self.language_names = self.metadata.get("language_names", {"ru": "Русский", "en": "English"})
            self.categories = self.metadata.get("categories", [])
            
            logger.info(f"Loaded localization metadata: {len(self.available_languages)} languages, "
                       f"{len(self.categories)} categories")
        except Exception as e:
            logger.error(f"Error loading localization metadata: {str(e)}")
            # Set defaults if metadata cannot be loaded
            self.available_languages = ["ru", "en"]
            self.default_language = "ru"
            self.language_names = {"ru": "Русский", "en": "English"}
            self.categories = ["menu", "errors", "stats", "auth", "common", "help"]
    
    def load_translations(self) -> None:
        """Load all translations from JSON files."""
        locales_dir = os.path.join("src", "locales")
        
        for lang in self.available_languages:
            lang_dir = os.path.join(locales_dir, lang)
            
            if not os.path.isdir(lang_dir):
                logger.warning(f"Language directory not found: {lang_dir}")
                continue
                
            self.translations[lang] = {}
            
            for file in os.listdir(lang_dir):
                if file.endswith('.json'):
                    category = file.split('.')[0]
                    file_path = os.path.join(lang_dir, file)
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            self.translations[lang][category] = json.load(f)
                            logger.debug(f"Loaded {len(self.translations[lang][category])} translations "
                                        f"for {lang}/{category}")
                    except Exception as e:
                        logger.error(f"Error loading translations from {file_path}: {str(e)}")
        
        logger.info(f"Loaded translations for {len(self.translations)} languages")
    
    def get_text(self, key: str, lang: str = None, category: str = None, 
                user_id: int = None, **kwargs) -> str:
        """
        Get translated text for a key.
        
        Args:
            key: The translation key.
            lang: The language code. If None, uses user_id to determine language.
            category: The category to look in. If None, searches all categories.
            user_id: The user's Telegram ID to determine language preference.
            **kwargs: Formatting arguments.
            
        Returns:
            The translated text.
        """
        # Determine language
        if lang is None:
            if user_id is not None:
                lang = self.get_language(user_id)
            else:
                lang = self.default_language
        
        # Check if language is supported
        if lang not in self.translations:
            lang = self.default_language
        
        # If category is specified
        if category is not None:
            if category in self.translations[lang]:
                text = self.translations[lang][category].get(key)
                if text:
                    # Apply formatting if kwargs provided
                    if kwargs:
                        try:
                            return text.format(**kwargs)
                        except (KeyError, ValueError) as e:
                            logger.error(f"Error formatting text for key {key} with args {kwargs}: {str(e)}")
                            return text
                    return text
        else:
            # Search in all categories
            for cat, translations in self.translations[lang].items():
                if key in translations:
                    text = translations[key]
                    # Apply formatting if kwargs provided
                    if kwargs:
                        try:
                            return text.format(**kwargs)
                        except (KeyError, ValueError) as e:
                            logger.error(f"Error formatting text for key {key} with args {kwargs}: {str(e)}")
                            return text
                    return text
        
        # Return key if translation not found
        logger.warning(f"Translation not found for key '{key}' in language '{lang}'")
        return key
    
    def get_language(self, user_id: int) -> str:
        """
        Get the user's preferred language.
        
        Args:
            user_id: The user's Telegram ID.
            
        Returns:
            The user's language code.
        """
        # Check cache first
        if user_id in self._user_languages:
            return self._user_languages[user_id]
        
        # Try to get from database
        session = get_session()
        try:
            user = session.query(User).filter_by(telegram_id=user_id).first()
            if user and hasattr(user, 'language'):
                lang = user.language
                # Cache the result
                self._user_languages[user_id] = lang
                return lang
        except Exception as e:
            logger.error(f"Error getting user language: {str(e)}")
        finally:
            session.close()
        
        # Default language
        return self.default_language
    
    def set_language(self, user_id: int, language: str) -> bool:
        """
        Set the user's preferred language.
        
        Args:
            user_id: The user's Telegram ID.
            language: The language code.
            
        Returns:
            True if successful, False otherwise.
        """
        if language not in self.available_languages:
            logger.warning(f"Attempted to set unsupported language: {language}")
            return False
        
        # Update cache
        self._user_languages[user_id] = language
        
        # Update database
        session = get_session()
        try:
            user = session.query(User).filter_by(telegram_id=user_id).first()
            if user:
                user.language = language
                session.commit()
                logger.info(f"Language for user {user_id} set to {language}")
                return True
            else:
                logger.warning(f"Attempted to set language for non-existent user: {user_id}")
        except Exception as e:
            logger.error(f"Error setting user language: {str(e)}")
            session.rollback()
        finally:
            session.close()
        
        return False
    
    def get_language_name(self, lang_code: str) -> str:
        """
        Get the human-readable name of a language.
        
        Args:
            lang_code: The language code.
            
        Returns:
            The language name.
        """
        return self.language_names.get(lang_code, lang_code)
    
    def get_available_languages(self) -> List[str]:
        """
        Get list of available language codes.
        
        Returns:
            List of language codes.
        """
        return self.available_languages
    
    def clear_cache(self, user_id: int = None) -> None:
        """
        Clear cached language preferences.
        
        Args:
            user_id: Specific user ID to clear, or all if None.
        """
        if user_id is None:
            self._user_languages = {}
        elif user_id in self._user_languages:
            del self._user_languages[user_id]

# Create global instance
_localization_manager = LocalizationManager()

# Update SUPPORTED_LANGUAGES with actual available languages
SUPPORTED_LANGUAGES = _localization_manager.get_available_languages()

# Convenience functions
def get_text(key: str, lang: str = None, category: str = None, 
            user_id: int = None, **kwargs) -> str:
    """
    Get translated text for a key.
    
    Args:
        key: The translation key.
        lang: The language code. If None, uses user_id to determine language.
        category: The category to look in. If None, searches all categories.
        user_id: The user's Telegram ID to determine language preference.
        **kwargs: Formatting arguments.
        
    Returns:
        The translated text.
    """
    return _localization_manager.get_text(key, lang, category, user_id, **kwargs)

def get_language(user_id: int) -> str:
    """
    Get the user's preferred language.
    
    Args:
        user_id: The user's Telegram ID.
        
    Returns:
        The user's language code.
    """
    return _localization_manager.get_language(user_id)

def set_language(user_id: int, language: str) -> bool:
    """
    Set the user's preferred language.
    
    Args:
        user_id: The user's Telegram ID.
        language: The language code.
        
    Returns:
        True if successful, False otherwise.
    """
    return _localization_manager.set_language(user_id, language)

def get_language_name(lang_code: str) -> str:
    """
    Get the human-readable name of a language.
    
    Args:
        lang_code: The language code.
        
    Returns:
        The language name.
    """
    return _localization_manager.get_language_name(lang_code)

def get_available_languages() -> List[str]:
    """
    Get list of available language codes.
    
    Returns:
        List of language codes.
    """
    return _localization_manager.get_available_languages()

# Function alias for shorter syntax (like _() in gettext)
_ = get_text 