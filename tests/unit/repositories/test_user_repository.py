"""
Модуль с тестами для UserRepository.
"""
import unittest
from unittest.mock import MagicMock, patch

from src.repositories.user_repository import UserRepository
from src.storage.models import User
from src.storage.enums import UserRole


class TestUserRepository(unittest.TestCase):
    """Тесты для репозитория UserRepository."""
    
    def setUp(self):
        """Настройка тестов."""
        self.session_mock = MagicMock()
        self.query_mock = MagicMock()
        self.session_mock.query.return_value = self.query_mock
        self.filter_mock = MagicMock()
        self.query_mock.filter.return_value = self.filter_mock
        
        self.repository = UserRepository(session=self.session_mock)
    
    def test_get_user_by_id(self):
        """Тест получения пользователя по ID."""
        # Подготовка
        user_mock = MagicMock(spec=User)
        self.filter_mock.first.return_value = user_mock
        
        # Выполнение
        result = self.repository.get_user_by_id(123456)
        
        # Проверка
        self.session_mock.query.assert_called_once_with(User)
        self.query_mock.filter.assert_called_once()
        self.assertEqual(result, user_mock)
    
    def test_get_user_by_id_not_found(self):
        """Тест получения несуществующего пользователя."""
        # Подготовка
        self.filter_mock.first.return_value = None
        
        # Выполнение
        result = self.repository.get_user_by_id(123456)
        
        # Проверка
        self.assertIsNone(result)
    
    def test_get_user_by_id_exception(self):
        """Тест обработки исключения при получении пользователя."""
        # Подготовка
        self.query_mock.filter.side_effect = Exception("Test error")
        
        # Выполнение
        result = self.repository.get_user_by_id(123456)
        
        # Проверка
        self.assertIsNone(result)
    
    def test_get_all_users(self):
        """Тест получения всех пользователей."""
        # Подготовка
        users = [MagicMock(spec=User), MagicMock(spec=User)]
        self.query_mock.all.return_value = users
        
        # Выполнение
        result = self.repository.get_all_users()
        
        # Проверка
        self.session_mock.query.assert_called_once_with(User)
        self.query_mock.all.assert_called_once()
        self.assertEqual(result, users)
    
    def test_get_all_users_empty(self):
        """Тест получения пустого списка пользователей."""
        # Подготовка
        self.query_mock.all.return_value = []
        
        # Выполнение
        result = self.repository.get_all_users()
        
        # Проверка
        self.assertEqual(result, [])
    
    def test_get_all_users_exception(self):
        """Тест обработки исключения при получении пользователей."""
        # Подготовка
        self.query_mock.all.side_effect = Exception("Test error")
        
        # Выполнение
        result = self.repository.get_all_users()
        
        # Проверка
        self.assertEqual(result, [])
    
    def test_get_users_by_role(self):
        """Тест получения пользователей по роли."""
        # Подготовка
        users = [MagicMock(spec=User), MagicMock(spec=User)]
        self.filter_mock.all.return_value = users
        
        # Выполнение с объектом UserRole
        result = self.repository.get_users_by_role(UserRole.ADMIN)
        
        # Проверка
        self.session_mock.query.assert_called_with(User)
        self.query_mock.filter.assert_called()
        self.assertEqual(result, users)
        
        # Выполнение со строкой
        result = self.repository.get_users_by_role("admin")
        
        # Проверка
        self.assertEqual(result, users)
    
    def test_get_users_by_role_empty(self):
        """Тест получения пустого списка пользователей по роли."""
        # Подготовка
        self.filter_mock.all.return_value = []
        
        # Выполнение
        result = self.repository.get_users_by_role(UserRole.PARTNER)
        
        # Проверка
        self.assertEqual(result, [])
    
    def test_get_users_by_role_exception(self):
        """Тест обработки исключения при получении пользователей по роли."""
        # Подготовка
        self.query_mock.filter.side_effect = Exception("Test error")
        
        # Выполнение
        result = self.repository.get_users_by_role(UserRole.TARGETOLOGIST)
        
        # Проверка
        self.assertEqual(result, [])
    
    def test_search_users(self):
        """Тест поиска пользователей."""
        # Подготовка
        users = [MagicMock(spec=User), MagicMock(spec=User)]
        self.filter_mock.all.return_value = users
        
        # Выполнение
        result = self.repository.search_users("test")
        
        # Проверка
        self.session_mock.query.assert_called_once_with(User)
        self.query_mock.filter.assert_called_once()
        self.assertEqual(result, users)
    
    def test_search_users_empty(self):
        """Тест пустого результата поиска пользователей."""
        # Подготовка
        self.filter_mock.all.return_value = []
        
        # Выполнение
        result = self.repository.search_users("test")
        
        # Проверка
        self.assertEqual(result, [])
    
    def test_search_users_exception(self):
        """Тест обработки исключения при поиске пользователей."""
        # Подготовка
        self.query_mock.filter.side_effect = Exception("Test error")
        
        # Выполнение
        result = self.repository.search_users("test")
        
        # Проверка
        self.assertEqual(result, [])
    
    def test_create_user_new(self):
        """Тест создания нового пользователя."""
        # Подготовка
        self.repository.get_user_by_id = MagicMock(return_value=None)
        
        # Выполнение
        result = self.repository.create_user(
            telegram_id=123456,
            username="testuser",
            first_name="Test",
            last_name="User",
            role=UserRole.PARTNER
        )
        
        # Проверка
        self.assertEqual(result.telegram_id, 123456)
        self.assertEqual(result.username, "testuser")
        self.assertEqual(result.first_name, "Test")
        self.assertEqual(result.last_name, "User")
        self.assertEqual(result.role, "partner")
        self.session_mock.add.assert_called_once()
        self.session_mock.commit.assert_called_once()
    
    def test_create_user_existing(self):
        """Тест обновления существующего пользователя при создании."""
        # Подготовка
        existing_user = MagicMock(spec=User)
        self.repository.get_user_by_id = MagicMock(return_value=existing_user)
        self.repository.update_user = MagicMock(return_value=existing_user)
        
        # Выполнение
        result = self.repository.create_user(
            telegram_id=123456,
            username="testuser",
            first_name="Test",
            last_name="User"
        )
        
        # Проверка
        self.repository.update_user.assert_called_once_with(
            telegram_id=123456,
            username="testuser",
            first_name="Test",
            last_name="User"
        )
        self.assertEqual(result, existing_user)
    
    def test_create_user_exception(self):
        """Тест обработки исключения при создании пользователя."""
        # Подготовка
        self.repository.get_user_by_id = MagicMock(return_value=None)
        self.session_mock.add.side_effect = Exception("Test error")
        
        # Выполнение
        result = self.repository.create_user(telegram_id=123456)
        
        # Проверка
        self.assertIsNone(result)
        self.session_mock.rollback.assert_called_once()
    
    def test_update_user(self):
        """Тест обновления пользователя."""
        # Подготовка
        user = MagicMock(spec=User)
        self.repository.get_user_by_id = MagicMock(return_value=user)
        
        # Выполнение
        result = self.repository.update_user(
            telegram_id=123456,
            username="newuser",
            first_name="New",
            last_name="User"
        )
        
        # Проверка
        self.assertEqual(user.username, "newuser")
        self.assertEqual(user.first_name, "New")
        self.assertEqual(user.last_name, "User")
        self.session_mock.commit.assert_called_once()
        self.assertEqual(result, user)
    
    def test_update_user_partial(self):
        """Тест частичного обновления пользователя."""
        # Подготовка
        user = MagicMock(spec=User)
        user.username = "olduser"
        user.first_name = "Old"
        user.last_name = "User"
        self.repository.get_user_by_id = MagicMock(return_value=user)
        
        # Выполнение
        result = self.repository.update_user(
            telegram_id=123456,
            first_name="New"
        )
        
        # Проверка
        self.assertEqual(user.username, "olduser")  # не изменилось
        self.assertEqual(user.first_name, "New")  # изменилось
        self.assertEqual(user.last_name, "User")  # не изменилось
        self.session_mock.commit.assert_called_once()
        self.assertEqual(result, user)
    
    def test_update_user_not_found(self):
        """Тест обновления несуществующего пользователя."""
        # Подготовка
        self.repository.get_user_by_id = MagicMock(return_value=None)
        
        # Выполнение
        result = self.repository.update_user(telegram_id=123456)
        
        # Проверка
        self.assertIsNone(result)
        self.session_mock.commit.assert_not_called()
    
    def test_update_user_exception(self):
        """Тест обработки исключения при обновлении пользователя."""
        # Подготовка
        user = MagicMock(spec=User)
        self.repository.get_user_by_id = MagicMock(return_value=user)
        self.session_mock.commit.side_effect = Exception("Test error")
        
        # Выполнение
        result = self.repository.update_user(telegram_id=123456)
        
        # Проверка
        self.assertIsNone(result)
        self.session_mock.rollback.assert_called_once()
    
    def test_set_user_role(self):
        """Тест установки роли пользователя."""
        # Подготовка
        user = MagicMock(spec=User)
        user.set_user_role.return_value = True
        self.repository.get_user_by_id = MagicMock(return_value=user)
        
        # Выполнение с объектом UserRole
        result = self.repository.set_user_role(123456, UserRole.ADMIN)
        
        # Проверка
        user.set_user_role.assert_called_with(UserRole.ADMIN)
        self.session_mock.commit.assert_called_once()
        self.assertTrue(result)
        
        # Выполнение со строкой
        self.session_mock.reset_mock()
        user.set_user_role.reset_mock()
        
        result = self.repository.set_user_role(123456, "admin")
        
        # Проверка
        user.set_user_role.assert_called_with("admin")
        self.session_mock.commit.assert_called_once()
        self.assertTrue(result)
    
    def test_set_user_role_not_found(self):
        """Тест установки роли несуществующего пользователя."""
        # Подготовка
        self.repository.get_user_by_id = MagicMock(return_value=None)
        
        # Выполнение
        result = self.repository.set_user_role(123456, UserRole.ADMIN)
        
        # Проверка
        self.assertFalse(result)
        self.session_mock.commit.assert_not_called()
    
    def test_set_user_role_failure(self):
        """Тест неудачной установки роли пользователя."""
        # Подготовка
        user = MagicMock(spec=User)
        user.set_user_role.return_value = False
        self.repository.get_user_by_id = MagicMock(return_value=user)
        
        # Выполнение
        result = self.repository.set_user_role(123456, UserRole.ADMIN)
        
        # Проверка
        user.set_user_role.assert_called_with(UserRole.ADMIN)
        self.session_mock.commit.assert_not_called()
        self.assertFalse(result)
    
    def test_set_user_role_exception(self):
        """Тест обработки исключения при установке роли."""
        # Подготовка
        user = MagicMock(spec=User)
        user.set_user_role.side_effect = Exception("Test error")
        self.repository.get_user_by_id = MagicMock(return_value=user)
        
        # Выполнение
        result = self.repository.set_user_role(123456, UserRole.ADMIN)
        
        # Проверка
        self.assertFalse(result)
        self.session_mock.rollback.assert_called_once()
    
    def test_delete_user(self):
        """Тест удаления пользователя."""
        # Подготовка
        user = MagicMock(spec=User)
        self.repository.get_user_by_id = MagicMock(return_value=user)
        
        # Выполнение
        result = self.repository.delete_user(123456)
        
        # Проверка
        self.session_mock.delete.assert_called_once_with(user)
        self.session_mock.commit.assert_called_once()
        self.assertTrue(result)
    
    def test_delete_user_not_found(self):
        """Тест удаления несуществующего пользователя."""
        # Подготовка
        self.repository.get_user_by_id = MagicMock(return_value=None)
        
        # Выполнение
        result = self.repository.delete_user(123456)
        
        # Проверка
        self.session_mock.delete.assert_not_called()
        self.session_mock.commit.assert_not_called()
        self.assertFalse(result)
    
    def test_delete_user_exception(self):
        """Тест обработки исключения при удалении пользователя."""
        # Подготовка
        user = MagicMock(spec=User)
        self.repository.get_user_by_id = MagicMock(return_value=user)
        self.session_mock.delete.side_effect = Exception("Test error")
        
        # Выполнение
        result = self.repository.delete_user(123456)
        
        # Проверка
        self.assertFalse(result)
        self.session_mock.rollback.assert_called_once()
    
    def test_get_active_users(self):
        """Тест получения активных пользователей."""
        # Подготовка
        users = [MagicMock(spec=User), MagicMock(spec=User)]
        self.repository.get_all_users = MagicMock(return_value=users)
        
        # Выполнение
        result = self.repository.get_active_users(30)
        
        # Проверка
        self.repository.get_all_users.assert_called_once()
        self.assertEqual(result, users)
    
    def test_get_active_users_exception(self):
        """Тест обработки исключения при получении активных пользователей."""
        # Подготовка
        self.repository.get_all_users = MagicMock(side_effect=Exception("Test error"))
        
        # Выполнение
        result = self.repository.get_active_users()
        
        # Проверка
        self.assertEqual(result, [])
    
    def test_count_users_by_role(self):
        """Тест подсчета пользователей по ролям."""
        # Подготовка
        # Переопределяем метод session.query для имитации результатов подсчета
        self.repository.session.query = MagicMock()
        
        # Мокируем целую цепочку выполнения для каждой роли
        admin_query = MagicMock()
        admin_filter = MagicMock()
        admin_filter.count.return_value = 2
        admin_query.filter.return_value = admin_filter
        
        targetologist_query = MagicMock()
        targetologist_filter = MagicMock()
        targetologist_filter.count.return_value = 5
        targetologist_query.filter.return_value = targetologist_filter
        
        partner_query = MagicMock()
        partner_filter = MagicMock()
        partner_filter.count.return_value = 10
        partner_query.filter.return_value = partner_filter
        
        # Устанавливаем разное поведение для разных вызовов query
        query_calls = 0
        def query_side_effect(model):
            nonlocal query_calls
            query_calls += 1
            if query_calls == 1:
                return admin_query
            elif query_calls == 2:
                return targetologist_query
            else:
                return partner_query
        
        self.repository.session.query.side_effect = query_side_effect
        
        # Выполнение
        result = self.repository.count_users_by_role()
        
        # Проверка
        self.assertEqual(result["admin"], 2)
        self.assertEqual(result["targetologist"], 5)
        self.assertEqual(result["partner"], 10)
    
    def test_count_users_by_role_exception(self):
        """Тест обработки исключения при подсчете пользователей."""
        # Подготовка
        self.query_mock.filter.side_effect = Exception("Test error")
        
        # Выполнение
        result = self.repository.count_users_by_role()
        
        # Проверка
        self.assertEqual(result, {})


if __name__ == "__main__":
    unittest.main() 