"""
Account-related handlers for the Telegram bot.
"""
import logging
from typing import List, Dict, Any, Union, Optional

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandObject, StateFilter
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton

from src.api.facebook import FacebookAdsClient, FacebookAdsApiError
from src.storage.database import get_session
from src.storage.models import User
from src.data.processor import DataProcessor
from src.utils.bot_helpers import fix_user_id, check_token_validity
from src.bot.keyboards import build_account_keyboard, build_date_preset_keyboard

# Create a router for account handlers
router = Router()
logger = logging.getLogger(__name__)

@router.message(Command("accounts"))
async def cmd_accounts(message: Message):
    """
    Handle the /accounts command.
    
    Args:
        message: The message object.
    """
    user_id = message.from_user.id
    
    # Debug output
    print(f"DEBUG: /accounts command received from user ID: {user_id}")
    
    # Ensure we're not using the bot ID
    user_id = await fix_user_id(user_id)
    
    # Check if user exists and has a valid token
    is_valid, expiration_date = await check_token_validity(user_id)
    
    if not is_valid:
        await message.answer(
            "⚠️ Ваш токен доступа истек или отсутствует. Пожалуйста, используйте команду /auth для авторизации."
        )
        return
        
    if expiration_date:
        print(f"DEBUG: Token expires at: {expiration_date}")
        
    await message.answer("🔄 Загружаем список ваших рекламных аккаунтов...")
    
    try:
        fb_client = FacebookAdsClient(user_id)
        accounts = await fb_client.get_ad_accounts()
        
        if not accounts:
            await message.answer(
                "⚠️ У вас нет доступных рекламных аккаунтов.\n"
                "Убедитесь, что ваша учетная запись Facebook имеет доступ к рекламным аккаунтам."
            )
            return
            
        # Создаем клавиатуру с кнопками аккаунтов
        try:
            # Create keyboard for accounts with additional stats button
            keyboard = build_account_keyboard(accounts, add_stats=True)
            
            await message.answer(
                "📊 <b>Выберите рекламный аккаунт:</b>",
                parse_mode="HTML",
                reply_markup=keyboard
            )
        except Exception as e:
            logger.error(f"Error creating account keyboard: {str(e)}")
            await message.answer(f"⚠️ Ошибка при создании клавиатуры: {str(e)}", parse_mode=None)
                
    except FacebookAdsApiError as e:
        # Handle API errors
        if e.code == "TOKEN_EXPIRED":
            await message.answer(
                "⚠️ Ваш токен доступа истек. Пожалуйста, пройдите авторизацию заново с помощью команды /auth.",
                parse_mode=None
            )
        else:
            logger.error(f"Facebook API error in accounts: {e.message} (code: {e.code})")
            await message.answer(f"⚠️ Ошибка API Facebook: {e.message}", parse_mode=None)
            
    except Exception as e:
        logger.error(f"Unexpected error in accounts: {str(e)}")
        await message.answer(f"⚠️ Произошла ошибка: {str(e)}", parse_mode=None)


@router.callback_query(F.data.startswith("account:"))
async def process_account_callback(callback: CallbackQuery):
    """
    Handle account selection callback.
    
    Args:
        callback: The callback query.
    """
    account_id = callback.data.split(':')[1]
    user_id = callback.from_user.id
    
    print(f"DEBUG: Process account callback - Account ID: {account_id}, User ID: {user_id}")
    
    try:
        await callback.answer()
    except Exception as e:
        logger.warning(f"Error answering callback: {str(e)}")
        # Continue even if we can't answer the callback
        pass
    
    # Ensure we're not using the bot ID
    user_id_before = user_id
    user_id = await fix_user_id(user_id)
    if user_id != user_id_before:
        print(f"DEBUG: User ID fixed from {user_id_before} to {user_id}")
    
    # Check token validity
    print(f"DEBUG: Checking token validity for user {user_id}")
    is_valid, expiration_date = await check_token_validity(user_id)
    print(f"DEBUG: Token valid: {is_valid}, expires: {expiration_date}")
    
    if not is_valid:
        print(f"DEBUG: User {user_id} token is invalid in account callback")
        try:
            # Создаем клавиатуру для возврата
            builder = InlineKeyboardBuilder()
            button_count = 0
            
            builder.add(InlineKeyboardButton(
                text="↩️ Назад к аккаунтам",
                callback_data="menu:accounts"
            ))
            button_count += 1
            
            builder.add(InlineKeyboardButton(
                text="🏠 Главное меню",
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
                "⚠️ Ваш токен доступа истек. Пожалуйста, пройдите авторизацию заново с помощью команды /auth.",
                parse_mode=None,
                reply_markup=builder.as_markup()
            )
        except Exception as e:
            print(f"DEBUG: Error sending token expired message: {str(e)}")
        return
    
    # Show loading message
    try:
        print(f"DEBUG: Showing loading message for account {account_id}")
        await callback.message.edit_text(f"🔄 Загружаем список кампаний для аккаунта {account_id}...", parse_mode=None)
    except Exception as e:
        print(f"DEBUG: Error updating message in account callback: {str(e)}")
    
    # We need to import this here to avoid circular imports
    from src.bot.handlers.campaign import process_campaigns
    
    # Process campaigns for the selected account
    print(f"DEBUG: Calling process_campaigns for account {account_id} and user {user_id}")
    try:
        await process_campaigns(callback, account_id, user_id)
        print(f"DEBUG: Successfully processed campaigns for account {account_id}")
    except Exception as e:
        print(f"DEBUG: Error in process_campaigns: {str(e)}")
        
        # Создаем клавиатуру для возврата при ошибке
        builder = InlineKeyboardBuilder()
        button_count = 0
        
        builder.add(InlineKeyboardButton(
            text="↩️ Назад к аккаунтам",
            callback_data="menu:accounts"
        ))
        button_count += 1
        
        builder.add(InlineKeyboardButton(
            text="🏠 Главное меню",
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
            f"⚠️ Ошибка при загрузке кампаний: {str(e)}",
            parse_mode=None,
            reply_markup=builder.as_markup()
        ) 