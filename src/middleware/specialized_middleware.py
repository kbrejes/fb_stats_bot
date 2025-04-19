"""
Модуль с специализированными middleware для проверки ролей пользователей.
"""
from typing import Dict, Any, Callable, Awaitable, Optional, Union
import time

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, Update

from src.storage.enums import UserRole
from src.utils.logger import get_logger
from src.repositories.access_control_repository import AccessControlRepository

logger = get_logger(__name__)


class AdminMiddleware(BaseMiddleware):
    """
    Middleware для проверки наличия прав администратора у пользователя.
    
    Требует наличия RoleMiddleware в цепочке middleware перед текущим.
    """
    
    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Union[Message, CallbackQuery],
        data: Dict[str, Any]
    ) -> Any:
        """
        Обрабатывает входящее событие, проверяя наличие прав администратора.
        
        Args:
            handler: Обработчик события.
            event: Входящее событие (сообщение или callback).
            data: Данные для обработчика.
            
        Returns:
            Результат выполнения обработчика или None при отсутствии прав.
        """
        # Получаем роль пользователя, добавленную RoleMiddleware
        if "user_role" not in data:
            logger.error("No user_role in data. Make sure RoleMiddleware is used before AdminMiddleware.")
            await self._access_denied(event, "Ошибка проверки роли пользователя")
            return None
        
        user_role = data["user_role"]
        db_user = data.get("db_user")
        
        # Получаем ID пользователя в зависимости от типа события
        if isinstance(event, Message):
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id
        else:
            # Если тип события не поддерживается, просто передаем управление дальше
            return await handler(event, data)
        
        # Проверяем права администратора
        if user_role == UserRole.ADMIN.value:
            logger.debug(f"Admin access granted for user {user_id}")
            return await handler(event, data)
        
        # Логируем попытку несанкционированного доступа
        logger.warning(f"Admin access denied for user {user_id} with role {user_role}")
        await self._access_denied(event, "Эта команда доступна только администраторам")
        return None
    
    async def _access_denied(self, event: Union[Message, CallbackQuery], message: str) -> None:
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


class TargetologistMiddleware(BaseMiddleware):
    """
    Middleware для проверки наличия прав таргетолога у пользователя.
    
    Требует наличия RoleMiddleware в цепочке middleware перед текущим.
    Пропускает пользователей с ролями admin и targetologist.
    """
    
    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Union[Message, CallbackQuery],
        data: Dict[str, Any]
    ) -> Any:
        """
        Обрабатывает входящее событие, проверяя наличие прав таргетолога.
        
        Args:
            handler: Обработчик события.
            event: Входящее событие (сообщение или callback).
            data: Данные для обработчика.
            
        Returns:
            Результат выполнения обработчика или None при отсутствии прав.
        """
        # Получаем роль пользователя, добавленную RoleMiddleware
        if "user_role" not in data:
            logger.error("No user_role in data. Make sure RoleMiddleware is used before TargetologistMiddleware.")
            await self._access_denied(event, "Ошибка проверки роли пользователя")
            return None
        
        user_role = data["user_role"]
        db_user = data.get("db_user")
        
        # Получаем ID пользователя в зависимости от типа события
        if isinstance(event, Message):
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id
        else:
            # Если тип события не поддерживается, просто передаем управление дальше
            return await handler(event, data)
        
        # Проверяем права таргетолога (таргетолог или администратор)
        if user_role in [UserRole.ADMIN.value, UserRole.TARGETOLOGIST.value]:
            logger.debug(f"Targetologist access granted for user {user_id} with role {user_role}")
            return await handler(event, data)
        
        # Логируем попытку несанкционированного доступа
        logger.warning(f"Targetologist access denied for user {user_id} with role {user_role}")
        await self._access_denied(event, "Эта команда доступна только таргетологам и администраторам")
        return None
    
    async def _access_denied(self, event: Union[Message, CallbackQuery], message: str) -> None:
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


class PartnerMiddleware(BaseMiddleware):
    """
    Middleware для проверки наличия прав партнера у пользователя.
    
    Требует наличия RoleMiddleware в цепочке middleware перед текущим.
    Пропускает всех авторизованных пользователей, так как роль партнера
    является базовой для всех пользователей.
    """
    
    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Union[Message, CallbackQuery],
        data: Dict[str, Any]
    ) -> Any:
        """
        Обрабатывает входящее событие, проверяя наличие прав партнера.
        
        Args:
            handler: Обработчик события.
            event: Входящее событие (сообщение или callback).
            data: Данные для обработчика.
            
        Returns:
            Результат выполнения обработчика или None при отсутствии прав.
        """
        # Получаем роль пользователя, добавленную RoleMiddleware
        if "user_role" not in data:
            logger.error("No user_role in data. Make sure RoleMiddleware is used before PartnerMiddleware.")
            await self._access_denied(event, "Ошибка проверки роли пользователя")
            return None
        
        user_role = data["user_role"]
        db_user = data.get("db_user")
        
        # Получаем ID пользователя в зависимости от типа события
        if isinstance(event, Message):
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id
        else:
            # Если тип события не поддерживается, просто передаем управление дальше
            return await handler(event, data)
        
        # Проверяем наличие роли (все пользователи имеют как минимум роль партнера)
        if user_role in UserRole.__members__.values():
            logger.debug(f"Partner access granted for user {user_id} with role {user_role}")
            return await handler(event, data)
        
        # Логируем попытку несанкционированного доступа
        logger.warning(f"Partner access denied for user {user_id} with invalid role {user_role}")
        await self._access_denied(event, "Доступ запрещен. Свяжитесь с администратором.")
        return None
    
    async def _access_denied(self, event: Union[Message, CallbackQuery], message: str) -> None:
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


class CampaignAccessMiddleware(BaseMiddleware):
    """
    Middleware для проверки доступа к конкретной кампании.
    
    Требует наличия RoleMiddleware в цепочке middleware перед текущим.
    Администраторы и таргетологи имеют доступ ко всем кампаниям,
    а партнеры - только к тем, которые им разрешены.
    """
    
    def __init__(self, campaign_id_extractor: Callable = None):
        """
        Инициализирует middleware.
        
        Args:
            campaign_id_extractor: Функция для извлечения ID кампании из события.
                                  Если не указана, ID кампании должен быть передан
                                  в data["campaign_id"].
        """
        super().__init__()
        self._campaign_id_extractor = campaign_id_extractor
        self._access_control_repo = AccessControlRepository()
    
    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Union[Message, CallbackQuery],
        data: Dict[str, Any]
    ) -> Any:
        """
        Обрабатывает входящее событие, проверяя доступ к кампании.
        
        Args:
            handler: Обработчик события.
            event: Входящее событие (сообщение или callback).
            data: Данные для обработчика.
            
        Returns:
            Результат выполнения обработчика или None при отсутствии прав.
        """
        # Получаем роль пользователя, добавленную RoleMiddleware
        if "user_role" not in data or "db_user" not in data:
            logger.error("No user_role or db_user in data. Make sure RoleMiddleware is used before CampaignAccessMiddleware.")
            await self._access_denied(event, "Ошибка проверки роли пользователя")
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
        if self._campaign_id_extractor:
            # Используем предоставленную функцию для извлечения ID
            campaign_id = self._campaign_id_extractor(event, data)
        elif "campaign_id" in data:
            # Используем ID из данных
            campaign_id = data["campaign_id"]
        
        if campaign_id is None:
            logger.error(f"No campaign_id provided for CampaignAccessMiddleware for user {user_id}")
            await self._access_denied(event, "Не указан ID кампании")
            return None
        
        # Администраторы и таргетологи имеют доступ ко всем кампаниям
        if user_role in [UserRole.ADMIN.value, UserRole.TARGETOLOGIST.value]:
            logger.debug(f"Campaign access granted for user {user_id} with role {user_role} to campaign:{campaign_id}")
            return await handler(event, data)
        
        # Для партнеров проверяем наличие доступа к конкретной кампании
        has_access = self._access_control_repo.check_access(
            user_id=db_user.telegram_id,
            resource_type="campaign",
            resource_id=campaign_id
        )
        
        if has_access:
            logger.debug(f"Campaign access granted for partner {user_id} to campaign:{campaign_id}")
            return await handler(event, data)
        
        # Логируем попытку несанкционированного доступа
        logger.warning(f"Campaign access denied for user {user_id} with role {user_role} to campaign:{campaign_id}")
        await self._access_denied(event, f"У вас нет доступа к кампании {campaign_id}")
        return None
    
    async def _access_denied(self, event: Union[Message, CallbackQuery], message: str) -> None:
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