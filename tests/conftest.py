"""
Pytest configuration and fixtures for tests.
"""

import asyncio
import os
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Set test environment
os.environ["ENVIRONMENT"] = "test"
os.environ["DB_CONNECTION_STRING"] = "sqlite:///test.db"


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_bot():
    """Mock Telegram bot."""
    bot = AsyncMock()
    bot.send_message = AsyncMock()
    bot.edit_message_text = AsyncMock()
    bot.answer_callback_query = AsyncMock()
    return bot


@pytest.fixture
def mock_session():
    """Mock database session."""
    session = MagicMock()
    session.query.return_value = session
    session.filter.return_value = session
    session.filter_by.return_value = session
    session.first.return_value = None
    session.all.return_value = []
    session.add = MagicMock()
    session.commit = MagicMock()
    session.close = MagicMock()
    return session


@pytest.fixture
def db_session():
    """Create a test database session."""
    # Create in-memory SQLite database for tests
    engine = create_engine("sqlite:///:memory:")
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Mock the session to avoid actual database operations
    session = MagicMock()
    session.query.return_value = session
    session.filter.return_value = session
    session.filter_by.return_value = session
    session.first.return_value = None
    session.all.return_value = []
    session.add = MagicMock()
    session.commit = MagicMock()
    session.close = MagicMock()
    
    yield session
    session.close()


@pytest.fixture
def test_user():
    """Create a test user."""
    user = MagicMock()
    user.telegram_id = 123456789
    user.username = "testuser"
    user.first_name = "Test"
    user.last_name = "User"
    user.fb_access_token = "test_token"
    return user


@pytest.fixture
def scheduler():
    """Create a mock scheduler."""
    scheduler = MagicMock()
    scheduler.add_job = MagicMock()
    scheduler.remove_job = MagicMock()
    scheduler.get_job = MagicMock(return_value=None)
    return scheduler


@pytest.fixture
def mock_openai():
    """Mock OpenAI client."""
    mock = AsyncMock()
    mock.chat.completions.create = AsyncMock()
    mock.chat.completions.create.return_value.choices = [
        MagicMock(message=MagicMock(content="Test response"))
    ]
    return mock


@pytest.fixture
def mock_facebook_api():
    """Mock Facebook Marketing API."""
    mock = MagicMock()
    mock.get_accounts.return_value = []
    mock.get_campaigns.return_value = []
    mock.get_ads.return_value = []
    return mock


@pytest.fixture
def mock_fb_client():
    """Mock Facebook Ads Client."""
    client = AsyncMock()
    client.get_accounts.return_value = ([
        {
            "id": "act_123",
            "name": "Test Account",
            "currency": "USD",
            "timezone_name": "UTC"
        }
    ], None)
    client.get_account_insights.return_value = [
        {
            "account_id": "123456789",
            "spend": "100.00",
            "impressions": "1000",
            "clicks": "50",
            "date_start": "2024-02-01",
            "date_stop": "2024-02-07"
        }
    ]
    client.get_campaigns.return_value = [
        {
            "id": "campaign_123",
            "name": "Test Campaign",
            "status": "ACTIVE"
        }
    ]
    client.get_campaign_insights.return_value = [
        {
            "campaign_id": "campaign_123",
            "spend": "50.00",
            "impressions": "500",
            "clicks": "25"
        }
    ]
    return client


@pytest.fixture(autouse=True)
def setup_test_env():
    """Setup test environment."""
    # Set test environment variables
    test_env = {
        "ENVIRONMENT": "test",
        "TELEGRAM_TOKEN": "test_token",
        "OPENAI_API_KEY": "test_openai_key",
        "FB_APP_ID": "test_fb_app_id",
        "FB_APP_SECRET": "test_fb_secret",
        "DB_CONNECTION_STRING": "sqlite:///test.db",
        "LOG_LEVEL": "DEBUG",
    }

    original_env = {}
    for key, value in test_env.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value

    yield

    # Restore original environment
    for key, value in original_env.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value
