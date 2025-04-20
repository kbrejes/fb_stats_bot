"""
Утилиты контроля доступа для проверки ролей пользователей и прав доступа к ресурсам.
"""
from typing import Optional, List, Union

from sqlalchemy.orm import Session

from src.storage.database import get_session
from src.storage.models import User
from src.storage.enums import UserRole
from src.repositories.access_control_repository import AccessControlRepository
from src.utils.logger import get_logger

logger = get_logger(__name__)


def check_user_role(user_id: int, role: Union[UserRole, str], session: Optional[Session] = None) -> bool:
    """
    Проверяет, имеет ли пользователь указанную роль.
    
    Args:
        user_id: Telegram ID пользователя
        role: Роль для проверки (значение перечисления UserRole или строка)
        session: Сессия базы данных (опционально)
        
    Returns:
        bool: True, если пользователь имеет указанную роль, иначе False
        
    Raises:
        ValueError: Если указана недопустимая роль
    """
    # Обрабатываем случай, когда роль передана как строка, но не как экземпляр UserRole
    if isinstance(role, str) and not isinstance(role, UserRole):
        try:
            role = UserRole[role]
        except KeyError:
            raise ValueError(f"Недопустимая роль: {role}")
    
    # Получаем сессию БД, если она не передана
    if session is None:
        session = get_session()
    
    # Ищем пользователя в БД
    user = session.query(User).filter(User.telegram_id == user_id).first()
    
    # Если пользователь не найден, возвращаем False
    if user is None:
        logger.warning(f"Пользователь с ID {user_id} не найден в базе данных")
        return False
    
    # Проверяем, имеет ли пользователь указанную роль
    return user.has_permission(role)


def is_admin(user_id: int, session: Optional[Session] = None) -> bool:
    """
    Проверяет, является ли пользователь администратором.
    
    Args:
        user_id: Telegram ID пользователя
        session: Сессия базы данных (опционально)
        
    Returns:
        bool: True, если пользователь является администратором, иначе False
    """
    return check_user_role(user_id, UserRole.ADMIN, session)


def is_targetologist(user_id: int, session: Optional[Session] = None) -> bool:
    """
    Проверяет, является ли пользователь таргетологом.
    
    Args:
        user_id: Telegram ID пользователя
        session: Сессия базы данных (опционально)
        
    Returns:
        bool: True, если пользователь является таргетологом, иначе False
    """
    return check_user_role(user_id, UserRole.TARGETOLOGIST, session)


def has_campaign_access(user_id: int, campaign_id: str, session: Optional[Session] = None) -> bool:
    """
    Проверяет, имеет ли пользователь доступ к указанной кампании.
    
    Args:
        user_id: Telegram ID пользователя
        campaign_id: ID кампании
        session: Сессия базы данных (опционально)
        
    Returns:
        bool: True, если пользователь имеет доступ к кампании, иначе False
    """
    # Получаем сессию БД, если она не передана
    if session is None:
        session = get_session()
    
    # Ищем пользователя в БД
    user = session.query(User).filter(User.telegram_id == user_id).first()
    
    # Если пользователь не найден, возвращаем False
    if user is None:
        logger.warning(f"Пользователь с ID {user_id} не найден в базе данных")
        return False
    
    # Администраторы и таргетологи имеют доступ ко всем кампаниям
    if user.is_admin() or user.is_targetologist():
        return True
    
    # Для партнеров проверяем наличие доступа через репозиторий
    repo = AccessControlRepository(session)
    return repo.check_access(
        user_id=user_id,
        resource_type="campaign",
        resource_id=campaign_id
    )


def has_financial_access(user_id: int, session: Optional[Session] = None) -> bool:
    """
    Проверяет, имеет ли пользователь доступ к финансовой информации.
    
    Args:
        user_id: Telegram ID пользователя
        session: Сессия базы данных (опционально)
        
    Returns:
        bool: True, если пользователь имеет доступ к финансовой информации, иначе False
    """
    # Только администраторы имеют доступ к финансовой информации
    return is_admin(user_id, session)


def get_user_campaigns(user_id: int, session: Optional[Session] = None) -> Optional[List[str]]:
    """
    Возвращает список ID кампаний, к которым у пользователя есть доступ.
    Для администраторов и таргетологов возвращает None, что означает "все кампании".
    
    Args:
        user_id: Telegram ID пользователя
        session: Сессия базы данных (опционально)
        
    Returns:
        Optional[List[str]]: Список ID кампаний или None для администраторов и таргетологов
    """
    # Получаем сессию БД, если она не передана
    if session is None:
        session = get_session()
    
    # Ищем пользователя в БД
    user = session.query(User).filter(User.telegram_id == user_id).first()
    
    # Если пользователь не найден, возвращаем пустой список
    if user is None:
        logger.warning(f"Пользователь с ID {user_id} не найден в базе данных")
        return []
    
    # Администраторы и таргетологи имеют доступ ко всем кампаниям
    if user.is_admin() or user.is_targetologist():
        return None
    
    # Для партнеров получаем список доступных кампаний
    repo = AccessControlRepository(session)
    permissions = repo.get_partner_permissions(user_id)
    
    # Фильтруем только действительные разрешения для кампаний
    campaign_ids = [
        p.resource_id for p in permissions 
        if p.resource_type == "campaign" and p.is_valid()
    ]
    
    return campaign_ids 