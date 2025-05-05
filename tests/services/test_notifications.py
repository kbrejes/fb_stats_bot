"""
Тесты для сервиса уведомлений.
"""
import pytest
import asyncio
from datetime import time
import pytz
from unittest.mock import MagicMock, patch, AsyncMock
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.services.notifications import NotificationService
from src.storage.models import NotificationSettings, User
from src.api.facebook import FacebookAdsClient, FacebookAdsApiError

pytestmark = pytest.mark.asyncio

@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def scheduler(event_loop):
    """Create a test scheduler."""
    scheduler = AsyncIOScheduler()
    scheduler.start()
    yield scheduler
    scheduler.shutdown()

@pytest.fixture
async def notification_service(db_session, scheduler):
    """Create a test notification service."""
    service = NotificationService(db_session, scheduler)
    return service

@pytest.fixture
def mock_fb_client():
    """Create a mock Facebook client."""
    with patch('src.services.notifications.FacebookAdsClient') as mock:
        client = AsyncMock()
        mock.return_value = client
        
        # Mock account data
        client.get_accounts.return_value = (
            [
                {
                    'id': 'act_123',
                    'name': 'Test Account',
                    'status': 'ACTIVE'
                }
            ],
            None
        )
        
        # Mock insights data
        client.get_account_insights.return_value = [
            {
                'impressions': '1000',
                'clicks': '100',
                'reach': '800',
                'spend': '50.00',
                'ctr': '10.0',
                'cpc': '0.50',
                'currency': 'USD'
            }
        ]
        
        # Mock campaigns data
        client.get_campaigns.return_value = [
            {
                'id': 'campaign_123',
                'name': 'Test Campaign',
                'status': 'ACTIVE'
            }
        ]
        
        # Mock campaign insights
        client.get_campaign_insights.return_value = [
            {
                'impressions': '500',
                'clicks': '50',
                'reach': '400',
                'spend': '25.00',
                'ctr': '10.0',
                'cpc': '0.50',
                'currency': 'USD'
            }
        ]
        
        yield client

@pytest.fixture
def mock_bot():
    """Create a mock Telegram bot."""
    with patch('src.services.notifications.Bot') as mock:
        bot = AsyncMock()
        mock.return_value = bot
        yield bot

async def test_create_notifications(notification_service, test_user):
    """Проверка создания уведомлений."""
    notification_time = time(10, 0)  # 10:00
    timezone = "Europe/Moscow"
    
    settings = await notification_service.create_user_notifications(
        test_user.telegram_id,
        notification_time,
        timezone
    )
    
    assert settings is not None
    assert settings.user_id == test_user.telegram_id
    assert settings.notification_time == notification_time
    assert settings.timezone == timezone
    assert settings.enabled is True
    
    # Проверяем, что задача создана в планировщике
    job_id = f"notifications_{test_user.telegram_id}"
    job = notification_service.scheduler.get_job(job_id)
    assert job is not None
    assert job.trigger.timezone == pytz.timezone(timezone)

async def test_invalid_timezone(notification_service, test_user):
    """Проверка обработки неверного часового пояса."""
    with pytest.raises(ValueError, match="Invalid timezone"):
        await notification_service.create_user_notifications(
            test_user.telegram_id,
            time(10, 0),
            "Invalid/Timezone"
        )

async def test_invalid_user(notification_service):
    """Проверка обработки несуществующего пользователя."""
    with pytest.raises(ValueError, match="User with telegram_id .* not found"):
        await notification_service.create_user_notifications(
            999999,  # несуществующий пользователь
            time(10, 0)
        )

async def test_update_notifications(notification_service, test_user):
    """Проверка обновления настроек уведомлений."""
    # Создаем начальные настройки
    initial_time = time(10, 0)
    await notification_service.create_user_notifications(
        test_user.telegram_id,
        initial_time
    )
    
    # Обновляем настройки
    new_time = time(15, 0)
    new_timezone = "Europe/London"
    updated_settings = await notification_service.create_user_notifications(
        test_user.telegram_id,
        new_time,
        new_timezone,
        notification_types={'daily_stats': False, 'performance_alerts': True}
    )
    
    assert updated_settings.notification_time == new_time
    assert updated_settings.timezone == new_timezone
    assert updated_settings.notification_types == {
        'daily_stats': False,
        'performance_alerts': True,
        'budget_alerts': True  # Не изменилось
    }

async def test_disable_notifications(notification_service, test_user):
    """Проверка отключения уведомлений."""
    # Создаем настройки
    await notification_service.create_user_notifications(
        test_user.telegram_id,
        time(10, 0)
    )
    
    # Отключаем уведомления
    success = await notification_service.disable_notifications(test_user.telegram_id)
    assert success is True
    
    # Проверяем, что настройки обновились
    settings = notification_service.session.query(NotificationSettings).filter_by(
        user_id=test_user.telegram_id
    ).first()
    assert settings is not None
    assert settings.enabled is False
    
    # Проверяем, что задача удалена из планировщика
    job_id = f"notifications_{test_user.telegram_id}"
    assert notification_service.scheduler.get_job(job_id) is None

async def test_send_notifications(notification_service, test_user, mock_fb_client, mock_bot, db_session):
    """Проверка отправки уведомлений."""
    # Создаем настройки уведомлений
    settings = NotificationSettings(
        user_id=test_user.telegram_id,
        notification_time=time(10, 0),
        timezone="UTC",
        enabled=True,
        notification_types={
            'daily_stats': True,
            'campaigns': True,
            'budget_alerts': True
        }
    )
    db_session.add(settings)
    db_session.commit()
    
    # Отправляем уведомления
    await notification_service._send_notifications(test_user.telegram_id)
    
    # Проверяем, что были вызваны нужные методы Facebook API
    mock_fb_client.get_accounts.assert_called_once()
    mock_fb_client.get_account_insights.assert_called_once_with('act_123', 'last_7d')
    mock_fb_client.get_campaigns.assert_called_once_with('act_123')
    mock_fb_client.get_campaign_insights.assert_called_once_with('campaign_123', 'last_7d')
    
    # Проверяем, что сообщение было отправлено
    mock_bot.send_message.assert_called()
    
    # Проверяем содержимое сообщения
    call_args = mock_bot.send_message.call_args_list[0]
    assert call_args[0][0] == test_user.telegram_id  # ID пользователя
    message_text = call_args[0][1]  # Текст сообщения
    
    # Проверяем основные компоненты сообщения
    assert "Test Account" in message_text
    assert "За последние 7 дней" in message_text
    assert "Test Campaign" in message_text

async def test_send_notifications_disabled(notification_service, test_user, mock_fb_client, mock_bot, db_session):
    """Проверка, что уведомления не отправляются, если они отключены."""
    # Создаем отключенные настройки уведомлений
    settings = NotificationSettings(
        user_id=test_user.telegram_id,
        notification_time=time(10, 0),
        timezone="UTC",
        enabled=False
    )
    db_session.add(settings)
    db_session.commit()
    
    # Пытаемся отправить уведомления
    await notification_service._send_notifications(test_user.telegram_id)
    
    # Проверяем, что API не вызывался
    mock_fb_client.get_accounts.assert_not_called()
    mock_fb_client.get_account_insights.assert_not_called()
    
    # Проверяем, что сообщение не отправлялось
    mock_bot.send_message.assert_not_called()

async def test_send_notifications_no_accounts(notification_service, test_user, mock_fb_client, mock_bot, db_session):
    """Проверка обработки случая, когда у пользователя нет аккаунтов."""
    # Создаем настройки уведомлений
    settings = NotificationSettings(
        user_id=test_user.telegram_id,
        notification_time=time(10, 0),
        timezone="UTC",
        enabled=True
    )
    db_session.add(settings)
    db_session.commit()
    
    # Меняем мок, чтобы он возвращал пустой список аккаунтов
    mock_fb_client.get_accounts.return_value = ([], None)
    
    # Пытаемся отправить уведомления
    await notification_service._send_notifications(test_user.telegram_id)
    
    # Проверяем, что API вызывался только для получения аккаунтов
    mock_fb_client.get_accounts.assert_called_once()
    mock_fb_client.get_account_insights.assert_not_called()
    mock_fb_client.get_campaigns.assert_not_called()
    
    # Проверяем, что сообщение не отправлялось
    mock_bot.send_message.assert_not_called()

async def test_send_notifications_api_error(notification_service, test_user, mock_fb_client, mock_bot, db_session):
    """Проверка обработки ошибок API."""
    # Создаем настройки уведомлений
    settings = NotificationSettings(
        user_id=test_user.telegram_id,
        notification_time=time(10, 0),
        timezone="UTC",
        enabled=True
    )
    db_session.add(settings)
    db_session.commit()
    
    # Настраиваем мок для имитации ошибки API
    mock_fb_client.get_accounts.side_effect = FacebookAdsApiError("API Error", "TOKEN_EXPIRED")
    
    # Пытаемся отправить уведомления
    await notification_service._send_notifications(test_user.telegram_id)
    
    # Проверяем, что было отправлено сообщение об ошибке
    mock_bot.send_message.assert_called_once()
    call_args = mock_bot.send_message.call_args
    assert call_args[0][0] == test_user.telegram_id
    assert "❌" in call_args[0][1]
    assert "API Error" in call_args[0][1] 