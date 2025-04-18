"""
Common handlers for the Telegram bot.
Basic commands like start, help, menu, etc.
"""
import logging
from typing import Dict, Any, List, Union, Optional

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandObject
from aiogram.exceptions import TelegramBadRequest
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton

from src.bot.keyboards import build_main_menu_keyboard, build_language_keyboard
from src.utils.localization import get_text, get_language, set_language, _, SUPPORTED_LANGUAGES
from src.utils.bot_helpers import fix_user_id
from src.storage.database import get_session
from src.storage.models import User
from src.utils.error_handlers import handle_exceptions, api_error_handler

# Create a router for common handlers
router = Router()
logger = logging.getLogger(__name__)

@router.message(Command("start"))
@handle_exceptions(notify_user=True, log_error=True)
async def cmd_start(message: Message):
    """
    Handle the /start command.
    
    Args:
        message: The message object.
    """
    await message.answer(
        "👋 Привет! Я бот для работы с Facebook Ads.\n\n"
        "С моей помощью вы можете получать информацию о ваших рекламных аккаунтах, "
        "кампаниях и объявлениях, а также просматривать статистику.\n\n"
        "Для начала работы вам необходимо авторизоваться с помощью команды /auth.",
        parse_mode="HTML"
    )

@router.message(Command("menu"))
@handle_exceptions(notify_user=True, log_error=True)
async def cmd_menu(message: Message):
    """
    Handle the /menu command.
    
    Args:
        message: The message object.
    """
    await message.answer(
        "📋 <b>Главное меню</b>\n\n"
        "Выберите нужный пункт меню:",
        parse_mode="HTML",
        reply_markup=build_main_menu_keyboard()
    )

@router.message(Command("language"))
@handle_exceptions(notify_user=True, log_error=True)
async def cmd_language(message: Message):
    """
    Handle the /language command.
    
    Args:
        message: The message object.
    """
    user_id = message.from_user.id
    current_language = get_language(user_id)
    
    language_names = {
        "ru": "🇷🇺 Русский",
        "en": "🇬🇧 English"
    }
    
    current_language_name = language_names.get(current_language, current_language)
    
    await message.answer(
        f"🌐 <b>Язык / Language</b>\n\n"
        f"Текущий язык / Current language: <b>{current_language_name}</b>\n\n"
        f"Выберите язык / Choose your language:",
        parse_mode="HTML",
        reply_markup=build_language_keyboard()
    )

@router.callback_query(F.data.startswith("back:"))
@handle_exceptions(notify_user=True, log_error=True)
async def process_back_callback(callback: CallbackQuery):
    """
    Handle back button callback.
    
    Args:
        callback: The callback query.
    """
    back_data = callback.data.split(':')
    back_type = back_data[1]
    
    try:
        await callback.answer()
    except Exception as e:
        logger.warning(f"Error answering callback: {str(e)}")
        # Continue even if we can't answer the callback
        pass
    
    # First try to delete the current message to avoid cluttering the chat
    try:
        await callback.message.delete()
    except TelegramBadRequest as e:
        logger.warning(f"Could not delete message when going back: {str(e)}")
        # If we can't delete, we'll just edit the text later
        pass
    
    if back_type == "accounts":
        # Go back to accounts list
        from src.bot.account_handlers import cmd_accounts
        await cmd_accounts(callback.message)
    elif back_type == "campaign" and len(back_data) > 2:
        # Go back to campaign's ads
        campaign_id = back_data[2]
        
        # Create a fake command object
        class FakeCommandObject:
            def __init__(self, args):
                self.args = args
        
        from src.bot.ad_handlers import cmd_ads
        await cmd_ads(callback.message, FakeCommandObject(campaign_id))
    elif back_type == "account" and len(back_data) > 2:
        # Go back to account's campaigns
        account_id = back_data[2]
        
        # Create a fake command object
        class FakeCommandObject:
            def __init__(self, args):
                self.args = args
        
        from src.bot.campaign_handlers import cmd_campaigns
        await cmd_campaigns(callback.message, FakeCommandObject(account_id))
    elif back_type == "cancel":
        # We already tried to delete the message above, but if that failed, edit it
        try:
            await callback.message.edit_text("Операция отменена.")
            await callback.message.edit_reply_markup(None)
        except Exception as e:
            logger.warning(f"Could not edit message when canceling: {str(e)}")

@router.callback_query(F.data.startswith("language:"))
@handle_exceptions(notify_user=True, log_error=True)
async def process_language_callback(callback: CallbackQuery):
    """
    Handle language selection callback.
    
    Args:
        callback: The callback query.
    """
    language_code = callback.data.split(":")[1]
    user_id = callback.from_user.id
    
    try:
        await callback.answer()
    except Exception as e:
        logger.warning(f"Error answering callback: {str(e)}")
    
    if language_code in SUPPORTED_LANGUAGES:
        success = set_language(user_id, language_code)
        
        language_names = {
            "ru": "🇷🇺 Русский",
            "en": "🇬🇧 English"
        }
        
        if success:
            if language_code == "ru":
                await callback.message.edit_text(
                    "✅ Язык успешно изменен на Русский.\n\n"
                    "Используйте /menu для перехода в главное меню.",
                    reply_markup=build_main_menu_keyboard()
                )
            else:
                await callback.message.edit_text(
                    "✅ Language successfully changed to English.\n\n"
                    "Use /menu to go to the main menu.",
                    reply_markup=build_main_menu_keyboard()
                )
        else:
            await callback.message.edit_text(
                "❌ Error: Could not save language setting. Please try again later.",
                reply_markup=build_main_menu_keyboard()
            )
    else:
        await callback.message.edit_text(
            "❌ Error: Invalid language code.",
            reply_markup=build_main_menu_keyboard()
        )

@router.callback_query(F.data.startswith("menu:campaign:"))
@handle_exceptions(notify_user=True, log_error=True)
async def process_menu_campaign_callback(callback: CallbackQuery):
    """
    Handle campaign menu callback - this is the handler for "Back to campaign" button.
    
    Args:
        callback: The callback query.
    """
    # Extract campaign ID from callback data
    campaign_id = callback.data.split(':')[2]
    user_id = callback.from_user.id 