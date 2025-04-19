"""
Репозиторий для работы с пользователями.
"""
from typing import List, Optional, Dict, Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from src.storage.database import get_session
from src.storage.models import User, Account
from src.storage.enums import UserRole
from src.utils.logger import get_logger

logger = get_logger(__name__)


class UserRepository:
    """Репозиторий для работы с пользователями."""
    
    def __init__(self, session: Optional[Session] = None):
        """
        Инициализирует репозиторий.
        
        Args:
            session: Сессия SQLAlchemy (опционально).
                    Если не предоставлена, будет создана новая сессия.
        """
        self._session = session
    
    @property
    def session(self) -> Session:
        """
        Возвращает текущую сессию или создает новую, если сессия не была предоставлена.
        
        Returns:
            Сессия SQLAlchemy.
        """
        if self._session is None:
            self._session = get_session()
            self._close_session = True
        else:
            self._close_session = False
        return self._session
    
    def close(self):
        """Закрывает сессию, если она была создана этим репозиторием."""
        if getattr(self, '_close_session', False) and self._session:
            self._session.close()
            self._session = None
    
    def get_user_by_id(self, telegram_id: int) -> Optional[User]:
        """
        Получает пользователя по Telegram ID.
        
        Args:
            telegram_id: Telegram ID пользователя.
            
        Returns:
            Объект User или None, если пользователь не найден.
        """
        try:
            return self.session.query(User).filter(User.telegram_id == telegram_id).first()
        except Exception as e:
            logger.error(f"Error fetching user {telegram_id}: {str(e)}")
            return None
    
    def get_all_users(self) -> List[User]:
        """
        Получает список всех пользователей.
        
        Returns:
            Список объектов User.
        """
        try:
            return self.session.query(User).all()
        except Exception as e:
            logger.error(f"Error fetching all users: {str(e)}")
            return []
    
    def get_users_by_role(self, role: UserRole) -> List[User]:
        """
        Получает список пользователей с указанной ролью.
        
        Args:
            role: Роль пользователя (объект UserRole или строка).
            
        Returns:
            Список объектов User с указанной ролью.
        """
        try:
            role_value = role.value if isinstance(role, UserRole) else role
            return self.session.query(User).filter(User.role == role_value).all()
        except Exception as e:
            logger.error(f"Error fetching users with role {role}: {str(e)}")
            return []
    
    def search_users(self, search_term: str) -> List[User]:
        """
        Ищет пользователей по имени пользователя, имени или фамилии.
        
        Args:
            search_term: Поисковый запрос.
            
        Returns:
            Список найденных пользователей.
        """
        try:
            search_pattern = f"%{search_term}%"
            return self.session.query(User).filter(
                or_(
                    User.username.ilike(search_pattern),
                    User.first_name.ilike(search_pattern),
                    User.last_name.ilike(search_pattern)
                )
            ).all()
        except Exception as e:
            logger.error(f"Error searching users: {str(e)}")
            return []
    
    def create_user(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        role: UserRole = UserRole.PARTNER
    ) -> Optional[User]:
        """
        Создает нового пользователя.
        
        Args:
            telegram_id: Telegram ID пользователя.
            username: Имя пользователя в Telegram.
            first_name: Имя пользователя.
            last_name: Фамилия пользователя.
            role: Роль пользователя (по умолчанию PARTNER).
            
        Returns:
            Созданный объект User или None в случае ошибки.
        """
        try:
            # Проверяем, существует ли пользователь
            existing_user = self.get_user_by_id(telegram_id)
            if existing_user:
                logger.warning(f"User {telegram_id} already exists, updating instead")
                return self.update_user(
                    telegram_id=telegram_id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name
                )
            
            # Создаем нового пользователя
            role_value = role.value if isinstance(role, UserRole) else role
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                role=role_value
            )
            
            self.session.add(user)
            self.session.commit()
            logger.info(f"Created user {telegram_id} with role {role_value}")
            return user
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error creating user {telegram_id}: {str(e)}")
            return None
    
    def update_user(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None
    ) -> Optional[User]:
        """
        Обновляет информацию о пользователе.
        
        Args:
            telegram_id: Telegram ID пользователя.
            username: Новое имя пользователя в Telegram.
            first_name: Новое имя пользователя.
            last_name: Новая фамилия пользователя.
            
        Returns:
            Обновленный объект User или None в случае ошибки.
        """
        try:
            user = self.get_user_by_id(telegram_id)
            if not user:
                logger.error(f"User {telegram_id} not found for update")
                return None
            
            # Обновляем только переданные поля
            if username is not None:
                user.username = username
            if first_name is not None:
                user.first_name = first_name
            if last_name is not None:
                user.last_name = last_name
            
            self.session.commit()
            logger.info(f"Updated user {telegram_id}")
            return user
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error updating user {telegram_id}: {str(e)}")
            return None
    
    def set_user_role(self, telegram_id: int, role: UserRole) -> bool:
        """
        Устанавливает роль пользователя.
        
        Args:
            telegram_id: Telegram ID пользователя.
            role: Новая роль пользователя (объект UserRole или строка).
            
        Returns:
            True, если роль успешно установлена, иначе False.
        """
        try:
            user = self.get_user_by_id(telegram_id)
            if not user:
                logger.error(f"User {telegram_id} not found for role update")
                return False
            
            # Используем метод модели для установки роли
            success = user.set_user_role(role)
            if success:
                self.session.commit()
                logger.info(f"Updated role for user {telegram_id} to {user.role}")
                return True
            else:
                logger.error(f"Failed to set role for user {telegram_id}")
                return False
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error setting role for user {telegram_id}: {str(e)}")
            return False
    
    def delete_user(self, telegram_id: int) -> bool:
        """
        Удаляет пользователя.
        
        Args:
            telegram_id: Telegram ID пользователя.
            
        Returns:
            True, если пользователь успешно удален, иначе False.
        """
        try:
            user = self.get_user_by_id(telegram_id)
            if not user:
                logger.error(f"User {telegram_id} not found for deletion")
                return False
            
            self.session.delete(user)
            self.session.commit()
            logger.info(f"Deleted user {telegram_id}")
            return True
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error deleting user {telegram_id}: {str(e)}")
            return False
    
    def get_active_users(self, days: int = 30) -> List[User]:
        """
        Получает список активных пользователей за последние N дней.
        
        Args:
            days: Количество дней для проверки активности.
            
        Returns:
            Список активных объектов User.
        """
        try:
            # В данной реализации просто возвращаем всех пользователей
            # В реальном проекте здесь может быть логика для проверки активности
            return self.get_all_users()
        except Exception as e:
            logger.error(f"Error fetching active users: {str(e)}")
            return []
    
    def count_users_by_role(self) -> Dict[str, int]:
        """
        Подсчитывает количество пользователей для каждой роли.
        
        Returns:
            Словарь с количеством пользователей по ролям.
        """
        try:
            result = {}
            for role in UserRole:
                count = self.session.query(User).filter(User.role == role.value).count()
                result[role.value] = count
            
            return result
        except Exception as e:
            logger.error(f"Error counting users by role: {str(e)}")
            return {} 