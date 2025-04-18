"""
Account-related callback handlers for the Facebook Ads Telegram Bot.
"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest

from src.api.facebook import FacebookAdsClient
from src.utils.languages import get_text, get_language, fix_user_id
from src.bot.keyboards import build_account_keyboard, build_date_preset_keyboard
from src.bot.filters import AccountCallbackFilter, DatePresetCallbackFilter
from src.data.processor import DataProcessor
from src.utils.error_handlers import handle_exceptions, api_error_handler

# Setup logger
logger = logging.getLogger(__name__)

# Create a router for account callbacks
account_router = Router()

@account_router.callback_query(F.data.startswith("menu:account"))
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

@account_router.callback_query(F.data.startswith("account:"))
@handle_exceptions(notify_user=True, log_error=True)
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

@account_router.callback_query(F.data.startswith("account_stats:"))
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

@account_router.callback_query(F.data.startswith("account_campaigns_stats:"))
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

@account_router.callback_query(F.data.startswith("campaign_stats:"))
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

@account_router.callback_query(F.data.startswith("ad_stats:"))
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

@account_router.callback_query(AccountCallbackFilter())
@handle_exceptions(notify_user=True)
async def on_account_selected(callback: CallbackQuery, account_id: str):
    """
    Handle callback when an ad account is selected.
    
    Args:
        callback: The callback query.
        account_id: The selected account ID.
    """
    await callback.answer("Выбран аккаунт: " + account_id[:8] + "...")
    
    user_id = callback.from_user.id
    await callback.message.edit_text(
        f"📊 <b>Выбран рекламный аккаунт:</b> <code>{account_id}</code>\n\n"
        "Выберите период для получения статистики:",
        parse_mode="HTML",
        reply_markup=build_date_preset_keyboard(account_id)
    )

@account_router.callback_query(DatePresetCallbackFilter())
@handle_exceptions(notify_user=True)
@api_error_handler(notify_user=True)
async def on_date_preset_selected(
    callback: CallbackQuery, account_id: str, date_preset: str
):
    """
    Handle callback when a date preset is selected.
    
    Args:
        callback: The callback query.
        account_id: The account ID.
        date_preset: The selected date preset.
    """
    await callback.answer(f"Загрузка данных за период: {date_preset}...")
    
    user_id = callback.from_user.id
    
    await callback.message.edit_text(
        f"🔄 <b>Загрузка данных...</b>\n\n"
        f"Аккаунт: <code>{account_id}</code>\n"
        f"Период: <code>{date_preset}</code>",
        parse_mode="HTML"
    )
    
    # Создаем клиент Facebook API и получаем данные
    fb_client = FacebookAdsClient(user_id)
    account_insights, error = await fb_client.get_account_insights(
        account_id=account_id, 
        date_preset=date_preset
    )
    
    if error:
        await callback.message.edit_text(
            f"⚠️ <b>Ошибка при получении данных</b>\n\n{error}",
            parse_mode="HTML",
            reply_markup=build_account_keyboard([{"account_id": account_id}])
        )
        return
    
    # Форматируем данные
    formatted_insights = DataProcessor.format_account_insights(account_insights)
    
    await callback.message.edit_text(
        f"📊 <b>Статистика аккаунта {account_id}</b>\n"
        f"<i>Период: {date_preset}</i>\n\n"
        f"{formatted_insights}\n\n"
        f"<i>Для выбора другого периода, нажмите на соответствующую кнопку:</i>",
        parse_mode="HTML",
        reply_markup=build_date_preset_keyboard(account_id)
    )

@account_router.callback_query(F.data == "back_to_accounts")
@handle_exceptions(notify_user=True)
@api_error_handler(notify_user=True)
async def on_back_to_accounts(callback: CallbackQuery):
    """
    Handle callback to go back to the list of accounts.
    
    Args:
        callback: The callback query.
    """
    await callback.answer("Загрузка списка аккаунтов...")
    
    user_id = callback.from_user.id
    
    # Создаем клиент Facebook API и получаем данные
    fb_client = FacebookAdsClient(user_id)
    accounts, error = await fb_client.get_accounts()
    
    if error:
        await callback.message.edit_text(
            f"⚠️ <b>Ошибка при получении данных</b>\n\n{error}",
            parse_mode="HTML"
        )
        return
    
    if not accounts:
        await callback.message.edit_text(
            "⚠️ У вас нет доступных рекламных аккаунтов. "
            "Убедитесь, что ваш аккаунт Facebook имеет доступ к рекламным аккаунтам.",
            parse_mode="HTML"
        )
        return
    
    # Format accounts data
    formatted_accounts = DataProcessor.format_accounts(accounts)
    
    # Message might be too long for one message
    account_parts = DataProcessor.truncate_for_telegram(formatted_accounts)
    
    # Edit the current message with the first part
    await callback.message.edit_text(
        f"💼 <b>Доступные рекламные аккаунты ({len(accounts)})</b>\n\n" + account_parts[0],
        parse_mode="HTML",
        reply_markup=build_account_keyboard(accounts)
    )
    
    # Send additional parts if necessary
    for part in account_parts[1:]:
        await callback.message.answer(
            part,
            parse_mode="HTML"
        ) 