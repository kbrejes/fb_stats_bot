"""
Обработчики команд для администраторов.
"""
from typing import Dict, Any, Optional, List
import re

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from src.storage.models import User
from src.storage.enums import UserRole
from src.repositories.user_repository import UserRepository
from src.utils.access_utils import is_admin
from src.decorators.role_required import admin_required
from src.utils.localization import _
from src.utils.message_formatter import format_user_list, format_user_info

# Создаем роутер для обработчиков команд администратора
router = Router()


class SetRoleStates(StatesGroup):
    """Состояния для процесса изменения роли пользователя."""
    waiting_for_user_id = State()  # Ожидание ID пользователя
    waiting_for_role = State()     # Ожидание выбора роли
    waiting_for_confirmation = State()  # Ожидание подтверждения


@router.message(Command("users"))
@admin_required
async def cmd_users(message: Message):
    """
    Обработчик команды /users.
    Показывает список всех пользователей с их ролями.
    """
    # Получаем репозиторий пользователей
    user_repo = UserRepository()
    
    try:
        # Получаем всех пользователей
        users = user_repo.get_all_users()
        
        if not users:
            await message.answer(_("admin.no_users_found"))
            return
        
        # Форматируем список пользователей
        response = format_user_list(users)
        
        # Отправляем ответ
        await message.answer(response, parse_mode="HTML")
    except Exception as e:
        await message.answer(_("errors.db_error", error=str(e)))
    finally:
        user_repo.close()


@router.message(Command("set_role"))
@admin_required
async def cmd_set_role(message: Message, state: FSMContext):
    """
    Обработчик команды /set_role.
    Запускает процесс изменения роли пользователя.
    
    Формат команды: 
    /set_role - интерактивный режим
    /set_role <telegram_id> <role> - прямое задание роли
    """
    # Проверяем формат команды - есть ли параметры
    command_parts = message.text.split()
    
    if len(command_parts) == 1:
        # Интерактивный режим
        await message.answer(_("admin.set_role.enter_user_id"))
        await state.set_state(SetRoleStates.waiting_for_user_id)
        return
    
    # Прямой режим с параметрами
    if len(command_parts) >= 3:
        # Извлекаем параметры
        try:
            user_id = int(command_parts[1])
            role_str = command_parts[2].upper()
            
            # Проверяем роль
            try:
                role = UserRole[role_str]
            except (KeyError, ValueError):
                await message.answer(_("admin.set_role.invalid_role", 
                                      valid_roles=", ".join(r.name for r in UserRole)))
                return
            
            # Сохраняем данные в состоянии
            await state.update_data(user_id=user_id, role=role)
            
            # Получаем информацию о пользователе для подтверждения
            user_repo = UserRepository()
            try:
                user = user_repo.get_user_by_id(user_id)
                if not user:
                    await message.answer(_("admin.user_not_found", user_id=user_id))
                    await state.clear()
                    return
                
                # Форматируем информацию о пользователе для подтверждения
                confirm_text = _("admin.set_role.confirm", 
                                user_info=format_user_info(user),
                                new_role=role.name)
                
                await message.answer(confirm_text, parse_mode="HTML")
                await state.set_state(SetRoleStates.waiting_for_confirmation)
            except Exception as e:
                await message.answer(_("errors.db_error", error=str(e)))
                await state.clear()
            finally:
                user_repo.close()
        except ValueError:
            await message.answer(_("admin.set_role.invalid_user_id"))
            await state.clear()
    else:
        await message.answer(_("admin.set_role.invalid_format"))
        await state.clear()


@router.message(SetRoleStates.waiting_for_user_id)
async def process_user_id(message: Message, state: FSMContext):
    """Обработка ввода ID пользователя."""
    # Пытаемся извлечь ID пользователя
    try:
        user_id = int(message.text.strip())
        
        # Проверяем существование пользователя
        user_repo = UserRepository()
        try:
            user = user_repo.get_user_by_id(user_id)
            if not user:
                await message.answer(_("admin.user_not_found", user_id=user_id))
                await state.clear()
                return
            
            # Сохраняем ID пользователя
            await state.update_data(user_id=user_id, user_info=format_user_info(user))
            
            # Запрашиваем роль
            roles_text = "\n".join([f"- {role.name}: {_(f'roles.{role.value}')}" for role in UserRole])
            await message.answer(
                _("admin.set_role.choose_role", 
                  user_info=format_user_info(user),
                  roles=roles_text),
                parse_mode="HTML"
            )
            await state.set_state(SetRoleStates.waiting_for_role)
        except Exception as e:
            await message.answer(_("errors.db_error", error=str(e)))
            await state.clear()
        finally:
            user_repo.close()
    except ValueError:
        await message.answer(_("admin.set_role.invalid_user_id"))


@router.message(SetRoleStates.waiting_for_role)
async def process_role(message: Message, state: FSMContext):
    """Обработка ввода роли."""
    # Получаем введенную роль
    role_str = message.text.strip().upper()
    
    # Проверяем роль
    try:
        role = UserRole[role_str]
    except (KeyError, ValueError):
        await message.answer(_("admin.set_role.invalid_role", 
                             valid_roles=", ".join(r.name for r in UserRole)))
        return
    
    # Сохраняем роль
    state_data = await state.get_data()
    await state.update_data(role=role)
    
    # Запрашиваем подтверждение
    confirm_text = _("admin.set_role.confirm", 
                   user_info=state_data.get("user_info", ""),
                   new_role=role.name)
    
    await message.answer(confirm_text, parse_mode="HTML")
    await state.set_state(SetRoleStates.waiting_for_confirmation)


@router.message(SetRoleStates.waiting_for_confirmation)
async def process_confirmation(message: Message, state: FSMContext):
    """Обработка подтверждения изменения роли."""
    response = message.text.strip().lower()
    
    # Проверяем ответ
    if response in ["да", "yes", "y", "д", "подтверждаю", "confirm"]:
        # Получаем данные из состояния
        state_data = await state.get_data()
        user_id = state_data.get("user_id")
        role = state_data.get("role")
        
        # Устанавливаем роль
        user_repo = UserRepository()
        try:
            success = user_repo.set_user_role(user_id, role)
            if success:
                await message.answer(_("admin.set_role.success", 
                                     user_id=user_id,
                                     role=role.name))
            else:
                await message.answer(_("admin.set_role.error"))
        except Exception as e:
            await message.answer(_("errors.db_error", error=str(e)))
        finally:
            user_repo.close()
    else:
        await message.answer(_("admin.set_role.cancelled"))
    
    # Очищаем состояние
    await state.clear() 