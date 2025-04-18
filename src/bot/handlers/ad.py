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
from src.utils.error_handlers import handle_exceptions, api_error_handler

# Create a router for ad handlers
router = Router()
logger = logging.getLogger(__name__)

@router.message(Command("ads"))
@handle_exceptions(notify_user=True, log_error=True)
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
    
    # Отправка сообщения о загрузке и сохранение объекта сообщения
    loading_msg = await message.answer(f"🔄 Загружаем список объявлений для кампании {campaign_id}...", parse_mode=None)
    
    try:
        fb_client = FacebookAdsClient(user_id)
        ads = await fb_client.get_ads(campaign_id)
        
        if not ads:
            # Обновляем сообщение о загрузке
            await loading_msg.edit_text(
                "⚠️ Не найдено объявлений для указанной кампании. "
                "Возможно, кампания не содержит активных объявлений или у вас нет прав доступа."
            )
            return
        
        # Format ads data
        formatted_ads = DataProcessor.format_ads(ads)
        
        # Message might be too long for one message
        ad_parts = DataProcessor.truncate_for_telegram(formatted_ads)
        
        # Обновляем сообщение о загрузке с первой частью данных
        try:
            await loading_msg.edit_text(
                f"📊 Объявления для кампании {campaign_id} ({len(ads)}):\n\n```\n{ad_parts[0]}\n```",
                parse_mode="Markdown",
                reply_markup=build_ad_keyboard(ads, campaign_id)
            )
        except Exception as markdown_error:
            logger.error(f"Markdown error: {str(markdown_error)}")
            # Try without parse_mode if markdown fails
            await loading_msg.edit_text(
                f"📊 Объявления для кампании {campaign_id} ({len(ads)}):\n\n{ad_parts[0]}",
                reply_markup=build_ad_keyboard(ads, campaign_id)
            )
        
        # Отправляем дополнительные части, если они есть
        for part in ad_parts[1:]:
            try:
                await message.answer(
                    f"```\n{part}\n```",
                    parse_mode="Markdown"
                )
            except Exception as markdown_error:
                logger.error(f"Markdown error: {str(markdown_error)}")
                # Try without parse_mode if markdown fails
                await message.answer(part)
                
    except FacebookAdsApiError as e:
        # Handle API errors
        logger.error(f"Facebook API error in ads: {e.message} (code: {e.code})")
        if e.code == "TOKEN_EXPIRED":
            await loading_msg.edit_text(
                "⚠️ Ваш токен доступа истек. Пожалуйста, пройдите авторизацию заново с помощью команды /auth.",
                parse_mode=None
            )
        else:
            logger.error(f"Facebook API error: {e.message} (code: {e.code})")
            await loading_msg.edit_text(f"⚠️ Ошибка API Facebook: {e.message}", parse_mode=None)
            
    except Exception as e:
        logger.error(f"Unexpected error in ads: {str(e)}")
        await loading_msg.edit_text(f"⚠️ Произошла ошибка: {str(e)}", parse_mode=None)


@handle_exceptions(notify_user=True, log_error=True)
async def process_ads(callback: CallbackQuery, campaign_id: str, user_id: int):
    """
    Process ads for the selected campaign.
    
    Args:
        callback: The callback query.
        campaign_id: The campaign ID.
        user_id: The user ID.
    """
    try:
        fb_client = FacebookAdsClient(user_id)
        ads = await fb_client.get_ads(campaign_id)
        
        if not ads:
            await callback.message.edit_text(
                "⚠️ Не найдено объявлений для указанной кампании. "
                "Возможно, кампания не содержит активных объявлений или у вас нет прав доступа.",
                parse_mode=None
            )
            return
        
        # Format ads data
        formatted_ads = DataProcessor.format_ads(ads)
        
        # Message might be too long for one message
        ad_parts = DataProcessor.truncate_for_telegram(formatted_ads)
        
        # Edit the original message with the first part
        try:
            await callback.message.edit_text(
                f"📊 Объявления для кампании {campaign_id} ({len(ads)}):\n\n```\n{ad_parts[0]}\n```",
                parse_mode="Markdown",
                reply_markup=build_ad_keyboard(ads, campaign_id)
            )
        except Exception as markdown_error:
            print(f"DEBUG: Markdown error in process_ads: {str(markdown_error)}")
            # Try without parse_mode if markdown fails
            await callback.message.edit_text(
                f"📊 Объявления для кампании {campaign_id} ({len(ads)}):\n\n{ad_parts[0]}",
                reply_markup=build_ad_keyboard(ads, campaign_id)
            )
        
        # Send additional parts as new messages if any
        for i in range(1, len(ad_parts)):
            try:
                await callback.message.answer(
                    f"```\n{ad_parts[i]}\n```",
                    parse_mode="Markdown"
                )
            except Exception as markdown_error:
                print(f"DEBUG: Markdown error in additional parts: {str(markdown_error)}")
                # Try without parse_mode if markdown fails
                await callback.message.answer(ad_parts[i])
                
    except FacebookAdsApiError as e:
        # Handle API errors
        logger.error(f"Facebook API error in process_ads: {e.message} (code: {e.code})")
        if e.code == "TOKEN_EXPIRED":
            await callback.message.edit_text(
                "⚠️ Ваш токен доступа истек. Пожалуйста, пройдите авторизацию заново с помощью команды /auth.",
                parse_mode=None
            )
        else:
            logger.error(f"Facebook API error: {e.message} (code: {e.code})")
            await callback.message.edit_text(f"⚠️ Ошибка API Facebook: {e.message}", parse_mode=None)
            
    except Exception as e:
        logger.error(f"Unexpected error in process_ads: {str(e)}")
        await callback.message.edit_text(f"⚠️ Произошла ошибка: {str(e)}", parse_mode=None) 