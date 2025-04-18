"""
Menu navigation callback handlers for the Facebook Ads Telegram Bot.
"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest

from src.utils.languages import get_text, get_language, fix_user_id
from src.api.facebook import FacebookAdsClient

# Setup logger
logger = logging.getLogger(__name__)

# Create a router for menu callbacks
menu_router = Router()

@menu_router.callback_query(F.data.startswith("menu:"))
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
    
    # For menu:account callbacks, redirect to account_menu_callback
    if menu_item == "account":
        # Import the callback handler from account_callbacks
        try:
            from src.bot.callbacks.account_callbacks import account_menu_callback
            await account_menu_callback(callback)
            return
        except Exception as e:
            logger.error(f"Error redirecting to account_menu_callback: {str(e)}")
            # If there's an error, we'll try to handle it with main.py handler instead
            try:
                from src.bot.handlers.main import process_menu_account_callback
                await process_menu_account_callback(callback)
                return
            except Exception as e2:
                logger.error(f"Error redirecting to process_menu_account_callback: {str(e2)}")
                # If both redirects fail, continue with regular menu handling
    
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

@menu_router.callback_query(F.data.startswith("empty:"))
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