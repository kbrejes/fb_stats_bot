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
from src.storage.models import User, Cache
from src.utils.export import export_data_to_csv, export_data_to_json, export_data_to_excel
from src.utils.message_formatter import format_insights, format_campaign_table
from src.utils.logger import get_logger
from src.utils.languages import get_text, get_language, fix_user_id
from src.bot.keyboards import build_date_preset_keyboard

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
                text="↩️ Назад к аккаунту",
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


@callback_router.callback_query(F.data.startswith("export:"))
async def export_callback(callback: CallbackQuery):
    """
    Handle export requests.
    Callback data format: export:user_id:export_key:format
    """
    try:
        await callback.answer()
    except Exception as e:
        logger.warning(f"Error answering export callback: {str(e)}")
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
                print(f"DEBUG: Replacing bot ID with user ID in export callback: {user.telegram_id}")
                user_id = user.telegram_id
        except Exception as e:
            print(f"DEBUG: Error finding alternative user in export callback: {str(e)}")
        finally:
            session.close()
    
    parts = callback.data.split(":")
    if len(parts) < 4:
        await callback.message.edit_text("❌ Invalid export request format.")
        return
    
    # Use our user_id instead of the one from callback data
    _, _, export_key, export_format = parts
    
    # Show loading message
    try:
        await callback.message.edit_text("⏳ Preparing export file...", parse_mode="HTML")
    except TelegramBadRequest:
        # Message was deleted or can't be edited
        return
    
    # Get the cached data
    session = get_session()
    try:
        cache_data = Cache.get(session, export_key)
        if not cache_data:
            await callback.message.edit_text("❌ Export data not found or expired. Please try again.")
            return
            
        file_path = None
        filename = f"facebook_ads_export_{export_key.split(':')[-1]}"
        
        # Export in the requested format
        if export_format == "csv":
            file_path = export_data_to_csv(cache_data, filename)
        elif export_format == "json":
            file_path = export_data_to_json(cache_data, filename)
        elif export_format == "excel":
            file_path = export_data_to_excel(cache_data, filename)
        else:
            await callback.message.edit_text(f"❌ Unsupported export format: {export_format}")
            return
            
        # Send the file
        if file_path and os.path.exists(file_path):
            await callback.message.delete()
            with open(file_path, "rb") as file:
                await callback.message.answer_document(file, caption=f"📊 Facebook Ads data export in {export_format.upper()} format")
            
            # Clean up the file
            try:
                os.remove(file_path)
            except Exception:
                pass
        else:
            await callback.message.edit_text("❌ Failed to create export file.")
            
    except Exception as e:
        await callback.message.edit_text(f"❌ Error exporting data: {str(e)}")
    finally:
        session.close()


@callback_router.callback_query(F.data.startswith("menu:"))
async def menu_callback(callback: CallbackQuery):
    """
    Handle menu selection callbacks.
    Callback data format: menu:item
    """
    try:
        await callback.answer()
    except Exception as e:
        logger.warning(f"Error answering menu callback: {str(e)}")
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
                print(f"DEBUG: Replacing bot ID with user ID in menu callback: {user.telegram_id}")
                user_id = user.telegram_id
        except Exception as e:
            print(f"DEBUG: Error finding alternative user in menu callback: {str(e)}")
        finally:
            session.close()
    
    parts = callback.data.split(":")
    if len(parts) < 2:
        return
    
    menu_item = parts[1]
    
    # Skip menu:account callbacks since they are handled by account_menu_callback
    if menu_item == "account":
        return
    
    # Check user token validity for accounts option
    if menu_item == "accounts":
        from src.storage.database import get_session
        from src.storage.models import User
        
        session = get_session()
        try:
            user = session.query(User).filter_by(telegram_id=user_id).first()
            if not user or not user.is_token_valid():
                await callback.message.edit_text(
                    "⚠️ Ваш токен доступа истек или отсутствует. Пожалуйста, используйте команду /auth для авторизации.",
                    parse_mode=None
                )
                return
        except Exception as e:
            print(f"DEBUG: Error checking token validity: {str(e)}")
        finally:
            session.close()
    
    try:
        if menu_item == "main":
            # Показать главное меню
            from src.bot.keyboards import build_main_menu_keyboard
            await callback.message.edit_text(
                "📋 <b>Главное меню</b>\n\n"
                "Выберите нужный пункт меню:",
                parse_mode="HTML",
                reply_markup=build_main_menu_keyboard()
            )
            
        elif menu_item == "accounts":
            # First, try to delete the current message
            try:
                await callback.message.delete()
            except Exception as e:
                logger.warning(f"Could not delete message when going to accounts: {str(e)}")
            
            # Get the chat ID where we need to send the message
            chat_id = callback.message.chat.id
            
            # Since we can't rely on message.answer or properly create a Message object,
            # we'll implement the account listing logic directly here
            
            # Show loading message
            try:
                # Send a new loading message using the callback's bot property
                loading_message = await callback.bot.send_message(
                    chat_id,
                    "🔄 Загружаем список ваших рекламных аккаунтов..."
                )
                
                # Get accounts directly
                fb_client = FacebookAdsClient(user_id)
                accounts = await fb_client.get_ad_accounts()
                
                if not accounts:
                    await loading_message.edit_text(
                        "⚠️ У вас нет доступных рекламных аккаунтов.\n"
                        "Убедитесь, что ваша учетная запись Facebook имеет доступ к рекламным аккаунтам."
                    )
                    return
                
                # Import the keyboard builder
                from src.bot.keyboards import build_account_keyboard
                
                # Create keyboard for accounts
                keyboard = build_account_keyboard(accounts, add_stats=True)
                
                # Update the loading message with accounts list
                try:
                    await loading_message.edit_text(
                        "📊 <b>Выберите рекламный аккаунт:</b>",
                        parse_mode="HTML",
                        reply_markup=keyboard
                    )
                except TelegramBadRequest as e:
                    if "can't parse entities" in str(e):
                        # Try without HTML parsing
                        await loading_message.edit_text(
                            "📊 Выберите рекламный аккаунт:",
                            reply_markup=keyboard
                        )
                    else:
                        raise
                        
            except Exception as e:
                logger.error(f"Error handling accounts navigation: {str(e)}")
                # Try to send an error message
                try:
                    await callback.bot.send_message(
                        chat_id,
                        f"❌ Ошибка при загрузке аккаунтов: {str(e)}"
                    )
                except Exception as inner_error:
                    logger.error(f"Could not send error message: {str(inner_error)}")
            
        elif menu_item == "auth":
            # Show authentication info
            await callback.message.edit_text(
                "🔑 <b>Информация об авторизации</b>\n\n"
                "Для использования бота необходимо пройти авторизацию в Facebook:\n\n"
                "1. Используйте команду /auth для начала процесса авторизации\n"
                "2. Перейдите по ссылке и предоставьте боту доступ к вашим данным Facebook Ads\n"
                "3. Скопируйте URL после перенаправления и отправьте его боту\n\n"
                "Ваша авторизация будет действительна в течение 60 дней.",
                parse_mode="HTML"
            )
            
        elif menu_item == "language":
            # Show language selection menu
            from src.bot.keyboards import build_language_keyboard
            from src.utils.languages import get_language
            
            # Get the user's current language
            current_language = get_language(user_id)
            
            language_names = {
                "ru": "🇷🇺 Русский",
                "en": "🇬🇧 English"
            }
            
            current_language_name = language_names.get(current_language, current_language)
            
            await callback.message.edit_text(
                f"🌐 <b>Язык / Language</b>\n\n"
                f"Текущий язык / Current language: <b>{current_language_name}</b>\n\n"
                f"Выберите язык / Choose your language:",
                parse_mode="HTML",
                reply_markup=build_language_keyboard()
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
        print(f"DEBUG: General exception in menu callback: {str(e)}")
        try:
            # Try to send error without parse_mode
            await callback.message.edit_text(f"❌ Ошибка: {str(e)}", parse_mode=None)
        except:
            pass

@callback_router.callback_query(F.data.startswith("account_stats:"))
async def account_stats_callback(callback: CallbackQuery):
    """
    Handle account stats button presses - DISABLED.
    This callback handler has been disabled to remove the account statistics feature.
    The stats_callback will still work when called with object_type="account", but 
    direct button access has been removed.
    
    Callback data format: account_stats:account_id:account_name
    """
    try:
        await callback.answer("Эта функция отключена", show_alert=True)
    except Exception as e:
        logger.warning(f"Error answering account_stats callback: {str(e)}")

    # Создаем клавиатуру для возврата
    builder = InlineKeyboardBuilder()
    
    builder.add(InlineKeyboardButton(
        text="↩️ Назад к аккаунтам",
        callback_data="menu:accounts"
    ))
    
    builder.add(InlineKeyboardButton(
        text="🏠 Главное меню",
        callback_data="menu:main"
    ))
    
    # Set up 2-button grid
    builder.adjust(2)
    
    await callback.message.edit_text(
        "⚠️ Функция статистики аккаунта отключена. Пожалуйста, используйте статистику кампаний.",
        reply_markup=builder.as_markup()
    )
    return

@callback_router.callback_query(F.data.startswith("campaign_stats:"))
async def campaign_stats_callback(callback: CallbackQuery):
    """
    Handle campaign stats button presses.
    Callback data format: campaign_stats:campaign_id[:campaign_name]
    """
    try:
        await callback.answer()
    except Exception as e:
        logger.warning(f"Error answering campaign_stats callback: {str(e)}")
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
                print(f"DEBUG: Replacing bot ID with user ID in campaign_stats callback: {user.telegram_id}")
                user_id = user.telegram_id
        except Exception as e:
            print(f"DEBUG: Error finding alternative user in campaign_stats callback: {str(e)}")
        finally:
            session.close()
    
    parts = callback.data.split(":")
    if len(parts) < 2:
        await callback.message.edit_text("❌ Invalid campaign stats request format.")
        return
    
    campaign_id = parts[1]
    campaign_name = parts[2] if len(parts) > 2 else campaign_id
    
    # Ограничиваем длину имени для отображения, если оно слишком длинное
    if len(campaign_name) > 40:
        display_name = campaign_name[:37] + "..."
    else:
        display_name = campaign_name
    
    # Import the date preset keyboard
    from src.bot.keyboards import build_date_preset_keyboard
    
    # Show date selection keyboard
    try:
        await callback.message.edit_text(
            f"📅 Выберите период для статистики кампании <b>{display_name}</b>:",
            parse_mode="HTML",
            reply_markup=build_date_preset_keyboard(campaign_id, "campaign", campaign_name)
        )
    except TelegramBadRequest as e:
        # Message was deleted or can't be edited
        logger.warning(f"Error showing date selection keyboard: {str(e)}")
        # Try without HTML
        try:
            await callback.message.edit_text(
                f"📅 Выберите период для статистики кампании {display_name}:",
                reply_markup=build_date_preset_keyboard(campaign_id, "campaign", campaign_name)
            )
        except Exception as text_error:
            logger.error(f"Failed to show date selection keyboard: {str(text_error)}")
            await callback.message.edit_text("❌ Не удалось отобразить выбор периода.")

@callback_router.callback_query(F.data.startswith("ad_stats:"))
async def ad_stats_callback(callback: CallbackQuery):
    """
    Handle ad stats button presses.
    Callback data format: ad_stats:ad_id[:ad_name]
    """
    try:
        await callback.answer()
    except Exception as e:
        logger.warning(f"Error answering ad_stats callback: {str(e)}")
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
                print(f"DEBUG: Replacing bot ID with user ID in ad_stats callback: {user.telegram_id}")
                user_id = user.telegram_id
        except Exception as e:
            print(f"DEBUG: Error finding alternative user in ad_stats callback: {str(e)}")
        finally:
            session.close()
    
    parts = callback.data.split(":")
    if len(parts) < 2:
        await callback.message.edit_text("❌ Invalid ad stats request format.")
        return
    
    ad_id = parts[1]
    ad_name = parts[2] if len(parts) > 2 else ad_id
    
    # Ограничиваем длину имени для отображения, если оно слишком длинное
    if len(ad_name) > 40:
        display_name = ad_name[:37] + "..."
    else:
        display_name = ad_name
    
    # Import the date preset keyboard
    from src.bot.keyboards import build_date_preset_keyboard
    
    # Show date selection keyboard
    try:
        await callback.message.edit_text(
            f"📅 Выберите период для статистики объявления <b>{display_name}</b>:",
            parse_mode="HTML",
            reply_markup=build_date_preset_keyboard(ad_id, "ad", ad_name)
        )
    except TelegramBadRequest as e:
        # Message was deleted or can't be edited
        logger.warning(f"Error showing date selection keyboard: {str(e)}")
        # Try without HTML
        try:
            await callback.message.edit_text(
                f"📅 Выберите период для статистики объявления {display_name}:",
                reply_markup=build_date_preset_keyboard(ad_id, "ad", ad_name)
            )
        except Exception as text_error:
            logger.error(f"Failed to show date selection keyboard: {str(text_error)}")
            await callback.message.edit_text("❌ Не удалось отобразить выбор периода.") 

@callback_router.callback_query(F.data.startswith("empty:"))
async def empty_callback(callback: CallbackQuery):
    """
    Handle empty button presses.
    This is a placeholder for layout purposes only.
    """
    try:
        await callback.answer()
    except Exception as e:
        logger.warning(f"Error answering empty callback: {str(e)}")
        # Игнорируем ошибки для пустой кнопки 

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
    
    # Campaign stats button - с укороченным названием
    builder.add(InlineKeyboardButton(
        text="📊 Статистика кампаний",
        callback_data=f"account_campaigns_stats:{account_id}"
    ))
    
    # Back to accounts list button
    builder.add(InlineKeyboardButton(
        text=get_text("back_to_accounts", lang),
        callback_data="menu:accounts"
    ))
    
    # Main menu button
    builder.add(InlineKeyboardButton(
        text=get_text("main_menu", lang),
        callback_data="menu:main"
    ))
    
    # Adjust the grid
    builder.adjust(2)
    
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
        f"{get_text('account_menu', lang)}: <b>{account_name}</b>",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )

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
                text="↩️ Назад к аккаунту",
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
                f"📅 Выберите период для статистики кампаний аккаунта <b>{display_name}</b>:",
                parse_mode="HTML",
                reply_markup=build_date_preset_keyboard(account_id, "account_campaigns", account_name)
            )
        except TelegramBadRequest as e:
            # Message was deleted or can't be edited
            logger.warning(f"Error showing date selection keyboard: {str(e)}")
            # Try without HTML
            try:
                await callback.message.edit_text(
                    f"📅 Выберите период для статистики кампаний аккаунта {display_name}:",
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
            text="↩️ Назад к аккаунту",
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