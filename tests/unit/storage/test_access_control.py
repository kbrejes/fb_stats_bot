"""
Тесты для моделей контроля доступа.
"""
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from src.storage.models import AccessControl, AccessRequest, User
from src.storage.enums import UserRole


class TestAccessControl(unittest.TestCase):
    """Тесты для модели AccessControl."""
    
    def setUp(self):
        """Подготовка к тестам."""
        self.user = User(telegram_id=123456, role=UserRole.PARTNER.value)
        self.access_control = AccessControl(
            telegram_id=self.user.telegram_id,
            resource_type="campaign",
            resource_id="123456789",
            is_active=True
        )
    
    def test_is_valid_active_no_expiration(self):
        """Тест проверки действительности разрешения без срока действия."""
        self.assertTrue(self.access_control.is_valid())
    
    def test_is_valid_active_with_future_expiration(self):
        """Тест проверки действительности разрешения с будущим сроком действия."""
        self.access_control.expires_at = datetime.now() + timedelta(days=1)
        self.assertTrue(self.access_control.is_valid())
    
    def test_is_valid_active_with_past_expiration(self):
        """Тест проверки действительности разрешения с истекшим сроком действия."""
        self.access_control.expires_at = datetime.now() - timedelta(days=1)
        self.assertFalse(self.access_control.is_valid())
    
    def test_is_valid_inactive(self):
        """Тест проверки недействительности неактивного разрешения."""
        self.access_control.is_active = False
        self.assertFalse(self.access_control.is_valid())
    
    def test_get_params_empty(self):
        """Тест получения пустых параметров."""
        self.assertEqual(self.access_control.get_params(), {})
    
    def test_set_get_params(self):
        """Тест установки и получения параметров."""
        params = {"limit": 10, "view_only": True}
        self.access_control.set_params(params)
        self.assertEqual(self.access_control.get_params(), params)
    
    def test_extend_expiration_from_none(self):
        """Тест продления срока действия, когда срок не был установлен."""
        self.access_control.expires_at = None
        
        # Запоминаем текущее время до вызова метода
        before = datetime.now()
        self.access_control.extend_expiration(days=10)
        after = datetime.now()
        
        # Проверяем, что новая дата находится в ожидаемом диапазоне
        expected_min = before + timedelta(days=10)
        expected_max = after + timedelta(days=10)
        self.assertTrue(expected_min <= self.access_control.expires_at <= expected_max)
    
    def test_extend_expiration_from_existing(self):
        """Тест продления срока действия, когда срок уже был установлен."""
        now = datetime.now()
        initial_expiration = now + timedelta(days=5)
        self.access_control.expires_at = initial_expiration
        self.access_control.extend_expiration(days=10)
        
        expected = initial_expiration + timedelta(days=10)
        self.assertEqual(self.access_control.expires_at, expected)
    
    def test_deactivate(self):
        """Тест деактивации разрешения."""
        self.access_control.deactivate()
        self.assertFalse(self.access_control.is_active)
    
    def test_reactivate(self):
        """Тест активации разрешения."""
        self.access_control.is_active = False
        self.access_control.reactivate()
        self.assertTrue(self.access_control.is_active)
    
    def test_reactivate_with_expired(self):
        """Тест активации разрешения с истекшим сроком действия."""
        self.access_control.is_active = False
        self.access_control.expires_at = datetime.now() - timedelta(days=1)
        
        # Запоминаем текущее время до вызова метода
        before = datetime.now()
        self.access_control.reactivate()
        after = datetime.now()
        
        self.assertTrue(self.access_control.is_active)
        
        # Проверяем, что новая дата находится в ожидаемом диапазоне
        expected_min = before + timedelta(days=30)
        expected_max = after + timedelta(days=30)
        self.assertTrue(expected_min <= self.access_control.expires_at <= expected_max)


class TestAccessRequest(unittest.TestCase):
    """Тесты для модели AccessRequest."""
    
    def setUp(self):
        """Подготовка к тестам."""
        self.user = User(telegram_id=123456, role=UserRole.PARTNER.value)
        self.admin = User(telegram_id=654321, role=UserRole.ADMIN.value)
        self.access_request = AccessRequest(
            telegram_id=self.user.telegram_id,
            resource_type="campaign",
            resource_id="123456789",
            message="Нужен доступ к кампании",
            requested_duration=15,
            status="pending"  # Явно устанавливаем начальный статус
        )
    
    def test_initial_status(self):
        """Тест начального статуса запроса."""
        self.assertEqual(self.access_request.status, "pending")
        self.assertTrue(self.access_request.is_pending())
        self.assertFalse(self.access_request.is_approved())
        self.assertFalse(self.access_request.is_rejected())
    
    def test_approve(self):
        """Тест одобрения запроса."""
        before = datetime.now()
        self.access_request.approve(admin_id=self.admin.telegram_id, admin_notes="Одобрено")
        after = datetime.now()
        
        self.assertEqual(self.access_request.status, "approved")
        self.assertTrue(before <= self.access_request.processed_at <= after)
        self.assertEqual(self.access_request.processed_by, self.admin.telegram_id)
        self.assertEqual(self.access_request.admin_notes, "Одобрено")
        self.assertTrue(self.access_request.is_approved())
    
    def test_reject(self):
        """Тест отклонения запроса."""
        before = datetime.now()
        self.access_request.reject(admin_id=self.admin.telegram_id, admin_notes="Отклонено")
        after = datetime.now()
        
        self.assertEqual(self.access_request.status, "rejected")
        self.assertTrue(before <= self.access_request.processed_at <= after)
        self.assertEqual(self.access_request.processed_by, self.admin.telegram_id)
        self.assertEqual(self.access_request.admin_notes, "Отклонено")
        self.assertTrue(self.access_request.is_rejected())
    
    def test_reset_status(self):
        """Тест сброса статуса запроса."""
        self.access_request.status = "approved"
        self.access_request.processed_at = datetime.now()
        self.access_request.processed_by = self.admin.telegram_id
        self.access_request.admin_notes = "Одобрено"
        
        self.access_request.reset_status()
        
        self.assertEqual(self.access_request.status, "pending")
        self.assertIsNone(self.access_request.processed_at)
        self.assertIsNone(self.access_request.processed_by)
        self.assertEqual(self.access_request.admin_notes, "Одобрено")  # заметки остаются
        self.assertTrue(self.access_request.is_pending()) 