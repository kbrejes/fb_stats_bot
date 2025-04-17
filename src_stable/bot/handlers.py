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

from src.bot.keyboards import build_main_menu_keyboard

# Create a router for common handlers
router = Router()
logger = logging.getLogger(__name__)

@router.message(Command("start"))
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
        "Для начала работы вам необходимо авторизоваться с помощью команды /auth.\n\n"
        "Используйте /help для получения списка всех доступных команд.",
        parse_mode="HTML"
    )

@router.message(Command("help"))
async def cmd_help(message: Message):
    """
    Handle the /help command.
    
    Args:
        message: The message object.
    """
    await message.answer(
        "📚 <b>Доступные команды:</b>\n\n"
        "/start - Приветственное сообщение и информация о боте\n"
        "/auth - Авторизация в Facebook\n"
        "/accounts - Список ваших рекламных аккаунтов\n"
        "/campaigns [id_аккаунта] - Список кампаний для аккаунта\n"
        "/ads [id_кампании] - Список объявлений для кампании\n"
        "/stats [id_объекта] [период] - Получение статистики\n"
        "/export - Экспорт данных в различных форматах\n"
        "/menu - Показать главное меню\n"
        "/help - Показать эту справку",
        parse_mode="HTML"
    )

@router.message(Command("menu"))
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

@router.callback_query(F.data.startswith("back:"))
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