"""
Модуль с middleware для проверки ролей пользователей.
"""
from typing import Dict, Any, Callable, Awaitable, Optional, Union
import time

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, Update
from sqlalchemy.orm import Session

from src.storage.models import User
from src.storage.enums import UserRole
from src.repositories.user_repository import UserRepository
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Время кеширования ролей пользователей (в секундах)
ROLE_CACHE_EXPIRY = 300  # 5 минут

# Кеш ролей пользователей: {user_id: (role, timestamp)}
_role_cache: Dict[int, tuple] = {}


class RoleMiddleware(BaseMiddleware):
    """
    Базовый middleware для проверки ролей пользователей.
    
    Определяет и кеширует роль пользователя, добавляя ее в данные обработчика.
    Также добавляет объект пользователя из базы данных.
    """
    
    def __init__(self, session: Optional[Session] = None):
        """
        Инициализирует middleware.
        
        Args:
            session: Сессия SQLAlchemy (опционально).
                    Если не предоставлена, будет создана новая сессия
                    для каждого запроса.
        """
        super().__init__()
        self._session = session
        self._user_repo = UserRepository(session=session)
        
    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Union[Message, CallbackQuery],
        data: Dict[str, Any]
    ) -> Any:
        """
        Обрабатывает входящее событие, добавляя информацию о роли пользователя.
        
        Args:
            handler: Обработчик события.
            event: Входящее событие (сообщение или callback).
            data: Данные для обработчика.
            
        Returns:
            Результат выполнения обработчика.
        """
        user = None
        close_repo = False
        
        # Получение ID пользователя в зависимости от типа события
        if isinstance(event, Message):
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id
        else:
            # Если тип события не поддерживается, просто передаем управление дальше
            return await handler(event, data)
            
        try:
            # Пытаемся получить роль из кеша
            role, user_obj = self._get_cached_role(user_id)
            
            if role is None or user_obj is None:
                # Если роль не найдена в кеше, получаем из БД
                if self._session is None:
                    # Создаем репозиторий с новой сессией, если не предоставлена
                    self._user_repo = UserRepository()
                    close_repo = True
                
                user_obj = self._user_repo.get_user_by_id(user_id)
                
                # Если пользователь не найден, создаем нового с ролью по умолчанию
                if user_obj is None:
                    logger.info(f"User {user_id} not found, creating with default role")
                    user_obj = self._user_repo.create_user(
                        telegram_id=user_id,
                        username=event.from_user.username,
                        first_name=event.from_user.first_name,
                        last_name=event.from_user.last_name,
                        role=UserRole.PARTNER
                    )
                    
                if user_obj:
                    role = user_obj.role
                    # Кешируем роль
                    self._cache_role(user_id, role, user_obj)
                else:
                    # Если что-то пошло не так, используем роль партнера
                    role = UserRole.PARTNER.value
            
            # Добавляем роль и объект пользователя в данные для обработчика
            data["user_role"] = role
            data["db_user"] = user_obj
            
            # Проверка разрешений будет выполняться в специализированных middleware
            # или декораторах, здесь только подготовка данных
            
            # Логирование для отладки
            logger.debug(f"User {user_id} has role: {role}")
            
            # Вызываем следующий обработчик
            return await handler(event, data)
        except Exception as e:
            logger.error(f"Error in RoleMiddleware: {str(e)}")
            # В случае ошибки устанавливаем роль по умолчанию
            data["user_role"] = UserRole.PARTNER.value
            data["db_user"] = None
            return await handler(event, data)
        finally:
            # Закрываем репозиторий, если мы его создали
            if close_repo:
                self._user_repo.close()
    
    def _get_cached_role(self, user_id: int) -> tuple:
        """
        Получает роль пользователя из кеша, если она актуальна.
        
        Args:
            user_id: ID пользователя Telegram.
            
        Returns:
            Кортеж (роль, объект пользователя) или (None, None), если роль не найдена в кеше
            или истек срок действия кеша.
        """
        if user_id in _role_cache:
            role, timestamp, user_obj = _role_cache[user_id]
            # Проверяем, не истек ли срок действия кеша
            if time.time() - timestamp < ROLE_CACHE_EXPIRY:
                return role, user_obj
        
        return None, None
    
    def _cache_role(self, user_id: int, role: str, user_obj: User) -> None:
        """
        Кеширует роль пользователя.
        
        Args:
            user_id: ID пользователя Telegram.
            role: Роль пользователя.
            user_obj: Объект пользователя из БД.
        """
        _role_cache[user_id] = (role, time.time(), user_obj)
    
    def clear_role_cache(self, user_id: Optional[int] = None) -> None:
        """
        Очищает кеш ролей для указанного пользователя или для всех пользователей.
        
        Args:
            user_id: ID пользователя Telegram (опционально).
                    Если не указан, очищается весь кеш.
        """
        if user_id is not None:
            if user_id in _role_cache:
                del _role_cache[user_id]
                logger.debug(f"Cleared role cache for user {user_id}")
        else:
            _role_cache.clear()
            logger.debug("Cleared all role cache") 