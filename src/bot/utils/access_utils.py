"""
Утилиты для проверки и применения контроля доступа в обработчиках бота.

Этот модуль предоставляет функции-декораторы и вспомогательные функции
для проверки доступа пользователей к функциональности бота.
"""
from functools import wraps
from typing import Callable, Any, Union, Awaitable, Optional

from aiogram.types import Message, CallbackQuery
from sqlalchemy.orm import Session

from src.db.models.user import UserRole
from src.services.access_service import AccessService
from src.utils.logger import get_logger

logger = get_logger(__name__)


def admin_required(handler: Callable):
    """
    Декоратор для проверки наличия прав администратора.
    
    Args:
        handler: Обработчик сообщения/колбэка.
        
    Returns:
        Обернутый обработчик.
    """
    @wraps(handler)
    async def wrapper(event: Union[Message, CallbackQuery], **kwargs):
        # Получаем идентификатор пользователя из события
        user_id = event.from_user.id if isinstance(event, Message) else event.message.from_user.id
        
        # Проверяем роль пользователя
        is_admin = await check_role(user_id, UserRole.ADMIN)
        
        if is_admin:
            # Если пользователь администратор, вызываем обработчик
            return await handler(event, **kwargs)
        else:
            # Иначе отказываем в доступе
            await access_denied(event, "Эта команда доступна только администраторам")
            return None
            
    return wrapper


def targetologist_required(handler: Callable):
    """
    Декоратор для проверки наличия прав таргетолога.
    
    Args:
        handler: Обработчик сообщения/колбэка.
        
    Returns:
        Обернутый обработчик.
    """
    @wraps(handler)
    async def wrapper(event: Union[Message, CallbackQuery], **kwargs):
        # Получаем идентификатор пользователя из события
        user_id = event.from_user.id if isinstance(event, Message) else event.message.from_user.id
        
        # Проверяем роль пользователя
        is_targetologist = await check_role(user_id, UserRole.TARGETOLOGIST)
        
        if is_targetologist:
            # Если пользователь таргетолог, вызываем обработчик
            return await handler(event, **kwargs)
        else:
            # Иначе отказываем в доступе
            await access_denied(event, "Эта команда доступна только таргетологам и администраторам")
            return None
            
    return wrapper


def partner_required(handler: Callable):
    """
    Декоратор для проверки наличия базовых прав партнера.
    
    Args:
        handler: Обработчик сообщения/колбэка.
        
    Returns:
        Обернутый обработчик.
    """
    @wraps(handler)
    async def wrapper(event: Union[Message, CallbackQuery], **kwargs):
        # Получаем идентификатор пользователя из события
        user_id = event.from_user.id if isinstance(event, Message) else event.message.from_user.id
        
        # Проверяем роль пользователя
        is_partner = await check_role(user_id, UserRole.PARTNER)
        
        if is_partner:
            # Если пользователь имеет доступ, вызываем обработчик
            return await handler(event, **kwargs)
        else:
            # Иначе отказываем в доступе
            await access_denied(event, "У вас нет доступа к этой функции")
            return None
            
    return wrapper


def campaign_access_required(campaign_id_selector: Callable = None):
    """
    Декоратор для проверки доступа к конкретной кампании.
    
    Args:
        campaign_id_selector: Функция для извлечения ID кампании из событий/аргументов.
                            Если не указана, ID кампании должен быть передан
                            в keyword-аргументе campaign_id.
    
    Returns:
        Декоратор для обработчика.
    """
    def decorator(handler: Callable[[Union[Message, CallbackQuery], dict], Awaitable[Any]]):
        @wraps(handler)
        async def wrapper(event: Union[Message, CallbackQuery], **kwargs):
            # Получаем идентификатор пользователя из события
            user_id = event.from_user.id if isinstance(event, Message) else event.message.from_user.id
            
            # Получаем ID кампании
            campaign_id = None
            
            if campaign_id_selector:
                # Используем функцию для извлечения ID
                campaign_id = campaign_id_selector(event, **kwargs)
            elif "campaign_id" in kwargs:
                # Используем ID из аргументов
                campaign_id = kwargs["campaign_id"]
            
            if campaign_id is None:
                logger.error(f"Не указан ID кампании для пользователя {user_id}")
                await access_denied(event, "Не указан ID кампании")
                return None
            
            # Проверяем доступ к кампании
            has_access = await has_campaign_access(user_id, campaign_id)
            
            if has_access:
                # Если пользователь имеет доступ, вызываем обработчик
                return await handler(event, **kwargs)
            else:
                # Иначе отказываем в доступе
                await access_denied(event, "У вас нет доступа к этой кампании")
                return None
                
        return wrapper
        
    return decorator


async def check_role(telegram_id: int, required_role: UserRole) -> bool:
    """
    Проверяет, соответствует ли роль пользователя требуемой роли.
    
    Args:
        telegram_id: ID пользователя в Telegram.
        required_role: Требуемая роль (UserRole).
    
    Returns:
        True, если роль пользователя соответствует требуемой роли,
        иначе False.
    """
    try:
        has_access = AccessService.check_access(
            telegram_id=telegram_id,
            resource_type="system",
            resource_id="base_access",
        )
        
        # Если у пользователя нет базового доступа, сразу возвращаем False
        if not has_access:
            return False
            
        # Проверяем роль в зависимости от требуемых прав
        if required_role == UserRole.ADMIN:
            return AccessService.check_access(
                telegram_id=telegram_id,
                resource_type="role",
                resource_id="admin",
            )
        elif required_role == UserRole.TARGETOLOGIST:
            return (AccessService.check_access(
                telegram_id=telegram_id,
                resource_type="role",
                resource_id="admin",
            ) or AccessService.check_access(
                telegram_id=telegram_id,
                resource_type="role",
                resource_id="targetologist",
            ))
        elif required_role == UserRole.PARTNER:
            # Для роли партнера достаточно базового доступа
            return True
        else:
            logger.error(f"Неизвестная роль: {required_role}")
            return False
            
    except Exception as e:
        logger.error(f"Ошибка при проверке роли пользователя: {str(e)}")
        return False


async def has_campaign_access(telegram_id: int, campaign_id: str) -> bool:
    """
    Проверяет, имеет ли пользователь доступ к указанной кампании.
    
    Args:
        telegram_id: ID пользователя в Telegram.
        campaign_id: ID кампании.
    
    Returns:
        True, если пользователь имеет доступ к кампании,
        иначе False.
    """
    try:
        return AccessService.check_access(
            telegram_id=telegram_id,
            resource_type="campaign",
            resource_id=campaign_id,
        )
    except Exception as e:
        logger.error(f"Ошибка при проверке доступа к кампании: {str(e)}")
        return False


async def has_account_access(telegram_id: int, account_id: str) -> bool:
    """
    Проверяет, имеет ли пользователь доступ к указанному аккаунту.
    
    Args:
        telegram_id: ID пользователя в Telegram.
        account_id: ID аккаунта Facebook.
    
    Returns:
        True, если пользователь имеет доступ к аккаунту,
        иначе False.
    """
    try:
        return AccessService.check_access(
            telegram_id=telegram_id,
            resource_type="account",
            resource_id=account_id,
        )
    except Exception as e:
        logger.error(f"Ошибка при проверке доступа к аккаунту: {str(e)}")
        return False


async def access_denied(event: Union[Message, CallbackQuery], message: str) -> None:
    """
    Отправляет сообщение об отказе в доступе.
    
    Args:
        event: Сообщение или колбэк.
        message: Текст сообщения об отказе.
    """
    try:
        if isinstance(event, Message):
            await event.reply(message)
        elif isinstance(event, CallbackQuery):
            await event.answer(message, show_alert=True)
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения об отказе: {str(e)}") 