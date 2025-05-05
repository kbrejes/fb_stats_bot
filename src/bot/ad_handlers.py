"""
Ad-related handlers for the Telegram bot.
"""
import logging
from typing import List, Dict, Any, Union, Optional

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandObject
from aiogram.exceptions import TelegramBadRequest
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from src.api.facebook import FacebookAdsClient, FacebookAdsApiError
from src.data.processor import DataProcessor
from src.utils.bot_helpers import fix_user_id, check_token_validity
from src.bot.keyboards import build_ad_keyboard
from src.bot.common import process_ads_list

# Create a router for ad handlers
router = Router()
logger = logging.getLogger(__name__)

@router.message(Command("ads"))
async def cmd_ads(message: Message, command: CommandObject):
    """
    Handle the /ads command.
    
    Args:
        message: The message object.
        command: The command object containing arguments.
    """
    if not command.args:
        await message.answer(
            "⚠️ Необходимо указать ID кампании.\n"
            "Пример использования: /ads 12345678\n\n"
            "Используйте команду /campaigns [id_аккаунта] для получения списка доступных кампаний."
        )
        return
        
    campaign_id = command.args
    user_id = message.from_user.id
    
    # Ensure we're not using the bot ID
    user_id = await fix_user_id(user_id)
    
    # Check token validity
    is_valid, _ = await check_token_validity(user_id)
    
    if not is_valid:
        await message.answer(
            "⚠️ Ваш токен доступа истек или отсутствует. Пожалуйста, используйте команду /auth для авторизации."
        )
        return
    
    await message.answer(f"🔄 Загружаем список объявлений для кампании {campaign_id}...", parse_mode=None)
    
    try:
        await process_ads_list(message, campaign_id, user_id)
    except Exception as e:
        logger.error(f"Unexpected error in ads: {str(e)}")
        await message.answer(f"⚠️ Произошла ошибка: {str(e)}", parse_mode=None)


@router.callback_query(F.data.startswith("ad:"))
async def process_ad_callback(callback: CallbackQuery):
    """
    Handle ad selection callback.
    
    Args:
        callback: The callback query.
    """
    ad_id = callback.data.split(':')[1]
    user_id = callback.from_user.id
    
    try:
        await callback.answer()
    except Exception as e:
        logger.warning(f"Error answering callback: {str(e)}")
        # Continue even if we can't answer the callback
        pass
    
    # Ensure we're not using the bot ID
    user_id = await fix_user_id(user_id)
    
    # Check token validity
    is_valid, _ = await check_token_validity(user_id)
    
    if not is_valid:
        try:
            # Создаем клавиатуру для возврата
            builder = InlineKeyboardBuilder()
            button_count = 0
            
            builder.add(InlineKeyboardButton(
                text="↩️ Назад к объявлениям",
                callback_data="menu:ads"
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
            logger.error(f"Error sending token expired message: {str(e)}")
        return
    
    # Show loading message
    try:
        await callback.message.edit_text(f"🔄 Загружаем статистику для объявления {ad_id}...", parse_mode=None)
    except Exception as e:
        logger.error(f"Error updating message in ad callback: {str(e)}")
    
    # Get ad statistics
    try:
        fb_client = FacebookAdsClient(user_id)
        insights = await fb_client.get_ad_insights(ad_id)
        
        if not insights:
            await callback.message.edit_text(
                "⚠️ Не найдена статистика для указанного объявления.",
                parse_mode=None
            )
            return
        
        # Format insights
        formatted_insights = DataProcessor.format_insights(insights)
        
        # Create keyboard
        builder = InlineKeyboardBuilder()
        button_count = 0
        
        builder.add(InlineKeyboardButton(
            text="↩️ Назад к объявлениям",
            callback_data="menu:ads"
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
            f"📊 Статистика для объявления {ad_id}:\n\n{formatted_insights}",
            parse_mode=None,
            reply_markup=builder.as_markup()
        )
        
    except Exception as e:
        logger.error(f"Error getting ad insights: {str(e)}")
        
        # Создаем клавиатуру для возврата при ошибке
        builder = InlineKeyboardBuilder()
        button_count = 0
        
        builder.add(InlineKeyboardButton(
            text="↩️ Назад к объявлениям",
            callback_data="menu:ads"
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
            f"⚠️ Ошибка при получении статистики: {str(e)}",
            parse_mode=None,
            reply_markup=builder.as_markup()
        ) 