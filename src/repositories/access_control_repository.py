"""
Репозиторий для работы с разрешениями доступа.
"""
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy import and_

from src.storage.database import get_session
from src.storage.models import AccessControl, User
from src.utils.logger import get_logger

logger = get_logger(__name__)


class AccessControlRepository:
    """Репозиторий для работы с разрешениями доступа партнеров к ресурсам."""
    
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
    
    def get_partner_permissions(self, telegram_id: int) -> List[AccessControl]:
        """
        Получает список активных разрешений для партнера.
        
        Args:
            telegram_id: Telegram ID пользователя.
            
        Returns:
            Список объектов AccessControl.
        """
        try:
            permissions = self.session.query(AccessControl).filter(
                AccessControl.telegram_id == telegram_id,
                AccessControl.is_active == True
            ).all()
            
            # Отфильтровываем истекшие разрешения
            valid_permissions = [p for p in permissions if p.is_valid()]
            
            return valid_permissions
        except Exception as e:
            logger.error(f"Error fetching permissions for user {telegram_id}: {str(e)}")
            return []
    
    def grant_access(
        self, 
        telegram_id: int, 
        resource_type: str, 
        resource_id: str, 
        expires_in_days: Optional[int] = 30,
        params: Optional[Dict[str, Any]] = None
    ) -> Optional[AccessControl]:
        """
        Предоставляет доступ партнеру к ресурсу.
        
        Args:
            telegram_id: Telegram ID пользователя.
            resource_type: Тип ресурса ("campaign", "account", etc.).
            resource_id: ID ресурса.
            expires_in_days: Срок действия доступа в днях (None - бессрочно).
            params: Дополнительные параметры доступа.
            
        Returns:
            Объект AccessControl или None в случае ошибки.
        """
        try:
            # Проверяем существование пользователя
            user = self.session.query(User).filter(User.telegram_id == telegram_id).first()
            if not user:
                logger.error(f"User {telegram_id} not found")
                return None
            
            # Ищем существующий доступ
            existing_access = self.session.query(AccessControl).filter(
                AccessControl.telegram_id == telegram_id,
                AccessControl.resource_type == resource_type,
                AccessControl.resource_id == resource_id
            ).first()
            
            if existing_access:
                # Обновляем существующий доступ
                existing_access.is_active = True
                
                if expires_in_days is not None:
                    existing_access.expires_at = datetime.now() + timedelta(days=expires_in_days)
                else:
                    existing_access.expires_at = None
                
                if params:
                    existing_access.set_params(params)
                
                self.session.commit()
                logger.info(f"Updated access for user {telegram_id} to {resource_type}:{resource_id}")
                return existing_access
            else:
                # Создаем новый доступ
                expires_at = datetime.now() + timedelta(days=expires_in_days) if expires_in_days is not None else None
                
                access_control = AccessControl(
                    telegram_id=telegram_id,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    expires_at=expires_at,
                    is_active=True
                )
                
                if params:
                    access_control.set_params(params)
                
                self.session.add(access_control)
                self.session.commit()
                logger.info(f"Granted access for user {telegram_id} to {resource_type}:{resource_id}")
                return access_control
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error granting access for user {telegram_id}: {str(e)}")
            return None
    
    def revoke_access(self, telegram_id: int, resource_type: str, resource_id: str) -> bool:
        """
        Отзывает доступ партнера к ресурсу.
        
        Args:
            telegram_id: Telegram ID пользователя.
            resource_type: Тип ресурса.
            resource_id: ID ресурса.
            
        Returns:
            True, если доступ успешно отозван, иначе False.
        """
        try:
            access = self.session.query(AccessControl).filter(
                AccessControl.telegram_id == telegram_id,
                AccessControl.resource_type == resource_type,
                AccessControl.resource_id == resource_id
            ).first()
            
            if access:
                access.is_active = False
                self.session.commit()
                logger.info(f"Revoked access for user {telegram_id} to {resource_type}:{resource_id}")
                return True
            else:
                logger.warning(f"Access not found for user {telegram_id} to {resource_type}:{resource_id}")
                return False
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error revoking access for user {telegram_id}: {str(e)}")
            return False
    
    def check_access(self, telegram_id: int, resource_type: str, resource_id: str) -> bool:
        """
        Проверяет наличие доступа партнера к ресурсу.
        
        Args:
            telegram_id: Telegram ID пользователя.
            resource_type: Тип ресурса.
            resource_id: ID ресурса.
            
        Returns:
            True, если доступ есть, иначе False.
        """
        try:
            # Проверяем роль пользователя
            user = self.session.query(User).filter(User.telegram_id == telegram_id).first()
            if not user:
                return False
            
            # Администраторы и таргетологи имеют доступ ко всем ресурсам
            if user.is_targetologist():
                return True
            
            # Для партнеров проверяем наличие разрешения
            access = self.session.query(AccessControl).filter(
                AccessControl.telegram_id == telegram_id,
                AccessControl.resource_type == resource_type,
                AccessControl.resource_id == resource_id,
                AccessControl.is_active == True
            ).first()
            
            if access and access.is_valid():
                return True
            
            return False
        except Exception as e:
            logger.error(f"Error checking access for user {telegram_id}: {str(e)}")
            return False
    
    def get_resource_access_list(self, resource_type: str, resource_id: str) -> List[AccessControl]:
        """
        Получает список всех разрешений для указанного ресурса.
        
        Args:
            resource_type: Тип ресурса.
            resource_id: ID ресурса.
            
        Returns:
            Список объектов AccessControl.
        """
        try:
            permissions = self.session.query(AccessControl).filter(
                AccessControl.resource_type == resource_type,
                AccessControl.resource_id == resource_id,
                AccessControl.is_active == True
            ).all()
            
            # Отфильтровываем истекшие разрешения
            valid_permissions = [p for p in permissions if p.is_valid()]
            
            return valid_permissions
        except Exception as e:
            logger.error(f"Error fetching access list for {resource_type}:{resource_id}: {str(e)}")
            return []
    
    def clean_expired_permissions(self) -> int:
        """
        Очищает истекшие разрешения.
        
        Returns:
            Количество деактивированных разрешений.
        """
        try:
            now = datetime.now()
            expired_permissions = self.session.query(AccessControl).filter(
                AccessControl.is_active == True,
                AccessControl.expires_at != None,
                AccessControl.expires_at < now
            ).all()
            
            count = 0
            for permission in expired_permissions:
                permission.is_active = False
                count += 1
            
            if count > 0:
                self.session.commit()
                logger.info(f"Deactivated {count} expired permissions")
            
            return count
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error cleaning expired permissions: {str(e)}")
            return 0 