"""
Finite State Machine for handling conversation flows in the Telegram bot.
This module implements a multi-step conversation with state tracking.
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton
from aiogram.fsm.storage.base import StorageKey
from config.settings import OWNER_ID

from src.storage.database import get_session
from src.storage.models import User, Account
from src.utils.logger import get_logger
from src.api.facebook import FacebookAdsClient
from config.settings import ADMIN_USERS
from src.bot.keyboards import build_main_menu_keyboard
from src.utils.bot_helpers import fix_user_id
from src.utils.languages import get_language
from src.utils.permissions import get_available_roles, is_valid_role, Role, has_permission, Permission

logger = get_logger(__name__)

# Create a router for FSM handlers
router = Router()

# Define FSM states for new user flow
class NewUserStates(StatesGroup):
    """States for new user registration flow."""
    waiting_for_admin = State()  # Ожидание реакции админа
    selecting_account = State()  # Выбор аккаунта для пользователя
    selecting_role = State()  # Выбор роли для пользователя

# Define states
class UserStates(StatesGroup):
    selecting_role = State()

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """
    Handle the /start command.
    
    Args:
        message: The message object.
        state: The FSM context.
    """
    user_id = await fix_user_id(message.from_user.id)
    
    # Get user's language
    lang = get_language(user_id)
    
    session = get_session()
    try:
        # Check if user exists in database
        user = session.query(User).filter_by(telegram_id=user_id).first()
        
        if user:
            # User already exists, show appropriate message based on role
            if user.role == "owner":
                await message.answer(
                    "✅ Вы уже зарегистрированы как владелец.\n"
                    "Используйте меню для работы с ботом:",
                    reply_markup=build_main_menu_keyboard(user.role)
                )
            else:
                # Get user's account names
                accounts = session.query(Account).filter_by(telegram_id=user_id).all()
                account_names = [acc.name or acc.fb_account_id for acc in accounts]
                accounts_str = "\n• ".join(account_names) if account_names else "нет привязанных аккаунтов"
                
                await message.answer(
                    f"✅ Вы уже зарегистрированы в системе\n\n"
                    f"Ваша роль: {user.role}\n"
                    f"Доступные аккаунты:\n• {accounts_str}\n\n"
                    f"Используйте меню для работы с ботом:",
                    reply_markup=build_main_menu_keyboard(user.role)
                )
            return
        
        # New user registration process
        welcome_message = await message.answer(
            "Добро пожаловать в Лови Лидов Бот 🫶 \n\n"
            "Скоро мы выдадим вам доступ к вашей статистике 🕑"
        )
        
        # Save user data in state
        user_data = {
            'telegram_id': user_id,
            'username': message.from_user.username,
            'first_name': message.from_user.first_name,
            'last_name': message.from_user.last_name,
            'full_name': message.from_user.full_name,
            'created_at': datetime.utcnow().isoformat(),
            'welcome_message_id': welcome_message.message_id,
            'welcome_chat_id': welcome_message.chat.id
        }
        
        # Notify admins about new user
        admin_users = session.query(User).filter(User.role.in_(["owner", "admin"])).all()
        admin_message = (
            f"📱 Новый запрос на доступ:\n"
            f"👤 {message.from_user.full_name}\n"
            f"🆔 {user_id}\n"
            f"Username: @{message.from_user.username or 'отсутствует'}"
        )
        
        # Create keyboard for admin actions
        builder = InlineKeyboardBuilder()
        builder.add(InlineKeyboardButton(
            text="✅ Принять",
            callback_data=f"new_user:accept:{user_id}"
        ))
        builder.add(InlineKeyboardButton(
            text="❌ Отклонить",
            callback_data=f"new_user:reject:{user_id}"
        ))
        builder.adjust(2)
        
        for admin in admin_users:
            try:
                # Set state for the new user
                new_key = StorageKey(
                    bot_id=message.bot.id,
                    chat_id=user_id,
                    user_id=user_id
                )
                new_state = FSMContext(storage=state.storage, key=new_key)
                await new_state.set_state(NewUserStates.waiting_for_admin)
                await new_state.update_data(new_user_data=user_data)
                
                # Send message to admin with buttons
                await message.bot.send_message(
                    admin.telegram_id,
                    admin_message,
                    reply_markup=builder.as_markup()
                )
            except Exception as e:
                logger.error(f"Failed to notify admin {admin.telegram_id}: {e}")
                
    except Exception as e:
        logger.error(f"Error in start command: {e}")
        await message.answer("❌ Произошла ошибка. Пожалуйста, попробуйте позже.")
    finally:
        session.close()

@router.callback_query(F.data.startswith("new_user:"))
async def process_new_user_action(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик действий админа по новому пользователю
    """
    action, user_id = callback.data.split(":")[1:]
    user_id = int(user_id)
    admin_id = callback.from_user.id
    logger.info(f"[NEW_USER_ACTION] 🎯 Обработка действия '{action}' от админа {admin_id} для пользователя {user_id}")
    
    # Создаем новый state для пользователя
    new_key = StorageKey(
        bot_id=callback.bot.id,
        chat_id=user_id,
        user_id=user_id
    )
    user_state = FSMContext(storage=state.storage, key=new_key)
    logger.debug(f"[NEW_USER_ACTION] 🔑 Создан state пользователя с ключом: {new_key}")
    
    # Проверяем состояние и данные пользователя
    current_state = await user_state.get_state()
    logger.debug(f"[NEW_USER_ACTION] 📊 Текущее состояние: {current_state}")
    logger.debug(f"[NEW_USER_ACTION] 📊 Ожидаемое состояние: {NewUserStates.waiting_for_admin.state}")
    
    if current_state != NewUserStates.waiting_for_admin.state:
        logger.error(f"[NEW_USER_ACTION] ❌ Несоответствие состояния. Текущее: {current_state}, "
                    f"Ожидаемое: {NewUserStates.waiting_for_admin.state}")
        await callback.message.edit_text("❌ Ошибка: неверное состояние процесса регистрации.")
        await user_state.clear()
        logger.debug(f"[NEW_USER_ACTION] 🗑 State пользователя очищен")
        return
        
    state_data = await user_state.get_data()
    new_user_data = state_data.get('new_user_data')
    logger.debug(f"[NEW_USER_ACTION] 📝 Получены данные пользователя: {new_user_data}")
    
    if not new_user_data or new_user_data['telegram_id'] != user_id:
        logger.error(f"[NEW_USER_ACTION] ❌ Несоответствие данных пользователя. "
                    f"Ожидаемый user_id: {user_id}, Полученные данные: {new_user_data}")
        await callback.message.edit_text("❌ Ошибка: данные пользователя не найдены или не совпадают.")
        await user_state.clear()
        logger.debug(f"[NEW_USER_ACTION] 🗑 State пользователя очищен")
        return
    
    if action == "accept":
        logger.info(f"[NEW_USER_ACTION] ✅ Админ принял пользователя {user_id}, получаем список аккаунтов")
        # Получаем список аккаунтов админа
        accounts = await get_accounts(admin_id)  # Используем admin_id для получения списка аккаунтов
        
        if not accounts:
            logger.error(f"[NEW_USER_ACTION] ❌ Не удалось получить список аккаунтов для админа {admin_id}")
            await callback.message.edit_text(
                "❌ Не удалось получить список аккаунтов. Убедитесь, что вы авторизованы в Facebook."
            )
            await user_state.clear()
            logger.debug(f"[NEW_USER_ACTION] 🗑 State пользователя очищен")
            return
            
        logger.debug(f"[NEW_USER_ACTION] 📊 Получено {len(accounts)} аккаунтов")
        
        # Создаем клавиатуру с аккаунтами
        builder = InlineKeyboardBuilder()
        for account in accounts:
            account_id = account.get('id')
            account_name = account.get('name', f"Аккаунт {account_id}")
            
            if len(account_name) > 30:
                account_name = account_name[:27] + '...'
            
            builder.add(InlineKeyboardButton(
                text=account_name,
                callback_data=f"assign_account:{user_id}:{account_id}"
            ))
            logger.debug(f"[NEW_USER_ACTION] 🔘 Добавлена кнопка для аккаунта: {account_name} ({account_id})")
        
        builder.add(InlineKeyboardButton(
            text="❌ Отмена",
            callback_data=f"assign_account:{user_id}:cancel"
        ))
        
        builder.adjust(1)
        
        # Переходим к выбору аккаунта
        await user_state.set_state(NewUserStates.selecting_account)
        new_state = await user_state.get_state()
        logger.debug(f"[NEW_USER_ACTION] 📝 Установлено новое состояние: {new_state}")
        
        # Проверяем, что состояние установилось
        if new_state != NewUserStates.selecting_account.state:
            logger.error(f"[NEW_USER_ACTION] ❌ Не удалось установить состояние. "
                        f"Текущее: {new_state}, Ожидаемое: {NewUserStates.selecting_account.state}")
            await callback.message.edit_text("❌ Ошибка: не удалось установить состояние выбора аккаунта.")
            await user_state.clear()
            logger.debug(f"[NEW_USER_ACTION] 🗑 State пользователя очищен")
            return
            
        await callback.message.edit_text(
            f"✅ Выберите аккаунт для пользователя {new_user_data['full_name']}:",
            reply_markup=builder.as_markup()
        )
        logger.info(f"[NEW_USER_ACTION] 🔄 Переход к выбору аккаунта для пользователя {user_id}")
            
    elif action == "reject":
        logger.info(f"[NEW_USER_ACTION] ❌ Админ отклонил пользователя {user_id}")
        # Отправляем сообщение пользователю
        await callback.bot.send_message(
            user_id,
            "❌ К сожалению, ваш запрос на использование бота был отклонен администратором."
        )
        logger.debug(f"[NEW_USER_ACTION] 📨 Отправлено уведомление пользователю {user_id} об отклонении")
        
        await callback.message.edit_text(
            f"❌ Пользователь {new_user_data['full_name']} был отклонен."
        )
        await user_state.clear()
        logger.debug(f"[NEW_USER_ACTION] 🗑 State пользователя очищен")
    
    await callback.answer()
    logger.debug(f"[NEW_USER_ACTION] ✅ Обработка действия '{action}' завершена")

@router.callback_query(F.data.startswith("assign_account:"))
async def process_account_selection(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик выбора аккаунта для нового пользователя
    """
    _, user_id, account_id = callback.data.split(":")
    user_id = int(user_id)
    admin_id = callback.from_user.id
    logger.info(f"[ACCOUNT_SELECTION] 🎯 Обработка выбора аккаунта {account_id} админом {admin_id} для пользователя {user_id}")
    
    # Используем состояние пользователя
    new_key = StorageKey(
        bot_id=callback.bot.id,
        chat_id=user_id,
        user_id=user_id
    )
    user_state = FSMContext(storage=state.storage, key=new_key)
    logger.debug(f"[ACCOUNT_SELECTION] 🔑 Создан state пользователя с ключом: {new_key}")
    
    # Проверяем текущее состояние
    current_state = await user_state.get_state()
    logger.debug(f"[ACCOUNT_SELECTION] 📊 Текущее состояние: {current_state}")
    logger.debug(f"[ACCOUNT_SELECTION] 📊 Ожидаемое состояние: {NewUserStates.selecting_account.state}")
    
    if current_state != NewUserStates.selecting_account.state:
        logger.error(f"[ACCOUNT_SELECTION] ❌ Несоответствие состояния. Текущее: {current_state}, "
                    f"Ожидаемое: {NewUserStates.selecting_account.state}")
        await callback.answer("❌ Ошибка: неверное состояние процесса регистрации.", show_alert=True)
        return
    
    # Проверяем данные пользователя
    state_data = await user_state.get_data()
    new_user_data = state_data.get('new_user_data')
    logger.debug(f"[ACCOUNT_SELECTION] 📝 Получены данные пользователя: {new_user_data}")
    
    if not new_user_data or new_user_data['telegram_id'] != user_id:
        logger.error(f"[ACCOUNT_SELECTION] ❌ Несоответствие данных пользователя. "
                    f"Ожидаемый user_id: {user_id}, Полученные данные: {new_user_data}")
        await callback.message.edit_text("❌ Ошибка: данные пользователя не найдены или не совпадают.")
        await user_state.clear()
        logger.debug(f"[ACCOUNT_SELECTION] 🗑 State пользователя очищен")
        return
    
    if account_id == "cancel":
        logger.info(f"[ACCOUNT_SELECTION] ❌ Выбор аккаунта отменен для пользователя {user_id}")
        await callback.message.edit_text(
            f"❌ Назначение аккаунта пользователю {new_user_data['full_name']} отменено."
        )
        await user_state.clear()
        logger.debug(f"[ACCOUNT_SELECTION] 🗑 State пользователя очищен")
        return
    
    # Сохраняем выбранный аккаунт
    await user_state.update_data(selected_account_id=account_id)
    logger.debug(f"[ACCOUNT_SELECTION] 💾 Сохранен выбранный аккаунт {account_id} для пользователя {user_id}")
    
    # Получаем список доступных ролей
    roles = await get_available_roles()
    logger.debug(f"[ACCOUNT_SELECTION] 📊 Получены доступные роли: {roles}")
    
    # Создаем клавиатуру с ролями
    builder = InlineKeyboardBuilder()
    for role in roles:
        builder.add(InlineKeyboardButton(
            text=role,
            callback_data=f"assign_role:{user_id}:{role}"
        ))
        logger.debug(f"[ACCOUNT_SELECTION] 🔘 Добавлена кнопка для роли: {role}")
    
    builder.add(InlineKeyboardButton(
        text="❌ Отмена",
        callback_data=f"assign_role:{user_id}:cancel"
    ))
    
    builder.adjust(1)
    
    # Переходим к выбору роли
    await user_state.set_state(NewUserStates.selecting_role)
    new_state = await user_state.get_state()
    logger.debug(f"[ACCOUNT_SELECTION] 📝 Установлено новое состояние: {new_state}")
    
    # Проверяем, что состояние установилось
    if new_state != NewUserStates.selecting_role.state:
        logger.error(f"[ACCOUNT_SELECTION] ❌ Не удалось установить состояние. "
                    f"Текущее: {new_state}, Ожидаемое: {NewUserStates.selecting_role.state}")
        await callback.message.edit_text("❌ Ошибка: не удалось установить состояние выбора роли.")
        await user_state.clear()
        logger.debug(f"[ACCOUNT_SELECTION] 🗑 State пользователя очищен")
        return
        
    await callback.message.edit_text(
        f"Выберите роль для пользователя {new_user_data['full_name']}:",
        reply_markup=builder.as_markup()
    )
    logger.info(f"[ACCOUNT_SELECTION] 🔄 Переход к выбору роли для пользователя {user_id}")
    
    await callback.answer()
    logger.debug(f"[ACCOUNT_SELECTION] ✅ Обработка выбора аккаунта завершена")

@router.callback_query(F.data.startswith("assign_role:"))
async def process_role_selection(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик выбора роли для нового пользователя
    """
    try:
        _, user_id, role = callback.data.split(":")
        user_id = int(user_id)
        admin_id = callback.from_user.id
        logger.info(f"[ROLE_SELECTION] 🎯 Обработка выбора роли '{role}' админом {admin_id} для пользователя {user_id}")
        
        # Используем состояние пользователя
        new_key = StorageKey(
            bot_id=callback.bot.id,
            chat_id=user_id,
            user_id=user_id
        )
        user_state = FSMContext(storage=state.storage, key=new_key)
        
        # Проверяем текущее состояние
        current_state = await user_state.get_state()
        if current_state != NewUserStates.selecting_role.state:
            await callback.answer("❌ Ошибка: неверное состояние процесса назначения роли.", show_alert=True)
            return
        
        # Проверяем данные пользователя
        state_data = await user_state.get_data()
        new_user_data = state_data.get('new_user_data')
        fb_account_id = state_data.get('selected_account_id')
        
        if not new_user_data or new_user_data['telegram_id'] != user_id:
            await callback.message.edit_text("❌ Ошибка: данные пользователя не найдены или не совпадают.")
            return
        
        if role == "cancel":
            await callback.message.edit_text(
                f"❌ Назначение роли пользователю {new_user_data['full_name']} отменено."
            )
            return
        
        # Проверяем валидность роли
        if not is_valid_role(role) or role == Role.OWNER.value:
            logger.error(f"[ROLE_SELECTION] ❌ Неверный формат роли: {role}")
            await callback.message.edit_text("❌ Ошибка: неверный формат роли")
            return
        
        # Добавляем пользователя в базу данных
        session = get_session()
        try:
            # Проверяем существование пользователя
            existing_user = session.query(User).filter_by(telegram_id=user_id).first()
            if existing_user:
                logger.error(f"[ROLE_SELECTION] ❌ Пользователь {user_id} уже существует в БД")
                await callback.message.edit_text("❌ Ошибка: пользователь уже существует")
                return
            
            # Получаем название аккаунта из Facebook API
            account_name = None
            try:
                client = FacebookAdsClient(admin_id)
                fb_accounts = await client.get_ad_accounts()
                account_name = next((acc['name'] for acc in fb_accounts if acc['id'] == fb_account_id), None)
            except Exception as e:
                logger.error(f"[ROLE_SELECTION] ❌ Ошибка при получении названия аккаунта: {str(e)}")
            
            # Создаем нового пользователя
            user = User(
                telegram_id=user_id,
                username=new_user_data['username'],
                first_name=new_user_data['first_name'],
                last_name=new_user_data['last_name'],
                role=role,
                created_at=datetime.fromisoformat(new_user_data['created_at'])
            )
            session.add(user)
            session.commit()
            
            # Создаем запись в таблице accounts
            account = Account(
                telegram_id=user_id,
                fb_account_id=fb_account_id,
                name=account_name,
                created_at=datetime.utcnow()
            )
            session.add(account)
            session.commit()
            
            # Отправляем сообщение пользователю
            try:
                # Пытаемся удалить приветственное сообщение
                welcome_message_id = new_user_data.get('welcome_message_id')
                welcome_chat_id = new_user_data.get('welcome_chat_id')
                if welcome_message_id and welcome_chat_id:
                    try:
                        await callback.bot.delete_message(welcome_chat_id, welcome_message_id)
                    except Exception as e:
                        logger.warning(f"Could not delete welcome message: {str(e)}")
                
                # Отправляем новое сообщение с доступом
                await callback.bot.send_message(
                    user_id,
                    "✅ Вам предоставлен доступ к статистике вашей рекламы в Instagram и Facebook. "
                    "Перейдите в \"Аккаунты\", чтобы увидеть её.",
                    reply_markup=build_main_menu_keyboard(role)
                )
                
                # Обновляем сообщение админу
                account_display_name = account_name or fb_account_id
                await callback.message.edit_text(
                    f"✅ Пользователю {new_user_data['full_name']} успешно предоставлен доступ к аккаунту "
                    f"{account_display_name} с ролью {role}."
                )
            except Exception as e:
                logger.error(f"Error sending messages after role assignment: {str(e)}")
            
        except Exception as e:
            logger.error(f"[ROLE_SELECTION] ❌ Ошибка при создании записей в БД: {str(e)}")
            await callback.message.edit_text(f"❌ Ошибка при создании пользователя: {str(e)}")
            if session:
                session.rollback()
        finally:
            if session:
                session.close()
            await callback.answer()
            await user_state.clear()
            
    except Exception as e:
        logger.error(f"[ROLE_SELECTION] ❌ Ошибка при обработке выбора роли: {str(e)}")
        await callback.answer("❌ Ошибка при обработке выбора роли. Пожалуйста, попробуйте позже.")

async def get_accounts(user_id: int) -> List[Dict[str, Any]]:
    """
    Получает список доступных аккаунтов для пользователя.
    
    Для владельца (owner):
    - Получает аккаунты напрямую из Facebook API
    - Обновляет информацию в БД
    
    Для остальных пользователей:
    - Возвращает только назначенные им аккаунты из БД
    - Использует токен owner'а для получения актуальных данных
    
    Args:
        user_id: ID пользователя в Telegram
        
    Returns:
        List[Dict[str, Any]]: Список словарей с данными аккаунтов
    """
    logger.debug(f"[GET_ACCOUNTS] 🔍 Получение аккаунтов для пользователя {user_id}")
    
    session = get_session()
    try:
        # Проверяем роль пользователя
        user = session.query(User).filter_by(telegram_id=user_id).first()
        if not user:
            logger.error(f"[GET_ACCOUNTS] ❌ Пользователь {user_id} не найден в БД")
            return []
            
        logger.debug(f"[GET_ACCOUNTS] 👤 Роль пользователя: {user.role}")
        
        # Находим owner'а и получаем его ID
        owner = session.query(User).filter_by(role="owner").first()
        if not owner:
            logger.error("[GET_ACCOUNTS] ❌ Owner не найден в БД")
            return []
            
        owner_id = owner.telegram_id
        logger.debug(f"[GET_ACCOUNTS] 👑 Найден owner с ID: {owner_id}")
        
        # Для всех пользователей используем токен owner'а
        try:
            client = FacebookAdsClient(owner_id)
            fb_accounts = await client.get_ad_accounts()
            logger.debug(f"[GET_ACCOUNTS] ✅ Получено {len(fb_accounts)} аккаунтов из Facebook API")
            
            if user.role == "owner":
                # Для owner'а обновляем все аккаунты в БД
                for account_data in fb_accounts:
                    account_id = account_data.get('id')
                    account_name = account_data.get('name', f"Аккаунт {account_id}")
                    
                    if not account_id:
                        continue
                        
                    # Проверяем существование записи
                    existing = session.query(Account).filter_by(
                        fb_account_id=account_id
                    ).all()
                    
                    for acc in existing:
                        # Обновляем существующую запись
                        acc.name = account_name
                        acc.currency = account_data.get('currency')
                        acc.timezone_name = account_data.get('timezone_name')
                        acc.updated_at = datetime.utcnow()
                        logger.debug(f"[GET_ACCOUNTS] 🔄 Обновлен аккаунт: {account_id} с именем {account_name}")
                    
                    # Если это новый аккаунт для owner
                    if not any(acc.telegram_id == user_id for acc in existing):
                        new_account = Account(
                            telegram_id=user_id,
                            fb_account_id=account_id,
                            name=account_name,
                            currency=account_data.get('currency'),
                            timezone_name=account_data.get('timezone_name')
                        )
                        session.add(new_account)
                        logger.debug(f"[GET_ACCOUNTS] ➕ Добавлен новый аккаунт: {account_id} с именем {account_name}")
                
                session.commit()
                logger.debug("[GET_ACCOUNTS] 💾 Аккаунты успешно сохранены в БД")
                
                return fb_accounts
            else:
                # Для обычных пользователей возвращаем только назначенные аккаунты
                user_accounts = session.query(Account).filter_by(telegram_id=user_id).all()
                logger.debug(f"[GET_ACCOUNTS] 📋 Найдено {len(user_accounts)} назначенных аккаунтов в БД")
                
                # Создаем словарь актуальных данных из Facebook
                fb_accounts_dict = {acc['id']: acc for acc in fb_accounts}
                
                result = []
                for account in user_accounts:
                    # Если есть актуальные данные из Facebook, используем их
                    if account.fb_account_id in fb_accounts_dict:
                        fb_data = fb_accounts_dict[account.fb_account_id]
                        account_name = fb_data.get('name')
                        # Обновляем имя в БД
                        account.name = account_name
                        account.updated_at = datetime.utcnow()
                        result.append({
                            'id': account.fb_account_id,
                            'name': account_name,
                            'currency': fb_data.get('currency'),
                            'timezone_name': fb_data.get('timezone_name')
                        })
                    else:
                        # Если нет актуальных данных, используем сохраненные
                        result.append({
                            'id': account.fb_account_id,
                            'name': account.name or f"Аккаунт {account.fb_account_id}",
                            'currency': account.currency,
                            'timezone_name': account.timezone_name
                        })
                
                session.commit()
                return result
                
        except Exception as e:
            logger.error(f"[GET_ACCOUNTS] ❌ Ошибка при получении аккаунтов из Facebook API: {str(e)}")
            if user.role != "owner":
                # Для обычных пользователей возвращаем данные из БД в случае ошибки
                accounts = session.query(Account).filter_by(telegram_id=user_id).all()
                return [
                    {
                        'id': account.fb_account_id,
                        'name': account.name or f"Аккаунт {account.fb_account_id}",
                        'currency': account.currency,
                        'timezone_name': account.timezone_name
                    }
                    for account in accounts
                ]
            return []
            
    except Exception as e:
        logger.error(f"[GET_ACCOUNTS] ❌ Неожиданная ошибка: {str(e)}")
        return []
    finally:
        session.close()
        logger.debug("[GET_ACCOUNTS] 🗑 Сессия БД закрыта")

async def get_available_roles() -> List[str]:
    """
    Получает список доступных ролей.
    
    Returns:
        List[str]: Список уникальных ролей, исключая роль "owner"
    """
    from src.utils.permissions import get_available_roles as get_roles_sync
    return get_roles_sync(exclude_owner=True)

async def check_token_validity(token: str) -> Tuple[bool, Optional[str]]:
    """
    Проверяет валидность токена Facebook.
    
    Args:
        token: Facebook токен для проверки
        
    Returns:
        Tuple[bool, Optional[str]]: (валидность токена, сообщение об ошибке)
    """
    try:
        # Здесь должна быть реальная проверка токена через Facebook API
        # Для тестов просто возвращаем результат
        if not token:
            return False, "Токен не предоставлен"
        return True, None
    except Exception as e:
        return False, str(e)

@router.message(Command("delete_role"))
async def cmd_delete_role(message: Message):
    """
    Удаляет роль пользователя и все связанные данные.
    Доступно только для админов.
    """
    user_id = message.from_user.id
    logger.info(f"[DELETE_ROLE] 🗑 Получена команда /delete_role от пользователя {user_id}")
    
    session = get_session()
    try:
        # Проверяем права пользователя
        admin = session.query(User).filter_by(telegram_id=user_id).first()
        if not admin or not has_permission(admin.role, Permission.MANAGE_USERS.value):
            logger.warning(f"[DELETE_ROLE] ⚠️ Попытка удаления роли без прав: {user_id}")
            await message.answer("❌ У вас нет прав для выполнения этой команды.")
            return
        
        # Проверяем, указан ли ID пользователя
        args = message.text.split()
        if len(args) != 2:
            logger.warning(f"[DELETE_ROLE] ⚠️ Неверный формат команды от пользователя {user_id}")
            await message.answer(
                "❌ Пожалуйста, укажите ID пользователя.\n"
                "Пример: /delete_role 123456789"
            )
            return
        
        try:
            target_user_id = int(args[1])
        except ValueError:
            logger.error(f"[DELETE_ROLE] ❌ Неверный формат ID пользователя: {args[1]}")
            await message.answer("❌ Неверный формат ID пользователя. Используйте только цифры.")
            return
        
        # Получаем пользователя из БД
        user = session.query(User).filter_by(telegram_id=target_user_id).first()
        if not user:
            logger.warning(f"[DELETE_ROLE] ⚠️ Пользователь не найден: {target_user_id}")
            await message.answer("❌ Пользователь с указанным ID не найден.")
            return
        
        # Проверяем, не пытается ли админ удалить owner'а
        if user.role == Role.OWNER.value:
            logger.warning(f"[DELETE_ROLE] ⚠️ Попытка удаления owner'а: {target_user_id}")
            await message.answer("❌ Невозможно удалить owner'а системы.")
            return
        
        # Сохраняем информацию о пользователе для лога
        user_info = f"{user.username} ({user.first_name} {user.last_name})"
        old_role = user.role
        
        # Удаляем связанные аккаунты
        session.query(Account).filter_by(telegram_id=target_user_id).delete()
        logger.info(f"[DELETE_ROLE] 🗑 Удалены аккаунты пользователя {target_user_id}")
        
        # Удаляем пользователя
        session.delete(user)
        session.commit()
        logger.info(f"[DELETE_ROLE] ✅ Пользователь {target_user_id} успешно удален")
        
        await message.answer(
            f"✅ Пользователь {user_info} успешно удален\n"
            f"Старая роль: {old_role}\n\n"
            "Теперь пользователь может заново начать процесс регистрации с помощью команды /start"
        )
        
    except Exception as e:
        logger.error(f"[DELETE_ROLE] ❌ Ошибка при удалении пользователя {target_user_id}: {str(e)}")
        session.rollback()
        await message.answer(f"❌ Произошла ошибка при удалении пользователя: {str(e)}")
    finally:
        session.close()
        logger.debug(f"[DELETE_ROLE] 🗑 Сессия БД закрыта")

@router.message(Command("list_users"))
async def cmd_list_users(message: Message):
    """
    List all users with their roles and accounts.
    
    Args:
        message: The message object.
    """
    user_id = await fix_user_id(message.from_user.id)
    
    session = get_session()
    try:
        # Проверяем права пользователя
        user = session.query(User).filter_by(telegram_id=user_id).first()
        if not user or not has_permission(user.role, Permission.VIEW_ADMIN_PANEL.value):
            await message.answer("❌ У вас нет прав для просмотра списка пользователей.")
            return
        
        # Get all users first
        users = session.query(User).all()
        
        if not users:
            await message.answer("ℹ️ Пользователи не найдены.")
            return
        
        # Format user list
        user_list = []
        for user in users:
            # Add user info
            user_list.append(f"\n👤 {user.username or user.first_name} (ID: {user.telegram_id})")
            user_list.append(f"📊 Роль: {user.role}")
            
            # Get accounts for this user
            accounts = session.query(Account).filter_by(telegram_id=user.telegram_id).all()
            
            if accounts:
                user_list.append("📁 Аккаунты:")
                for account in accounts:
                    # Truncate long account names
                    account_name = account.name[:27] + "..." if account.name and len(account.name) > 30 else account.name or "Без имени"
                    user_list.append(f"   • {account_name}")
            else:
                user_list.append("📁 Нет привязанных аккаунтов")
        
        # Send the formatted list
        await message.answer("\n".join(user_list))
        
    except Exception as e:
        logger.error(f"Error listing users: {str(e)}")
        await message.answer("❌ Произошла ошибка при получении списка пользователей.")
    finally:
        session.close()