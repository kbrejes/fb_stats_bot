"""
Main handlers file for the Telegram bot.
Contains menu navigation handlers and other general handlers.
"""
import logging
from typing import Dict, Any, List, Union, Optional

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandObject
from aiogram.exceptions import TelegramBadRequest
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton

from src.bot.keyboards import build_main_menu_keyboard
from src.utils.bot_helpers import fix_user_id
from src.storage.database import get_session
from src.storage.models import User

# Create a router for main handlers
router = Router()
logger = logging.getLogger(__name__)

@router.callback_query(F.data.startswith("menu:main"))
async def process_menu_main_callback(callback: CallbackQuery):
    """
    Handle main menu callback.
    
    Args:
        callback: The callback query.
    """
    try:
        await callback.answer()
    except Exception as e:
        logger.warning(f"Error answering callback: {str(e)}")
    
    try:
        await callback.message.edit_text(
            "📋 <b>Главное меню</b>\n\n"
            "Выберите нужный пункт меню:",
            parse_mode="HTML",
            reply_markup=build_main_menu_keyboard()
        )
    except Exception as e:
        logger.error(f"Error updating message in menu main: {str(e)}")

@router.callback_query(F.data.startswith("menu:campaign:"))
async def process_menu_campaign_callback(callback: CallbackQuery):
    """
    Handle campaign menu callback - this is the handler for "Back to campaign" button.
    
    Args:
        callback: The callback query.
    """
    # Extract campaign ID from callback data
    campaign_id = callback.data.split(':')[2]
    user_id = callback.from_user.id
    
    # Ensure we're not using the bot ID
    user_id = await fix_user_id(user_id)
    
    # Create a fake command object
    class FakeCommandObject:
        def __init__(self, args):
            self.args = args
    
    # We need to import this here to avoid circular imports
    from src.bot.handlers.ad import cmd_ads
    await cmd_ads(callback.message, FakeCommandObject(campaign_id))

@router.callback_query(F.data.startswith("menu:account:"))
async def process_menu_account_callback(callback: CallbackQuery):
    """
    Handle account menu callback - this is the handler for "Back to account" button.
    
    Args:
        callback: The callback query.
    """
    # Extract account ID from callback data
    account_id = callback.data.split(':')[2]
    user_id = callback.from_user.id
    
    # Ensure we're not using the bot ID
    user_id = await fix_user_id(user_id)
    
    # Create a fake command object
    class FakeCommandObject:
        def __init__(self, args):
            self.args = args
    
    # We need to import this here to avoid circular imports
    from src.bot.handlers.campaign import cmd_campaigns
    await cmd_campaigns(callback.message, FakeCommandObject(account_id))

@router.callback_query(F.data == "menu:campaigns")
async def process_menu_campaigns_callback(callback: CallbackQuery):
    """
    Handle campaigns menu callback - this is the handler for "Campaigns" button.
    Uses the account ID stored in user context.
    
    Args:
        callback: The callback query.
    """
    user_id = callback.from_user.id
    
    # Ensure we're not using the bot ID
    user_id = await fix_user_id(user_id)
    
    try:
        await callback.answer()
    except Exception as e:
        logger.warning(f"Error answering callback: {str(e)}")
    
    session = get_session()
    account_id = None
    
    try:
        user = session.query(User).filter_by(telegram_id=user_id).first()
        if user:
            # Get existing context
            context = user.get_context()
            # Get account_id from context
            account_id = context.get('current_account_id')
    except Exception as e:
        logger.error(f"Error getting account_id from context: {str(e)}")
    finally:
        session.close()
    
    if not account_id:
        try:
            await callback.message.edit_text(
                "⚠️ Не удалось найти ID аккаунта. Пожалуйста, выберите аккаунт с помощью команды /accounts.",
                parse_mode=None
            )
        except Exception as e:
            logger.error(f"Error updating message in menu campaigns: {str(e)}")
        return
    
    # Create a fake command object
    class FakeCommandObject:
        def __init__(self, args):
            self.args = args
    
    # We need to import this here to avoid circular imports
    from src.bot.handlers.campaign import cmd_campaigns
    await cmd_campaigns(callback.message, FakeCommandObject(account_id))

@router.callback_query(F.data == "menu:accounts")
async def process_menu_accounts_callback(callback: CallbackQuery):
    """
    Handle accounts menu callback - this is the handler for "Accounts" button.
    
    Args:
        callback: The callback query.
    """
    try:
        await callback.answer()
    except Exception as e:
        logger.warning(f"Error answering callback: {str(e)}")
    
    # We need to import this here to avoid circular imports
    from src.bot.handlers.account import cmd_accounts
    await cmd_accounts(callback.message)

@router.callback_query(F.data == "menu:help")
async def process_menu_help_callback(callback: CallbackQuery):
    """
    Handle help menu callback - this is the handler for "Help" button.
    
    Args:
        callback: The callback query.
    """
    try:
        await callback.answer()
    except Exception as e:
        logger.warning(f"Error answering callback: {str(e)}")
    
    # Return to main menu after showing help
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="🏠 Главное меню",
        callback_data="menu:main"
    ))
    
    try:
        await callback.message.edit_text(
            "📚 <b>Справка по командам</b>\n\n"
            "/start - Начало работы\n"
            "/auth - Авторизация в Facebook\n"
            "/accounts - Список доступных рекламных аккаунтов\n"
            "/campaigns [ID аккаунта] - Список кампаний в указанном аккаунте\n"
            "/ads [ID кампании] - Список объявлений в указанной кампании\n"
            "/language - Изменить язык бота\n"
            "/menu - Открыть главное меню\n",
            parse_mode="HTML",
            reply_markup=builder.as_markup()
        )
    except Exception as e:
        logger.error(f"Error updating message in menu help: {str(e)}")

@router.callback_query(F.data.startswith("empty:"))
async def process_empty_callback(callback: CallbackQuery):
    """
    Handle empty callback - This is used for placeholder buttons.
    
    Args:
        callback: The callback query.
    """
    try:
        await callback.answer()
    except Exception as e:
        logger.warning(f"Error answering callback: {str(e)}")
    
    # Nothing to do here, just clear the "loading" indicator 