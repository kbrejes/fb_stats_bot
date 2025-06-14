"""
SQLAlchemy models for the application.
"""

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import (JSON, Boolean, Column, DateTime, ForeignKey, Integer,
                        String, Table, Text, Time)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from src.storage.database import Base
from src.utils.logger import get_logger
from src.utils.security import decrypt_token, encrypt_token

logger = get_logger(__name__)

# Ассоциативная таблица для связи многие-ко-многим между пользователями и аккаунтами
accounts_to_users = Table(
    "accounts_to_users",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.telegram_id"), primary_key=True),
    Column("account_id", Integer, ForeignKey("accounts.id"), primary_key=True),
)


class Permission(Base):
    """Model for storing role-based permissions."""

    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    role = Column(String(255), nullable=False)
    permission = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    users = relationship(
        "User",
        primaryjoin="Permission.role==User.role",
        foreign_keys="User.role",
        backref="permissions",
        viewonly=True,
    )

    def __repr__(self):
        return f"<Permission {self.id}: {self.role} - {self.permission}>"

    @classmethod
    def get_permissions_for_role(cls, session, role_name: str) -> List[str]:
        """
        Get all permissions for a specific role.

        Args:
            session: The database session.
            role_name: The name of the role.

        Returns:
            List of permission strings for this role.
        """
        permissions = session.query(cls).filter_by(role=role_name).all()
        return [p.permission for p in permissions if p.permission]


class User(Base):
    """User model for storing Telegram user data and Facebook tokens."""

    __tablename__ = "users"

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

    # State tracking
    last_command = Column(String(255), nullable=True)
    last_context = Column(Text, nullable=True)  # JSON-encoded context data

    # Role-based access control
    role = Column(String(255), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    accounts = relationship(
        "Account", back_populates="user", cascade="all, delete-orphan"
    )
    shared_accounts = relationship(
        "Account", secondary=accounts_to_users, backref="shared_users"
    )
    notification_settings = relationship(
        "NotificationSettings",
        back_populates="user",
        uselist=False,  # один-к-одному
        cascade="all, delete-orphan",
    )

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
            print(
                f"DEBUG: Token validation for user {self.telegram_id} - No token found"
            )
            return False

        if not self.token_expires_at:
            print(
                f"DEBUG: Token validation for user {self.telegram_id} - No expiration time, assuming valid"
            )
            return True  # No expiration time set, assuming valid

        now = datetime.now()
        expires = self.token_expires_at
        is_valid = now < expires

        print(
            f"DEBUG: Token validation for user {self.telegram_id} - "
            + f"Current time: {now.isoformat()}, Expires: {expires.isoformat()}, Valid: {is_valid}"
        )

        # If token expires in less than 10 minutes, consider it expired
        if is_valid and (expires - now).total_seconds() < 600:
            print(
                f"DEBUG: Token for user {self.telegram_id} expires in less than 10 minutes, considering expired"
            )
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

    def get_permissions(self, session) -> List[str]:
        """
        Get all permissions for this user based on their role.

        Args:
            session: The database session.

        Returns:
            List of permission strings for this user.
        """
        if not self.role:
            return []

        return Permission.get_permissions_for_role(session, self.role)

    def has_permission(self, session, permission: str) -> bool:
        """
        Check if the user has a specific permission.

        Args:
            session: The database session.
            permission: The permission to check.

        Returns:
            True if the user has the permission, False otherwise.
        """
        permissions = self.get_permissions(session)
        return permission in permissions


class Account(Base):
    """Model for storing Facebook Ad Account information."""

    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Foreign key to User
    telegram_id = Column(Integer, ForeignKey("users.telegram_id"), nullable=False)

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

    __tablename__ = "cache"

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
            cache_entry = cls(key=key, value=json.dumps(value), expires_at=expires_at)
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

        Returns:
            Number of entries cleared.
        """
        now = datetime.now()
        expired_entries = session.query(cls).filter(cls.expires_at < now).all()
        count = len(expired_entries)

        for entry in expired_entries:
            session.delete(entry)

        session.commit()
        return count


class NotificationSettings(Base):
    """Настройки уведомлений пользователя."""

    __tablename__ = "notification_settings"

    id = Column(Integer, primary_key=True)
    user_id = Column(
        Integer, ForeignKey("users.telegram_id", ondelete="CASCADE"), nullable=False
    )
    enabled = Column(Boolean, default=True, nullable=False)
    notification_time = Column(Time, nullable=False)  # Время отправки уведомлений
    timezone = Column(
        String, nullable=False, default="UTC"
    )  # Часовой пояс пользователя
    notification_types = Column(
        JSON,
        nullable=False,
        default={
            "daily_stats": True,
            "performance_alerts": True,
            "budget_alerts": True,
        },
    )
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Связь с пользователем
    user = relationship("User", back_populates="notification_settings")
