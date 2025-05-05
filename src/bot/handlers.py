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
from aiogram.fsm.context import FSMContext

from src.bot.keyboards import build_main_menu_keyboard, build_language_keyboard
from src.utils.languages import set_language, get_language, SUPPORTED_LANGUAGES
from src.utils.bot_helpers import fix_user_id
from src.storage.database import get_session
from src.storage.models import User, NotificationSettings
from config.settings import ADMIN_USERS

# Create a router for common handlers
router = Router()
logger = logging.getLogger(__name__)

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
        "/notifications - Управление уведомлениями\n"
        "/menu - Показать меню\n"
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
    user_id = await fix_user_id(message.from_user.id)
    session = get_session()
    
    try:
        # Получаем пользователя и его роль
        user = session.query(User).filter_by(telegram_id=user_id).first()
        if not user:
            await message.answer(
                "⚠️ Пользователь не найден. Используйте /start для начала работы.",
                parse_mode="HTML"
            )
            return
            
        await message.answer(
            "<b>Меню:</b>",
            parse_mode="HTML",
            reply_markup=build_main_menu_keyboard(user.role)
        )
    except Exception as e:
        logger.error(f"Error in menu command: {str(e)}")
        await message.answer(
            "❌ Произошла ошибка при открытии меню. Пожалуйста, попробуйте позже.",
            parse_mode="HTML"
        )
    finally:
        session.close()

@router.message(Command("language"))
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
async def process_menu_campaign_callback(callback: CallbackQuery):
    """
    Handle campaign menu callback - this is the handler for "Back to campaign" button.
    
    Args:
        callback: The callback query.
    """
    # Extract campaign ID from callback data
    campaign_id = callback.data.split(':')[2]
    user_id = callback.from_user.id
    
    try:
        await callback.answer()
    except Exception as e:
        logger.warning(f"Error answering callback: {str(e)}")
        # Continue even if we can't answer the callback
        pass
    
    # Fix user_id if needed
    user_id = await fix_user_id(user_id)
    
    # Get account_id from user context
    session = get_session()
    try:
        user = session.query(User).filter_by(telegram_id=user_id).first()
        if user:
            context = user.get_context()
            account_id = context.get('current_account_id')
            print(f"DEBUG: Found account_id {account_id} in context for user {user_id}")
    except Exception as e:
        print(f"DEBUG: Error getting account_id from context: {str(e)}")
    finally:
        session.close()
    
    if not account_id:
        # If we can't get the account_id from context, show an error message
        logger.warning(f"No account_id found in context for user {user_id}")
        try:
            builder = InlineKeyboardBuilder()
            button_count = 0
            
            builder.add(InlineKeyboardButton(
                text="⬅️",
                callback_data="menu:accounts"
            ))
            button_count += 1
            
            builder.add(InlineKeyboardButton(
                text="🌎 Меню",
                callback_data="menu:main"
            ))
            button_count += 1
            
            if button_count % 2 != 0:
                builder.add(InlineKeyboardButton(
                    text=" ",
                    callback_data="empty:action"
                ))
            
            builder.adjust(2)
            
            await callback.message.edit_text(
                "⚠️ Не удалось найти информацию об аккаунте. Пожалуйста, вернитесь к списку аккаунтов.",
                parse_mode=None,
                reply_markup=builder.as_markup()
            )
        except Exception as e:
            logger.error(f"Error showing error message: {str(e)}")
        return
    
    # Show loading message
    try:
        await callback.message.edit_text(f"🔄 Загружаем список кампаний для аккаунта {account_id}...", parse_mode=None)
    except Exception as e:
        logger.warning(f"Error updating message: {str(e)}")
    
    # Import and call process_campaigns
    from src.bot.campaign_handlers import process_campaigns
    await process_campaigns(callback, account_id, user_id)

@router.callback_query(F.data.startswith("menu:account:"))
async def process_menu_account_callback(callback: CallbackQuery):
    """
    Handle account menu callback - this is the handler for "Назад к аккаунту" button.
    
    Args:
        callback: The callback query.
    """
    try:
        await callback.answer()
    except Exception as e:
        logger.warning(f"Error answering callback: {str(e)}")
        # Continue even if we can't answer the callback
        pass
    
    # Import and call account_menu_callback
    from src.bot.callbacks import account_menu_callback
    await account_menu_callback(callback)

@router.callback_query(F.data == "menu:campaigns")
async def process_menu_campaigns_callback(callback: CallbackQuery):
    """
    Handle campaigns menu callback - this is the new handler for "Back to campaigns" button.
    
    Args:
        callback: The callback query.
    """
    try:
        await callback.answer()
    except Exception as e:
        logger.warning(f"Error answering callback: {str(e)}")
        # Continue even if we can't answer the callback
        pass
    
    # Import account_handlers to show list of accounts, then user will be able to select account and see campaigns
    from src.bot.account_handlers import cmd_accounts
    await cmd_accounts(callback.message)

@router.message(Command("notifications"))
async def cmd_notifications(message: Message):
    """
    Handle the /notifications command.
    Shows notification settings and control buttons.
    
    Args:
        message: The message object.
    """
    user_id = await fix_user_id(message.from_user.id)
    session = get_session()
    
    try:
        # Получаем текущие настройки уведомлений
        settings = session.query(NotificationSettings).filter_by(user_id=user_id).first()
        enabled = settings.enabled if settings else False
        
        # Импортируем функции для работы с уведомлениями
        from src.bot.notification_handlers import build_notification_keyboard, format_notification_settings
        
        await message.answer(
            format_notification_settings(settings),
            parse_mode="HTML",
            reply_markup=build_notification_keyboard(enabled).as_markup()
        )
    except Exception as e:
        logger.error(f"Error in notifications command: {str(e)}")
        await message.answer(
            "❌ Произошла ошибка при получении настроек уведомлений. Пожалуйста, попробуйте позже.",
            parse_mode="HTML"
        )
    finally:
        session.close()