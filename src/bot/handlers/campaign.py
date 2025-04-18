"""
Campaign-related handlers for the Telegram bot.
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
from src.bot.keyboards import build_campaign_keyboard
from src.storage.database import get_session
from src.storage.models import User
from src.utils.error_handlers import handle_exceptions

# Create a router for campaign handlers
router = Router()
logger = logging.getLogger(__name__)

@router.message(Command("campaigns"))
@handle_exceptions(notify_user=True, log_error=True)
async def cmd_campaigns(message: Message, command: CommandObject):
    """
    Handle the /campaigns command.
    
    Args:
        message: The message object.
        command: The command object containing arguments.
    """
    if not command.args:
        await message.answer(
            "⚠️ Необходимо указать ID аккаунта.\n"
            "Пример использования: /campaigns act_12345678\n\n"
            "Используйте команду /accounts для получения списка доступных аккаунтов."
        )
        return
        
    account_id = command.args
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
    
    await message.answer(f"🔄 Загружаем список кампаний для аккаунта {account_id}...", parse_mode=None)
    
    try:
        fb_client = FacebookAdsClient(user_id)
        campaigns = await fb_client.get_campaigns(account_id)
        
        if not campaigns:
            await message.answer(
                "⚠️ Не найдено кампаний для указанного аккаунта. "
                "Возможно, аккаунт не содержит активных кампаний или у вас нет прав доступа."
            )
            return
        
        # Format campaigns data
        formatted_campaigns = DataProcessor.format_campaigns(campaigns)
        
        # Message might be too long for one message
        campaign_parts = DataProcessor.truncate_for_telegram(formatted_campaigns)
        
        for i, part in enumerate(campaign_parts):
            if i == 0:
                # First part with keyboard
                try:
                    await message.answer(
                        f"📊 Кампании для аккаунта {account_id} ({len(campaigns)}):\n\n```\n{part}\n```",
                        parse_mode="Markdown",
                        reply_markup=build_campaign_keyboard(campaigns)
                    )
                except Exception as markdown_error:
                    logger.error(f"Markdown error: {str(markdown_error)}")
                    # Try without parse_mode if markdown fails
                    await message.answer(
                        f"📊 Кампании для аккаунта {account_id} ({len(campaigns)}):\n\n{part}",
                        reply_markup=build_campaign_keyboard(campaigns)
                    )
            else:
                # Additional parts if any
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
        logger.error(f"Facebook API error in campaigns: {e.message} (code: {e.code})")
        if e.code == "TOKEN_EXPIRED":
            await message.answer(
                "⚠️ Ваш токен доступа истек. Пожалуйста, пройдите авторизацию заново с помощью команды /auth.",
                parse_mode=None
            )
        else:
            logger.error(f"Facebook API error: {e.message} (code: {e.code})")
            await message.answer(f"⚠️ Ошибка API Facebook: {e.message}", parse_mode=None)
            
    except Exception as e:
        logger.error(f"Unexpected error in campaigns: {str(e)}")
        await message.answer(f"⚠️ Произошла ошибка: {str(e)}", parse_mode=None)


@router.callback_query(F.data.startswith("campaign:"))
@handle_exceptions(notify_user=True, log_error=True)
async def process_campaign_callback(callback: CallbackQuery):
    """
    Handle campaign selection callback.
    
    Args:
        callback: The callback query.
    """
    campaign_id = callback.data.split(':')[1]
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
        print(f"DEBUG: User {user_id} token is invalid in campaign callback")
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
        await callback.message.edit_text(f"🔄 Загружаем список объявлений для кампании {campaign_id}...", parse_mode=None)
    except Exception as e:
        print(f"DEBUG: Error updating message in campaign callback: {str(e)}")
    
    # We need to import this here to avoid circular imports
    from src.bot.handlers.ad import process_ads
    
    # Save the campaign_id in the user's context
    session = get_session()
    try:
        user = session.query(User).filter_by(telegram_id=user_id).first()
        if user:
            # Get existing context
            context = user.get_context()
            # Update with current campaign_id
            context['current_campaign_id'] = campaign_id
            # Save updated context
            user.set_context(context)
            session.commit()
            print(f"DEBUG: Saved campaign_id {campaign_id} in user context")
    except Exception as e:
        print(f"DEBUG: Error saving campaign_id in context: {str(e)}")
    finally:
        session.close()
    
    # Process ads for the selected campaign
    try:
        await process_ads(callback, campaign_id, user_id)
    except Exception as e:
        print(f"DEBUG: Error processing ads for campaign {campaign_id}: {str(e)}")
        
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
            f"⚠️ Ошибка при загрузке объявлений: {str(e)}",
            parse_mode=None,
            reply_markup=builder.as_markup()
        )


async def process_campaigns(callback: CallbackQuery, account_id: str, user_id: int):
    """
    Process campaigns for the selected account.
    
    Args:
        callback: The callback query.
        account_id: The account ID.
        user_id: The user ID.
    """
    try:
        fb_client = FacebookAdsClient(user_id)
        campaigns = await fb_client.get_campaigns(account_id)
        
        if not campaigns:
            await callback.message.edit_text(
                "⚠️ Не найдено кампаний для указанного аккаунта. "
                "Возможно, аккаунт не содержит активных кампаний или у вас нет прав доступа.",
                parse_mode=None
            )
            return
            
        # Save the account_id in the user's context
        session = get_session()
        try:
            user = session.query(User).filter_by(telegram_id=user_id).first()
            if user:
                # Get existing context
                context = user.get_context()
                # Update with current account_id
                context['current_account_id'] = account_id
                # Save updated context
                user.set_context(context)
                session.commit()
                print(f"DEBUG: Saved account_id {account_id} in user context")
        except Exception as e:
            print(f"DEBUG: Error saving account_id in context: {str(e)}")
        finally:
            session.close()
        
        # Format campaigns data
        formatted_campaigns = DataProcessor.format_campaigns(campaigns)
        
        # Message might be too long for one message
        campaign_parts = DataProcessor.truncate_for_telegram(formatted_campaigns)
        
        # Edit the original message with the first part
        try:
            await callback.message.edit_text(
                f"📊 Кампании для аккаунта {account_id} ({len(campaigns)}):\n\n```\n{campaign_parts[0]}\n```",
                parse_mode="Markdown",
                reply_markup=build_campaign_keyboard(campaigns, account_id=account_id)
            )
        except Exception as markdown_error:
            print(f"DEBUG: Markdown error in process_campaigns: {str(markdown_error)}")
            # Try without parse_mode if markdown fails
            await callback.message.edit_text(
                f"📊 Кампании для аккаунта {account_id} ({len(campaigns)}):\n\n{campaign_parts[0]}",
                reply_markup=build_campaign_keyboard(campaigns, account_id=account_id)
            )
        
        # Send additional parts as new messages if any
        for i in range(1, len(campaign_parts)):
            try:
                await callback.message.answer(
                    f"```\n{campaign_parts[i]}\n```",
                    parse_mode="Markdown"
                )
            except Exception as markdown_error:
                print(f"DEBUG: Markdown error in additional parts: {str(markdown_error)}")
                # Try without parse_mode if markdown fails
                await callback.message.answer(campaign_parts[i])
                
    except FacebookAdsApiError as e:
        # Handle API errors
        logger.error(f"Facebook API error in process_campaigns: {e.message} (code: {e.code})")
        if e.code == "TOKEN_EXPIRED":
            await callback.message.edit_text(
                "⚠️ Ваш токен доступа истек. Пожалуйста, пройдите авторизацию заново с помощью команды /auth.",
                parse_mode=None
            )
        else:
            logger.error(f"Facebook API error: {e.message} (code: {e.code})")
            await callback.message.edit_text(f"⚠️ Ошибка API Facebook: {e.message}", parse_mode=None)
            
    except Exception as e:
        logger.error(f"Unexpected error in process_campaigns: {str(e)}")
        await callback.message.edit_text(f"⚠️ Произошла ошибка: {str(e)}", parse_mode=None) 