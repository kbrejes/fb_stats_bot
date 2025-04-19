"""
Тесты для репозитория AccessControlRepository.
"""
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from sqlalchemy.orm import Session

from src.repositories.access_control_repository import AccessControlRepository
from src.storage.models import AccessControl, User
from src.storage.enums import UserRole


class TestAccessControlRepository(unittest.TestCase):
    """Тесты для репозитория AccessControlRepository."""
    
    def setUp(self):
        """Подготовка к тестам."""
        # Создаем моки
        self.session_mock = MagicMock(spec=Session)
        self.user = User(telegram_id=123456, role=UserRole.PARTNER.value)
        self.admin = User(telegram_id=654321, role=UserRole.ADMIN.value)
        self.targetologist = User(telegram_id=789012, role=UserRole.TARGETOLOGIST.value)
        
        # Создаем репозиторий с моком сессии
        self.repo = AccessControlRepository(session=self.session_mock)
        
        # Создаем объект разрешения для тестов
        self.access_control = AccessControl(
            id=1,
            telegram_id=self.user.telegram_id,
            resource_type="campaign",
            resource_id="123456789",
            is_active=True
        )
    
    def test_get_partner_permissions_active(self):
        """Тест получения активных разрешений партнера."""
        # Настраиваем мок запроса
        query_mock = self.session_mock.query.return_value
        filter_mock = query_mock.filter.return_value
        filter_mock.all.return_value = [self.access_control]
        
        # Подменяем метод is_valid, чтобы он всегда возвращал True
        with patch.object(AccessControl, 'is_valid', return_value=True):
            permissions = self.repo.get_partner_permissions(self.user.telegram_id)
            
            # Проверяем результат
            self.assertEqual(len(permissions), 1)
            self.assertEqual(permissions[0], self.access_control)
            
            # Проверяем, что запрос был вызван с правильными параметрами
            self.session_mock.query.assert_called_once_with(AccessControl)
            query_mock.filter.assert_called_once()
    
    def test_get_partner_permissions_expired(self):
        """Тест получения разрешений партнера с истекшим сроком действия."""
        # Настраиваем мок запроса
        query_mock = self.session_mock.query.return_value
        filter_mock = query_mock.filter.return_value
        filter_mock.all.return_value = [self.access_control]
        
        # Подменяем метод is_valid, чтобы он всегда возвращал False
        with patch.object(AccessControl, 'is_valid', return_value=False):
            permissions = self.repo.get_partner_permissions(self.user.telegram_id)
            
            # Проверяем результат - список должен быть пустым
            self.assertEqual(len(permissions), 0)
            
            # Проверяем, что запрос был вызван с правильными параметрами
            self.session_mock.query.assert_called_once_with(AccessControl)
            query_mock.filter.assert_called_once()
    
    def test_grant_access_new(self):
        """Тест создания нового разрешения."""
        # Настраиваем моки для поиска пользователя и существующего разрешения
        user_query_mock = MagicMock()
        self.session_mock.query.side_effect = [user_query_mock, user_query_mock]
        
        user_filter_mock = MagicMock()
        user_query_mock.filter.return_value = user_filter_mock
        user_filter_mock.first.side_effect = [self.user, None]  # Сначала находим пользователя, потом не находим разрешение
        
        # Вызываем метод
        result = self.repo.grant_access(
            telegram_id=self.user.telegram_id,
            resource_type="campaign",
            resource_id="123456789",
            expires_in_days=30
        )
        
        # Проверяем результат
        self.assertIsNotNone(result)
        
        # Проверяем, что новое разрешение было добавлено в сессию
        self.session_mock.add.assert_called_once()
        self.session_mock.commit.assert_called_once()
    
    def test_grant_access_existing(self):
        """Тест обновления существующего разрешения."""
        # Настраиваем моки для поиска пользователя и существующего разрешения
        user_query_mock = MagicMock()
        access_query_mock = MagicMock()
        self.session_mock.query.side_effect = [user_query_mock, access_query_mock]
        
        user_filter_mock = MagicMock()
        user_query_mock.filter.return_value = user_filter_mock
        user_filter_mock.first.return_value = self.user
        
        access_filter_mock = MagicMock()
        access_query_mock.filter.return_value = access_filter_mock
        access_filter_mock.first.return_value = self.access_control
        
        # Вызываем метод
        result = self.repo.grant_access(
            telegram_id=self.user.telegram_id,
            resource_type="campaign",
            resource_id="123456789",
            expires_in_days=30
        )
        
        # Проверяем результат
        self.assertEqual(result, self.access_control)
        
        # Проверяем, что разрешение было обновлено
        self.assertTrue(self.access_control.is_active)
        self.assertIsNotNone(self.access_control.expires_at)
        
        # Проверяем, что новое разрешение не было добавлено в сессию
        self.session_mock.add.assert_not_called()
        self.session_mock.commit.assert_called_once()
    
    def test_revoke_access_existing(self):
        """Тест отзыва существующего разрешения."""
        # Настраиваем моки
        query_mock = self.session_mock.query.return_value
        filter_mock = query_mock.filter.return_value
        filter_mock.first.return_value = self.access_control
        
        # Вызываем метод
        result = self.repo.revoke_access(
            telegram_id=self.user.telegram_id,
            resource_type="campaign",
            resource_id="123456789"
        )
        
        # Проверяем результат
        self.assertTrue(result)
        self.assertFalse(self.access_control.is_active)
        self.session_mock.commit.assert_called_once()
    
    def test_revoke_access_not_found(self):
        """Тест отзыва несуществующего разрешения."""
        # Настраиваем моки
        query_mock = self.session_mock.query.return_value
        filter_mock = query_mock.filter.return_value
        filter_mock.first.return_value = None
        
        # Вызываем метод
        result = self.repo.revoke_access(
            telegram_id=self.user.telegram_id,
            resource_type="campaign",
            resource_id="123456789"
        )
        
        # Проверяем результат
        self.assertFalse(result)
        self.session_mock.commit.assert_not_called()
    
    def test_check_access_admin(self):
        """Тест проверки доступа для администратора."""
        # Настраиваем моки
        query_mock = self.session_mock.query.return_value
        filter_mock = query_mock.filter.return_value
        filter_mock.first.return_value = self.admin
        
        # Вызываем метод
        result = self.repo.check_access(
            telegram_id=self.admin.telegram_id,
            resource_type="campaign",
            resource_id="any_campaign_id"
        )
        
        # Проверяем результат - админ должен иметь доступ ко всему
        self.assertTrue(result)
        
        # Проверяем, что запрос к AccessControl не был выполнен
        self.assertEqual(self.session_mock.query.call_count, 1)
    
    def test_check_access_targetologist(self):
        """Тест проверки доступа для таргетолога."""
        # Настраиваем моки
        query_mock = self.session_mock.query.return_value
        filter_mock = query_mock.filter.return_value
        filter_mock.first.return_value = self.targetologist
        
        # Вызываем метод
        result = self.repo.check_access(
            telegram_id=self.targetologist.telegram_id,
            resource_type="campaign",
            resource_id="any_campaign_id"
        )
        
        # Проверяем результат - таргетолог должен иметь доступ ко всему
        self.assertTrue(result)
        
        # Проверяем, что запрос к AccessControl не был выполнен
        self.assertEqual(self.session_mock.query.call_count, 1)
    
    def test_check_access_partner_with_permission(self):
        """Тест проверки доступа для партнера с разрешением."""
        # Настраиваем моки для user и access_control
        user_query_mock = MagicMock()
        access_query_mock = MagicMock()
        self.session_mock.query.side_effect = [user_query_mock, access_query_mock]
        
        user_filter_mock = MagicMock()
        user_query_mock.filter.return_value = user_filter_mock
        user_filter_mock.first.return_value = self.user
        
        access_filter_mock = MagicMock()
        access_query_mock.filter.return_value = access_filter_mock
        access_filter_mock.first.return_value = self.access_control
        
        # Подменяем метод is_valid, чтобы он всегда возвращал True
        with patch.object(AccessControl, 'is_valid', return_value=True):
            # Вызываем метод
            result = self.repo.check_access(
                telegram_id=self.user.telegram_id,
                resource_type="campaign",
                resource_id="123456789"
            )
            
            # Проверяем результат - партнер должен иметь доступ, если есть разрешение
            self.assertTrue(result)
    
    def test_check_access_partner_without_permission(self):
        """Тест проверки доступа для партнера без разрешения."""
        # Настраиваем моки для user и отсутствующего access_control
        user_query_mock = MagicMock()
        access_query_mock = MagicMock()
        self.session_mock.query.side_effect = [user_query_mock, access_query_mock]
        
        user_filter_mock = MagicMock()
        user_query_mock.filter.return_value = user_filter_mock
        user_filter_mock.first.return_value = self.user
        
        access_filter_mock = MagicMock()
        access_query_mock.filter.return_value = access_filter_mock
        access_filter_mock.first.return_value = None
        
        # Вызываем метод
        result = self.repo.check_access(
            telegram_id=self.user.telegram_id,
            resource_type="campaign",
            resource_id="123456789"
        )
        
        # Проверяем результат - партнер не должен иметь доступа без разрешения
        self.assertFalse(result)
    
    def test_get_resource_access_list(self):
        """Тест получения списка разрешений для ресурса."""
        # Создаем несколько объектов разрешений
        access1 = AccessControl(telegram_id=123, resource_type="campaign", resource_id="123456789", is_active=True)
        access2 = AccessControl(telegram_id=456, resource_type="campaign", resource_id="123456789", is_active=True)
        access3 = AccessControl(telegram_id=789, resource_type="campaign", resource_id="123456789", is_active=True)
        
        # Настраиваем моки
        query_mock = self.session_mock.query.return_value
        filter_mock = query_mock.filter.return_value
        filter_mock.all.return_value = [access1, access2, access3]
        
        # Подменяем метод is_valid, чтобы два разрешения были валидными, а одно - нет
        with patch.object(AccessControl, 'is_valid', side_effect=[True, False, True]):
            # Вызываем метод
            result = self.repo.get_resource_access_list(
                resource_type="campaign",
                resource_id="123456789"
            )
            
            # Проверяем результат - должны получить только валидные разрешения
            self.assertEqual(len(result), 2)
            self.assertIn(access1, result)
            self.assertNotIn(access2, result)
            self.assertIn(access3, result)
    
    def test_clean_expired_permissions(self):
        """Тест очистки истекших разрешений."""
        # Создаем несколько объектов разрешений
        access1 = AccessControl(id=1, telegram_id=123, is_active=True, expires_at=datetime.now() - timedelta(days=1))
        access2 = AccessControl(id=2, telegram_id=456, is_active=True, expires_at=datetime.now() - timedelta(days=2))
        
        # Настраиваем моки
        query_mock = self.session_mock.query.return_value
        filter_mock = query_mock.filter.return_value
        filter_mock.all.return_value = [access1, access2]
        
        # Вызываем метод
        result = self.repo.clean_expired_permissions()
        
        # Проверяем результат
        self.assertEqual(result, 2)
        self.assertFalse(access1.is_active)
        self.assertFalse(access2.is_active)
        self.session_mock.commit.assert_called_once() 