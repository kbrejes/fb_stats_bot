"""
SQLAlchemy models for the application.
"""
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from src.storage.database import Base
from src.utils.security import encrypt_token, decrypt_token
from src.utils.logger import get_logger
from src.storage.enums import UserRole

logger = get_logger(__name__)

class User(Base):
    """User model for storing Telegram user data and Facebook tokens."""
    __tablename__ = 'users'

    # Primary key - Telegram user ID
    telegram_id = Column(Integer, primary_key=True)
    
    # User information
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    
    # Facebook authentication
    fb_access_token = Column(Text, nullable=True)
    fb_refresh_token = Column(Text, nullable=True)
    token_expires_at = Column(DateTime, nullable=True)
    
    # User preferences
    language = Column(String(10), default="ru", nullable=False)
    
    # User role for access control
    role = Column(String(20), default=UserRole.PARTNER.value, nullable=False)
    
    # State tracking
    last_command = Column(String(255), nullable=True)
    last_context = Column(Text, nullable=True)  # JSON-encoded context data
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    accounts = relationship("Account", back_populates="user", cascade="all, delete-orphan")

    def set_fb_token(self, token: str, expires_in: int = 0):
        """
        Set the Facebook access token with encryption.
        
        Args:
            token: The Facebook access token.
            expires_in: Token expiration time in seconds.
        """
        self.fb_access_token = encrypt_token(token)
        
        if expires_in > 0:
            self.token_expires_at = datetime.now() + timedelta(seconds=expires_in)
        else:
            self.token_expires_at = None
    
    def get_fb_token(self) -> Optional[str]:
        """
        Get the decrypted Facebook access token.
        
        Returns:
            The decrypted token or None if not set.
        """
        if not self.fb_access_token:
            return None
        
        return decrypt_token(self.fb_access_token)
    
    def set_fb_refresh_token(self, token: str):
        """
        Set the Facebook refresh token with encryption.
        
        Args:
            token: The Facebook refresh token.
        """
        self.fb_refresh_token = encrypt_token(token)
    
    def get_fb_refresh_token(self) -> Optional[str]:
        """
        Get the decrypted Facebook refresh token.
        
        Returns:
            The decrypted refresh token or None if not set.
        """
        if not self.fb_refresh_token:
            return None
        
        return decrypt_token(self.fb_refresh_token)
    
    def is_token_valid(self) -> bool:
        """
        Check if the Facebook token is still valid.
        
        Returns:
            True if the token is valid, False otherwise.
        """
        if not self.fb_access_token:
            print(f"DEBUG: Token validation for user {self.telegram_id} - No token found")
            return False
        
        if not self.token_expires_at:
            print(f"DEBUG: Token validation for user {self.telegram_id} - No expiration time, assuming valid")
            return True  # No expiration time set, assuming valid
        
        now = datetime.now()
        expires = self.token_expires_at
        is_valid = now < expires
        
        print(f"DEBUG: Token validation for user {self.telegram_id} - " +
              f"Current time: {now.isoformat()}, Expires: {expires.isoformat()}, Valid: {is_valid}")
        
        # If token expires in less than 10 minutes, consider it expired
        if is_valid and (expires - now).total_seconds() < 600:
            print(f"DEBUG: Token for user {self.telegram_id} expires in less than 10 minutes, considering expired")
            return False
            
        return is_valid
    
    def set_context(self, context_data: Dict[str, Any]):
        """
        Save context data for the user.
        
        Args:
            context_data: The context data to save.
        """
        self.last_context = json.dumps(context_data)
    
    def get_context(self) -> Dict[str, Any]:
        """
        Get the user's context data.
        
        Returns:
            The context data or an empty dict if not set.
        """
        if not self.last_context:
            return {}
        
        try:
            return json.loads(self.last_context)
        except json.JSONDecodeError:
            logger.error(f"Failed to decode context for user {self.telegram_id}")
            return {}
    
    def get_user_role(self) -> UserRole:
        """
        Получает роль пользователя как объект перечисления UserRole.
        
        Returns:
            Объект UserRole, соответствующий роли пользователя.
        """
        try:
            return UserRole(self.role)
        except ValueError:
            logger.warning(f"Invalid role '{self.role}' for user {self.telegram_id}, using PARTNER as default")
            # Если роль недействительна, используем роль по умолчанию
            return UserRole.PARTNER
    
    def set_user_role(self, role: UserRole) -> bool:
        """
        Устанавливает роль пользователя.
        
        Args:
            role: Роль пользователя (объект UserRole или строка).
            
        Returns:
            True, если роль была установлена успешно, иначе False.
        """
        if isinstance(role, str):
            if not UserRole.has_value(role):
                logger.error(f"Trying to set invalid role '{role}' for user {self.telegram_id}")
                return False
            self.role = role
        else:
            self.role = role.value
        
        return True
    
    def is_admin(self) -> bool:
        """
        Проверяет, является ли пользователь администратором.
        
        Returns:
            True, если пользователь имеет роль ADMIN, иначе False.
        """
        return self.get_user_role() == UserRole.ADMIN
    
    def is_targetologist(self) -> bool:
        """
        Проверяет, является ли пользователь таргетологом или администратором.
        
        Returns:
            True, если пользователь имеет роль TARGETOLOGIST или ADMIN, иначе False.
        """
        role = self.get_user_role()
        return role in [UserRole.TARGETOLOGIST, UserRole.ADMIN]
    
    def is_partner(self) -> bool:
        """
        Проверяет, является ли пользователь партнером.
        Все пользователи имеют как минимум права партнера.
        
        Returns:
            True всегда, так как все пользователи имеют как минимум права партнера.
        """
        return True
    
    def has_financial_access(self) -> bool:
        """
        Проверяет, имеет ли пользователь доступ к финансовой информации.
        
        Returns:
            True, если пользователь имеет роль ADMIN, иначе False.
        """
        return self.is_admin()
    
    def has_creative_access(self) -> bool:
        """
        Проверяет, имеет ли пользователь доступ к управлению креативами.
        
        Returns:
            True, если пользователь имеет роль ADMIN или TARGETOLOGIST, иначе False.
        """
        return self.is_targetologist()
    
    def has_user_management_access(self) -> bool:
        """
        Проверяет, имеет ли пользователь доступ к управлению пользователями.
        
        Returns:
            True, если пользователь имеет роль ADMIN, иначе False.
        """
        return self.is_admin()
    
    def has_permission(self, required_role: UserRole) -> bool:
        """
        Проверяет, имеет ли пользователь разрешения роли required_role.
        
        Args:
            required_role: Требуемая роль для проверки.
            
        Returns:
            True, если пользователь имеет соответствующие права доступа, иначе False.
        """
        return self.get_user_role().has_permission(required_role)
    
    def has_campaign_access(self, campaign_id: str) -> bool:
        """
        Проверяет, имеет ли пользователь доступ к кампании.
        
        Args:
            campaign_id: Идентификатор кампании для проверки.
            
        Returns:
            True, если пользователь имеет доступ к кампании, иначе False.
        """
        # Администраторы и таргетологи имеют доступ ко всем кампаниям
        if self.is_targetologist():
            return True
        
        # Для партнеров проверяем наличие специальных разрешений в Access Control
        try:
            from sqlalchemy.orm import Session
            from src.storage.database import get_session
            
            session = get_session()
            try:
                # Проверяем наличие активного разрешения для данной кампании
                access_control = session.query(AccessControl).filter(
                    AccessControl.telegram_id == self.telegram_id,
                    AccessControl.resource_type == "campaign",
                    AccessControl.resource_id == campaign_id,
                    AccessControl.is_active == True
                ).first()
                
                if access_control and access_control.is_valid():
                    return True
            finally:
                session.close()
        except Exception as e:
            # В случае ошибки (например, таблица еще не создана) логируем и возвращаем False
            logger.error(f"Error checking campaign access: {str(e)}")
        
        return False


class AccessControl(Base):
    """Модель для отслеживания разрешений партнеров."""
    __tablename__ = 'access_controls'

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Связь с пользователем
    telegram_id = Column(Integer, ForeignKey('users.telegram_id'), nullable=False)
    
    # Тип ресурса и его идентификатор
    resource_type = Column(String(50), nullable=False)  # campaign, account, etc.
    resource_id = Column(String(255), nullable=False)
    
    # Срок действия разрешения
    created_at = Column(DateTime, default=func.now())
    expires_at = Column(DateTime, nullable=True)  # Если None, разрешение не истекает
    
    # Статус разрешения
    is_active = Column(Boolean, default=True)
    
    # Дополнительные параметры (JSON)
    parameters = Column(Text, nullable=True)
    
    # Отношения
    user = relationship("User", backref="access_controls")
    
    def is_valid(self) -> bool:
        """
        Проверяет, действительно ли разрешение.
        
        Returns:
            True, если разрешение активно и не истекло, иначе False.
        """
        if not self.is_active:
            return False
            
        if self.expires_at is not None and datetime.now() > self.expires_at:
            return False
            
        return True
    
    def get_params(self) -> Dict[str, Any]:
        """
        Получает параметры разрешения.
        
        Returns:
            Словарь с параметрами или пустой словарь, если параметры не заданы.
        """
        if not self.parameters:
            return {}
            
        try:
            return json.loads(self.parameters)
        except json.JSONDecodeError:
            logger.error(f"Failed to decode parameters for access control {self.id}")
            return {}
    
    def set_params(self, params: Dict[str, Any]):
        """
        Устанавливает параметры разрешения.
        
        Args:
            params: Словарь с параметрами.
        """
        self.parameters = json.dumps(params)
    
    def extend_expiration(self, days: int = 30):
        """
        Продляет срок действия разрешения.
        
        Args:
            days: Количество дней для продления.
        """
        now = datetime.now()
        if self.expires_at is None:
            # Если разрешение не имеет срока действия, устанавливаем его
            self.expires_at = now + timedelta(days=days)
        else:
            # Если срок действия уже установлен, продляем его
            self.expires_at = self.expires_at + timedelta(days=days)
    
    def deactivate(self):
        """Деактивирует разрешение."""
        self.is_active = False
    
    def reactivate(self):
        """Активирует разрешение."""
        self.is_active = True
        
        now = datetime.now()
        # Если срок действия истек, продляем его на 30 дней
        if self.expires_at is not None and now > self.expires_at:
            self.expires_at = now + timedelta(days=30)


class AccessRequest(Base):
    """Модель для запросов доступа от партнеров."""
    __tablename__ = 'access_requests'

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Связь с пользователем
    telegram_id = Column(Integer, ForeignKey('users.telegram_id'), nullable=False)
    
    # Тип ресурса и идентификатор
    resource_type = Column(String(50), nullable=False)  # campaign, account, etc.
    resource_id = Column(String(255), nullable=False)
    
    # Статус запроса
    status = Column(String(20), default="pending", nullable=False)  # pending, approved, rejected
    
    # Дополнительная информация
    message = Column(Text, nullable=True)  # Сообщение от пользователя
    admin_notes = Column(Text, nullable=True)  # Заметки администратора
    
    # Запрашиваемая длительность доступа (в днях)
    requested_duration = Column(Integer, default=30, nullable=False)
    
    # Таймстампы
    created_at = Column(DateTime, default=func.now())
    processed_at = Column(DateTime, nullable=True)  # Время обработки запроса
    processed_by = Column(Integer, nullable=True)  # ID администратора, обработавшего запрос
    
    # Связи
    user = relationship("User", backref="access_requests")
    
    def is_pending(self) -> bool:
        """
        Проверяет, находится ли запрос в ожидании обработки.
        
        Returns:
            True, если запрос в статусе 'pending', иначе False.
        """
        return self.status == "pending"
    
    def is_approved(self) -> bool:
        """
        Проверяет, был ли запрос одобрен.
        
        Returns:
            True, если запрос в статусе 'approved', иначе False.
        """
        return self.status == "approved"
    
    def is_rejected(self) -> bool:
        """
        Проверяет, был ли запрос отклонен.
        
        Returns:
            True, если запрос в статусе 'rejected', иначе False.
        """
        return self.status == "rejected"
    
    def approve(self, admin_id: int, admin_notes: str = None):
        """
        Одобряет запрос доступа.
        
        Args:
            admin_id: ID администратора, одобрившего запрос.
            admin_notes: Заметки администратора (опционально).
        """
        self.status = "approved"
        self.processed_at = datetime.now()
        self.processed_by = admin_id
        
        if admin_notes:
            self.admin_notes = admin_notes
    
    def reject(self, admin_id: int, admin_notes: str = None):
        """
        Отклоняет запрос доступа.
        
        Args:
            admin_id: ID администратора, отклонившего запрос.
            admin_notes: Заметки администратора (опционально).
        """
        self.status = "rejected"
        self.processed_at = datetime.now()
        self.processed_by = admin_id
        
        if admin_notes:
            self.admin_notes = admin_notes
    
    def reset_status(self):
        """Сбрасывает статус запроса до 'pending'."""
        self.status = "pending"
        self.processed_at = None
        self.processed_by = None


class Account(Base):
    """Model for storing Facebook Ad Account information."""
    __tablename__ = 'accounts'

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign key to User
    telegram_id = Column(Integer, ForeignKey('users.telegram_id'), nullable=False)
    
    # Account information
    fb_account_id = Column(String(255), nullable=False)
    name = Column(String(255), nullable=True)
    currency = Column(String(10), nullable=True)
    timezone_name = Column(String(100), nullable=True)
    
    # Is this the user's primary account?
    is_primary = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="accounts")

    def __repr__(self):
        return f"<Account {self.fb_account_id} ({self.name})>"


class Cache(Base):
    """Model for caching API responses."""
    __tablename__ = 'cache'

    # Cache key (unique identifier)
    key = Column(String(255), primary_key=True)
    
    # Cache value (JSON-encoded data)
    value = Column(Text, nullable=False)
    
    # Expiration timestamp
    expires_at = Column(DateTime, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())

    @classmethod
    def set(cls, session, key: str, value: Any, expires_in: int = 3600):
        """
        Set a cache entry.
        
        Args:
            session: The database session.
            key: The cache key.
            value: The value to cache.
            expires_in: Cache expiration time in seconds.
        """
        expires_at = datetime.now() + timedelta(seconds=expires_in)
        
        # Try to get existing cache entry
        cache_entry = session.query(cls).filter_by(key=key).first()
        
        if cache_entry:
            # Update existing entry
            cache_entry.value = json.dumps(value)
            cache_entry.expires_at = expires_at
        else:
            # Create new entry
            cache_entry = cls(
                key=key,
                value=json.dumps(value),
                expires_at=expires_at
            )
            session.add(cache_entry)
        
        session.commit()
    
    @classmethod
    def get(cls, session, key: str) -> Optional[Any]:
        """
        Get a cache entry.
        
        Args:
            session: The database session.
            key: The cache key.
            
        Returns:
            The cached value or None if not found or expired.
        """
        # Try to get the cache entry
        cache_entry = session.query(cls).filter_by(key=key).first()
        
        if not cache_entry:
            return None
        
        # Check if expired
        if datetime.now() > cache_entry.expires_at:
            # Delete expired entry
            session.delete(cache_entry)
            session.commit()
            return None
        
        # Return value
        try:
            return json.loads(cache_entry.value)
        except json.JSONDecodeError:
            logger.error(f"Failed to decode cache value for key {key}")
            return None
    
    @classmethod
    def delete(cls, session, key: str):
        """
        Delete a cache entry.
        
        Args:
            session: The database session.
            key: The cache key.
        """
        # Try to get the cache entry
        cache_entry = session.query(cls).filter_by(key=key).first()
        
        if cache_entry:
            session.delete(cache_entry)
            session.commit()
    
    @classmethod
    def clear_expired(cls, session):
        """
        Clear all expired cache entries.
        
        Args:
            session: The database session.
        """
        # Find all expired entries
        expired_entries = session.query(cls).filter(
            cls.expires_at < datetime.now()
        ).all()
        
        # Delete them
        for entry in expired_entries:
            session.delete(entry)
        
        session.commit() 