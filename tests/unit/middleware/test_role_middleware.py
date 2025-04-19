"""
Модуль с тестами для RoleMiddleware.
"""
import unittest
from unittest.mock import MagicMock, AsyncMock, patch
import asyncio
import time

from aiogram.types import Message, User as TelegramUser
from sqlalchemy.orm import Session

from src.middleware.role_middleware import RoleMiddleware
from src.storage.models import User
from src.storage.enums import UserRole
from src.repositories.user_repository import UserRepository


class TestRoleMiddleware(unittest.IsolatedAsyncioTestCase):
    """Тесты для RoleMiddleware."""
    
    def setUp(self):
        """Настройка тестов."""
        self.session_mock = MagicMock(spec=Session)
        self.user_repo_mock = MagicMock(spec=UserRepository)
        self.user_repo_mock.session = self.session_mock
        
        # Патчим конструктор UserRepository
        self.patcher = patch('src.middleware.role_middleware.UserRepository', return_value=self.user_repo_mock)
        self.user_repo_class_mock = self.patcher.start()
        
        # Создаем middleware
        self.middleware = RoleMiddleware(session=self.session_mock)
        
        # Патчим приватные методы для работы с кешем
        self.middleware._get_cached_role = MagicMock(return_value=(None, None))
        self.middleware._cache_role = MagicMock()
        
        # Создаем моки для telegram User
        self.telegram_user = MagicMock(spec=TelegramUser)
        self.telegram_user.id = 123456
        self.telegram_user.username = "testuser"
        self.telegram_user.first_name = "Test"
        self.telegram_user.last_name = "User"
        
        # Создаем моки для сообщения и обработчика
        self.message = MagicMock(spec=Message)
        self.message.from_user = self.telegram_user
        
        self.handler = AsyncMock()
        self.data = {}
    
    def tearDown(self):
        """Очистка после тестов."""
        self.patcher.stop()
    
    async def test_get_existing_user(self):
        """Тест получения существующего пользователя."""
        # Создаем мок пользователя из БД
        db_user = MagicMock(spec=User)
        db_user.role = UserRole.ADMIN.value
        
        # Настраиваем возвращаемое значение для get_user_by_id
        self.user_repo_mock.get_user_by_id.return_value = db_user
        
        # Вызываем middleware
        await self.middleware(self.handler, self.message, self.data)
        
        # Проверяем, что метод get_user_by_id был вызван с правильным ID
        self.user_repo_mock.get_user_by_id.assert_called_once_with(self.telegram_user.id)
        
        # Проверяем, что роль и пользователь были добавлены в данные
        self.assertEqual(self.data["user_role"], UserRole.ADMIN.value)
        self.assertEqual(self.data["db_user"], db_user)
        
        # Проверяем, что метод кеширования был вызван
        self.middleware._cache_role.assert_called_once_with(
            self.telegram_user.id, UserRole.ADMIN.value, db_user
        )
        
        # Проверяем, что обработчик был вызван
        self.handler.assert_called_once_with(self.message, self.data)
    
    async def test_create_new_user(self):
        """Тест создания нового пользователя."""
        # Настраиваем возвращаемое значение для get_user_by_id - пользователь не найден
        self.user_repo_mock.get_user_by_id.return_value = None
        
        # Создаем мок нового пользователя
        new_user = MagicMock(spec=User)
        new_user.role = UserRole.PARTNER.value
        
        # Настраиваем возвращаемое значение для create_user
        self.user_repo_mock.create_user.return_value = new_user
        
        # Вызываем middleware
        await self.middleware(self.handler, self.message, self.data)
        
        # Проверяем, что метод get_user_by_id был вызван с правильным ID
        self.user_repo_mock.get_user_by_id.assert_called_once_with(self.telegram_user.id)
        
        # Проверяем, что метод create_user был вызван с правильными параметрами
        self.user_repo_mock.create_user.assert_called_once_with(
            telegram_id=self.telegram_user.id,
            username=self.telegram_user.username,
            first_name=self.telegram_user.first_name,
            last_name=self.telegram_user.last_name,
            role=UserRole.PARTNER
        )
        
        # Проверяем, что роль и пользователь были добавлены в данные
        self.assertEqual(self.data["user_role"], UserRole.PARTNER.value)
        self.assertEqual(self.data["db_user"], new_user)
        
        # Проверяем, что метод кеширования был вызван
        self.middleware._cache_role.assert_called_once_with(
            self.telegram_user.id, UserRole.PARTNER.value, new_user
        )
        
        # Проверяем, что обработчик был вызван
        self.handler.assert_called_once_with(self.message, self.data)
    
    async def test_get_from_cache(self):
        """Тест получения пользователя из кеша."""
        # Создаем мок пользователя для возврата из кеша
        cached_user = MagicMock(spec=User)
        cached_user.role = UserRole.TARGETOLOGIST.value
        
        # Настраиваем возвращаемое значение для _get_cached_role
        self.middleware._get_cached_role.return_value = (
            UserRole.TARGETOLOGIST.value, cached_user
        )
        
        # Вызываем middleware
        await self.middleware(self.handler, self.message, self.data)
        
        # Проверяем, что метод _get_cached_role был вызван с правильным ID
        self.middleware._get_cached_role.assert_called_once_with(self.telegram_user.id)
        
        # Проверяем, что метод get_user_by_id не был вызван (т.к. пользователь из кеша)
        self.user_repo_mock.get_user_by_id.assert_not_called()
        
        # Проверяем, что роль и пользователь были добавлены в данные
        self.assertEqual(self.data["user_role"], UserRole.TARGETOLOGIST.value)
        self.assertEqual(self.data["db_user"], cached_user)
        
        # Проверяем, что метод кеширования не был вызван
        self.middleware._cache_role.assert_not_called()
        
        # Проверяем, что обработчик был вызван
        self.handler.assert_called_once_with(self.message, self.data)
    
    async def test_exception_handling(self):
        """Тест обработки исключений."""
        # Настраиваем get_user_by_id, чтобы он вызывал исключение
        self.user_repo_mock.get_user_by_id.side_effect = Exception("Test error")
        
        # Вызываем middleware
        await self.middleware(self.handler, self.message, self.data)
        
        # Проверяем, что роль партнера была установлена в случае ошибки
        self.assertEqual(self.data["user_role"], UserRole.PARTNER.value)
        self.assertIsNone(self.data["db_user"])
        
        # Проверяем, что обработчик был вызван, несмотря на ошибку
        self.handler.assert_called_once_with(self.message, self.data)
    
    async def test_unsupported_event_type(self):
        """Тест обработки неподдерживаемого типа события."""
        # Создаем событие неподдерживаемого типа
        unsupported_event = MagicMock()
        
        # Вызываем middleware
        await self.middleware(self.handler, unsupported_event, self.data)
        
        # Проверяем, что обработчик был вызван без изменения данных
        self.handler.assert_called_once_with(unsupported_event, self.data)
        
        # Проверяем, что никакие данные не были добавлены
        self.assertNotIn("user_role", self.data)
        self.assertNotIn("db_user", self.data)
    
    async def test_repository_close_on_new_session(self):
        """Тест закрытия репозитория, если создавалась новая сессия."""
        # Создаем middleware без сессии
        middleware = RoleMiddleware()
        
        # Патчим приватные методы
        middleware._get_cached_role = MagicMock(return_value=(None, None))
        middleware._cache_role = MagicMock()
        
        # Создаем мок пользователя
        db_user = MagicMock(spec=User)
        db_user.role = UserRole.ADMIN.value
        
        # Настраиваем репозиторий
        repo_instance = MagicMock(spec=UserRepository)
        repo_instance.get_user_by_id.return_value = db_user
        self.user_repo_class_mock.return_value = repo_instance
        
        # Вызываем middleware
        await middleware(self.handler, self.message, self.data)
        
        # Проверяем, что репозиторий был закрыт
        repo_instance.close.assert_called_once()
    
    @patch('src.middleware.role_middleware.time')
    def test_get_cached_role_valid(self, time_mock):
        """Тест получения актуальной роли из кеша."""
        # Восстанавливаем реальную реализацию метода
        self.middleware._get_cached_role = RoleMiddleware._get_cached_role.__get__(self.middleware)
        
        # Настраиваем текущее время
        current_time = 1000.0
        time_mock.time.return_value = current_time
        
        # Создаем мок пользователя
        user_mock = MagicMock(spec=User)
        
        # Создаем запись в кеше с "свежим" временем
        cache_time = current_time - 100  # 100 секунд назад (меньше ROLE_CACHE_EXPIRY)
        from src.middleware.role_middleware import _role_cache
        _role_cache[self.telegram_user.id] = (UserRole.ADMIN.value, cache_time, user_mock)
        
        # Вызываем метод
        role, user_obj = self.middleware._get_cached_role(self.telegram_user.id)
        
        # Проверяем результат
        self.assertEqual(role, UserRole.ADMIN.value)
        self.assertEqual(user_obj, user_mock)
    
    @patch('src.middleware.role_middleware.time')
    def test_get_cached_role_expired(self, time_mock):
        """Тест получения устаревшей роли из кеша."""
        # Восстанавливаем реальную реализацию метода
        self.middleware._get_cached_role = RoleMiddleware._get_cached_role.__get__(self.middleware)
        
        # Настраиваем текущее время
        current_time = 1000.0
        time_mock.time.return_value = current_time
        
        # Создаем мок пользователя
        user_mock = MagicMock(spec=User)
        
        # Создаем запись в кеше с устаревшим временем
        cache_time = current_time - 400  # 400 секунд назад (больше ROLE_CACHE_EXPIRY)
        from src.middleware.role_middleware import _role_cache
        _role_cache[self.telegram_user.id] = (UserRole.ADMIN.value, cache_time, user_mock)
        
        # Вызываем метод
        role, user_obj = self.middleware._get_cached_role(self.telegram_user.id)
        
        # Проверяем результат - кеш устарел, должен вернуть None
        self.assertIsNone(role)
        self.assertIsNone(user_obj)
    
    @patch('src.middleware.role_middleware.time')
    def test_cache_role(self, time_mock):
        """Тест кеширования роли пользователя."""
        # Восстанавливаем реальную реализацию метода
        self.middleware._cache_role = RoleMiddleware._cache_role.__get__(self.middleware)
        
        # Настраиваем текущее время
        current_time = 1000.0
        time_mock.time.return_value = current_time
        
        # Создаем мок пользователя
        user_mock = MagicMock(spec=User)
        
        # Вызываем метод
        self.middleware._cache_role(self.telegram_user.id, UserRole.TARGETOLOGIST.value, user_mock)
        
        # Проверяем, что запись была добавлена в кеш
        from src.middleware.role_middleware import _role_cache
        self.assertIn(self.telegram_user.id, _role_cache)
        
        cached_role, cached_time, cached_user = _role_cache[self.telegram_user.id]
        self.assertEqual(cached_role, UserRole.TARGETOLOGIST.value)
        self.assertEqual(cached_time, current_time)
        self.assertEqual(cached_user, user_mock)
    
    def test_clear_role_cache_specific_user(self):
        """Тест очистки кеша для конкретного пользователя."""
        # Восстанавливаем реальную реализацию метода
        self.middleware.clear_role_cache = RoleMiddleware.clear_role_cache.__get__(self.middleware)
        
        # Создаем моки пользователей
        user1_mock = MagicMock(spec=User)
        user2_mock = MagicMock(spec=User)
        
        # Заполняем кеш
        from src.middleware.role_middleware import _role_cache
        _role_cache[123] = (UserRole.ADMIN.value, time.time(), user1_mock)
        _role_cache[456] = (UserRole.PARTNER.value, time.time(), user2_mock)
        
        # Очищаем кеш для одного пользователя
        self.middleware.clear_role_cache(123)
        
        # Проверяем результат
        self.assertNotIn(123, _role_cache)
        self.assertIn(456, _role_cache)
    
    def test_clear_role_cache_all(self):
        """Тест очистки всего кеша."""
        # Восстанавливаем реальную реализацию метода
        self.middleware.clear_role_cache = RoleMiddleware.clear_role_cache.__get__(self.middleware)
        
        # Создаем моки пользователей
        user1_mock = MagicMock(spec=User)
        user2_mock = MagicMock(spec=User)
        
        # Заполняем кеш
        from src.middleware.role_middleware import _role_cache
        _role_cache[123] = (UserRole.ADMIN.value, time.time(), user1_mock)
        _role_cache[456] = (UserRole.PARTNER.value, time.time(), user2_mock)
        
        # Очищаем весь кеш
        self.middleware.clear_role_cache()
        
        # Проверяем результат
        self.assertEqual(len(_role_cache), 0)


if __name__ == "__main__":
    unittest.main() 