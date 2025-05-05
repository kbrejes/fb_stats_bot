"""
Callback query handlers for the Facebook Ads Telegram Bot.
"""
import json
import os
import logging
from typing import Dict, Any, List, Union, Optional
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest
import pandas as pd

from src.api.facebook import FacebookAdsClient
from src.storage.database import get_session
from src.storage.models import User, Cache, Account
from src.utils.export import export_data_to_csv, export_data_to_json, export_data_to_excel
from src.utils.message_formatter import format_insights, format_campaign_table
from src.utils.logger import get_logger
from src.utils.languages import get_text, get_language, fix_user_id
from src.bot.keyboards import build_date_preset_keyboard, build_main_menu_keyboard

# Setup logger
logger = logging.getLogger(__name__)

# Create a router for callback queries
callback_router = Router()

@callback_router.callback_query(F.data.startswith("stats:"))
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
        await callback.message.edit_text(get_text("loading_stats", lang), parse_mode="HTML")
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
                    text=get_text("back_to_account", lang),
                    callback_data=f"menu:account:{object_id}"
                ))
                button_count += 1
                
                builder.add(InlineKeyboardButton(
                    text=get_text("main_menu", lang),
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
                    get_text("no_campaigns_found", lang),
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
                text=get_text("back_to_accounts", lang),
                callback_data="menu:accounts"
            ))
            button_count += 1
            
            builder.add(InlineKeyboardButton(
                text=get_text("main_menu", lang),
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
                get_text("no_stats_found", lang, object_type=get_text(object_type.replace('_campaigns', ''), lang)),
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
        
        # Replace the header with object name if needed
        if object_type != "account_campaigns":
            obj_type_display = get_text(object_type, lang).capitalize()
            if formatted_text.startswith(f"<b>{get_text('insights_for', lang, type=obj_type_display, name='')}</b>"):
                # Replace header with object name included
                old_header = f"<b>{get_text('insights_for', lang, type=obj_type_display, name='')}</b>\n"
                new_header = f"<b>{get_text('insights_for', lang, type=obj_type_display, name=display_name)}</b>\n"
                formatted_text = formatted_text.replace(old_header, new_header)
        
        # Create navigation buttons
        builder = InlineKeyboardBuilder()
        button_count = 0
        
        # Back buttons based on object type
        if object_type == "account":
            builder.add(InlineKeyboardButton(
                text=get_text("back_to_accounts", lang),
                callback_data="menu:accounts"
            ))
        elif object_type == "campaign":
            account_id = object_id.split('_')[0] if '_' in object_id else None
            if account_id:
                builder.add(InlineKeyboardButton(
                    text=get_text("back_to_campaigns", lang),
                    callback_data=f"menu:campaigns:{account_id}"
                ))
            else:
                builder.add(InlineKeyboardButton(
                    text=get_text("back_to_accounts", lang),
                    callback_data="menu:accounts"
                ))
        elif object_type == "account_campaigns":
            builder.add(InlineKeyboardButton(
                text="⬅️",
                callback_data=f"menu:account:{object_id}"
            ))
        else:
            builder.add(InlineKeyboardButton(
                text=get_text("back_to_accounts", lang),
                callback_data="menu:accounts"
            ))
        
        button_count += 1
        
        # Main menu button
        builder.add(InlineKeyboardButton(
            text=get_text("main_menu", lang),
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
            text=get_text("back_to_accounts", lang),
            callback_data="menu:accounts"
        ))
        button_count += 1
        
        builder.add(InlineKeyboardButton(
            text=get_text("main_menu", lang),
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
            f"❌ {get_text('error_fetching_stats', lang)}: {str(e)}",
            reply_markup=builder.as_markup()
        )



@callback_router.callback_query(F.data.startswith("menu:"))
async def menu_callback(callback: CallbackQuery):
    """
    Handle menu button presses.
    """
    try:
        await callback.answer()
    except Exception as e:
        logger.warning(f"Error answering menu callback: {str(e)}")
        # Continue even if we can't answer the callback
        pass
    
    # Get menu item from callback data
    parts = callback.data.split(":")
    if len(parts) < 2:
        await callback.message.edit_text("❌ Invalid menu request.")
        return
        
    menu_item = parts[1]
    user_id = callback.from_user.id
    user_id = fix_user_id(user_id)
    
    # Get user's language
    lang = get_language(user_id)
    
    session = get_session()
    try:
        user = session.query(User).filter_by(telegram_id=user_id).first()
        if not user:
            await callback.message.edit_text(
                "⚠️ Пользователь не найден. Используйте /start для начала работы.",
                parse_mode="HTML"
            )
            return
            
        if menu_item == "main":
            # Return to main menu
            from src.bot.keyboards import build_main_menu_keyboard
            user_role = user.role if user else None
            
            await callback.message.edit_text(
                "<b>Меню</b>",
                parse_mode="HTML",
                reply_markup=build_main_menu_keyboard(user_role)
            )
            
        elif menu_item == "accounts":
            # First, try to delete the current message
            try:
                await callback.message.delete()
            except Exception as e:
                logger.warning(f"Could not delete message when going to accounts: {str(e)}")
            
            # Get the chat ID where we need to send the message
            chat_id = callback.message.chat.id
            
            # Show loading message
            try:
                # Send a new loading message using the callback's bot property
                loading_message = await callback.bot.send_message(
                    chat_id,
                    "🔄 Загружаем список ваших рекламных аккаунтов..."
                )
                
                # Get accounts using the same function as in /accounts command
                from src.bot.finite_state_machine import get_accounts
                accounts = await get_accounts(user_id)
                
                if not accounts:
                    await loading_message.edit_text(
                        "⚠️ У вас нет доступных рекламных аккаунтов.\n"
                        "Если вы владелец, убедитесь, что ваша учетная запись Facebook имеет доступ к рекламным аккаунтам.\n"
                        "Если вы пользователь, обратитесь к владельцу для получения доступа к аккаунтам."
                    )
                    return
                
                # Import the keyboard builder
                from src.bot.keyboards import build_account_keyboard
                
                # Create keyboard for accounts
                keyboard = build_account_keyboard(accounts, add_stats=True)
                
                # Update the loading message with the account list
                await loading_message.edit_text(
                    "<b>📊 Ваши рекламные аккаунты:</b>",
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
                
            except Exception as e:
                logger.error(f"Error loading accounts: {str(e)}")
                try:
                    await loading_message.edit_text(
                        f"❌ Ошибка при загрузке аккаунтов: {str(e)}"
                    )
                except:
                    pass
                    
        elif menu_item == "auth":
            # Check if user has permission to manage users
            if not has_permission(user.role, Permission.MANAGE_USERS.value):
                await callback.message.edit_text(
                    "❌ У вас нет прав для выполнения этой команды.",
                    parse_mode="HTML"
                )
                return
                
            # Import auth keyboard builder
            from src.bot.auth_handlers import build_auth_keyboard
            
            # Show auth menu
            await callback.message.edit_text(
                "<b>🔐 Меню авторизации:</b>\n\n"
                "Выберите действие:",
                parse_mode="HTML",
                reply_markup=build_auth_keyboard()
            )
            
        elif menu_item == "help":
            # Show help text with available commands
            await callback.message.edit_text(
                "📚 <b>Доступные команды:</b>\n\n"
                "/start - Приветственное сообщение и информация о боте\n"
                "/auth - Авторизация в Facebook\n"
                "/accounts - Список ваших рекламных аккаунтов\n"
                "/campaigns [id_аккаунта] - Список кампаний для аккаунта\n"
                "/ads [id_кампании] - Список объявлений для кампании\n"
                "/stats [id_объекта] [период] - Получение статистики\n"
                "/export - Экспорт данных в различных форматах\n"
                "/menu - Показать меню\n"
                "/language - Изменить язык бота\n"
                "/help - Показать эту справку",
                parse_mode="HTML"
            )
            
        elif menu_item == "language":
            # Show language selection menu
            from src.bot.keyboards import build_language_keyboard
            
            await callback.message.edit_text(
                "🌐 Language",
                parse_mode="HTML",
                reply_markup=build_language_keyboard()
            )
            
        elif menu_item == "notifications":
            # Show notifications menu
            from src.bot.notification_handlers import build_notification_keyboard, format_notification_settings
            from src.storage.models import NotificationSettings
            
            # Получаем текущие настройки уведомлений
            settings = session.query(NotificationSettings).filter_by(user_id=user_id).first()
            enabled = settings.enabled if settings else False
            
            await callback.message.edit_text(
                format_notification_settings(settings),
                parse_mode="HTML",
                reply_markup=build_notification_keyboard(enabled).as_markup()
            )
            
    except TelegramBadRequest as e:
        # Message was deleted or can't be edited
        print(f"DEBUG: TelegramBadRequest in menu callback: {str(e)}")
        try:
            # Try to send error without parse_mode
            await callback.message.edit_text(f"❌ Ошибка: {str(e)}", parse_mode=None)
        except:
            pass
    except Exception as e:
        logger.error(f"Error in menu callback: {str(e)}")
        try:
            await callback.message.edit_text(
                f"❌ Произошла ошибка: {str(e)}",
                parse_mode=None
            )
        except:
            pass
    finally:
        session.close()

@callback_router.callback_query(F.data.startswith("account_campaigns_stats:"))
async def account_campaigns_stats_callback(callback: CallbackQuery):
    """
    Handle account campaigns stats button presses.
    Shows a table with all campaigns and their key metrics.
    Callback data format: account_campaigns_stats:account_id
    """
    try:
        await callback.answer()
    except Exception as e:
        logger.warning(f"Error answering account_campaigns_stats callback: {str(e)}")
        # Continue even if we can't answer the callback
        pass
    
    # Get the user ID
    user_id = callback.from_user.id
    user_id = fix_user_id(user_id)
    
    # Get user language
    lang = get_language(user_id)
    
    parts = callback.data.split(":")
    if len(parts) < 2:
        await callback.message.edit_text("❌ Неверный формат запроса статистики кампаний.")
        return
    
    account_id = parts[1]
    
    # Show loading message
    try:
        await callback.message.edit_text(
            get_text("loading_stats", lang),
            parse_mode="HTML"
        )
    except TelegramBadRequest:
        # Message was deleted or can't be edited
        return
    
    client = FacebookAdsClient(user_id)
    
    try:
        # First, get all campaigns for the account
        campaigns = await client.get_campaigns(account_id)
        
        if not campaigns:
            # Create navigation keyboard
            builder = InlineKeyboardBuilder()
            
            builder.add(InlineKeyboardButton(
                text="⬅️",
                callback_data=f"menu:account:{account_id}"
            ))
            
            builder.add(InlineKeyboardButton(
                text=get_text("main_menu", lang),
                callback_data="menu:main"
            ))
            
            # Set up 2-button grid
            builder.adjust(2)
            
            await callback.message.edit_text(
                get_text("no_campaigns_found", lang),
                reply_markup=builder.as_markup()
            )
            return
        
        # Show date selection keyboard first
        from src.bot.keyboards import build_date_preset_keyboard
        
        # Get account name
        account_name = account_id
        try:
            accounts = await client.get_ad_accounts()
            for account in accounts:
                if account.get('id') == account_id:
                    account_name = account.get('name', account_id)
                    break
        except Exception as e:
            logger.error(f"Error getting account name: {str(e)}")
        
        # Ограничиваем длину имени для отображения, если оно слишком длинное
        if len(account_name) > 40:
            display_name = account_name[:37] + "..."
        else:
            display_name = account_name
        
        try:
            await callback.message.edit_text(
                "📅 Выберите период:",
                parse_mode="HTML",
                reply_markup=build_date_preset_keyboard(account_id, "account_campaigns", account_name)
            )
        except TelegramBadRequest as e:
            # Message was deleted or can't be edited
            logger.warning(f"Error showing date selection keyboard: {str(e)}")
            # Try without HTML
            try:
                await callback.message.edit_text(
                    "📅 Выберите период:",
                    reply_markup=build_date_preset_keyboard(account_id, "account_campaigns", account_name)
                )
            except Exception as text_error:
                logger.error(f"Failed to show date selection keyboard: {str(text_error)}")
                await callback.message.edit_text("❌ Не удалось отобразить выбор периода.")
        
    except Exception as e:
        logger.error(f"Error in account_campaigns_stats_callback: {str(e)}")
        
        # Create navigation keyboard even on error
        builder = InlineKeyboardBuilder()
        
        builder.add(InlineKeyboardButton(
            text="⬅️",
            callback_data=f"menu:account:{account_id}"
        ))
        
        builder.add(InlineKeyboardButton(
            text=get_text("main_menu", lang),
            callback_data="menu:main"
        ))
        
        # Set up 2-button grid
        builder.adjust(2)
        
        await callback.message.edit_text(
            f"❌ {get_text('error_fetching_campaigns', lang)}: {str(e)}",
            reply_markup=builder.as_markup()
        ) 

@callback_router.callback_query(F.data.startswith("account:"))
async def account_callback(callback: CallbackQuery):
    """
    Handle account selection callback.
    Redirects to account menu.
    Callback data format: account:account_id
    """
    try:
        await callback.answer()
    except Exception as e:
        logger.warning(f"Error answering account callback: {str(e)}")
        # Continue even if we can't answer the callback
        pass
    
    parts = callback.data.split(":")
    if len(parts) < 2:
        await callback.message.edit_text("❌ Invalid account selection format.")
        return
    
    account_id = parts[1]
    print(f"DEBUG: Process account callback - Account ID: {account_id}, User ID: {callback.from_user.id}")
    
    # Redirect to account menu
    await account_menu_callback(callback) 

@callback_router.callback_query(F.data.startswith("menu:account"))
async def account_menu_callback(callback: CallbackQuery):
    """
    Handle account menu button presses.
    Used for showing account operations menu.
    Callback data formats:
    - menu:account:account_id
    - account:account_id (через account_callback)
    """
    try:
        await callback.answer()
    except Exception as e:
        logger.warning(f"Error answering account menu callback: {str(e)}")
        # Continue even if we can't answer the callback
        pass
    
    parts = callback.data.split(":")
    if len(parts) < 2:
        await callback.message.edit_text("❌ Invalid account menu request.")
        return
    
    # Get the account ID based on callback type
    if parts[0] == "menu" and len(parts) > 2:
        # Format: menu:account:account_id
        account_id = parts[2]
    elif parts[0] == "account":
        # Format: account:account_id
        account_id = parts[1]
    else:
        await callback.message.edit_text("❌ No account ID provided.")
        return
    
    if not account_id:
        await callback.message.edit_text("❌ No account ID provided.")
        return
    
    # Get user ID
    user_id = callback.from_user.id
    user_id = fix_user_id(user_id)
    
    # Get user language
    lang = get_language(user_id)
    
    # Build account menu keyboard
    builder = InlineKeyboardBuilder()
    
    # Campaign stats button
    builder.add(InlineKeyboardButton(
        text="📊 Статистика",
        callback_data=f"account_campaigns_stats:{account_id}"
    ))

    # Main menu button
    builder.add(InlineKeyboardButton(
        text="🌎 Меню",
        callback_data="menu:main"
    ))

    # Back to accounts list button
    builder.add(InlineKeyboardButton(
        text="⬅️",
        callback_data="menu:accounts"
    ))

    # Adjust the grid
    builder.adjust(2, 1)
    
    # Try to get the account name
    account_name = account_id
    client = FacebookAdsClient(user_id)
    try:
        accounts = await client.get_ad_accounts()
        for account in accounts:
            if account.get('id') == account_id:
                account_name = account.get('name', account_id)
                break
    except Exception as e:
        logger.error(f"Error getting account name: {str(e)}")
    
    # Send the menu
    await callback.message.edit_text(
        f"<b>{account_name}</b>",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    ) 