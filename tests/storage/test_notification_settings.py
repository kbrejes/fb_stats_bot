"""
Тесты для модели NotificationSettings.
"""

from datetime import datetime, time

import pytest
from sqlalchemy.exc import IntegrityError

from src.storage.models import NotificationSettings


def test_create_notification_settings(db_session, test_user):
    """Проверка создания записи настроек уведомлений."""
    settings = NotificationSettings(
        user_id=test_user.telegram_id,
        notification_time=time(10, 0),  # 10:00
        timezone="Europe/Moscow",
    )
    db_session.add(settings)
    db_session.commit()

    # Проверяем, что запись создана
    saved_settings = db_session.query(NotificationSettings).first()
    assert saved_settings is not None
    assert saved_settings.user_id == test_user.telegram_id
    assert saved_settings.notification_time == time(10, 0)
    assert saved_settings.timezone == "Europe/Moscow"
    assert saved_settings.enabled is True  # значение по умолчанию
    assert saved_settings.notification_types == {
        "daily_stats": True,
        "performance_alerts": True,
        "budget_alerts": True,
    }


def test_user_relationship(db_session, test_user):
    """Проверка связи с моделью User."""
    settings = NotificationSettings(
        user_id=test_user.telegram_id, notification_time=time(10, 0), timezone="UTC"
    )
    db_session.add(settings)
    db_session.commit()

    # Проверяем связь от NotificationSettings к User
    assert settings.user == test_user
    # Проверяем связь от User к NotificationSettings
    assert test_user.notification_settings == settings


def test_default_values(db_session, test_user):
    """Проверка значений по умолчанию."""
    settings = NotificationSettings(
        user_id=test_user.telegram_id, notification_time=time(9, 0)
    )
    db_session.add(settings)
    db_session.commit()

    assert settings.enabled is True
    assert settings.timezone == "UTC"
    assert settings.notification_types == {
        "daily_stats": True,
        "performance_alerts": True,
        "budget_alerts": True,
    }
    assert settings.created_at is not None
    assert settings.updated_at is not None


def test_invalid_user_id(db_session):
    """Проверка на невозможность создания настроек для несуществующего пользователя."""
    settings = NotificationSettings(
        user_id=999999,  # несуществующий пользователь
        notification_time=time(10, 0),
        timezone="UTC",
    )
    db_session.add(settings)

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_cascade_delete(db_session, test_user):
    """Проверка удаления настроек при удалении пользователя."""
    settings = NotificationSettings(
        user_id=test_user.telegram_id, notification_time=time(10, 0), timezone="UTC"
    )
    db_session.add(settings)
    db_session.commit()

    # Удаляем пользователя
    db_session.delete(test_user)
    db_session.commit()

    # Проверяем, что настройки тоже удалены
    assert db_session.query(NotificationSettings).count() == 0


def test_update_settings(db_session, test_user):
    """Проверка обновления настроек."""
    settings = NotificationSettings(
        user_id=test_user.telegram_id, notification_time=time(10, 0), timezone="UTC"
    )
    db_session.add(settings)
    db_session.commit()

    # Запоминаем время создания
    created_at = settings.created_at

    # Обновляем настройки
    settings.notification_time = time(11, 0)
    settings.timezone = "Europe/London"
    settings.enabled = False
    settings.notification_types = {
        "daily_stats": False,
        "performance_alerts": True,
        "budget_alerts": True,
    }
    db_session.commit()

    # Перезагружаем из базы
    db_session.refresh(settings)

    assert settings.notification_time == time(11, 0)
    assert settings.timezone == "Europe/London"
    assert settings.enabled is False
    assert settings.notification_types == {
        "daily_stats": False,
        "performance_alerts": True,
        "budget_alerts": True,
    }
    assert settings.created_at == created_at
    assert settings.updated_at > created_at
