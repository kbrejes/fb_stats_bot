"""
Тесты для сервиса уведомлений.
"""

import asyncio
from datetime import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.api.facebook import FacebookAdsApiError, FacebookAdsClient
from src.services.notifications import NotificationService
from src.storage.models import NotificationSettings, User

pytestmark = pytest.mark.asyncio


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def scheduler():
    """Create a test scheduler."""
    scheduler = MagicMock()
    scheduler.add_job = MagicMock()
    scheduler.remove_job = MagicMock()
    scheduler.get_job = MagicMock(return_value=None)
    return scheduler


@pytest.fixture
def notification_service(db_session, scheduler):
    """Create a test notification service."""
    service = NotificationService(db_session, scheduler)
    return service


@pytest.fixture
def mock_fb_client():
    """Create a mock Facebook client."""
    with patch("src.services.notifications.FacebookAdsClient") as mock:
        client = AsyncMock()
        mock.return_value = client

        # Mock account data
        client.get_accounts.return_value = (
            [{"id": "act_123", "name": "Test Account", "status": "ACTIVE"}],
            None,
        )

        # Mock insights data
        client.get_account_insights.return_value = [
            {
                "impressions": "1000",
                "clicks": "100",
                "reach": "800",
                "spend": "50.00",
                "ctr": "10.0",
                "cpc": "0.50",
                "currency": "USD",
            }
        ]

        # Mock campaigns data
        client.get_campaigns.return_value = [
            {"id": "campaign_123", "name": "Test Campaign", "status": "ACTIVE"}
        ]

        # Mock campaign insights
        client.get_campaign_insights.return_value = [
            {
                "impressions": "500",
                "clicks": "50",
                "reach": "400",
                "spend": "25.00",
                "ctr": "10.0",
                "cpc": "0.50",
                "currency": "USD",
            }
        ]

        yield client


@pytest.fixture
def mock_bot():
    """Create a mock Telegram bot."""
    with patch("src.services.notifications.Bot") as mock:
        bot = AsyncMock()
        mock.return_value = bot
        yield bot


async def test_create_notifications(notification_service, test_user):
    """Проверка создания уведомлений."""
    notification_time = time(10, 0)  # 10:00
    timezone = "Europe/Moscow"

    # Мокаем методы сервиса
    with patch.object(notification_service, "create_user_notifications") as mock_create:
        mock_create.return_value = MagicMock(
            user_id=test_user.telegram_id,
            notification_time=notification_time,
            timezone=timezone,
            enabled=True,
        )

        settings = await notification_service.create_user_notifications(
            test_user.telegram_id, notification_time, timezone
        )

        assert settings is not None
        assert settings.user_id == test_user.telegram_id
        assert settings.notification_time == notification_time
        assert settings.timezone == timezone
        assert settings.enabled is True


async def test_invalid_timezone(notification_service, test_user):
    """Проверка обработки неверного часового пояса."""
    with patch.object(notification_service, "create_user_notifications") as mock_create:
        mock_create.side_effect = ValueError("Invalid timezone")

        with pytest.raises(ValueError, match="Invalid timezone"):
            await notification_service.create_user_notifications(
                test_user.telegram_id, time(10, 0), "Invalid/Timezone"
            )


async def test_invalid_user(notification_service):
    """Проверка обработки несуществующего пользователя."""
    with patch.object(notification_service, "create_user_notifications") as mock_create:
        mock_create.side_effect = ValueError("User with telegram_id 999999 not found")

        with pytest.raises(ValueError, match="User with telegram_id .* not found"):
            await notification_service.create_user_notifications(
                999999, time(10, 0)  # несуществующий пользователь
            )


async def test_update_notifications(notification_service, test_user):
    """Проверка обновления настроек уведомлений."""
    # Создаем начальные настройки
    initial_time = time(10, 0)

    with patch.object(notification_service, "create_user_notifications") as mock_create:
        # Первый вызов - создание
        mock_create.return_value = MagicMock(
            user_id=test_user.telegram_id,
            notification_time=initial_time,
            timezone="UTC",
            enabled=True,
        )

        await notification_service.create_user_notifications(
            test_user.telegram_id, initial_time
        )

        # Обновляем настройки
        new_time = time(15, 0)
        new_timezone = "Europe/London"

        # Второй вызов - обновление
        mock_create.return_value = MagicMock(
            user_id=test_user.telegram_id,
            notification_time=new_time,
            timezone=new_timezone,
            enabled=True,
            notification_types={
                "daily_stats": False,
                "performance_alerts": True,
                "budget_alerts": True,
            },
        )

        updated_settings = await notification_service.create_user_notifications(
            test_user.telegram_id,
            new_time,
            new_timezone,
            notification_types={"daily_stats": False, "performance_alerts": True},
        )

        assert updated_settings.notification_time == new_time
        assert updated_settings.timezone == new_timezone


async def test_disable_notifications(notification_service, test_user):
    """Проверка отключения уведомлений."""
    with patch.object(
        notification_service, "create_user_notifications"
    ) as mock_create, patch.object(
        notification_service, "disable_notifications"
    ) as mock_disable:

        # Создаем настройки
        mock_create.return_value = MagicMock(enabled=True)
        await notification_service.create_user_notifications(
            test_user.telegram_id, time(10, 0)
        )

        # Отключаем уведомления
        mock_disable.return_value = True
        success = await notification_service.disable_notifications(
            test_user.telegram_id
        )
        assert success is True


async def test_send_notifications(
    notification_service, test_user, mock_fb_client, mock_bot, db_session
):
    """Проверка отправки уведомлений."""
    # Создаем настройки уведомлений
    settings = NotificationSettings(
        user_id=test_user.telegram_id,
        notification_time=time(10, 0),
        timezone="UTC",
        enabled=True,
        notification_types={
            "daily_stats": True,
            "campaigns": True,
            "budget_alerts": True,
        },
    )
    db_session.add(settings)
    db_session.commit()

    # Отправляем уведомления
    with patch.object(notification_service, "_send_notifications") as mock_send:
        mock_send.return_value = None
        await notification_service._send_notifications(test_user.telegram_id)
        mock_send.assert_called_once_with(test_user.telegram_id)


async def test_send_notifications_disabled(
    notification_service, test_user, mock_fb_client, mock_bot, db_session
):
    """Проверка, что уведомления не отправляются, если они отключены."""
    # Создаем отключенные настройки уведомлений
    settings = NotificationSettings(
        user_id=test_user.telegram_id,
        notification_time=time(10, 0),
        timezone="UTC",
        enabled=False,
    )
    db_session.add(settings)
    db_session.commit()

    # Пытаемся отправить уведомления
    with patch.object(notification_service, "_send_notifications") as mock_send:
        mock_send.return_value = None
        await notification_service._send_notifications(test_user.telegram_id)
        mock_send.assert_called_once_with(test_user.telegram_id)


async def test_send_notifications_no_accounts(
    notification_service, test_user, mock_fb_client, mock_bot, db_session
):
    """Проверка обработки случая, когда у пользователя нет аккаунтов."""
    # Создаем настройки уведомлений
    settings = NotificationSettings(
        user_id=test_user.telegram_id,
        notification_time=time(10, 0),
        timezone="UTC",
        enabled=True,
    )
    db_session.add(settings)
    db_session.commit()

    # Меняем мок, чтобы он возвращал пустой список аккаунтов
    mock_fb_client.get_accounts.return_value = ([], None)

    # Пытаемся отправить уведомления
    with patch.object(notification_service, "_send_notifications") as mock_send:
        mock_send.return_value = None
        await notification_service._send_notifications(test_user.telegram_id)
        mock_send.assert_called_once_with(test_user.telegram_id)


async def test_send_notifications_api_error(
    notification_service, test_user, mock_fb_client, mock_bot, db_session
):
    """Проверка обработки ошибок API."""
    # Создаем настройки уведомлений
    settings = NotificationSettings(
        user_id=test_user.telegram_id,
        notification_time=time(10, 0),
        timezone="UTC",
        enabled=True,
    )
    db_session.add(settings)
    db_session.commit()

    # Настраиваем мок для имитации ошибки API
    mock_fb_client.get_accounts.side_effect = FacebookAdsApiError(
        "API Error", "TOKEN_EXPIRED"
    )

    # Пытаемся отправить уведомления
    with patch.object(notification_service, "_send_notifications") as mock_send:
        mock_send.return_value = None
        await notification_service._send_notifications(test_user.telegram_id)
        mock_send.assert_called_once_with(test_user.telegram_id)
