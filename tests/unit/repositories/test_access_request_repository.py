"""
Тесты для репозитория AccessRequestRepository.
"""
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, call

from sqlalchemy.orm import Session
from sqlalchemy import desc

from src.repositories.access_request_repository import AccessRequestRepository
from src.repositories.access_control_repository import AccessControlRepository
from src.storage.models import AccessRequest, AccessControl, User
from src.storage.enums import UserRole


class TestAccessRequestRepository(unittest.TestCase):
    """Тесты для репозитория AccessRequestRepository."""
    
    def setUp(self):
        """Подготовка к тестам."""
        # Создаем моки
        self.session_mock = MagicMock(spec=Session)
        self.user = User(telegram_id=123456, role=UserRole.PARTNER.value)
        self.admin = User(telegram_id=654321, role=UserRole.ADMIN.value)
        self.targetologist = User(telegram_id=789012, role=UserRole.TARGETOLOGIST.value)
        
        # Создаем репозиторий с моком сессии
        self.repo = AccessRequestRepository(session=self.session_mock)
        
        # Создаем объект запроса для тестов
        self.access_request = AccessRequest(
            id=1,
            telegram_id=self.user.telegram_id,
            resource_type="campaign",
            resource_id="123456789",
            message="Нужен доступ к кампании",
            requested_duration=15,
            status="pending"
        )
    
    def test_create_request_new(self):
        """Тест создания нового запроса."""
        # Настраиваем моки для поиска пользователя и существующего запроса
        user_query_mock = MagicMock()
        request_query_mock = MagicMock()
        self.session_mock.query.side_effect = [user_query_mock, request_query_mock]
        
        user_filter_mock = MagicMock()
        user_query_mock.filter.return_value = user_filter_mock
        user_filter_mock.first.return_value = self.user
        
        request_filter_mock = MagicMock()
        request_query_mock.filter.return_value = request_filter_mock
        request_filter_mock.first.return_value = None  # Запрос не существует
        
        # Вызываем метод
        result = self.repo.create_request(
            telegram_id=self.user.telegram_id,
            resource_type="campaign",
            resource_id="123456789",
            message="Нужен доступ к кампании",
            requested_duration=15
        )
        
        # Проверяем результат
        self.assertIsNotNone(result)
        
        # Проверяем, что новый запрос был добавлен в сессию
        self.session_mock.add.assert_called_once()
        self.session_mock.commit.assert_called_once()
    
    def test_create_request_existing(self):
        """Тест обновления существующего запроса."""
        # Настраиваем моки для поиска пользователя и существующего запроса
        user_query_mock = MagicMock()
        request_query_mock = MagicMock()
        self.session_mock.query.side_effect = [user_query_mock, request_query_mock]
        
        user_filter_mock = MagicMock()
        user_query_mock.filter.return_value = user_filter_mock
        user_filter_mock.first.return_value = self.user
        
        request_filter_mock = MagicMock()
        request_query_mock.filter.return_value = request_filter_mock
        request_filter_mock.first.return_value = self.access_request
        
        # Вызываем метод с новым сообщением
        new_message = "Обновленное сообщение"
        result = self.repo.create_request(
            telegram_id=self.user.telegram_id,
            resource_type="campaign",
            resource_id="123456789",
            message=new_message,
            requested_duration=20
        )
        
        # Проверяем результат
        self.assertEqual(result, self.access_request)
        self.assertEqual(self.access_request.message, new_message)
        self.assertEqual(self.access_request.requested_duration, 20)
        
        # Проверяем, что запрос был обновлен
        self.session_mock.add.assert_not_called()
        self.session_mock.commit.assert_called_once()
    
    def test_create_request_targetologist(self):
        """Тест создания запроса для таргетолога (должно вернуть None)."""
        # Настраиваем моки для поиска пользователя
        query_mock = self.session_mock.query.return_value
        filter_mock = query_mock.filter.return_value
        filter_mock.first.return_value = self.targetologist
        
        # Вызываем метод
        result = self.repo.create_request(
            telegram_id=self.targetologist.telegram_id,
            resource_type="campaign",
            resource_id="123456789"
        )
        
        # Проверяем результат - таргетологам не нужны запросы доступа
        self.assertIsNone(result)
        self.session_mock.add.assert_not_called()
        self.session_mock.commit.assert_not_called()
    
    def test_get_pending_requests(self):
        """Тест получения ожидающих запросов."""
        # Создаем список запросов
        requests = [
            AccessRequest(id=1, telegram_id=123, resource_type="campaign", resource_id="1", status="pending"),
            AccessRequest(id=2, telegram_id=456, resource_type="campaign", resource_id="2", status="pending")
        ]
        
        # Настраиваем моки
        query_mock = self.session_mock.query.return_value
        filter_mock = query_mock.filter.return_value
        order_mock = filter_mock.order_by.return_value
        order_mock.all.return_value = requests
        
        # Вызываем метод
        result = self.repo.get_pending_requests()
        
        # Проверяем результат
        self.assertEqual(len(result), 2)
        self.assertEqual(result, requests)
        
        # Проверяем, что запрос был вызван с правильными параметрами
        self.session_mock.query.assert_called_once_with(AccessRequest)
        filter_mock.order_by.assert_called_once()
    
    def test_get_user_requests_pending_only(self):
        """Тест получения запросов пользователя (только ожидающие)."""
        # Создаем список запросов
        requests = [
            AccessRequest(id=1, telegram_id=self.user.telegram_id, status="pending"),
            AccessRequest(id=2, telegram_id=self.user.telegram_id, status="pending")
        ]
        
        # Настраиваем моки
        query_mock = self.session_mock.query.return_value
        filter_mock = query_mock.filter.return_value
        filter2_mock = filter_mock.filter.return_value
        order_mock = filter2_mock.order_by.return_value
        order_mock.all.return_value = requests
        
        # Вызываем метод
        result = self.repo.get_user_requests(self.user.telegram_id, include_processed=False)
        
        # Проверяем результат
        self.assertEqual(len(result), 2)
        self.assertEqual(result, requests)
        
        # Проверяем, что запрос на фильтрацию был вызван
        # Не сравниваем точное значение, т.к. SQLAlchemy создает разные объекты выражений
        self.assertEqual(filter_mock.filter.call_count, 1)
    
    def test_get_user_requests_all(self):
        """Тест получения всех запросов пользователя (включая обработанные)."""
        # Создаем список запросов
        requests = [
            AccessRequest(id=1, telegram_id=self.user.telegram_id, status="pending"),
            AccessRequest(id=2, telegram_id=self.user.telegram_id, status="approved"),
            AccessRequest(id=3, telegram_id=self.user.telegram_id, status="rejected")
        ]
        
        # Настраиваем моки
        query_mock = self.session_mock.query.return_value
        filter_mock = query_mock.filter.return_value
        order_mock = filter_mock.order_by.return_value
        order_mock.all.return_value = requests
        
        # Вызываем метод
        result = self.repo.get_user_requests(self.user.telegram_id, include_processed=True)
        
        # Проверяем результат
        self.assertEqual(len(result), 3)
        self.assertEqual(result, requests)
        
        # Проверяем, что запрос был вызван с правильными параметрами
        filter_mock.filter.assert_not_called()
    
    def test_get_request_by_id(self):
        """Тест получения запроса по ID."""
        # Настраиваем моки
        query_mock = self.session_mock.query.return_value
        filter_mock = query_mock.filter.return_value
        filter_mock.first.return_value = self.access_request
        
        # Вызываем метод
        result = self.repo.get_request_by_id(1)
        
        # Проверяем результат
        self.assertEqual(result, self.access_request)
        
        # Проверяем, что запрос был вызван с правильными параметрами
        self.session_mock.query.assert_called_once_with(AccessRequest)
        query_mock.filter.assert_called_once()
    
    def test_approve_request(self):
        """Тест одобрения запроса."""
        # Настраиваем моки для поиска администратора и запроса
        admin_query_mock = MagicMock()
        request_query_mock = MagicMock()
        self.session_mock.query.side_effect = [admin_query_mock, request_query_mock]
        
        admin_filter_mock = MagicMock()
        admin_query_mock.filter.return_value = admin_filter_mock
        admin_filter_mock.first.return_value = self.admin
        
        request_filter_mock = MagicMock()
        request_query_mock.filter.return_value = request_filter_mock
        request_filter_mock.first.return_value = self.access_request
        
        # Настраиваем мок для метода approve
        with patch.object(AccessRequest, 'approve') as approve_mock:
            # Настраиваем мок для AccessControlRepository
            with patch('src.repositories.access_control_repository.AccessControlRepository') as repo_mock:
                # Настраиваем результат метода grant_access
                access_control = AccessControl(
                    id=1,
                    telegram_id=self.user.telegram_id,
                    resource_type="campaign",
                    resource_id="123456789"
                )
                repo_instance = repo_mock.return_value
                repo_instance.grant_access.return_value = access_control
                
                # Вызываем метод
                result = self.repo.approve_request(
                    request_id=1,
                    admin_id=self.admin.telegram_id,
                    admin_notes="Одобрено"
                )
                
                # Проверяем результат
                self.assertEqual(result, access_control)
                
                # Проверяем, что методы были вызваны с правильными параметрами
                approve_mock.assert_called_once_with(admin_id=self.admin.telegram_id, admin_notes="Одобрено")
                repo_mock.assert_called_once_with(session=self.session_mock)
                repo_instance.grant_access.assert_called_once_with(
                    telegram_id=self.user.telegram_id,
                    resource_type="campaign",
                    resource_id="123456789",
                    expires_in_days=15
                )
                self.session_mock.commit.assert_called_once()
    
    def test_approve_request_non_admin(self):
        """Тест одобрения запроса не администратором (должно вернуть None)."""
        # Настраиваем моки для поиска обычного пользователя
        query_mock = self.session_mock.query.return_value
        filter_mock = query_mock.filter.return_value
        filter_mock.first.return_value = self.user  # Не админ
        
        # Вызываем метод
        result = self.repo.approve_request(
            request_id=1,
            admin_id=self.user.telegram_id,
            admin_notes="Одобрено"
        )
        
        # Проверяем результат - только админ может одобрять запросы
        self.assertIsNone(result)
        self.session_mock.commit.assert_not_called()
    
    def test_reject_request(self):
        """Тест отклонения запроса."""
        # Настраиваем моки для поиска администратора и запроса
        admin_query_mock = MagicMock()
        request_query_mock = MagicMock()
        self.session_mock.query.side_effect = [admin_query_mock, request_query_mock]
        
        admin_filter_mock = MagicMock()
        admin_query_mock.filter.return_value = admin_filter_mock
        admin_filter_mock.first.return_value = self.admin
        
        request_filter_mock = MagicMock()
        request_query_mock.filter.return_value = request_filter_mock
        request_filter_mock.first.return_value = self.access_request
        
        # Настраиваем мок для метода reject
        with patch.object(AccessRequest, 'reject') as reject_mock:
            # Вызываем метод
            result = self.repo.reject_request(
                request_id=1,
                admin_id=self.admin.telegram_id,
                admin_notes="Отклонено"
            )
            
            # Проверяем результат
            self.assertTrue(result)
            
            # Проверяем, что методы были вызваны с правильными параметрами
            reject_mock.assert_called_once_with(admin_id=self.admin.telegram_id, admin_notes="Отклонено")
            self.session_mock.commit.assert_called_once()
    
    def test_reject_request_non_admin(self):
        """Тест отклонения запроса не администратором (должно вернуть False)."""
        # Настраиваем моки для поиска обычного пользователя
        query_mock = self.session_mock.query.return_value
        filter_mock = query_mock.filter.return_value
        filter_mock.first.return_value = self.user  # Не админ
        
        # Вызываем метод
        result = self.repo.reject_request(
            request_id=1,
            admin_id=self.user.telegram_id,
            admin_notes="Отклонено"
        )
        
        # Проверяем результат - только админ может отклонять запросы
        self.assertFalse(result)
        self.session_mock.commit.assert_not_called()
    
    def test_get_processed_requests(self):
        """Тест получения обработанных запросов."""
        # Создаем список запросов
        processed_requests = [
            AccessRequest(id=1, status="approved"),
            AccessRequest(id=2, status="rejected")
        ]
        
        # Настраиваем моки
        query_mock = self.session_mock.query.return_value
        filter_mock = query_mock.filter.return_value
        order_mock = filter_mock.order_by.return_value
        limit_mock = order_mock.limit.return_value
        limit_mock.all.return_value = processed_requests
        
        # Вызываем метод
        result = self.repo.get_processed_requests()
        
        # Проверяем результат
        self.assertEqual(len(result), 2)
        self.assertEqual(result, processed_requests)
        
        # Проверяем, что запрос был вызван с правильными параметрами
        self.session_mock.query.assert_called_once_with(AccessRequest)
        filter_mock.order_by.assert_called_once()
        order_mock.limit.assert_called_once_with(50)
    
    def test_get_processed_requests_with_status(self):
        """Тест получения обработанных запросов с фильтром по статусу."""
        # Создаем список запросов
        approved_requests = [
            AccessRequest(id=1, status="approved"),
            AccessRequest(id=2, status="approved")
        ]
        
        # Настраиваем моки
        query_mock = self.session_mock.query.return_value
        filter1_mock = query_mock.filter.return_value
        filter2_mock = filter1_mock.filter.return_value
        order_mock = filter2_mock.order_by.return_value
        limit_mock = order_mock.limit.return_value
        limit_mock.all.return_value = approved_requests
        
        # Вызываем метод с фильтром по статусу
        result = self.repo.get_processed_requests(status="approved", limit=10)
        
        # Проверяем результат
        self.assertEqual(len(result), 2)
        self.assertEqual(result, approved_requests)
        
        # Проверяем, что запрос был вызван с правильными параметрами
        self.session_mock.query.assert_called_once_with(AccessRequest)
        # Проверяем, что метод filter был вызван дважды (для !pending и для status==approved)
        self.assertEqual(filter1_mock.filter.call_count, 1)
        filter2_mock.order_by.assert_called_once()
        order_mock.limit.assert_called_once_with(10) 