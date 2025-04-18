"""
Example usage of UserSession module for bot handlers.
"""
import logging
from typing import Dict, Any, Optional

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandObject

from src.state.user_session import UserSession
from src.api.facebook import FacebookAdsClient

logger = logging.getLogger(__name__)

# Example router just for demonstration
router = Router()


@router.message(Command("example"))
async def cmd_example(message: Message) -> None:
    """
    Example command showing UserSession usage.
    
    Args:
        message: Message object from Telegram
    """
    # Initialize user session with proper ID handling
    user_session = await UserSession.get_session(message.from_user.id)
    
    # Check if the user has a valid token
    if not user_session.is_token_valid():
        await message.answer(
            "⚠️ Ваш токен доступа к Facebook API истек или отсутствует.\n"
            "Пожалуйста, используйте команду /auth для авторизации."
        )
        return
    
    # Get user's language preference
    language = user_session.get_language()
    
    # Get current account ID from session
    account_id = user_session.get_current_account()
    
    if not account_id:
        await message.answer(
            "⚠️ Не выбран активный рекламный аккаунт.\n"
            "Пожалуйста, выберите аккаунт с помощью команды /accounts."
        )
        return
    
    # Store the command in user's history
    user_session.set_last_command("example")
    
    # Set some context values for the current session
    user_session.set_context({
        "example_run_time": "2023-04-19 14:30:00",
        "example_mode": "demonstration"
    })
    
    # Retrieve a specific value from context
    mode = user_session.get_value("example_mode", "default")
    
    await message.answer(
        f"✅ Пример использования UserSession:\n\n"
        f"🌐 Язык пользователя: {language}\n"
        f"📊 Текущий аккаунт: {account_id}\n"
        f"⚙️ Режим работы: {mode}\n"
    )


@router.callback_query(F.data.startswith("example:"))
async def example_callback(callback: CallbackQuery) -> None:
    """
    Example callback handler showing UserSession usage.
    
    Args:
        callback: Callback query from Telegram
    """
    try:
        await callback.answer()
    except Exception as e:
        logger.warning(f"Error answering callback: {str(e)}")
    
    # Initialize user session
    user_session = await UserSession.get_session(callback.from_user.id)
    
    # Get the action from callback data
    action = callback.data.split(":")[1]
    
    if action == "set_campaign":
        # Example: extract campaign ID from callback data
        campaign_id = callback.data.split(":")[2]
        
        # Save it to the user's session
        user_session.set_current_campaign(campaign_id)
        
        await callback.message.edit_text(
            f"✅ Установлена текущая кампания: {campaign_id}"
        )
    
    elif action == "clear":
        # Clear all user context
        user_session.clear_context()
        
        await callback.message.edit_text(
            "✅ Контекст пользователя очищен"
        )
    
    else:
        await callback.message.edit_text(
            "❌ Неизвестное действие"
        )


# Example of using UserSession with FacebookAdsClient
async def get_user_campaigns(user_id: int) -> Dict[str, Any]:
    """
    Example function that combines UserSession and FacebookAdsClient.
    
    Args:
        user_id: Telegram user ID
        
    Returns:
        Dictionary with results
    """
    # Initialize session
    user_session = await UserSession.get_session(user_id)
    
    # Check token validity
    if not user_session.is_token_valid():
        return {"error": "token_expired"}
    
    # Get current account
    account_id = user_session.get_current_account()
    if not account_id:
        return {"error": "no_account_selected"}
    
    try:
        # Now we can use the Facebook API client
        fb_client = FacebookAdsClient(user_session.user_id)
        
        # Get campaigns
        campaigns = await fb_client.get_campaigns(account_id)
        
        # Store last command execution
        user_session.set_last_command("get_campaigns")
        
        return {
            "success": True,
            "campaigns": campaigns
        }
    except Exception as e:
        logger.error(f"Error getting campaigns: {str(e)}")
        return {"error": str(e)} 