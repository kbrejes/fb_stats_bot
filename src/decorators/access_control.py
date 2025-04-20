"""
Декораторы для проверки ролей и прав доступа пользователей.
"""
from functools import wraps
from typing import Callable, Any, Optional, Union, Awaitable

from aiogram.types import Message, CallbackQuery
from sqlalchemy.orm import Session

from src.storage.enums import UserRole
from src.repositories.user_repository import UserRepository
from src.repositories.access_control_repository import AccessControlRepository
from src.utils.logger import get_logger

logger = get_logger(__name__)

__all__ = [
    "role_required",
    "admin_required",
    "targetologist_required",
    "partner_required",
    "campaign_access_required",
]


def role_required(role: Union[UserRole, str]):
    """
    Декоратор для проверки роли пользователя.
    
    Проверяет, имеет ли пользователь достаточные права для выполнения 
    действия требующего указанный уровень доступа.
    
    Args:
        role: Требуемая роль (UserRole или строка с названием роли).
    
    Returns:
        Декоратор для обработчика сообщений.
    """
    # Преобразуем строку в перечисление, если необходимо
    if isinstance(role, str):
        if UserRole.has_value(role):
            required_role = UserRole(role)
        else:
            raise ValueError(f"Недопустимая роль: {role}")
    else:
        required_role = role
    
    def decorator(handler: Callable[[Union[Message, CallbackQuery], dict], Awaitable[Any]]):
        @wraps(handler)
        async def wrapper(event: Union[Message, CallbackQuery], data: dict):
            # Проверяем наличие информации о роли пользователя
            if "user_role" not in data or "db_user" not in data:
                logger.error("Нет данных о роли пользователя. Убедитесь, что RoleMiddleware используется перед декоратором.")
                await _access_denied(event, "Ошибка проверки роли пользователя")
                return None
            
            user_role = data["user_role"]
            db_user = data["db_user"]
            
            # Получаем ID пользователя в зависимости от типа события
            if isinstance(event, Message):
                user_id = event.from_user.id
            elif isinstance(event, CallbackQuery):
                user_id = event.from_user.id
            else:
                # Если тип события не поддерживается, просто передаем управление дальше
                return await handler(event, data)
            
            # Конвертируем строковую роль в перечисление
            current_role = UserRole(user_role) if isinstance(user_role, str) else user_role
            
            # Проверяем права доступа
            if current_role.has_permission(required_role):
                logger.debug(f"Доступ разрешен для пользователя {user_id} с ролью {user_role}")
                return await handler(event, data)
            else:
                # Логируем попытку несанкционированного доступа
                logger.warning(f"Доступ запрещен для пользователя {user_id} с ролью {user_role}, требуется {required_role.value}")
                
                # Определяем сообщение об ошибке в зависимости от требуемой роли
                if required_role == UserRole.ADMIN:
                    message = "Эта команда доступна только администраторам"
                elif required_role == UserRole.TARGETOLOGIST:
                    message = "Эта команда доступна только таргетологам и администраторам"
                else:
                    message = "У вас недостаточно прав для выполнения этой команды"
                
                await _access_denied(event, message)
                return None
                
        return wrapper
    
    return decorator


def admin_required(handler: Callable):
    """
    Декоратор для проверки наличия прав администратора.
    
    Shortcut для role_required(UserRole.ADMIN).
    
    Args:
        handler: Обработчик сообщения.
        
    Returns:
        Обернутый обработчик сообщений.
    """
    return role_required(UserRole.ADMIN)(handler)


def targetologist_required(handler: Callable):
    """
    Декоратор для проверки наличия прав таргетолога.
    
    Shortcut для role_required(UserRole.TARGETOLOGIST).
    
    Args:
        handler: Обработчик сообщения.
        
    Returns:
        Обернутый обработчик сообщений.
    """
    return role_required(UserRole.TARGETOLOGIST)(handler)


def partner_required(handler: Callable):
    """
    Декоратор для проверки наличия базовых прав партнера.
    
    Shortcut для role_required(UserRole.PARTNER).
    
    Args:
        handler: Обработчик сообщения.
        
    Returns:
        Обернутый обработчик сообщений.
    """
    return role_required(UserRole.PARTNER)(handler)


def campaign_access_required(campaign_id_extractor: Callable = None):
    """
    Декоратор для проверки доступа к конкретной кампании.
    
    Args:
        campaign_id_extractor: Функция для извлечения ID кампании из события.
                             Если не указана, ID кампании должен быть передан
                             в data["campaign_id"].
    
    Returns:
        Декоратор для обработчика сообщений.
    """
    def decorator(handler: Callable[[Union[Message, CallbackQuery], dict], Awaitable[Any]]):
        @wraps(handler)
        async def wrapper(event: Union[Message, CallbackQuery], data: dict):
            # Проверяем наличие информации о роли пользователя
            if "user_role" not in data or "db_user" not in data:
                logger.error("Нет данных о роли пользователя. Убедитесь, что RoleMiddleware используется перед декоратором.")
                await _access_denied(event, "Ошибка проверки роли пользователя")
                return None
            
            user_role = data["user_role"]
            db_user = data["db_user"]
            
            # Получаем ID пользователя в зависимости от типа события
            if isinstance(event, Message):
                user_id = event.from_user.id
            elif isinstance(event, CallbackQuery):
                user_id = event.from_user.id
            else:
                # Если тип события не поддерживается, просто передаем управление дальше
                return await handler(event, data)
            
            # Получаем ID кампании
            campaign_id = None
            if campaign_id_extractor:
                # Используем предоставленную функцию для извлечения ID
                campaign_id = campaign_id_extractor(event, data)
            elif "campaign_id" in data:
                # Используем ID из данных
                campaign_id = data["campaign_id"]
            
            if campaign_id is None:
                logger.error(f"Не указан ID кампании для пользователя {user_id}")
                await _access_denied(event, "Не указан ID кампании")
                return None
            
            # Администраторы и таргетологи имеют доступ ко всем кампаниям
            if user_role in [UserRole.ADMIN.value, UserRole.TARGETOLOGIST.value]:
                logger.debug(f"Доступ к кампании разрешен для пользователя {user_id} с ролью {user_role}")
                return await handler(event, data)
            
            # Для партнеров проверяем наличие доступа к конкретной кампании
            access_control_repo = AccessControlRepository()
            try:
                has_access = access_control_repo.check_access(
                    user_id=db_user.telegram_id,
                    resource_type="campaign",
                    resource_id=campaign_id
                )
                
                if has_access:
                    logger.debug(f"Доступ к кампании разрешен для партнера {user_id} к campaign:{campaign_id}")
                    return await handler(event, data)
                
                # Логируем попытку несанкционированного доступа
                logger.warning(f"Доступ к кампании запрещен для пользователя {user_id} с ролью {user_role} к campaign:{campaign_id}")
                await _access_denied(event, f"У вас нет доступа к кампании {campaign_id}")
                return None
            finally:
                # Закрываем репозиторий
                access_control_repo.close()
                
        return wrapper
    
    return decorator


async def _access_denied(event: Union[Message, CallbackQuery], message: str) -> None:
    """
    Отправляет сообщение о запрете доступа.
    
    Args:
        event: Входящее событие (сообщение или callback).
        message: Сообщение для отправки.
    """
    if isinstance(event, Message):
        await event.answer(message)
    elif isinstance(event, CallbackQuery):
        await event.answer(message, show_alert=True)
        await event.message.answer(message) 