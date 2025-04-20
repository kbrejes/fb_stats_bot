"""
Утилиты для проверки прав доступа пользователей.

Содержит набор функций для удобной проверки прав доступа пользователей
к различным частям системы.
"""
from typing import Optional, Union

from sqlalchemy.orm import Session

from src.storage.enums import UserRole
from src.storage.models import User
from src.repositories.user_repository import UserRepository
from src.repositories.access_control_repository import AccessControlRepository
from src.utils.logger import get_logger

logger = get_logger(__name__)


def check_user_role(telegram_id: int, required_role: Union[UserRole, str], 
                   session: Optional[Session] = None) -> bool:
    """
    Проверяет, соответствует ли роль пользователя требуемой роли.
    
    Args:
        telegram_id: ID пользователя в Telegram.
        required_role: Требуемая роль (UserRole или строка с названием роли).
        session: Сессия SQLAlchemy (опционально).
    
    Returns:
        True, если роль пользователя соответствует требуемой роли,
        иначе False.
    """
    close_repo = False
    user_repo = None
    
    try:
        # Преобразуем строку в перечисление, если необходимо
        if isinstance(required_role, str):
            if UserRole.has_value(required_role):
                required_role = UserRole(required_role)
            else:
                logger.error(f"Недопустимая роль: {required_role}")
                return False
        
        # Создаем репозиторий, используя предоставленную сессию или создавая новую
        if session is None:
            user_repo = UserRepository()
            close_repo = True
        else:
            user_repo = UserRepository(session=session)
        
        # Получаем пользователя из базы данных
        user = user_repo.get_user_by_id(telegram_id)
        
        # Если пользователь не найден, возвращаем False
        if user is None:
            logger.debug(f"Пользователь с ID {telegram_id} не найден")
            return False
        
        # Получаем роль пользователя
        user_role = UserRole(user.role) if isinstance(user.role, str) else user.role
        
        # Проверяем, имеет ли пользователь достаточные права
        return user_role.has_permission(required_role)
    except Exception as e:
        logger.error(f"Ошибка при проверке роли пользователя: {str(e)}")
        return False
    finally:
        # Закрываем репозиторий, если мы его создали
        if close_repo and user_repo is not None:
            user_repo.close()


def is_admin(telegram_id: int, session: Optional[Session] = None) -> bool:
    """
    Проверяет, является ли пользователь администратором.
    
    Args:
        telegram_id: ID пользователя в Telegram.
        session: Сессия SQLAlchemy (опционально).
    
    Returns:
        True, если пользователь является администратором,
        иначе False.
    """
    return check_user_role(telegram_id, UserRole.ADMIN, session)


def is_targetologist(telegram_id: int, session: Optional[Session] = None) -> bool:
    """
    Проверяет, является ли пользователь таргетологом или администратором.
    
    Args:
        telegram_id: ID пользователя в Telegram.
        session: Сессия SQLAlchemy (опционально).
    
    Returns:
        True, если пользователь является таргетологом или администратором,
        иначе False.
    """
    return check_user_role(telegram_id, UserRole.TARGETOLOGIST, session)


def has_campaign_access(telegram_id: int, campaign_id: str, 
                       session: Optional[Session] = None) -> bool:
    """
    Проверяет, имеет ли пользователь доступ к указанной кампании.
    
    Администраторы и таргетологи имеют доступ ко всем кампаниям.
    Партнеры имеют доступ только к разрешенным кампаниям.
    
    Args:
        telegram_id: ID пользователя в Telegram.
        campaign_id: ID кампании.
        session: Сессия SQLAlchemy (опционально).
    
    Returns:
        True, если пользователь имеет доступ к кампании,
        иначе False.
    """
    close_repos = False
    user_repo = None
    access_control_repo = None
    
    try:
        # Создаем репозитории
        if session is None:
            user_repo = UserRepository()
            access_control_repo = AccessControlRepository()
            close_repos = True
        else:
            user_repo = UserRepository(session=session)
            access_control_repo = AccessControlRepository(session=session)
        
        # Получаем пользователя из базы данных
        user = user_repo.get_user_by_id(telegram_id)
        
        # Если пользователь не найден, возвращаем False
        if user is None:
            logger.debug(f"Пользователь с ID {telegram_id} не найден")
            return False
        
        # Администраторы и таргетологи имеют доступ ко всем кампаниям
        if user.role in [UserRole.ADMIN.value, UserRole.TARGETOLOGIST.value]:
            return True
        
        # Для партнеров проверяем наличие доступа к конкретной кампании
        return access_control_repo.check_access(
            telegram_id=telegram_id,
            resource_type="campaign",
            resource_id=campaign_id
        )
    except Exception as e:
        logger.error(f"Ошибка при проверке доступа к кампании: {str(e)}")
        return False
    finally:
        # Закрываем репозитории, если мы их создали
        if close_repos:
            if user_repo is not None:
                user_repo.close()
            if access_control_repo is not None:
                access_control_repo.close()


def has_financial_access(telegram_id: int, session: Optional[Session] = None) -> bool:
    """
    Проверяет, имеет ли пользователь доступ к финансовым данным.
    
    Только администраторы имеют доступ к финансовым данным.
    
    Args:
        telegram_id: ID пользователя в Telegram.
        session: Сессия SQLAlchemy (опционально).
    
    Returns:
        True, если пользователь имеет доступ к финансовым данным,
        иначе False.
    """
    return is_admin(telegram_id, session) 