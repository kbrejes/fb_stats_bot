"""
Тесты для декораторов проверки ролей и прав доступа.
"""
import unittest
from unittest.mock import MagicMock, AsyncMock, patch
import asyncio

from aiogram.types import Message, CallbackQuery, User as TelegramUser

from src.storage.enums import UserRole
from src.storage.models import User
from src.decorators.access_control import (
    role_required, 
    admin_required, 
    targetologist_required, 
    partner_required, 
    campaign_access_required
)
from src.repositories.access_control_repository import AccessControlRepository


class BaseDecoratorsTest(unittest.IsolatedAsyncioTestCase):
    """Базовый класс для тестов декораторов."""
    
    def setUp(self):
        """Настройка тестов."""
        # Создаем моки для telegram User
        self.telegram_user = MagicMock(spec=TelegramUser)
        self.telegram_user.id = 123456
        self.telegram_user.username = "testuser"
        self.telegram_user.first_name = "Test"
        self.telegram_user.last_name = "User"
        
        # Создаем моки для сообщения и callback
        self.message = MagicMock(spec=Message)
        self.message.from_user = self.telegram_user
        self.message.answer = AsyncMock()
        
        self.callback = MagicMock(spec=CallbackQuery)
        self.callback.from_user = self.telegram_user
        self.callback.answer = AsyncMock()
        self.callback.message = MagicMock(spec=Message)
        self.callback.message.answer = AsyncMock()
        
        # Создаем моки пользовательских объектов из БД
        self.admin_user = MagicMock(spec=User)
        self.admin_user.telegram_id = 123456
        self.admin_user.role = UserRole.ADMIN.value
        
        self.targetologist_user = MagicMock(spec=User)
        self.targetologist_user.telegram_id = 234567
        self.targetologist_user.role = UserRole.TARGETOLOGIST.value
        
        self.partner_user = MagicMock(spec=User)
        self.partner_user.telegram_id = 345678
        self.partner_user.role = UserRole.PARTNER.value
        
        # Создаем мок для обработчика
        self.handler = AsyncMock()
        self.handler.__name__ = "test_handler"


class TestRoleRequiredDecorator(BaseDecoratorsTest):
    """Тесты для декоратора role_required."""
    
    async def test_role_required_admin_access_granted(self):
        """Тест успешного доступа администратора."""
        # Создаем декорированный обработчик
        decorated_handler = role_required(UserRole.ADMIN)(self.handler)
        
        # Данные с ролью администратора
        data = {
            "user_role": UserRole.ADMIN.value,
            "db_user": self.admin_user
        }
        
        # Вызываем декорированный обработчик
        result = await decorated_handler(self.message, data)
        
        # Проверяем, что обработчик был вызван
        self.handler.assert_called_once_with(self.message, data)
        
        # Проверяем, что сообщение об ошибке не отправлялось
        self.message.answer.assert_not_called()
    
    async def test_role_required_targetologist_access_denied(self):
        """Тест запрета доступа таргетолога к функциям администратора."""
        # Создаем декорированный обработчик
        decorated_handler = role_required(UserRole.ADMIN)(self.handler)
        
        # Данные с ролью таргетолога
        data = {
            "user_role": UserRole.TARGETOLOGIST.value,
            "db_user": self.targetologist_user
        }
        
        # Вызываем декорированный обработчик
        result = await decorated_handler(self.message, data)
        
        # Проверяем, что обработчик не был вызван
        self.handler.assert_not_called()
        
        # Проверяем, что было отправлено сообщение об ошибке
        self.message.answer.assert_called_once()
        self.assertEqual(
            "Эта команда доступна только администраторам",
            self.message.answer.call_args[0][0]
        )
    
    async def test_role_required_targetologist_access_granted(self):
        """Тест успешного доступа таргетолога к функциям таргетолога."""
        # Создаем декорированный обработчик
        decorated_handler = role_required(UserRole.TARGETOLOGIST)(self.handler)
        
        # Данные с ролью таргетолога
        data = {
            "user_role": UserRole.TARGETOLOGIST.value,
            "db_user": self.targetologist_user
        }
        
        # Вызываем декорированный обработчик
        result = await decorated_handler(self.message, data)
        
        # Проверяем, что обработчик был вызван
        self.handler.assert_called_once_with(self.message, data)
        
        # Проверяем, что сообщение об ошибке не отправлялось
        self.message.answer.assert_not_called()
    
    async def test_role_required_admin_access_to_targetologist_function(self):
        """Тест доступа администратора к функциям таргетолога."""
        # Создаем декорированный обработчик
        decorated_handler = role_required(UserRole.TARGETOLOGIST)(self.handler)
        
        # Данные с ролью администратора
        data = {
            "user_role": UserRole.ADMIN.value,
            "db_user": self.admin_user
        }
        
        # Вызываем декорированный обработчик
        result = await decorated_handler(self.message, data)
        
        # Проверяем, что обработчик был вызван
        self.handler.assert_called_once_with(self.message, data)
        
        # Проверяем, что сообщение об ошибке не отправлялось
        self.message.answer.assert_not_called()
    
    async def test_role_required_partner_access_to_partner_function(self):
        """Тест доступа партнера к функциям партнера."""
        # Создаем декорированный обработчик
        decorated_handler = role_required(UserRole.PARTNER)(self.handler)
        
        # Данные с ролью партнера
        data = {
            "user_role": UserRole.PARTNER.value,
            "db_user": self.partner_user
        }
        
        # Вызываем декорированный обработчик
        result = await decorated_handler(self.message, data)
        
        # Проверяем, что обработчик был вызван
        self.handler.assert_called_once_with(self.message, data)
        
        # Проверяем, что сообщение об ошибке не отправлялось
        self.message.answer.assert_not_called()
    
    async def test_role_required_missing_user_role(self):
        """Тест обработки отсутствия роли пользователя."""
        # Создаем декорированный обработчик
        decorated_handler = role_required(UserRole.ADMIN)(self.handler)
        
        # Данные без роли
        data = {}
        
        # Вызываем декорированный обработчик
        result = await decorated_handler(self.message, data)
        
        # Проверяем, что обработчик не был вызван
        self.handler.assert_not_called()
        
        # Проверяем, что было отправлено сообщение об ошибке
        self.message.answer.assert_called_once()
        self.assertEqual(
            "Ошибка проверки роли пользователя",
            self.message.answer.call_args[0][0]
        )


class TestShortcutDecorators(BaseDecoratorsTest):
    """Тесты для декораторов-сокращений."""
    
    async def test_admin_required(self):
        """Тест декоратора admin_required."""
        # Создаем декорированный обработчик
        decorated_handler = admin_required(self.handler)
        
        # Данные с ролью администратора
        data = {
            "user_role": UserRole.ADMIN.value,
            "db_user": self.admin_user
        }
        
        # Вызываем декорированный обработчик
        result = await decorated_handler(self.message, data)
        
        # Проверяем, что обработчик был вызван
        self.handler.assert_called_once_with(self.message, data)
        
        # Пробуем с ролью партнера
        self.handler.reset_mock()
        data = {
            "user_role": UserRole.PARTNER.value,
            "db_user": self.partner_user
        }
        
        result = await decorated_handler(self.message, data)
        
        # Проверяем, что обработчик не был вызван
        self.handler.assert_not_called()
    
    async def test_targetologist_required(self):
        """Тест декоратора targetologist_required."""
        # Создаем декорированный обработчик
        decorated_handler = targetologist_required(self.handler)
        
        # Проверяем с ролью таргетолога
        data = {
            "user_role": UserRole.TARGETOLOGIST.value,
            "db_user": self.targetologist_user
        }
        
        result = await decorated_handler(self.message, data)
        self.handler.assert_called_once_with(self.message, data)
        
        # Проверяем с ролью администратора
        self.handler.reset_mock()
        data = {
            "user_role": UserRole.ADMIN.value,
            "db_user": self.admin_user
        }
        
        result = await decorated_handler(self.message, data)
        self.handler.assert_called_once_with(self.message, data)
        
        # Проверяем с ролью партнера
        self.handler.reset_mock()
        data = {
            "user_role": UserRole.PARTNER.value,
            "db_user": self.partner_user
        }
        
        result = await decorated_handler(self.message, data)
        self.handler.assert_not_called()
    
    async def test_partner_required(self):
        """Тест декоратора partner_required."""
        # Создаем декорированный обработчик
        decorated_handler = partner_required(self.handler)
        
        # Все роли должны иметь доступ к функциям партнера
        
        # Проверяем с ролью партнера
        data = {
            "user_role": UserRole.PARTNER.value,
            "db_user": self.partner_user
        }
        
        result = await decorated_handler(self.message, data)
        self.handler.assert_called_once_with(self.message, data)
        
        # Проверяем с ролью таргетолога
        self.handler.reset_mock()
        data = {
            "user_role": UserRole.TARGETOLOGIST.value,
            "db_user": self.targetologist_user
        }
        
        result = await decorated_handler(self.message, data)
        self.handler.assert_called_once_with(self.message, data)
        
        # Проверяем с ролью администратора
        self.handler.reset_mock()
        data = {
            "user_role": UserRole.ADMIN.value,
            "db_user": self.admin_user
        }
        
        result = await decorated_handler(self.message, data)
        self.handler.assert_called_once_with(self.message, data)


class TestCampaignAccessDecorator(BaseDecoratorsTest):
    """Тесты для декоратора campaign_access_required."""
    
    def setUp(self):
        """Настройка тестов."""
        super().setUp()
        
        # Патчим репозиторий контроля доступа
        self.access_control_repo_mock = MagicMock(spec=AccessControlRepository)
        self.patcher = patch(
            'src.decorators.access_control.AccessControlRepository',
            return_value=self.access_control_repo_mock
        )
        self.access_control_repo_class_mock = self.patcher.start()
    
    def tearDown(self):
        """Очистка после тестов."""
        super().tearDown()
        self.patcher.stop()
    
    async def test_campaign_access_admin(self):
        """Тест доступа администратора к кампании."""
        # Создаем декорированный обработчик
        decorated_handler = campaign_access_required()(self.handler)
        
        # Данные с ролью администратора и ID кампании
        data = {
            "user_role": UserRole.ADMIN.value,
            "db_user": self.admin_user,
            "campaign_id": "123456789"
        }
        
        # Вызываем декорированный обработчик
        result = await decorated_handler(self.message, data)
        
        # Проверяем, что обработчик был вызван
        self.handler.assert_called_once_with(self.message, data)
        
        # Проверяем, что метод проверки доступа не вызывался (администраторы имеют доступ ко всем кампаниям)
        self.access_control_repo_mock.check_access.assert_not_called()
    
    async def test_campaign_access_targetologist(self):
        """Тест доступа таргетолога к кампании."""
        # Создаем декорированный обработчик
        decorated_handler = campaign_access_required()(self.handler)
        
        # Данные с ролью таргетолога и ID кампании
        data = {
            "user_role": UserRole.TARGETOLOGIST.value,
            "db_user": self.targetologist_user,
            "campaign_id": "123456789"
        }
        
        # Вызываем декорированный обработчик
        result = await decorated_handler(self.message, data)
        
        # Проверяем, что обработчик был вызван
        self.handler.assert_called_once_with(self.message, data)
        
        # Проверяем, что метод проверки доступа не вызывался (таргетологи имеют доступ ко всем кампаниям)
        self.access_control_repo_mock.check_access.assert_not_called()
    
    async def test_campaign_access_partner_with_access(self):
        """Тест доступа партнера к кампании, к которой у него есть доступ."""
        # Настраиваем мок репозитория
        self.access_control_repo_mock.check_access.return_value = True
        
        # Создаем декорированный обработчик
        decorated_handler = campaign_access_required()(self.handler)
        
        # Данные с ролью партнера и ID кампании
        data = {
            "user_role": UserRole.PARTNER.value,
            "db_user": self.partner_user,
            "campaign_id": "123456789"
        }
        
        # Вызываем декорированный обработчик
        result = await decorated_handler(self.message, data)
        
        # Проверяем, что обработчик был вызван
        self.handler.assert_called_once_with(self.message, data)
        
        # Проверяем, что метод проверки доступа был вызван с правильными параметрами
        self.access_control_repo_mock.check_access.assert_called_once_with(
            user_id=self.partner_user.telegram_id,
            resource_type="campaign",
            resource_id="123456789"
        )
    
    async def test_campaign_access_partner_without_access(self):
        """Тест запрета доступа партнера к кампании, к которой у него нет доступа."""
        # Настраиваем мок репозитория
        self.access_control_repo_mock.check_access.return_value = False
        
        # Создаем декорированный обработчик
        decorated_handler = campaign_access_required()(self.handler)
        
        # Данные с ролью партнера и ID кампании
        data = {
            "user_role": UserRole.PARTNER.value,
            "db_user": self.partner_user,
            "campaign_id": "123456789"
        }
        
        # Вызываем декорированный обработчик
        result = await decorated_handler(self.message, data)
        
        # Проверяем, что обработчик не был вызван
        self.handler.assert_not_called()
        
        # Проверяем, что было отправлено сообщение об ошибке
        self.message.answer.assert_called_once()
        
        # Проверяем, что метод проверки доступа был вызван с правильными параметрами
        self.access_control_repo_mock.check_access.assert_called_once_with(
            user_id=self.partner_user.telegram_id,
            resource_type="campaign",
            resource_id="123456789"
        )
    
    async def test_campaign_access_missing_campaign_id(self):
        """Тест обработки отсутствия ID кампании."""
        # Создаем декорированный обработчик
        decorated_handler = campaign_access_required()(self.handler)
        
        # Данные с ролью партнера без ID кампании
        data = {
            "user_role": UserRole.PARTNER.value,
            "db_user": self.partner_user,
        }
        
        # Вызываем декорированный обработчик
        result = await decorated_handler(self.message, data)
        
        # Проверяем, что обработчик не был вызван
        self.handler.assert_not_called()
        
        # Проверяем, что было отправлено сообщение об ошибке
        self.message.answer.assert_called_once()
        self.assertEqual(
            "Не указан ID кампании",
            self.message.answer.call_args[0][0]
        )
    
    async def test_campaign_access_extractor(self):
        """Тест использования функции извлечения ID кампании."""
        # Создаем функцию извлечения ID кампании
        def campaign_id_extractor(event, data):
            return "987654321"
        
        # Настраиваем мок репозитория
        self.access_control_repo_mock.check_access.return_value = True
        
        # Создаем декорированный обработчик с функцией извлечения ID
        decorated_handler = campaign_access_required(campaign_id_extractor)(self.handler)
        
        # Данные с ролью партнера без ID кампании
        data = {
            "user_role": UserRole.PARTNER.value,
            "db_user": self.partner_user,
        }
        
        # Вызываем декорированный обработчик
        result = await decorated_handler(self.message, data)
        
        # Проверяем, что обработчик был вызван
        self.handler.assert_called_once_with(self.message, data)
        
        # Проверяем, что метод проверки доступа был вызван с правильными параметрами
        self.access_control_repo_mock.check_access.assert_called_once_with(
            user_id=self.partner_user.telegram_id,
            resource_type="campaign",
            resource_id="987654321"
        )


if __name__ == "__main__":
    unittest.main() 