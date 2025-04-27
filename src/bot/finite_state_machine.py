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

from src.storage.database import get_session
from src.storage.models import User, Account, Permission
from src.utils.logger import get_logger
from src.api.facebook import FacebookAdsClient
from config.settings import ADMIN_USERS

logger = get_logger(__name__)

# Create a router for FSM handlers
router = Router()

# Define FSM states for new user flow
class NewUserStates(StatesGroup):
    """States for new user registration flow."""
    waiting_for_admin = State()  # Ожидание реакции админа
    selecting_account = State()  # Выбор аккаунта для пользователя
    selecting_role = State()  # Выбор роли для пользователя


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """
    Handle the /start command.
    """
    user_id = message.from_user.id
    logger.info(f"[START] 🚀 Получена команда /start от пользователя {user_id}")
    logger.debug(f"[START] Данные пользователя: username={message.from_user.username}, "
                f"first_name={message.from_user.first_name}, last_name={message.from_user.last_name}")
    
    await message.answer(
        "👋 Привет! Я бот для работы с Facebook Ads.\n\n"
        "С моей помощью вы можете получать информацию о ваших рекламных аккаунтах, "
        "кампаниях и объявлениях, а также просматривать статистику.\n\n"
        "Для начала работы вам необходимо авторизоваться с помощью команды /auth.\n\n"
        "Используйте /help для получения списка всех доступных команд.",
        parse_mode="HTML"
    )
    
    # Если пользователь не является админом, начинаем процесс регистрации
    if user_id not in ADMIN_USERS:
        admin_id = 400133981  # ID админа
        logger.info(f"[START] 👤 Пользователь {user_id} не является админом, начинаем процесс регистрации")
        
        # Создаем состояние для пользователя
        user_key = StorageKey(
            bot_id=message.bot.id,
            chat_id=user_id,
            user_id=user_id
        )
        user_state = FSMContext(storage=state.storage, key=user_key)
        logger.debug(f"[START] 🔑 Создан state для пользователя с ключом: {user_key}")
        
        # Сохраняем информацию о пользователе в state
        user_data = {
            'telegram_id': user_id,
            'username': message.from_user.username,
            'first_name': message.from_user.first_name,
            'last_name': message.from_user.last_name,
            'full_name': message.from_user.full_name,
            'created_at': datetime.utcnow().isoformat()
        }
        await user_state.set_state(NewUserStates.waiting_for_admin)
        current_state = await user_state.get_state()
        logger.debug(f"[START] 📝 Установлено состояние: {current_state}")
        
        await user_state.update_data(new_user_data=user_data)
        logger.debug(f"[START] 💾 Сохранены данные пользователя: {user_data}")
        
        # Создаем клавиатуру для подтверждения
        builder = InlineKeyboardBuilder()
        builder.add(InlineKeyboardButton(text="Принять", callback_data=f"new_user:accept:{user_id}"))
        builder.add(InlineKeyboardButton(text="Отклонить", callback_data=f"new_user:reject:{user_id}"))
        builder.adjust(2)
        
        # Отправляем уведомление админу
        await message.bot.send_message(
            admin_id,
            f"🔔 Новый пользователь!\n\n"
            f"ID: {user_id}\n"
            f"Имя: {message.from_user.full_name}\n"
            f"Username: @{message.from_user.username or 'отсутствует'}\n\n"
            f"Что делаем с пользователем?",
            reply_markup=builder.as_markup()
        )
        logger.info(f"[START] 📨 Отправлено уведомление админу {admin_id} о новом пользователе {user_id}")

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
        logger.debug(f"[ROLE_SELECTION] 🔑 Создан state пользователя с ключом: {new_key}")
        
        # Проверяем текущее состояние
        current_state = await user_state.get_state()
        logger.debug(f"[ROLE_SELECTION] 📊 Текущее состояние: {current_state}")
        logger.debug(f"[ROLE_SELECTION] 📊 Ожидаемое состояние: {NewUserStates.selecting_role.state}")
        
        if current_state != NewUserStates.selecting_role.state:
            logger.error(f"[ROLE_SELECTION] ❌ Несоответствие состояния. Текущее: {current_state}, "
                        f"Ожидаемое: {NewUserStates.selecting_role.state}")
            await callback.answer("❌ Ошибка: неверное состояние процесса назначения роли.", show_alert=True)
            return
        
        # Проверяем данные пользователя
        state_data = await user_state.get_data()
        new_user_data = state_data.get('new_user_data')
        fb_account_id = state_data.get('selected_account_id')
        logger.debug(f"[ROLE_SELECTION] 📝 Получены данные пользователя: {new_user_data}")
        logger.debug(f"[ROLE_SELECTION] 📝 ID выбранного аккаунта FB: {fb_account_id}")
        
        if not new_user_data or new_user_data['telegram_id'] != user_id:
            logger.error(f"[ROLE_SELECTION] ❌ Несоответствие данных пользователя. "
                        f"Ожидаемый user_id: {user_id}, Полученные данные: {new_user_data}")
            await callback.message.edit_text("❌ Ошибка: данные пользователя не найдены или не совпадают.")
            return
        
        if role == "cancel":
            logger.info(f"[ROLE_SELECTION] ❌ Выбор роли отменен для пользователя {user_id}")
            await callback.message.edit_text(
                f"❌ Назначение роли пользователю {new_user_data['full_name']} отменено."
            )
            return
        
        # Проверяем валидность роли
        valid_roles = await get_available_roles()
        if role not in valid_roles:
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
                logger.debug(f"[ROLE_SELECTION] 📝 Получено название аккаунта: {account_name}")
            except Exception as e:
                logger.error(f"[ROLE_SELECTION] ❌ Ошибка при получении названия аккаунта: {str(e)}")
            
            # Создаем нового пользователя
            logger.info(f"[ROLE_SELECTION] 📝 Создание записи пользователя в БД. User: {user_id}, Role: {role}")
            user = User(
                telegram_id=user_id,
                username=new_user_data['username'],
                first_name=new_user_data['first_name'],
                last_name=new_user_data['last_name'],
                role=role,
                created_at=datetime.fromisoformat(new_user_data['created_at'])
            )
            session.add(user)
            
            # Делаем commit для сохранения пользователя
            session.commit()
            logger.debug(f"[ROLE_SELECTION] ✅ Пользователь успешно создан в БД")
            
            # Удаляем существующие дубликаты аккаунтов, если они есть
            existing_accounts = session.query(Account).filter_by(
                telegram_id=user_id,
                fb_account_id=fb_account_id
            ).all()
            
            if existing_accounts:
                logger.warning(f"[ROLE_SELECTION] ⚠️ Найдены дубликаты аккаунта {fb_account_id} для пользователя {user_id}")
                for acc in existing_accounts:
                    session.delete(acc)
                session.commit()
                logger.debug(f"[ROLE_SELECTION] 🗑 Удалены дубликаты аккаунта {fb_account_id}")
            
            # Создаем запись в таблице accounts
            account = Account(
                telegram_id=user_id,
                fb_account_id=fb_account_id,
                name=account_name,
                created_at=datetime.utcnow()
            )
            session.add(account)
            
            # Делаем commit для сохранения аккаунта
            session.commit()
            logger.debug(f"[ROLE_SELECTION] ✅ Аккаунт успешно создан в БД")
            
            # Проверяем, что все создалось
            check_user = session.query(User).filter_by(telegram_id=user_id).first()
            check_account = session.query(Account).filter_by(telegram_id=user_id, fb_account_id=fb_account_id).first()
            
            if not check_user or not check_account:
                raise Exception("Ошибка при создании записей в базе данных")
            
            logger.info(f"[ROLE_SELECTION] 💾 Успешно сохранены записи пользователя и аккаунта в БД")
            
            # Отправляем сообщение пользователю
            await callback.bot.send_message(
                user_id,
                "✅ Вам предоставлен доступ к рекламному аккаунту Facebook!\n"
                "Теперь вы можете использовать все функции бота."
            )
            logger.debug(f"[ROLE_SELECTION] 📨 Отправлено уведомление пользователю {user_id} о предоставлении доступа")
            
            # Обновляем сообщение админу с названием аккаунта
            account_display_name = account_name or fb_account_id
            await callback.message.edit_text(
                f"✅ Пользователю {new_user_data['full_name']} успешно предоставлен доступ к аккаунту "
                f"{account_display_name} с ролью {role}."
            )
            logger.info(f"[ROLE_SELECTION] 📨 Отправлено подтверждение админу о завершении регистрации")
            
        except Exception as e:
            logger.error(f"[ROLE_SELECTION] ❌ Ошибка при создании записей в БД: {str(e)}")
            await callback.message.edit_text(
                f"❌ Ошибка при создании пользователя: {str(e)}"
            )
            if session:
                session.rollback()
        finally:
            if session:
                session.close()
            await callback.answer()
            logger.debug(f"[ROLE_SELECTION] ✅ Обработка выбора роли завершена")
            # Очищаем состояние в любом случае
            await user_state.clear()
            logger.debug(f"[ROLE_SELECTION] 🗑 State пользователя очищен")
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
        
        if user.role == "owner":
            # Для владельца получаем аккаунты из Facebook API
            try:
                client = FacebookAdsClient(user_id)
                accounts = await client.get_ad_accounts()
                logger.debug(f"[GET_ACCOUNTS] ✅ Получено {len(accounts)} аккаунтов из Facebook API")
                
                # Обновляем информацию в БД
                for account_data in accounts:
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
                
                return accounts
                
            except Exception as e:
                logger.error(f"[GET_ACCOUNTS] ❌ Ошибка при получении аккаунтов из Facebook API: {str(e)}")
                return []
        else:
            # Для обычных пользователей возвращаем только назначенные аккаунты из БД
            accounts = session.query(Account).filter_by(telegram_id=user_id).all()
            logger.debug(f"[GET_ACCOUNTS] 📋 Найдено {len(accounts)} назначенных аккаунтов в БД")
            
            # Пытаемся получить актуальные данные из Facebook API
            try:
                client = FacebookAdsClient(user_id)
                fb_accounts = await client.get_ad_accounts()
                fb_accounts_dict = {acc['id']: acc for acc in fb_accounts}
                
                result = []
                for account in accounts:
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
                logger.warning(f"[GET_ACCOUNTS] ⚠️ Не удалось получить актуальные данные из Facebook: {str(e)}")
                # В случае ошибки возвращаем данные из БД
                return [
                    {
                        'id': account.fb_account_id,
                        'name': account.name or f"Аккаунт {account.fb_account_id}",
                        'currency': account.currency,
                        'timezone_name': account.timezone_name
                    }
                    for account in accounts
                ]
            
    except Exception as e:
        logger.error(f"[GET_ACCOUNTS] ❌ Неожиданная ошибка: {str(e)}")
        return []
    finally:
        session.close()
        logger.debug("[GET_ACCOUNTS] 🗑 Сессия БД закрыта")

async def get_available_roles() -> List[str]:
    """
    Получает список доступных ролей из таблицы permissions.
    Если роли не найдены, создает базовые разрешения и возвращает список ролей.
    
    Returns:
        List[str]: Список уникальных ролей, исключая роль "owner"
    """
    try:
        session = get_session()
        # Получаем уникальные роли из таблицы permissions
        roles = session.query(Permission.role).distinct().all()
        roles = [role[0] for role in roles if role[0] != "owner"]
        
        # Если ролей нет, создаем базовые разрешения
        if not roles:
            logger.warning("Роли не найдены в БД. Создаю базовые разрешения...")
            from src.storage.migrations.seed_permissions import seed_permissions
            seed_permissions()
            # Получаем роли снова после создания
            roles = session.query(Permission.role).distinct().all()
            roles = [role[0] for role in roles if role[0] != "owner"]
        
        logger.info(f"Получены доступные роли: {roles}")
        return roles or ["admin", "targetologist", "partner"]
    except Exception as e:
        logger.error(f"Ошибка при получении ролей: {str(e)}")
        return ["admin", "targetologist", "partner"]
    finally:
        session.close()

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
    
    # Проверяем, является ли пользователь админом
    if user_id not in ADMIN_USERS:
        logger.warning(f"[DELETE_ROLE] ⚠️ Попытка удаления роли от неадмина: {user_id}")
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
    
    session = get_session()
    try:
        # Получаем пользователя из БД
        user = session.query(User).filter_by(telegram_id=target_user_id).first()
        if not user:
            logger.warning(f"[DELETE_ROLE] ⚠️ Пользователь не найден: {target_user_id}")
            await message.answer("❌ Пользователь с указанным ID не найден.")
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
    Показывает список всех пользователей с их ролями.
    Доступно только для админов.
    """
    user_id = message.from_user.id
    logger.info(f"[LIST_USERS] 📋 Получена команда /list_users от пользователя {user_id}")
    
    # Проверяем, является ли пользователь админом
    if user_id not in ADMIN_USERS:
        logger.warning(f"[LIST_USERS] ⚠️ Попытка просмотра списка пользователей от неадмина: {user_id}")
        await message.answer("❌ У вас нет прав для выполнения этой команды.")
        return
    
    session = get_session()
    try:
        # Получаем всех пользователей из БД
        users = session.query(User).all()
        logger.debug(f"[LIST_USERS] 📊 Найдено пользователей в БД: {len(users)}")
        for user in users:
            logger.debug(f"[LIST_USERS] 👤 Пользователь: ID={user.telegram_id}, "
                       f"Username={user.username}, Role={user.role}")
        
        if not users:
            await message.answer("ℹ️ В базе данных нет зарегистрированных пользователей.")
            return
        
        # Получаем актуальные данные аккаунтов для owner
        owner_accounts = {}
        try:
            owner_id = next((user.telegram_id for user in users if user.role == "owner"), None)
            if owner_id:
                client = FacebookAdsClient(owner_id)
                fb_accounts = await client.get_ad_accounts()
                owner_accounts = {acc['id']: acc['name'] for acc in fb_accounts}
                logger.debug(f"[LIST_USERS] 📊 Получены актуальные данные аккаунтов: {owner_accounts}")
        except Exception as e:
            logger.error(f"[LIST_USERS] ❌ Ошибка при получении актуальных данных аккаунтов: {str(e)}")
        
        # Формируем сообщение со списком пользователей
        response = "📋 Список пользователей:\n\n"
        for user in users:
            # Получаем аккаунты пользователя
            accounts = session.query(Account).filter_by(telegram_id=user.telegram_id).all()
            logger.debug(f"[LIST_USERS] 📊 Найдено {len(accounts)} аккаунтов для пользователя {user.telegram_id}")
            
            account_info = []
            for acc in accounts:
                # Используем актуальное название из Facebook API или сохраненное в БД
                name = owner_accounts.get(acc.fb_account_id) or acc.name or f"Аккаунт {acc.fb_account_id}"
                account_info.append(name)
                logger.debug(f"[LIST_USERS] 📝 Аккаунт {acc.fb_account_id}: {name}")
                
                # Обновляем название в БД, если оно изменилось
                if acc.fb_account_id in owner_accounts and acc.name != owner_accounts[acc.fb_account_id]:
                    acc.name = owner_accounts[acc.fb_account_id]
                    acc.updated_at = datetime.utcnow()
                    logger.debug(f"[LIST_USERS] 🔄 Обновлено название аккаунта {acc.fb_account_id}")
            
            # Формируем строку с информацией о пользователе
            user_info = (
                f"👤 {user.first_name or ''} {user.last_name or ''}\n"
                f"ID: {user.telegram_id}\n"
                f"Username: @{user.username or 'отсутствует'}\n"
                f"Роль: {user.role or 'не назначена'}\n"
            )
            
            # Добавляем список аккаунтов
            if account_info:
                user_info += "Аккаунты FB:\n" + "\n".join(account_info)
            else:
                user_info += "Аккаунты FB: нет"
                
            # Добавляем дату создания и пустую строку для разделения пользователей
            user_info += f"\nСоздан: {user.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            
            response += user_info
        
        # Сохраняем обновленные названия
        session.commit()
        logger.debug("[LIST_USERS] 💾 Изменения сохранены в БД")
        
        # Отправляем сообщение частями, если оно слишком длинное
        if len(response) > 4096:
            for i in range(0, len(response), 4096):
                await message.answer(response[i:i+4096])
        else:
            await message.answer(response)
            
        logger.info(f"[LIST_USERS] ✅ Отправлен список из {len(users)} пользователей")
        
    except Exception as e:
        logger.error(f"[LIST_USERS] ❌ Ошибка при получении списка пользователей: {str(e)}")
        await message.answer(f"❌ Произошла ошибка при получении списка пользователей: {str(e)}")
    finally:
        session.close()
        logger.debug(f"[LIST_USERS] 🗑 Сессия БД закрыта")