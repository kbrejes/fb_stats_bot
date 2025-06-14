"""
Tests for analytics handlers.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram import Bot
from aiogram.types import (CallbackQuery, Chat, InlineKeyboardButton, Message,
                           User)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.bot.analytics_handlers import (handle_analysis,
                                        handle_analytics_callback,
                                        handle_comparison,
                                        handle_period_selection)
from src.services.analytics import ComparisonPeriod


# Фикстуры
@pytest.fixture
def bot():
    return Bot(token="1234567890:ABCdefGHIjklMNOpqrsTUVwxyz")


@pytest.fixture
def user():
    return User(
        id=123,
        is_bot=False,
        first_name="Test",
        last_name="User",
        username="testuser",
        language_code="ru",
    )


@pytest.fixture
def chat():
    return Chat(id=123, type="private")


@pytest.fixture
def message(chat):
    return Message(message_id=1, date=1234567890, chat=chat, text="Test message")


@pytest.fixture
def callback_query(user, message, bot):
    # Создаем мок для CallbackQuery
    callback = MagicMock()
    callback.id = "test_id"
    callback.from_user = user
    callback.chat_instance = "test_chat"
    callback.message = MagicMock()
    callback.message.edit_text = AsyncMock()
    callback.data = "test_data"
    callback.answer = AsyncMock()
    return callback


@pytest.fixture
def sample_account():
    return {
        "id": "123456789",
        "name": "Test Account",
        "currency": "USD",
        "timezone_name": "America/Los_Angeles",
    }


# Тесты для обработчиков
@pytest.mark.asyncio
async def test_handle_analytics_callback_menu(callback_query):
    callback_query.data = "analytics:menu"

    await handle_analytics_callback(callback_query)

    # Проверяем, что сообщение было отредактировано
    callback_query.message.edit_text.assert_called_once()

    # Проверяем содержимое сообщения
    call_args = callback_query.message.edit_text.call_args[0]
    assert "Выберите период для сравнения" in call_args[0]

    # Проверяем клавиатуру
    keyboard = callback_query.message.edit_text.call_args[1]["reply_markup"]
    assert isinstance(keyboard, InlineKeyboardBuilder().as_markup().__class__)


@pytest.mark.asyncio
async def test_handle_analytics_callback_invalid(callback_query):
    callback_query.data = "analytics:invalid"

    await handle_analytics_callback(callback_query)

    callback_query.answer.assert_called_once_with("⚠️ Неизвестное действие")


@pytest.mark.asyncio
async def test_handle_period_selection(callback_query, sample_account):
    callback_query.data = "period:daily"

    with patch("src.bot.analytics_handlers.get_accounts") as mock_get_accounts:
        # Мокаем get_accounts из finite_state_machine
        mock_get_accounts.return_value = [sample_account]

        await handle_period_selection(callback_query)

        # Проверяем вызов get_accounts
        mock_get_accounts.assert_called_once()

        # Проверяем сообщение
        callback_query.message.edit_text.assert_called_once()
        call_args = callback_query.message.edit_text.call_args[0]
        assert "Выберите аккаунт для анализа" in call_args[0]

        # Проверяем клавиатуру
        keyboard = callback_query.message.edit_text.call_args[1]["reply_markup"]
        assert isinstance(keyboard, InlineKeyboardBuilder().as_markup().__class__)


@pytest.mark.asyncio
async def test_handle_period_selection_no_accounts(callback_query):
    callback_query.data = "period:daily"

    with patch("src.bot.analytics_handlers.get_accounts") as mock_get_accounts:
        # Мокаем get_accounts чтобы вернуть пустой список
        mock_get_accounts.return_value = []

        await handle_period_selection(callback_query)

        # Проверяем сообщение об ошибке
        callback_query.message.edit_text.assert_called_once()
        call_args = callback_query.message.edit_text.call_args[0]
        assert "У вас нет доступных рекламных аккаунтов" in call_args[0]


@pytest.mark.asyncio
async def test_handle_comparison(callback_query, sample_account):
    callback_query.data = f"compare:daily:{sample_account['id']}"

    with patch("src.bot.analytics_handlers.get_accounts") as mock_get_accounts, patch(
        "src.bot.analytics_handlers.analytics_service"
    ) as mock_analytics:

        # Настраиваем моки
        mock_get_accounts.return_value = [sample_account]
        mock_analytics.get_comprehensive_analysis = AsyncMock(
            return_value="Test comprehensive analysis"
        )

        await handle_comparison(callback_query)

        # Проверяем вызовы
        mock_get_accounts.assert_called_once()
        mock_analytics.get_comprehensive_analysis.assert_called_once()

        # Проверяем сообщение
        callback_query.message.edit_text.assert_called_once()
        call_args = callback_query.message.edit_text.call_args[0]
        assert "Test comprehensive analysis" in call_args[0]


@pytest.mark.asyncio
async def test_handle_analysis(callback_query, sample_account):
    callback_query.data = f"analyze:daily:{sample_account['id']}"

    with patch("src.bot.analytics_handlers.get_accounts") as mock_get_accounts, patch(
        "src.bot.analytics_handlers.analytics_service"
    ) as mock_analytics:

        # Настраиваем моки
        mock_get_accounts.return_value = [sample_account]

        # Мокаем непустые данные для insights, чтобы пройти проверку активности
        sample_insights = [{"spend": "100.00", "impressions": "1000"}]
        mock_analytics.get_comparative_insights = AsyncMock(
            return_value=(sample_insights, sample_insights)
        )
        mock_analytics.analyze_insights = AsyncMock(return_value="Test analysis")

        await handle_analysis(callback_query)

        # Проверяем вызовы
        mock_analytics.get_comparative_insights.assert_called_once()
        mock_analytics.analyze_insights.assert_called_once()

        # Проверяем сообщение
        assert callback_query.message.edit_text.call_count == 2  # Загрузка + результат
        assert "Test analysis" in callback_query.message.edit_text.call_args[0][0]
