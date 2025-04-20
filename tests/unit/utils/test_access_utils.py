"""
Тесты для утилит проверки прав доступа пользователей.
"""
import unittest
from unittest.mock import MagicMock, patch

from src.storage.enums import UserRole
from src.storage.models import User
from src.utils.access_utils import (
    check_user_role,
    is_admin,
    is_targetologist,
    has_campaign_access,
    has_financial_access
)
from src.repositories.user_repository import UserRepository
from src.repositories.access_control_repository import AccessControlRepository


class TestAccessUtils(unittest.TestCase):
    """Тесты для утилит проверки прав доступа."""
    
    def setUp(self):
        """Настройка тестов."""
        # Создаем моки для пользователей
        self.admin_user = MagicMock(spec=User)
        self.admin_user.telegram_id = 123456
        self.admin_user.role = UserRole.ADMIN.value
        
        self.targetologist_user = MagicMock(spec=User)
        self.targetologist_user.telegram_id = 234567
        self.targetologist_user.role = UserRole.TARGETOLOGIST.value
        
        self.partner_user = MagicMock(spec=User)
        self.partner_user.telegram_id = 345678
        self.partner_user.role = UserRole.PARTNER.value
        
        # Создаем моки для репозиториев
        self.user_repo_mock = MagicMock(spec=UserRepository)
        self.user_repo_mock.get_user_by_id.side_effect = self._get_user_by_id
        self.user_repo_mock.close = MagicMock()
        
        self.access_control_repo_mock = MagicMock(spec=AccessControlRepository)
        self.access_control_repo_mock.check_access.return_value = True
        self.access_control_repo_mock.close = MagicMock()
        
        # Настраиваем патчи
        self.user_repo_patch = patch('src.utils.access_utils.UserRepository', 
                                     return_value=self.user_repo_mock)
        self.access_control_repo_patch = patch('src.utils.access_utils.AccessControlRepository', 
                                              return_value=self.access_control_repo_mock)
        
        # Начинаем патчи
        self.user_repo_mock_instance = self.user_repo_patch.start()
        self.access_control_repo_mock_instance = self.access_control_repo_patch.start()
    
    def tearDown(self):
        """Очистка после тестов."""
        # Останавливаем патчи
        self.user_repo_patch.stop()
        self.access_control_repo_patch.stop()
    
    def _get_user_by_id(self, telegram_id):
        """Мок-функция для получения пользователя по ID."""
        if telegram_id == self.admin_user.telegram_id:
            return self.admin_user
        elif telegram_id == self.targetologist_user.telegram_id:
            return self.targetologist_user
        elif telegram_id == self.partner_user.telegram_id:
            return self.partner_user
        else:
            return None
    
    def test_check_user_role_admin(self):
        """Тест проверки роли администратора."""
        # Проверяем, что администратор имеет роль администратора
        self.assertTrue(check_user_role(self.admin_user.telegram_id, UserRole.ADMIN))
        
        # Проверяем, что администратор имеет роль таргетолога
        self.assertTrue(check_user_role(self.admin_user.telegram_id, UserRole.TARGETOLOGIST))
        
        # Проверяем, что администратор имеет роль партнера
        self.assertTrue(check_user_role(self.admin_user.telegram_id, UserRole.PARTNER))
    
    def test_check_user_role_targetologist(self):
        """Тест проверки роли таргетолога."""
        # Проверяем, что таргетолог НЕ имеет роль администратора
        self.assertFalse(check_user_role(self.targetologist_user.telegram_id, UserRole.ADMIN))
        
        # Проверяем, что таргетолог имеет роль таргетолога
        self.assertTrue(check_user_role(self.targetologist_user.telegram_id, UserRole.TARGETOLOGIST))
        
        # Проверяем, что таргетолог имеет роль партнера
        self.assertTrue(check_user_role(self.targetologist_user.telegram_id, UserRole.PARTNER))
    
    def test_check_user_role_partner(self):
        """Тест проверки роли партнера."""
        # Проверяем, что партнер НЕ имеет роль администратора
        self.assertFalse(check_user_role(self.partner_user.telegram_id, UserRole.ADMIN))
        
        # Проверяем, что партнер НЕ имеет роль таргетолога
        self.assertFalse(check_user_role(self.partner_user.telegram_id, UserRole.TARGETOLOGIST))
        
        # Проверяем, что партнер имеет роль партнера
        self.assertTrue(check_user_role(self.partner_user.telegram_id, UserRole.PARTNER))
    
    def test_check_user_role_not_found(self):
        """Тест проверки роли несуществующего пользователя."""
        # Проверяем, что для несуществующего пользователя возвращается False
        self.assertFalse(check_user_role(999999, UserRole.ADMIN))
        self.assertFalse(check_user_role(999999, UserRole.TARGETOLOGIST))
        self.assertFalse(check_user_role(999999, UserRole.PARTNER))
    
    def test_check_user_role_invalid_role(self):
        """Тест проверки недопустимой роли."""
        # Проверяем, что для недопустимой роли возвращается False
        self.assertFalse(check_user_role(self.admin_user.telegram_id, "invalid_role"))
    
    def test_is_admin(self):
        """Тест функции is_admin."""
        # Проверяем, что администратор распознается как администратор
        self.assertTrue(is_admin(self.admin_user.telegram_id))
        
        # Проверяем, что таргетолог НЕ распознается как администратор
        self.assertFalse(is_admin(self.targetologist_user.telegram_id))
        
        # Проверяем, что партнер НЕ распознается как администратор
        self.assertFalse(is_admin(self.partner_user.telegram_id))
        
        # Проверяем, что для несуществующего пользователя возвращается False
        self.assertFalse(is_admin(999999))
    
    def test_is_targetologist(self):
        """Тест функции is_targetologist."""
        # Проверяем, что администратор распознается как таргетолог
        self.assertTrue(is_targetologist(self.admin_user.telegram_id))
        
        # Проверяем, что таргетолог распознается как таргетолог
        self.assertTrue(is_targetologist(self.targetologist_user.telegram_id))
        
        # Проверяем, что партнер НЕ распознается как таргетолог
        self.assertFalse(is_targetologist(self.partner_user.telegram_id))
        
        # Проверяем, что для несуществующего пользователя возвращается False
        self.assertFalse(is_targetologist(999999))
    
    def test_has_campaign_access_admin(self):
        """Тест проверки доступа к кампании для администратора."""
        # Проверяем, что администратор имеет доступ к любой кампании
        self.assertTrue(has_campaign_access(self.admin_user.telegram_id, "campaign_123"))
        
        # Проверяем, что access_control_repo.check_access не вызывается для администратора
        self.access_control_repo_mock.check_access.assert_not_called()
    
    def test_has_campaign_access_targetologist(self):
        """Тест проверки доступа к кампании для таргетолога."""
        # Проверяем, что таргетолог имеет доступ к любой кампании
        self.assertTrue(has_campaign_access(self.targetologist_user.telegram_id, "campaign_123"))
        
        # Проверяем, что access_control_repo.check_access не вызывается для таргетолога
        self.access_control_repo_mock.check_access.assert_not_called()
    
    def test_has_campaign_access_partner_with_access(self):
        """Тест проверки доступа к кампании для партнера с доступом."""
        # Устанавливаем, что партнер имеет доступ к кампании
        self.access_control_repo_mock.check_access.return_value = True
        
        # Проверяем, что партнер имеет доступ к кампании
        self.assertTrue(has_campaign_access(self.partner_user.telegram_id, "campaign_123"))
        
        # Проверяем, что access_control_repo.check_access вызывается с правильными параметрами
        self.access_control_repo_mock.check_access.assert_called_once_with(
            telegram_id=self.partner_user.telegram_id,
            resource_type="campaign",
            resource_id="campaign_123"
        )
    
    def test_has_campaign_access_partner_without_access(self):
        """Тест проверки доступа к кампании для партнера без доступа."""
        # Устанавливаем, что партнер НЕ имеет доступ к кампании
        self.access_control_repo_mock.check_access.return_value = False
        
        # Проверяем, что партнер НЕ имеет доступ к кампании
        self.assertFalse(has_campaign_access(self.partner_user.telegram_id, "campaign_123"))
    
    def test_has_campaign_access_not_found(self):
        """Тест проверки доступа к кампании для несуществующего пользователя."""
        # Проверяем, что для несуществующего пользователя возвращается False
        self.assertFalse(has_campaign_access(999999, "campaign_123"))
    
    def test_has_financial_access(self):
        """Тест функции has_financial_access."""
        # Проверяем, что администратор имеет доступ к финансовым данным
        self.assertTrue(has_financial_access(self.admin_user.telegram_id))
        
        # Проверяем, что таргетолог НЕ имеет доступ к финансовым данным
        self.assertFalse(has_financial_access(self.targetologist_user.telegram_id))
        
        # Проверяем, что партнер НЕ имеет доступ к финансовым данным
        self.assertFalse(has_financial_access(self.partner_user.telegram_id))
        
        # Проверяем, что для несуществующего пользователя возвращается False
        self.assertFalse(has_financial_access(999999))


if __name__ == "__main__":
    unittest.main() 