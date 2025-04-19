"""
SQLAlchemy models for the application.
"""
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from enum import Enum, auto

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from src.storage.database import Base
from src.utils.security import encrypt_token, decrypt_token
from src.utils.logger import get_logger

logger = get_logger(__name__)

class UserRole(Enum):
    """Роли пользователей в системе."""
    ADMIN = "admin"           # Полный доступ ко всем функциям
    TARGETOLOGIST = "targetologist"  # Полный доступ кроме платежных данных
    PARTNER = "partner"       # Ограниченный доступ только к статистике

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
    
    # Role information
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
    
    def get_role(self) -> UserRole:
        """
        Get the user's role.
        
        Returns:
            The user's role as UserRole enum.
        """
        try:
            return UserRole(self.role)
        except ValueError:
            # If the role is invalid, log an error and return the default role
            logger.error(f"Invalid role '{self.role}' for user {self.telegram_id}, using default")
            return UserRole.PARTNER
    
    def set_role(self, role: UserRole) -> None:
        """
        Set the user's role.
        
        Args:
            role: The role to set for the user.
        """
        self.role = role.value
    
    def is_admin(self) -> bool:
        """
        Check if the user has admin role.
        
        Returns:
            True if the user is an admin, False otherwise.
        """
        return self.get_role() == UserRole.ADMIN
    
    def is_targetologist(self) -> bool:
        """
        Check if the user has targetologist role.
        
        Returns:
            True if the user is a targetologist, False otherwise.
        """
        return self.get_role() == UserRole.TARGETOLOGIST
    
    def is_partner(self) -> bool:
        """
        Check if the user has partner role.
        
        Returns:
            True if the user is a partner, False otherwise.
        """
        return self.get_role() == UserRole.PARTNER


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

    @classmethod
    def clear_by_prefix(cls, session, prefix: str):
        """
        Clear all cache entries with a given prefix.
        
        Args:
            session: The database session.
            prefix: The prefix to match in cache keys.
        """
        # Find all entries with the given prefix
        cache_entries = session.query(cls).filter(
            cls.key.like(f"{prefix}%")
        ).all()
        
        # Delete them
        for entry in cache_entries:
            session.delete(entry)
        
        session.commit()

    @classmethod
    def clear_all(cls, session):
        """
        Clear all cache entries.
        
        Args:
            session: The database session.
        """
        return cls.clear_by_prefix(session, "")


class AccessRequest(Base):
    """Model for managing partner access requests."""
    __tablename__ = 'access_requests'

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign key to User (partner)
    partner_id = Column(Integer, ForeignKey('users.telegram_id'), nullable=False)
    
    # Request information
    status = Column(String(20), default="pending", nullable=False)  # 'pending', 'approved', 'rejected'
    requested_at = Column(DateTime, default=func.now(), nullable=False)
    processed_at = Column(DateTime, nullable=True)
    
    # Foreign key to User (admin who processed the request)
    processed_by = Column(Integer, ForeignKey('users.telegram_id'), nullable=True)
    
    # Relationships
    partner = relationship("User", foreign_keys=[partner_id])
    admin = relationship("User", foreign_keys=[processed_by])
    
    def __repr__(self):
        return f"<AccessRequest {self.id} by partner {self.partner_id}, status: {self.status}>"


class AccessControl(Base):
    """Model for managing partner access to campaigns."""
    __tablename__ = 'access_controls'

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign key to User (partner)
    partner_id = Column(Integer, ForeignKey('users.telegram_id'), nullable=False)
    
    # Foreign key to User (admin who granted access)
    admin_id = Column(Integer, ForeignKey('users.telegram_id'), nullable=False)
    
    # Campaign information
    campaign_id = Column(String(255), nullable=False)
    
    # Access information
    granted_at = Column(DateTime, default=func.now(), nullable=False)
    expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    partner = relationship("User", foreign_keys=[partner_id])
    admin = relationship("User", foreign_keys=[admin_id])
    
    def __repr__(self):
        return f"<AccessControl {self.id} for partner {self.partner_id}, campaign: {self.campaign_id}>"
    
    def is_expired(self) -> bool:
        """
        Check if the access has expired.
        
        Returns:
            True if the access has expired, False otherwise.
        """
        if not self.expires_at:
            return False
            
        return datetime.now() > self.expires_at 