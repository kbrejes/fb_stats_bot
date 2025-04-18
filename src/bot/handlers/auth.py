"""
Authentication-related handlers for the Telegram bot.
"""
import logging
import uuid
import re
from typing import Dict, Any, Union, Optional

from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from src.api.auth import oauth_handler
from src.storage.database import get_session
from src.storage.models import User
from src.bot.keyboards import build_main_menu_keyboard
from src.utils.error_handlers import handle_exceptions, api_error_handler

# Create a router for auth handlers
router = Router()
logger = logging.getLogger(__name__)

# FSM States
class AuthStates(StatesGroup):
    """States for the authentication flow."""
    waiting_for_code = State()

@router.message(Command("auth"))
@handle_exceptions(notify_user=True, log_error=True)
async def cmd_auth(message: Message, state: FSMContext):
    """
    Handle the /auth command.
    
    Args:
        message: The message object.
        state: The FSM context.
    """
    # Generate a state parameter to protect against CSRF
    state_param = str(uuid.uuid4())
    
    # Store the state in FSM
    await state.set_state(AuthStates.waiting_for_code)
    await state.update_data(state_param=state_param)
    
    # Get auth URL
    auth_url = oauth_handler.get_auth_url(state=state_param)
    
    await message.answer(
        "Для авторизации в Facebook, пожалуйста, перейдите по ссылке ниже:\n\n"
        f"{auth_url}\n\n"
        "После авторизации вы будете перенаправлены на указанный URI. "
        "Скопируйте полный URL из адресной строки и отправьте его в этот чат."
    )

@router.message(AuthStates.waiting_for_code)
@handle_exceptions(notify_user=True, log_error=True)
async def process_auth_code(message: Message, state: FSMContext):
    """
    Process the authorization URL response.
    
    Args:
        message: The message object.
        state: The FSM context.
    """
    # Extract the code from the URL
    url = message.text
    user_id = message.from_user.id
    print(f"DEBUG: Processing auth code for user ID: {user_id}")
    
    # Extract the code and state parameters
    code_match = re.search(r'code=([^&]*)', url)
    state_match = re.search(r'state=([^&]*)', url)
    
    if not code_match:
        await message.answer(
            "⚠️ Не удалось извлечь код авторизации из URL. "
            "Пожалуйста, убедитесь, что вы отправили полный URL с параметром code."
        )
        return
        
    code = code_match.group(1)
    received_state = state_match.group(1) if state_match else None
    
    # Get the stored state
    state_data = await state.get_data()
    stored_state = state_data.get('state_param')
    
    # Check state parameter to prevent CSRF
    if received_state != stored_state:
        await message.answer(
            "⚠️ Параметр state не совпадает. Возможная атака CSRF. "
            "Пожалуйста, начните процесс авторизации заново с помощью команды /auth."
        )
        return
    
    # Clear the state
    await state.clear()
    
    # Exchange code for token
    await message.answer("🔄 Обмениваем код на токен доступа...")
    
    token_data, error = await oauth_handler.exchange_code_for_token(code)
    
    if error:
        await message.answer(f"⚠️ Ошибка при получении токена: {error}")
        return
        
    if 'access_token' not in token_data:
        await message.answer("⚠️ В ответе сервера отсутствует токен.")
        return
        
    # Store the token in the database
    session = get_session()
    try:
        print(f"DEBUG: Looking for user {user_id} to store token")
        user = session.query(User).filter_by(telegram_id=user_id).first()
        
        if not user:
            print(f"DEBUG: User {user_id} not found, creating new user")
            # Create new user
            user = User(
                telegram_id=user_id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name
            )
            session.add(user)
            
        # Set the token
        print(f"DEBUG: Setting token for user {user_id}")
        user.set_fb_token(
            token_data['access_token'], 
            int(token_data.get('expires_in', 0))
        )
        
        # Set refresh token if provided
        if 'refresh_token' in token_data:
            user.set_fb_refresh_token(token_data['refresh_token'])
            
        session.commit()
        print(f"DEBUG: Successfully saved token for user {user_id}")
        
        # Verify that the user and token were actually saved
        saved_user = session.query(User).filter_by(telegram_id=user_id).first()
        if saved_user and saved_user.is_token_valid():
            print(f"DEBUG: Verification successful - user {user_id} has valid token")
        else:
            print(f"DEBUG: Verification FAILED - user {user_id} token not saved properly")
            
    finally:
        session.close()
        
    await message.answer(
        "✅ Авторизация успешно завершена!\n\n"
        "Теперь вы можете использовать команду /accounts для просмотра "
        "доступных рекламных аккаунтов или /help для списка всех команд.",
        reply_markup=build_main_menu_keyboard()
    ) 