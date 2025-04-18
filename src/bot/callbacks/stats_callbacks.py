"""
Statistics callback handlers for the Facebook Ads Telegram Bot.
"""
import logging
from typing import Dict, Any, List, Union, Optional
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest

from src.api.facebook import FacebookAdsClient
from src.storage.database import get_session
from src.storage.models import User
from src.utils.message_formatter import format_insights, format_campaign_table
from src.utils.localization import get_text, get_language, fix_user_id, _
from src.bot.keyboards import build_date_preset_keyboard
from src.utils.error_handlers import handle_exceptions, api_error_handler

# Setup logger
logger = logging.getLogger(__name__)

# Create a router for stats callbacks
stats_router = Router()

@stats_router.callback_query(F.data.startswith("stats:"))
@handle_exceptions(notify_user=True, log_error=True)
async def stats_callback(callback: CallbackQuery):
    """
    Handle statistics request callbacks.
    Callback data format: stats:object_type:object_id:date_preset
    """
    try:
        await callback.answer()
    except Exception as e:
        logger.warning(f"Error answering stats callback: {str(e)}")
        # Continue even if we can't answer the callback
        pass
    
    # Get the user ID
    user_id = callback.from_user.id
    
    # Fix for the issue where bot ID might be used
    if user_id == 8113924050 or str(user_id) == "8113924050":
        from src.storage.database import get_session
        from src.storage.models import User
        
        # Try to find a valid user
        session = get_session()
        try:
            user = session.query(User).filter(User.telegram_id != 8113924050).first()
            if user:
                print(f"DEBUG: Replacing bot ID with user ID in stats callback: {user.telegram_id}")
                user_id = user.telegram_id
        except Exception as e:
            print(f"DEBUG: Error finding alternative user in stats callback: {str(e)}")
        finally:
            session.close()
    
    parts = callback.data.split(":")
    if len(parts) < 4:
        await callback.message.edit_text("❌ Invalid stats request format.")
        return
    
    _, object_type, object_id, date_preset = parts[:4]
    
    # Get user's language
    lang = get_language(user_id)
    
    # Show loading message
    try:
        await callback.message.edit_text(get_text("loading_stats", lang=lang, category="stats"), parse_mode="HTML")
    except TelegramBadRequest:
        # Message was deleted or can't be edited
        return
    
    client = FacebookAdsClient(user_id)  # Use the fixed user_id
    
    try:
        insights = []
        object_name = None
        
        # Get insights based on object type
        if object_type == "account":
            insights = await client.get_account_insights(object_id, date_preset)
            # Try to get account name
            try:
                accounts = await client.get_ad_accounts()
                for account in accounts:
                    if account.get('id') == object_id:
                        object_name = account.get('name', object_id)
                        break
            except:
                object_name = object_id
        elif object_type == "campaign":
            insights = await client.get_campaign_insights(object_id, date_preset)
            # Use campaign ID if name not available
            object_name = object_id
        elif object_type == "adset":
            insights = await client.get_adset_insights(object_id, date_preset)
            object_name = object_id
        elif object_type == "ad":
            insights = await client.get_ad_insights(object_id, date_preset)
            object_name = object_id
        elif object_type == "account_campaigns":
            # Специальный тип для таблицы статистики всех кампаний аккаунта
            # Сначала получаем список всех кампаний
            campaigns = await client.get_campaigns(object_id)
            
            if not campaigns:
                builder = InlineKeyboardBuilder()
                button_count = 0
                
                builder.add(InlineKeyboardButton(
                    text=get_text("back_to_account", lang=lang, category="menu"),
                    callback_data=f"menu:account:{object_id}"
                ))
                button_count += 1
                
                builder.add(InlineKeyboardButton(
                    text=get_text("main_menu", lang=lang, category="menu"),
                    callback_data="menu:main"
                ))
                button_count += 1
                
                # Add empty button for even grid if needed
                if button_count % 2 != 0:
                    builder.add(InlineKeyboardButton(
                        text=" ",
                        callback_data="empty:action"
                    ))
                
                # Set up 2-button grid
                builder.adjust(2)
                
                await callback.message.edit_text(
                    get_text("no_campaigns_found", lang=lang, category="stats"),
                    reply_markup=builder.as_markup()
                )
                return
            
            # Теперь получаем insights для каждой кампании
            all_insights = []
            for campaign in campaigns:
                campaign_id = campaign.get('id')
                if campaign_id:
                    try:
                        campaign_insights = await client.get_campaign_insights(campaign_id, date_preset)
                        # Добавляем ID кампании в каждый insight для последующей группировки
                        for insight in campaign_insights:
                            insight['campaign_id'] = campaign_id
                        all_insights.extend(campaign_insights)
                    except Exception as e:
                        logger.warning(f"Error getting insights for campaign {campaign_id}: {str(e)}")
            
            insights = all_insights
            
            # Попробуем получить имя аккаунта
            try:
                accounts = await client.get_ad_accounts()
                for account in accounts:
                    if account.get('id') == object_id:
                        object_name = account.get('name', object_id)
                        break
            except:
                object_name = object_id
        else:
            await callback.message.edit_text(f"❌ Unknown object type: {object_type}")
            return
            
        if not insights:
            # Create navigation keyboard
            builder = InlineKeyboardBuilder()
            button_count = 0
            
            builder.add(InlineKeyboardButton(
                text=get_text("back_to_accounts", lang=lang, category="menu"),
                callback_data="menu:accounts"
            ))
            button_count += 1
            
            builder.add(InlineKeyboardButton(
                text=get_text("main_menu", lang=lang, category="menu"),
                callback_data="menu:main"
            ))
            button_count += 1
            
            # Add empty button for even grid if needed
            if button_count % 2 != 0:
                builder.add(InlineKeyboardButton(
                    text=" ",
                    callback_data="empty:action"
                ))
            
            # Set up 2-button grid
            builder.adjust(2)
            
            await callback.message.edit_text(
                get_text("no_stats_found", lang=lang, category="stats", 
                        object_type=get_text(object_type.replace('_campaigns', ''), lang=lang, category="common")),
                reply_markup=builder.as_markup()
            )
            return
        
        # If object name is available, use it in the insights header
        display_name = object_name or object_id
        
        # Limit name length for display
        if len(display_name) > 40:
            display_name = display_name[:37] + "..."
        
        # Format insights data for display
        if object_type == "account_campaigns":
            # Используем специальный форматтер для таблицы статистики кампаний
            formatted_text = format_campaign_table(campaigns, insights, date_preset, user_id)
        else:
            formatted_text = format_insights(insights, object_type, date_preset, user_id)
        
        # Try to improve message with object name if available
        if object_name and formatted_text:
            try:
                # Formatting insights with display name
                display_name = object_name
                if len(display_name) > 20:
                    display_name = display_name[:17] + "..."
                
                # Fix header with object name
                obj_type_display = get_text(object_type, lang=lang, category="common").capitalize()
                if formatted_text.startswith(f"<b>{get_text('insights_for', lang=lang, category='stats', type=obj_type_display, name='')}</b>"):
                    # Get beginning of the string up to the first </b> tag, then append new text after
                    old_header = f"<b>{get_text('insights_for', lang=lang, category='stats', type=obj_type_display, name='')}</b>\n"
                    new_header = f"<b>{get_text('insights_for', lang=lang, category='stats', type=obj_type_display, name=display_name)}</b>\n"
                    formatted_text = formatted_text.replace(old_header, new_header)
            except Exception as e:
                logger.error(f"Error formatting object name: {str(e)}")
        
        # Create navigation buttons
        builder = InlineKeyboardBuilder()
        button_count = 0
        
        # Back buttons based on object type
        if object_type == "account":
            builder.add(InlineKeyboardButton(
                text=get_text("back_to_accounts", lang=lang, category="menu"),
                callback_data="menu:accounts"
            ))
        elif object_type == "campaign":
            account_id = object_id.split('_')[0] if '_' in object_id else None
            if account_id:
                builder.add(InlineKeyboardButton(
                    text=get_text("back_to_campaigns", lang=lang),
                    callback_data=f"menu:campaigns:{account_id}"
                ))
            else:
                builder.add(InlineKeyboardButton(
                    text=get_text("back_to_accounts", lang=lang, category="menu"),
                    callback_data="menu:accounts"
                ))
        elif object_type == "account_campaigns":
            builder.add(InlineKeyboardButton(
                text="↩️ Назад к аккаунту",
                callback_data=f"menu:account:{object_id}"
            ))
        else:
            builder.add(InlineKeyboardButton(
                text=get_text("back_to_accounts", lang=lang, category="menu"),
                callback_data="menu:accounts"
            ))
        
        button_count += 1
        
        # Main menu button
        builder.add(InlineKeyboardButton(
            text=get_text("main_menu", lang=lang, category="menu"),
            callback_data="menu:main"
        ))
        button_count += 1
        
        # Add empty button for even grid if needed
        if button_count % 2 != 0:
            builder.add(InlineKeyboardButton(
                text=" ",
                callback_data="empty:action"
            ))
        
        # Set up 2-button grid
        builder.adjust(2)
        
        # Send the formatted insights
        await callback.message.edit_text(
            formatted_text, 
            parse_mode="HTML",
            reply_markup=builder.as_markup()
        )
        
    except Exception as e:
        logger.error(f"Error in stats_callback: {str(e)}")
        
        # Create navigation keyboard even on error
        builder = InlineKeyboardBuilder()
        button_count = 0
        
        builder.add(InlineKeyboardButton(
            text=get_text("back_to_accounts", lang=lang, category="menu"),
            callback_data="menu:accounts"
        ))
        button_count += 1
        
        builder.add(InlineKeyboardButton(
            text=get_text("main_menu", lang=lang, category="menu"),
            callback_data="menu:main"
        ))
        button_count += 1
        
        # Если нечетное количество кнопок, добавляем пустую для поддержания сетки
        if button_count % 2 != 0:
            builder.add(InlineKeyboardButton(
                text=" ",
                callback_data="empty:action"
            ))
        
        builder.adjust(2)
        
        await callback.message.edit_text(
            f"❌ {get_text('error_fetching_stats', lang=lang, category='errors')}: {str(e)}",
            reply_markup=builder.as_markup()
        ) 