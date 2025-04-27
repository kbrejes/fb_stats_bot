"""
Language manager for the Telegram bot.
Handles translations and language settings.
"""
from typing import Dict, Any, Optional
import logging
from src.storage.database import get_session
from src.storage.models import User

logger = logging.getLogger(__name__)

# Supported languages
SUPPORTED_LANGUAGES = ["ru", "en"]
DEFAULT_LANGUAGE = "ru"

# User language settings cache
_user_languages: Dict[int, str] = {}

# Translation dictionaries
translations = {
    "ru": {
        # General
        "loading_stats": "⏳ Загрузка статистики...",
        "no_stats_found": "❌ Статистика не найдена для этого {object_type}.",
        "no_campaigns_found": "❌ Кампании не найдены для этого аккаунта.",
        "back_to_accounts": "↩️ Назад к аккаунтам",
        "back_to_account": "↩️ Назад к аккаунту",
        "back_to_campaigns": "↩️ Назад к кампаниям",
        "main_menu": "🌏 Меню",
        "error_fetching_stats": "Ошибка при получении статистики",
        "error_fetching_campaigns": "Ошибка при получении кампаний",
        "view_campaigns": "👁 Просмотр кампаний",
        "export_account_data": "📤 Экспорт данных",
        "account_menu": "Меню аккаунта",
        
        # Insights
        "insights_for": "📊 Статистика для {type}: <b>{name}</b>",
        "period": "Период",
        "summary": "Сводка",
        "impressions": "Показы",
        "clicks": "Клики",
        "reach": "Охват",
        "spend": "Расходы",
        "ctr": "CTR",
        "cpm": "CPM",
        "cpc": "CPC",
        "conversion_data": "Данные о конверсиях",
        "custom_conversions": "Пользовательские конверсии",
        "cost": "Стоимость",
        "est_cost": "Примерная стоимость",
        "all_conversions": "Все конверсии",
        "export_note": "Используйте кнопки экспорта ниже для скачивания данных в разных форматах.",
        
        # Object types
        "account": "аккаунта",
        "campaign": "кампании",
        "adset": "группы объявлений",
        "ad": "объявления",
        "account_campaigns": "кампаний аккаунта",
        
        # Date presets
        "today": "Сегодня",
        "yesterday": "Вчера",
        "last_3d": "Последние 3 дня",
        "last_7d": "Последние 7 дней",
        "last_14d": "Последние 14 дней",
        "last_30d": "Последние 30 дней",
        "this_month": "Текущий месяц",
        "last_month": "Прошлый месяц",
        
        # Conversion types
        "link_clicks": "Клики по ссылкам",
        "landing_page_view": "Просмотры целевой страницы",
        "lead": "Лиды",
        "purchase": "Покупки",
        "offsite_conversion.fb_pixel_lead": "Лиды (пиксель)",
        "offsite_conversion.fb_pixel_purchase": "Покупки (пиксель)"
    },
    "en": {
        # General
        "loading_stats": "⏳ Loading statistics...",
        "no_stats_found": "❌ No statistics found for this {object_type}.",
        "no_campaigns_found": "❌ No campaigns found for this account.",
        "back_to_accounts": "↩️ Back to accounts",
        "back_to_account": "↩️ Back to account",
        "back_to_campaigns": "↩️ Back to campaigns",
        "main_menu": "🏠 Main menu",
        "error_fetching_stats": "Error fetching statistics",
        "error_fetching_campaigns": "Error fetching campaigns",
        "view_campaigns": "👁 View campaigns",
        "export_account_data": "📤 Export data",
        "account_menu": "Account menu",
        
        # Insights
        "insights_for": "📊 Insights for {type}: <b>{name}</b>",
        "period": "Period",
        "summary": "Summary",
        "impressions": "Impressions",
        "clicks": "Clicks",
        "reach": "Reach",
        "spend": "Spend",
        "ctr": "CTR",
        "cpm": "CPM",
        "cpc": "CPC",
        "conversion_data": "Conversion Data",
        "custom_conversions": "Custom Conversions",
        "cost": "Cost",
        "est_cost": "Est. Cost",
        "all_conversions": "All Conversions",
        "export_note": "Use the export buttons below to download this data in different formats.",
        
        # Object types
        "account": "account",
        "campaign": "campaign",
        "adset": "ad set",
        "ad": "ad",
        "account_campaigns": "account campaigns",
        
        # Date presets
        "today": "Today",
        "yesterday": "Yesterday",
        "last_3d": "Last 3 days",
        "last_7d": "Last 7 days",
        "last_14d": "Last 14 days",
        "last_30d": "Last 30 days",
        "this_month": "This month",
        "last_month": "Last month",
        
        # Conversion types
        "link_clicks": "Link Clicks",
        "landing_page_view": "Landing Page Views",
        "lead": "Leads",
        "purchase": "Purchases",
        "offsite_conversion.fb_pixel_lead": "Pixel Leads",
        "offsite_conversion.fb_pixel_purchase": "Pixel Purchases"
    }
}

def get_language(user_id: int) -> str:
    """
    Get the user's preferred language.
    
    Args:
        user_id: The user's Telegram ID.
        
    Returns:
        The user's language code ('ru' or 'en').
    """
    # Check cache first
    if user_id in _user_languages:
        return _user_languages[user_id]
    
    # Try to get from database
    session = get_session()
    try:
        user = session.query(User).filter_by(telegram_id=user_id).first()
        if user and hasattr(user, 'language'):
            lang = user.language
            # Cache the result
            _user_languages[user_id] = lang
            return lang
    except Exception as e:
        logger.error(f"Error getting user language: {str(e)}")
    finally:
        session.close()
    
    # Default to Russian
    return DEFAULT_LANGUAGE

def set_language(user_id: int, language: str) -> bool:
    """
    Set the user's preferred language.
    
    Args:
        user_id: The user's Telegram ID.
        language: The language code ('ru' or 'en').
        
    Returns:
        True if successful, False otherwise.
    """
    if language not in SUPPORTED_LANGUAGES:
        return False
    
    # Update cache
    _user_languages[user_id] = language
    
    # Update database
    session = get_session()
    try:
        user = session.query(User).filter_by(telegram_id=user_id).first()
        if user:
            user.language = language
            session.commit()
            return True
    except Exception as e:
        logger.error(f"Error setting user language: {str(e)}")
        session.rollback()
    finally:
        session.close()
    
    return False

def get_text(key: str, language: str, **kwargs) -> str:
    """
    Get translated text for a key.
    
    Args:
        key: The translation key.
        language: The language code.
        **kwargs: Formatting arguments.
        
    Returns:
        The translated text.
    """
    if language not in SUPPORTED_LANGUAGES:
        language = DEFAULT_LANGUAGE
    
    lang_dict = translations.get(language, translations[DEFAULT_LANGUAGE])
    text = lang_dict.get(key, translations[DEFAULT_LANGUAGE].get(key, key))
    
    # Apply formatting if kwargs provided
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, ValueError):
            logger.error(f"Error formatting text for key {key} with args {kwargs}")
            return text
    
    return text

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