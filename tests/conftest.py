"""
Конфигурация и общие фикстуры для тестов.
"""
import os
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session

from src.storage.database import Base
from src.storage.models import User, NotificationSettings

@pytest.fixture(scope="session")
def engine():
    """Create a test database engine."""
    # Используем SQLite в памяти для тестов
    engine = create_engine("sqlite:///:memory:")
    
    # Включаем поддержку внешних ключей для SQLite
    def _enable_foreign_keys(connection, connection_record):
        connection.execute('pragma foreign_keys=ON')
    
    event.listen(engine, 'connect', _enable_foreign_keys)
    
    Base.metadata.create_all(engine)
    return engine

@pytest.fixture(scope="function")
def db_session(engine):
    """Create a new database session for a test."""
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def test_user(db_session):
    """Create a test user."""
    user = User(
        telegram_id=123456789,
        username="test_user",
        first_name="Test",
        last_name="User",
        role="user"
    )
    db_session.add(user)
    db_session.commit()
    return user 