"""
Tests for analytics service.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

from src.services.analytics import AnalyticsService, ComparisonPeriod, PeriodDates
from src.data.processor import DataProcessor

# Фикстуры
@pytest.fixture
def mock_openai():
    with patch('openai.OpenAI') as mock:
        mock.return_value.chat.completions.create = AsyncMock()
        yield mock

@pytest.fixture
def analytics_service(mock_openai):
    return AnalyticsService("test_api_key")

@pytest.fixture
def sample_insights():
    return [{
        'account_id': '123456789',
        'spend': '100.00',
        'impressions': '1000',
        'clicks': '50',
        'conversions': [{
            'action_type': 'purchase',
            'value': '10'
        }],
        'date_start': '2024-02-01',
        'date_stop': '2024-02-07',
        'cpc': '2.00',
        'ctr': '5.00',
        'conversion_rate': '20.00',
        'reach': '800',
        'frequency': '1.25',
        'cost_per_conversion': '10.00',
        'actions': [
            {
                'action_type': 'link_click',
                'value': '50'
            },
            {
                'action_type': 'purchase',
                'value': '10'
            },
            {
                'action_type': 'add_to_cart',
                'value': '20'
            }
        ]
    }]

# Тесты для периодов
@pytest.mark.parametrize("period,expected_days", [
    (ComparisonPeriod.DAILY, 1),
    (ComparisonPeriod.WEEKLY, 7),
    (ComparisonPeriod.PREV_WEEKLY, 7),
    (ComparisonPeriod.BIWEEKLY_VS_MONTHLY, 14)
])
def test_get_period_dates(analytics_service, period, expected_days):
    dates = analytics_service._get_period_dates(period)
    
    assert isinstance(dates, PeriodDates)
    assert isinstance(dates.current_start, datetime)
    assert isinstance(dates.current_end, datetime)
    assert isinstance(dates.previous_start, datetime)
    assert isinstance(dates.previous_end, datetime)
    
    # Проверяем корректность периодов
    if period == ComparisonPeriod.DAILY:
        assert (dates.current_end - dates.current_start).days == 1
        assert (dates.previous_end - dates.previous_start).days == 1
    elif period == ComparisonPeriod.WEEKLY:
        assert dates.current_start.weekday() == 0  # Понедельник
        assert (dates.current_end - dates.current_start).days <= 7
    elif period == ComparisonPeriod.PREV_WEEKLY:
        assert dates.current_start.weekday() == 0
        assert (dates.current_end - dates.current_start).days == 7
    elif period == ComparisonPeriod.BIWEEKLY_VS_MONTHLY:
        assert (dates.current_end - dates.current_start).days == 14
        assert (dates.previous_end - dates.previous_start).days == 30

def test_get_period_dates_invalid(analytics_service):
    with pytest.raises(ValueError, match="Неподдерживаемый период сравнения"):
        analytics_service._get_period_dates("invalid_period")

# Тесты для получения статистики
@pytest.mark.asyncio
async def test_get_comparative_insights(analytics_service, sample_insights):
    with patch('src.services.analytics.FacebookAdsClient') as mock_fb_client:
        mock_instance = AsyncMock()
        mock_instance.get_account_insights.return_value = sample_insights
        mock_fb_client.return_value.__aenter__.return_value = mock_instance
        
        current, previous = await analytics_service.get_comparative_insights(
            user_id=123,
            account_id="123456789",
            period=ComparisonPeriod.DAILY
        )
        
        assert current == sample_insights
        assert previous == sample_insights
        assert mock_instance.get_account_insights.call_count == 2

@pytest.mark.asyncio
async def test_get_comparative_insights_empty(analytics_service):
    with patch('src.services.analytics.FacebookAdsClient') as mock_fb_client:
        mock_instance = AsyncMock()
        mock_instance.get_account_insights.return_value = []
        mock_fb_client.return_value.__aenter__.return_value = mock_instance
        
        current, previous = await analytics_service.get_comparative_insights(
            user_id=123,
            account_id="123456789",
            period=ComparisonPeriod.DAILY
        )
        
        assert current == []
        assert previous == []

# Тесты для анализа через OpenAI
@pytest.mark.asyncio
async def test_analyze_insights_success(analytics_service, sample_insights):
    expected_analysis = "Test analysis response"
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = expected_analysis
    
    analytics_service.openai_client.chat.completions.create = AsyncMock(
        return_value=mock_response
    )
    
    with patch('src.data.processor.DataProcessor.format_insights') as mock_format:
        mock_format.return_value = "Test formatted insights"
        
        analysis = await analytics_service.analyze_insights(
            sample_insights,
            sample_insights,
            "Test Account"
        )
        
        assert analysis == expected_analysis
        assert analytics_service.openai_client.chat.completions.create.called

@pytest.mark.asyncio
async def test_analyze_insights_no_data(analytics_service):
    analysis = await analytics_service.analyze_insights(
        [],
        [],
        "Test Account"
    )
    
    assert analysis == "Недостаточно данных для анализа"
    assert not analytics_service.openai_client.chat.completions.create.called

@pytest.mark.asyncio
async def test_analyze_insights_api_error(analytics_service, sample_insights):
    analytics_service.openai_client.chat.completions.create = AsyncMock(
        side_effect=Exception("API Error")
    )
    
    with patch('src.data.processor.DataProcessor.format_insights') as mock_format:
        mock_format.return_value = "Test formatted insights"
        
        analysis = await analytics_service.analyze_insights(
            sample_insights,
            sample_insights,
            "Test Account"
        )
        
        assert analysis == "Не удалось получить рекомендации. Пожалуйста, попробуйте позже." 