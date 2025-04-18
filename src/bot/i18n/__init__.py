"""
Internationalization module for the Facebook Ads Telegram Bot.
Provides translation functions and language support.
"""
import logging
from typing import Dict, Optional

# Logger
logger = logging.getLogger(__name__)

# Default language
DEFAULT_LANGUAGE = 'en'

# Current user locale - will be set in handlers before rendering messages
_current_locale = DEFAULT_LANGUAGE

# Translations dictionary
# This is a simple implementation, for production consider using gettext or other i18n libraries
_translations: Dict[str, Dict[str, str]] = {
    'en': {},  # English is default, no translation needed
    'ru': {
        # Common
        'Back': 'Назад',
        '⬅️ Back': '⬅️ Назад',
        '🏠 Main Menu': '🏠 Главное меню',
        '⬅️ Back to Main Menu': '⬅️ Назад в главное меню',
        'Cancel': 'Отмена',
        '❌ Cancel': '❌ Отмена',
        
        # Menu items
        '📋 Main Menu': '📋 Главное меню',
        '📊 My Accounts': '📊 Мои аккаунты',
        '🔎 Search': '🔎 Поиск',
        '⚙️ Settings': '⚙️ Настройки',
        'ℹ️ Help': 'ℹ️ Помощь',
        
        # Settings
        '🌐 Change Language': '🌐 Изменить язык',
        '🔔 Notification Settings': '🔔 Настройки уведомлений',
        '⬅️ Back to Settings': '⬅️ Назад к настройкам',
        '🔔 Notifications: ON': '🔔 Уведомления: ВКЛ',
        '🔕 Notifications: OFF': '🔕 Уведомления: ВЫКЛ',
        '⚙️ Advanced Settings': '⚙️ Расширенные настройки',
        
        # Stats
        'Today': 'Сегодня',
        'Yesterday': 'Вчера',
        'Last 3 days': 'Последние 3 дня',
        'Last 7 days': 'Последние 7 дней',
        'Last 30 days': 'Последние 30 дней',
        'This month': 'Текущий месяц',
        'Last month': 'Прошлый месяц',
        '📊 Stats': '📊 Статистика',
        '📊 Analytics': '📊 Аналитика',
        '📈 Performance': '📈 Производительность',
        '📤 Export': '📤 Экспорт',
        
        # Accounts
        '⬅️ Back to Accounts': '⬅️ Назад к аккаунтам',
        
        # Campaigns
        '⬅️ Back to Campaigns': '⬅️ Назад к кампаниям',
        
        # Ads
        '⬅️ Back to Campaign': '⬅️ Назад к кампании',
        '⬅️ Back to Ads': '⬅️ Назад к объявлениям',
        '🔍 Preview': '🔍 Предпросмотр',
        '🔄 Refresh': '🔄 Обновить',
        
        # Confirmation
        '✅ Yes': '✅ Да',
        '❌ No': '❌ Нет',
        
        # Welcome message
        '👋 Welcome to the Facebook Ads Bot!\n\nThis bot helps you manage and monitor your Facebook ad campaigns.\n\n'
        'To get started, please authenticate with your Facebook account.':
        '👋 Добро пожаловать в Facebook Ads Bot!\n\nЭтот бот поможет вам управлять и мониторить ваши рекламные кампании в Facebook.\n\n'
        'Для начала, пожалуйста, авторизуйтесь с вашим аккаунтом Facebook.'
    }
}


def set_user_locale(locale: str) -> None:
    """
    Set the current locale for translation.
    
    Args:
        locale: Language code (e.g., 'en', 'ru')
    """
    global _current_locale
    if locale in _translations:
        _current_locale = locale
    else:
        logger.warning(f"Unsupported locale: {locale}, using default: {DEFAULT_LANGUAGE}")
        _current_locale = DEFAULT_LANGUAGE


def _(text: str) -> str:
    """
    Translate text based on current locale.
    
    Args:
        text: Text to translate
        
    Returns:
        Translated text or original if translation not found
    """
    if _current_locale == DEFAULT_LANGUAGE:
        return text
        
    translation = _translations.get(_current_locale, {}).get(text)
    if translation:
        return translation
    
    # Return original text if no translation found
    return text


def get_current_locale() -> str:
    """
    Get the current locale.
    
    Returns:
        Current locale code
    """
    return _current_locale 