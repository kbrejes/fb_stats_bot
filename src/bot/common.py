"""
Common functions and utilities for bot handlers.
"""

import logging
from typing import Any, Dict, List, Optional, Union

from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton

from src.api.facebook import FacebookAdsClient
from src.data.processor import DataProcessor
from src.utils.bot_helpers import check_token_validity, fix_user_id

logger = logging.getLogger(__name__)


async def process_campaigns_list(
    message_or_callback: Union[Message, CallbackQuery], account_id: str, user_id: int
) -> None:
    """
    Process and display campaigns list.

    Args:
        message_or_callback: Message or CallbackQuery object
        account_id: Facebook account ID
        user_id: Telegram user ID
    """
    try:
        fb_client = FacebookAdsClient(user_id)
        campaigns = await fb_client.get_campaigns(account_id)

        if not campaigns:
            text = (
                "⚠️ Не найдено кампаний для указанного аккаунта. "
                "Возможно, аккаунт не содержит активных кампаний или у вас нет прав доступа."
            )
            if isinstance(message_or_callback, CallbackQuery):
                await message_or_callback.message.edit_text(text)
            else:
                await message_or_callback.answer(text)
            return

        # Format campaigns data
        formatted_campaigns = DataProcessor.format_campaigns(campaigns)
        campaign_parts = DataProcessor.truncate_for_telegram(formatted_campaigns)

        # Create keyboard
        keyboard = build_campaign_keyboard(campaigns)

        # Send message(s)
        for i, part in enumerate(campaign_parts):
            text = f"📊 Кампании для аккаунта {account_id} ({len(campaigns)}):\n\n```\n{part}\n```"

            if isinstance(message_or_callback, CallbackQuery):
                if i == 0:
                    await message_or_callback.message.edit_text(
                        text, parse_mode="Markdown", reply_markup=keyboard
                    )
                else:
                    await message_or_callback.message.answer(
                        f"```\n{part}\n```", parse_mode="Markdown"
                    )
            else:
                await message_or_callback.answer(
                    text,
                    parse_mode="Markdown",
                    reply_markup=keyboard if i == 0 else None,
                )

    except Exception as e:
        logger.error(f"Error processing campaigns list: {str(e)}")
        error_text = f"⚠️ Произошла ошибка: {str(e)}"

        if isinstance(message_or_callback, CallbackQuery):
            await message_or_callback.message.edit_text(error_text, parse_mode=None)
        else:
            await message_or_callback.answer(error_text, parse_mode=None)


async def process_ads_list(
    message_or_callback: Union[Message, CallbackQuery], campaign_id: str, user_id: int
) -> None:
    """
    Process and display ads list.

    Args:
        message_or_callback: Message or CallbackQuery object
        campaign_id: Facebook campaign ID
        user_id: Telegram user ID
    """
    try:
        fb_client = FacebookAdsClient(user_id)
        ads = await fb_client.get_ads(campaign_id)

        if not ads:
            text = (
                "⚠️ Не найдено объявлений для указанной кампании. "
                "Возможно, кампания не содержит активных объявлений или у вас нет прав доступа."
            )
            if isinstance(message_or_callback, CallbackQuery):
                await message_or_callback.message.edit_text(text)
            else:
                await message_or_callback.answer(text)
            return

        # Format ads data
        formatted_ads = DataProcessor.format_ads(ads)
        ad_parts = DataProcessor.truncate_for_telegram(formatted_ads)

        # Create keyboard
        keyboard = build_ads_keyboard(ads, campaign_id)

        # Send message(s)
        for i, part in enumerate(ad_parts):
            text = f"📊 Объявления для кампании {campaign_id} ({len(ads)}):\n\n```\n{part}\n```"

            if isinstance(message_or_callback, CallbackQuery):
                if i == 0:
                    await message_or_callback.message.edit_text(
                        text, parse_mode="Markdown", reply_markup=keyboard
                    )
                else:
                    await message_or_callback.message.answer(
                        f"```\n{part}\n```", parse_mode="Markdown"
                    )
            else:
                await message_or_callback.answer(
                    text,
                    parse_mode="Markdown",
                    reply_markup=keyboard if i == 0 else None,
                )

    except Exception as e:
        logger.error(f"Error processing ads list: {str(e)}")
        error_text = f"⚠️ Произошла ошибка: {str(e)}"

        if isinstance(message_or_callback, CallbackQuery):
            await message_or_callback.message.edit_text(error_text, parse_mode=None)
        else:
            await message_or_callback.answer(error_text, parse_mode=None)
