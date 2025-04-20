"""
Тесты для утилит контроля доступа.
"""
import unittest
from unittest.mock import patch, MagicMock

from src.utils.access_utils import (
    check_user_role,
    is_admin,
    is_targetologist,
    has_campaign_access,
    has_financial_access,
    get_user_campaigns
)
from src.storage.models import User, AccessControl
from src.storage.enums import UserRole
from src.repositories.access_control_repository import AccessControlRepository


class TestAccessUtils(unittest.TestCase):
    """Тесты для утилит контроля доступа."""
    
    def setUp(self):
        """Подготовка к тестам."""
        # Создаем мок для сессии
        self.session_mock = MagicMock()
        
        # Создаем моки пользовательских объектов
        self.admin_user = MagicMock(spec=User)
        self.admin_user.telegram_id = 123456
        self.admin_user.role = UserRole.ADMIN.value
        self.admin_user.has_permission = MagicMock(return_value=True)
        self.admin_user.is_targetologist = MagicMock(return_value=True)
        self.admin_user.is_admin = MagicMock(return_value=True)
        
        self.targetologist_user = MagicMock(spec=User)
        self.targetologist_user.telegram_id = 234567
        self.targetologist_user.role = UserRole.TARGETOLOGIST.value
        self.targetologist_user.has_permission = MagicMock(
            side_effect=lambda role: role in [UserRole.TARGETOLOGIST, UserRole.PARTNER]
        )
        self.targetologist_user.is_targetologist = MagicMock(return_value=True)
        self.targetologist_user.is_admin = MagicMock(return_value=False)
        
        self.partner_user = MagicMock(spec=User)
        self.partner_user.telegram_id = 345678
        self.partner_user.role = UserRole.PARTNER.value
        self.partner_user.has_permission = MagicMock(
            side_effect=lambda role: role == UserRole.PARTNER
        )
        self.partner_user.is_targetologist = MagicMock(return_value=False)
        self.partner_user.is_admin = MagicMock(return_value=False)
        
        # Патчим get_session для использования мок-сессии
        self.session_patcher = patch('src.utils.access_utils.get_session', return_value=self.session_mock)
        self.session_mock_func = self.session_patcher.start()
    
    def tearDown(self):
        """Очистка после тестов."""
        self.session_patcher.stop()
    
    def test_check_user_role_admin(self):
        """Тест функции check_user_role для администратора."""
        # Настраиваем мок сессии для возврата пользователя-администратора
        query_mock = self.session_mock.query.return_value
        filter_mock = query_mock.filter.return_value
        filter_mock.first.return_value = self.admin_user
        
        # Вызываем функцию
        result = check_user_role(user_id=123456, role=UserRole.ADMIN)
        
        # Проверяем результат
        self.assertTrue(result)
        
        # Проверяем, что был вызван метод has_permission с правильным параметром
        self.admin_user.has_permission.assert_called_once_with(UserRole.ADMIN)
    
    def test_check_user_role_string_role(self):
        """Тест функции check_user_role со строковым представлением роли."""
        # Настраиваем мок сессии для возврата пользователя-администратора
        query_mock = self.session_mock.query.return_value
        filter_mock = query_mock.filter.return_value
        filter_mock.first.return_value = self.admin_user
        
        # Вызываем функцию со строковым представлением роли
        result = check_user_role(user_id=123456, role="ADMIN")
        
        # Проверяем результат
        self.assertTrue(result)
        
        # Проверяем, что был вызван метод has_permission с правильным параметром
        self.admin_user.has_permission.assert_called_once_with(UserRole.ADMIN)
    
    def test_check_user_role_invalid_role(self):
        """Тест функции check_user_role с недопустимой ролью."""
        # Настраиваем мок сессии для возврата пользователя-администратора
        query_mock = self.session_mock.query.return_value
        filter_mock = query_mock.filter.return_value
        filter_mock.first.return_value = self.admin_user
        
        # Проверяем, что функция выбрасывает ValueError при недопустимой роли
        with self.assertRaises(ValueError):
            check_user_role(user_id=123456, role="INVALID_ROLE")
    
    def test_check_user_role_user_not_found(self):
        """Тест функции check_user_role для пользователя, которого нет в базе данных."""
        # Настраиваем мок сессии для возврата None (пользователь не найден)
        query_mock = self.session_mock.query.return_value
        filter_mock = query_mock.filter.return_value
        filter_mock.first.return_value = None
        
        # Вызываем функцию
        result = check_user_role(user_id=999999, role=UserRole.ADMIN)
        
        # Проверяем результат - должен быть False, так как пользователь не найден
        self.assertFalse(result)
    
    def test_is_admin_true(self):
        """Тест функции is_admin для администратора."""
        # Патчим функцию check_user_role для возврата True
        with patch('src.utils.access_utils.check_user_role', return_value=True) as check_role_mock:
            # Вызываем функцию
            result = is_admin(user_id=123456)
            
            # Проверяем результат
            self.assertTrue(result)
            
            # Проверяем, что была вызвана функция check_user_role с правильными параметрами
            check_role_mock.assert_called_once_with(123456, UserRole.ADMIN, None)
    
    def test_is_admin_false(self):
        """Тест функции is_admin для не-администратора."""
        # Патчим функцию check_user_role для возврата False
        with patch('src.utils.access_utils.check_user_role', return_value=False) as check_role_mock:
            # Вызываем функцию
            result = is_admin(user_id=345678)
            
            # Проверяем результат
            self.assertFalse(result)
            
            # Проверяем, что была вызвана функция check_user_role с правильными параметрами
            check_role_mock.assert_called_once_with(345678, UserRole.ADMIN, None)
    
    def test_is_targetologist_true(self):
        """Тест функции is_targetologist для таргетолога."""
        # Патчим функцию check_user_role для возврата True
        with patch('src.utils.access_utils.check_user_role', return_value=True) as check_role_mock:
            # Вызываем функцию
            result = is_targetologist(user_id=234567)
            
            # Проверяем результат
            self.assertTrue(result)
            
            # Проверяем, что была вызвана функция check_user_role с правильными параметрами
            check_role_mock.assert_called_once_with(234567, UserRole.TARGETOLOGIST, None)
    
    def test_is_targetologist_false(self):
        """Тест функции is_targetologist для не-таргетолога."""
        # Патчим функцию check_user_role для возврата False
        with patch('src.utils.access_utils.check_user_role', return_value=False) as check_role_mock:
            # Вызываем функцию
            result = is_targetologist(user_id=345678)
            
            # Проверяем результат
            self.assertFalse(result)
            
            # Проверяем, что была вызвана функция check_user_role с правильными параметрами
            check_role_mock.assert_called_once_with(345678, UserRole.TARGETOLOGIST, None)
    
    def test_has_campaign_access_admin(self):
        """Тест функции has_campaign_access для администратора."""
        # Настраиваем мок сессии для возврата пользователя-администратора
        query_mock = self.session_mock.query.return_value
        filter_mock = query_mock.filter.return_value
        filter_mock.first.return_value = self.admin_user
        
        # Патчим AccessControlRepository для использования мок-репозитория
        with patch('src.utils.access_utils.AccessControlRepository') as repo_mock:
            # Вызываем функцию
            result = has_campaign_access(user_id=123456, campaign_id="test_campaign")
            
            # Проверяем результат - должен быть True, так как администраторы имеют доступ ко всем кампаниям
            self.assertTrue(result)
            
            # Проверяем, что метод check_access не вызывался (администраторы имеют доступ ко всем кампаниям)
            repo_instance = repo_mock.return_value
            repo_instance.check_access.assert_not_called()
    
    def test_has_campaign_access_targetologist(self):
        """Тест функции has_campaign_access для таргетолога."""
        # Настраиваем мок сессии для возврата пользователя-таргетолога
        query_mock = self.session_mock.query.return_value
        filter_mock = query_mock.filter.return_value
        filter_mock.first.return_value = self.targetologist_user
        
        # Патчим AccessControlRepository для использования мок-репозитория
        with patch('src.utils.access_utils.AccessControlRepository') as repo_mock:
            # Вызываем функцию
            result = has_campaign_access(user_id=234567, campaign_id="test_campaign")
            
            # Проверяем результат - должен быть True, так как таргетологи имеют доступ ко всем кампаниям
            self.assertTrue(result)
            
            # Проверяем, что метод check_access не вызывался (таргетологи имеют доступ ко всем кампаниям)
            repo_instance = repo_mock.return_value
            repo_instance.check_access.assert_not_called()
    
    def test_has_campaign_access_partner_with_access(self):
        """Тест функции has_campaign_access для партнера с доступом к кампании."""
        # Настраиваем мок сессии для возврата пользователя-партнера
        query_mock = self.session_mock.query.return_value
        filter_mock = query_mock.filter.return_value
        filter_mock.first.return_value = self.partner_user
        
        # Патчим AccessControlRepository для использования мок-репозитория
        with patch('src.utils.access_utils.AccessControlRepository') as repo_mock:
            # Настраиваем мок репозитория для возврата True (доступ разрешен)
            repo_instance = repo_mock.return_value
            repo_instance.check_access.return_value = True
            
            # Вызываем функцию
            result = has_campaign_access(user_id=345678, campaign_id="test_campaign")
            
            # Проверяем результат - должен быть True, так как партнер имеет доступ к кампании
            self.assertTrue(result)
            
            # Проверяем, что метод check_access был вызван с правильными параметрами
            repo_instance.check_access.assert_called_once_with(
                user_id=345678,
                resource_type="campaign",
                resource_id="test_campaign"
            )
    
    def test_has_campaign_access_partner_without_access(self):
        """Тест функции has_campaign_access для партнера без доступа к кампании."""
        # Настраиваем мок сессии для возврата пользователя-партнера
        query_mock = self.session_mock.query.return_value
        filter_mock = query_mock.filter.return_value
        filter_mock.first.return_value = self.partner_user
        
        # Патчим AccessControlRepository для использования мок-репозитория
        with patch('src.utils.access_utils.AccessControlRepository') as repo_mock:
            # Настраиваем мок репозитория для возврата False (доступ запрещен)
            repo_instance = repo_mock.return_value
            repo_instance.check_access.return_value = False
            
            # Вызываем функцию
            result = has_campaign_access(user_id=345678, campaign_id="test_campaign")
            
            # Проверяем результат - должен быть False, так как партнер не имеет доступа к кампании
            self.assertFalse(result)
            
            # Проверяем, что метод check_access был вызван с правильными параметрами
            repo_instance.check_access.assert_called_once_with(
                user_id=345678,
                resource_type="campaign",
                resource_id="test_campaign"
            )
    
    def test_has_campaign_access_user_not_found(self):
        """Тест функции has_campaign_access для пользователя, которого нет в базе данных."""
        # Настраиваем мок сессии для возврата None (пользователь не найден)
        query_mock = self.session_mock.query.return_value
        filter_mock = query_mock.filter.return_value
        filter_mock.first.return_value = None
        
        # Вызываем функцию
        result = has_campaign_access(user_id=999999, campaign_id="test_campaign")
        
        # Проверяем результат - должен быть False, так как пользователь не найден
        self.assertFalse(result)
    
    def test_has_financial_access_admin(self):
        """Тест функции has_financial_access для администратора."""
        # Патчим функцию is_admin для возврата True
        with patch('src.utils.access_utils.is_admin', return_value=True) as is_admin_mock:
            # Вызываем функцию
            result = has_financial_access(user_id=123456)
            
            # Проверяем результат
            self.assertTrue(result)
            
            # Проверяем, что была вызвана функция is_admin с правильными параметрами
            is_admin_mock.assert_called_once_with(123456, None)
    
    def test_has_financial_access_non_admin(self):
        """Тест функции has_financial_access для не-администратора."""
        # Патчим функцию is_admin для возврата False
        with patch('src.utils.access_utils.is_admin', return_value=False) as is_admin_mock:
            # Вызываем функцию
            result = has_financial_access(user_id=234567)
            
            # Проверяем результат
            self.assertFalse(result)
            
            # Проверяем, что была вызвана функция is_admin с правильными параметрами
            is_admin_mock.assert_called_once_with(234567, None)
    
    def test_get_user_campaigns_admin(self):
        """Тест функции get_user_campaigns для администратора."""
        # Настраиваем мок сессии для возврата пользователя-администратора
        query_mock = self.session_mock.query.return_value
        filter_mock = query_mock.filter.return_value
        filter_mock.first.return_value = self.admin_user
        
        # Патчим AccessControlRepository для использования мок-репозитория
        with patch('src.utils.access_utils.AccessControlRepository') as repo_mock:
            # Вызываем функцию
            result = get_user_campaigns(user_id=123456)
            
            # Проверяем результат - должен быть None, что означает "все кампании"
            self.assertIsNone(result)
            
            # Проверяем, что метод get_partner_permissions не вызывался 
            # (администраторы имеют доступ ко всем кампаниям)
            repo_instance = repo_mock.return_value
            repo_instance.get_partner_permissions.assert_not_called()
    
    def test_get_user_campaigns_targetologist(self):
        """Тест функции get_user_campaigns для таргетолога."""
        # Настраиваем мок сессии для возврата пользователя-таргетолога
        query_mock = self.session_mock.query.return_value
        filter_mock = query_mock.filter.return_value
        filter_mock.first.return_value = self.targetologist_user
        
        # Патчим AccessControlRepository для использования мок-репозитория
        with patch('src.utils.access_utils.AccessControlRepository') as repo_mock:
            # Вызываем функцию
            result = get_user_campaigns(user_id=234567)
            
            # Проверяем результат - должен быть None, что означает "все кампании"
            self.assertIsNone(result)
            
            # Проверяем, что метод get_partner_permissions не вызывался 
            # (таргетологи имеют доступ ко всем кампаниям)
            repo_instance = repo_mock.return_value
            repo_instance.get_partner_permissions.assert_not_called()
    
    def test_get_user_campaigns_partner(self):
        """Тест функции get_user_campaigns для партнера."""
        # Настраиваем мок сессии для возврата пользователя-партнера
        query_mock = self.session_mock.query.return_value
        filter_mock = query_mock.filter.return_value
        filter_mock.first.return_value = self.partner_user
        
        # Патчим AccessControlRepository для использования мок-репозитория
        with patch('src.utils.access_utils.AccessControlRepository') as repo_mock:
            # Создаем моки разрешений доступа
            campaign1 = MagicMock(spec=AccessControl)
            campaign1.resource_type = "campaign"
            campaign1.resource_id = "campaign1"
            campaign1.is_valid = MagicMock(return_value=True)
            
            campaign2 = MagicMock(spec=AccessControl)
            campaign2.resource_type = "campaign"
            campaign2.resource_id = "campaign2"
            campaign2.is_valid = MagicMock(return_value=True)
            
            # Настраиваем мок репозитория для возврата списка разрешений
            repo_instance = repo_mock.return_value
            repo_instance.get_partner_permissions.return_value = [campaign1, campaign2]
            
            # Вызываем функцию
            result = get_user_campaigns(user_id=345678)
            
            # Проверяем результат - должен быть список ID кампаний
            self.assertEqual(result, ["campaign1", "campaign2"])
            
            # Проверяем, что метод get_partner_permissions был вызван с правильными параметрами
            repo_instance.get_partner_permissions.assert_called_once_with(345678)
    
    def test_get_user_campaigns_invalid_permissions(self):
        """Тест функции get_user_campaigns для партнера с недействительными разрешениями."""
        # Настраиваем мок сессии для возврата пользователя-партнера
        query_mock = self.session_mock.query.return_value
        filter_mock = query_mock.filter.return_value
        filter_mock.first.return_value = self.partner_user
        
        # Патчим AccessControlRepository для использования мок-репозитория
        with patch('src.utils.access_utils.AccessControlRepository') as repo_mock:
            # Создаем моки разрешений доступа
            campaign1 = MagicMock(spec=AccessControl)
            campaign1.resource_type = "campaign"
            campaign1.resource_id = "campaign1"
            campaign1.is_valid = MagicMock(return_value=False)  # Недействительное разрешение
            
            account1 = MagicMock(spec=AccessControl)
            account1.resource_type = "account"  # Другой тип ресурса
            account1.resource_id = "account1"
            account1.is_valid = MagicMock(return_value=True)
            
            # Настраиваем мок репозитория для возврата списка разрешений
            repo_instance = repo_mock.return_value
            repo_instance.get_partner_permissions.return_value = [campaign1, account1]
            
            # Вызываем функцию
            result = get_user_campaigns(user_id=345678)
            
            # Проверяем результат - должен быть пустой список, 
            # так как нет действительных разрешений для кампаний
            self.assertEqual(result, [])
            
            # Проверяем, что метод get_partner_permissions был вызван с правильными параметрами
            repo_instance.get_partner_permissions.assert_called_once_with(345678)
    
    def test_get_user_campaigns_user_not_found(self):
        """Тест функции get_user_campaigns для пользователя, которого нет в базе данных."""
        # Настраиваем мок сессии для возврата None (пользователь не найден)
        query_mock = self.session_mock.query.return_value
        filter_mock = query_mock.filter.return_value
        filter_mock.first.return_value = None
        
        # Вызываем функцию
        result = get_user_campaigns(user_id=999999)
        
        # Проверяем результат - должен быть пустой список, так как пользователь не найден
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main() 