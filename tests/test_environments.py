"""
Tests for different environments configuration.
"""

import logging
import os
from unittest.mock import AsyncMock, patch

import openai
import pytest

from config.settings import ENVIRONMENT, OPENAI_API_KEY
from src.services.analytics import AnalyticsService, ComparisonPeriod


@pytest.fixture
def mock_env_vars():
    """Базовые переменные окружения для тестов."""
    return {
        "OPENAI_API_KEY": "test_openai_key",
        "TELEGRAM_TOKEN": "test_telegram_token",
        "FB_APP_ID": "test_fb_app_id",
        "FB_APP_SECRET": "test_fb_secret",
        "FB_REDIRECT_URI": "http://localhost:8000/callback",
        "ENCRYPTION_KEY": "test_encryption_key",
        "DEBUG": "false",
        "LOG_LEVEL": "INFO",
    }


@pytest.fixture
def sample_insights():
    return [
        {
            "account_id": "123456789",
            "spend": "100.00",
            "impressions": "1000",
            "clicks": "50",
            "conversions": [{"action_type": "purchase", "value": "10"}],
            "date_start": "2024-02-01",
            "date_stop": "2024-02-07",
            "cpc": "2.00",
            "ctr": "5.00",
            "conversion_rate": "20.00",
            "reach": "800",
            "frequency": "1.25",
            "cost_per_conversion": "10.00",
            "actions": [
                {"action_type": "link_click", "value": "50"},
                {"action_type": "purchase", "value": "10"},
                {"action_type": "add_to_cart", "value": "20"},
            ],
        }
    ]


@pytest.mark.parametrize("environment", ["development", "production"])
def test_environment_settings(environment, mock_env_vars):
    """Проверка загрузки настроек для разных окружений."""
    env_vars = mock_env_vars.copy()
    env_vars["ENVIRONMENT"] = environment

    with patch.dict(os.environ, env_vars, clear=True):
        # Перезагружаем модуль настроек
        import importlib

        import config.settings

        importlib.reload(config.settings)

        # Проверяем базовые настройки
        assert config.settings.ENVIRONMENT == environment
        assert config.settings.OPENAI_API_KEY == "test_openai_key"
        assert config.settings.BOT_TOKEN == "test_telegram_token"
        assert config.settings.FB_APP_ID == "test_fb_app_id"
        assert config.settings.FB_APP_SECRET == "test_fb_secret"


@pytest.mark.parametrize("environment", ["development", "production"])
def test_analytics_service_initialization(environment, mock_env_vars):
    """Проверка инициализации сервиса аналитики в разных окружениях."""
    env_vars = mock_env_vars.copy()
    env_vars["ENVIRONMENT"] = environment

    with patch.dict(os.environ, env_vars, clear=True), patch(
        "openai.OpenAI"
    ) as mock_openai:

        service = AnalyticsService("test_openai_key")
        assert service.openai_client is not None
        mock_openai.assert_called_once_with(api_key="test_openai_key")


@pytest.mark.asyncio
@pytest.mark.parametrize("environment", ["development", "production"])
async def test_analytics_service_functionality(
    environment, mock_env_vars, sample_insights
):
    """Проверка функциональности сервиса аналитики в разных окружениях."""
    env_vars = mock_env_vars.copy()
    env_vars["ENVIRONMENT"] = environment

    with patch.dict(os.environ, env_vars, clear=True), patch(
        "openai.OpenAI"
    ) as mock_openai, patch(
        "src.services.analytics.FacebookAdsClient"
    ) as mock_fb_client:

        # Настраиваем моки
        mock_completion = AsyncMock()
        mock_completion.choices = [AsyncMock()]
        mock_completion.choices[0].message.content = "Test analysis"

        mock_openai.return_value.chat.completions.create = AsyncMock(
            return_value=mock_completion
        )

        mock_fb_instance = AsyncMock()
        mock_fb_instance.get_account_insights.return_value = sample_insights
        mock_fb_client.return_value.__aenter__.return_value = mock_fb_instance

        # Создаем сервис и тестируем
        service = AnalyticsService("test_openai_key")

        # Тестируем получение данных
        current, previous = await service.get_comparative_insights(
            user_id=123, account_id="123456789", period=ComparisonPeriod.DAILY
        )

        assert current == previous == sample_insights
        assert mock_fb_instance.get_account_insights.call_count == 2

        # Тестируем анализ
        analysis = await service.analyze_insights(
            current_insights=current,
            previous_insights=previous,
            account_name="Test Account",
        )

        assert analysis == "Test analysis"
        assert mock_openai.return_value.chat.completions.create.called


@pytest.mark.parametrize(
    "environment,expected_level",
    [("development", logging.DEBUG), ("production", logging.INFO)],
)
def test_environment_specific_settings(environment, expected_level, mock_env_vars):
    """Проверка специфичных для окружения настроек."""
    env_vars = mock_env_vars.copy()
    env_vars["ENVIRONMENT"] = environment

    if environment == "development":
        env_vars["DEBUG"] = "true"
        env_vars["LOG_LEVEL"] = "DEBUG"
    else:
        env_vars["DEBUG"] = "false"
        env_vars["LOG_LEVEL"] = "INFO"

    with patch.dict(os.environ, env_vars, clear=True):
        import importlib

        import config.settings

        importlib.reload(config.settings)

        if environment == "development":
            # Проверяем настройки для разработки
            assert config.settings.DEBUG is True
            assert config.settings.LOG_LEVEL == expected_level
        else:
            # Проверяем настройки для продакшена
            assert config.settings.DEBUG is False
            assert config.settings.LOG_LEVEL == expected_level


@pytest.mark.parametrize("environment", ["development", "production"])
def test_database_configuration(environment, mock_env_vars):
    """Проверка конфигурации базы данных для разных окружений."""
    env_vars = mock_env_vars.copy()
    env_vars["ENVIRONMENT"] = environment

    if environment == "development":
        env_vars["DB_CONNECTION_STRING"] = "sqlite:///database_dev.sqlite"
    else:
        env_vars["DB_CONNECTION_STRING"] = "postgresql://user:pass@localhost/db"

    with patch.dict(os.environ, env_vars, clear=True):
        import importlib

        import config.settings

        importlib.reload(config.settings)

        assert config.settings.DB_CONNECTION_STRING is not None
        if environment == "development":
            assert "sqlite" in config.settings.DB_CONNECTION_STRING
        else:
            assert "postgresql" in config.settings.DB_CONNECTION_STRING
