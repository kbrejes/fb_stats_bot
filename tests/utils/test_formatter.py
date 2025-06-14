"""
Tests for message formatter utilities.
"""

import pytest
from unittest.mock import MagicMock, patch

from src.utils.message_formatter import format_insights


@pytest.fixture
def sample_insights():
    """Sample insights data for testing."""
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


def test_format_insights_basic(sample_insights):
    """Test basic formatting of insights data."""
    result = format_insights(sample_insights, "account", "yesterday")
    
    # Проверяем что результат не пустой
    assert result is not None
    assert len(result) > 0
    
    # Проверяем что в результате есть основные метрики (форматированные)
    assert "1,000" in result  # impressions (с запятой)
    assert "100.00" in result  # spend
    assert "50" in result      # clicks


def test_format_insights_empty_data():
    """Test formatting with empty insights data."""
    result = format_insights([], "account", "yesterday")
    
    # Для пустых данных возвращается сообщение об отсутствии данных
    assert result is not None
    assert "❌ Статистика не найдена" in result


def test_format_insights_different_object_types(sample_insights):
    """Test formatting for different object types."""
    object_types = ["account", "campaign", "adset", "ad"]
    
    for obj_type in object_types:
        result = format_insights(sample_insights, obj_type, "yesterday")
        assert result is not None
        assert len(result) > 0
