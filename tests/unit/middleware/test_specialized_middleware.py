"""
Модуль с тестами для специализированных middleware.
"""
import unittest
from unittest.mock import MagicMock, AsyncMock, patch
import asyncio

from aiogram.types import Message, CallbackQuery, User as TelegramUser

from src.middleware.specialized_middleware import (
    AdminMiddleware, 
    TargetologistMiddleware, 
    PartnerMiddleware, 
    CampaignAccessMiddleware
)
from src.storage.models import User
from src.storage.enums import UserRole
from src.repositories.access_control_repository import AccessControlRepository


class BaseMiddlewareTest(unittest.IsolatedAsyncioTestCase):
    """Базовый класс для тестов middleware."""
    
    def setUp(self):
        """Настройка тестов."""
        # Создаем моки для telegram User
        self.telegram_user = MagicMock(spec=TelegramUser)
        self.telegram_user.id = 123456
        self.telegram_user.username = "testuser"
        self.telegram_user.first_name = "Test"
        self.telegram_user.last_name = "User"
        
        # Создаем моки для сообщения и обработчика
        self.message = MagicMock(spec=Message)
        self.message.from_user = self.telegram_user
        self.message.answer = AsyncMock()
        
        # Создаем мок для callback query
        self.callback = MagicMock(spec=CallbackQuery)
        self.callback.from_user = self.telegram_user
        self.callback.answer = AsyncMock()
        self.callback.message = MagicMock(spec=Message)
        self.callback.message.answer = AsyncMock()
        
        # Создаем мок для обработчика
        self.handler = AsyncMock()
        
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


class TestAdminMiddleware(BaseMiddlewareTest):
    """Тесты для AdminMiddleware."""
    
    def setUp(self):
        """Настройка тестов."""
        super().setUp()
        self.middleware = AdminMiddleware()
    
    async def test_admin_access_granted(self):
        """Тест успешного доступа администратора."""
        # Данные с ролью администратора
        data = {
            "user_role": UserRole.ADMIN.value,
            "db_user": self.admin_user
        }
        
        # Вызываем middleware
        result = await self.middleware(self.handler, self.message, data)
        
        # Проверяем, что обработчик был вызван
        self.handler.assert_called_once_with(self.message, data)
        
        # Проверяем, что сообщение об ошибке не отправлялось
        self.message.answer.assert_not_called()
    
    async def test_admin_access_denied(self):
        """Тест запрета доступа для не-администратора."""
        # Данные с ролью партнера
        data = {
            "user_role": UserRole.PARTNER.value,
            "db_user": self.partner_user
        }
        
        # Вызываем middleware
        result = await self.middleware(self.handler, self.message, data)
        
        # Проверяем, что обработчик не был вызван
        self.handler.assert_not_called()
        
        # Проверяем, что было отправлено сообщение об ошибке
        self.message.answer.assert_called_once()
        self.assertEqual(
            "Эта команда доступна только администраторам",
            self.message.answer.call_args[0][0]
        )
    
    async def test_admin_missing_role(self):
        """Тест обработки отсутствия роли пользователя."""
        # Данные без роли
        data = {}
        
        # Вызываем middleware
        result = await self.middleware(self.handler, self.message, data)
        
        # Проверяем, что обработчик не был вызван
        self.handler.assert_not_called()
        
        # Проверяем, что было отправлено сообщение об ошибке
        self.message.answer.assert_called_once()
        self.assertEqual(
            "Ошибка проверки роли пользователя",
            self.message.answer.call_args[0][0]
        )
    
    async def test_admin_unsupported_event_type(self):
        """Тест обработки неподдерживаемого типа события."""
        # Создаем событие неподдерживаемого типа
        unsupported_event = MagicMock()
        
        # Данные с ролью администратора
        data = {
            "user_role": UserRole.ADMIN.value,
            "db_user": self.admin_user
        }
        
        # Вызываем middleware
        result = await self.middleware(self.handler, unsupported_event, data)
        
        # Проверяем, что обработчик был вызван
        self.handler.assert_called_once_with(unsupported_event, data)


class TestTargetologistMiddleware(BaseMiddlewareTest):
    """Тесты для TargetologistMiddleware."""
    
    def setUp(self):
        """Настройка тестов."""
        super().setUp()
        self.middleware = TargetologistMiddleware()
    
    async def test_targetologist_access_granted(self):
        """Тест успешного доступа таргетолога."""
        # Данные с ролью таргетолога
        data = {
            "user_role": UserRole.TARGETOLOGIST.value,
            "db_user": self.targetologist_user
        }
        
        # Вызываем middleware
        result = await self.middleware(self.handler, self.message, data)
        
        # Проверяем, что обработчик был вызван
        self.handler.assert_called_once_with(self.message, data)
        
        # Проверяем, что сообщение об ошибке не отправлялось
        self.message.answer.assert_not_called()
    
    async def test_admin_access_to_targetologist_function(self):
        """Тест доступа администратора к функциям таргетолога."""
        # Данные с ролью администратора
        data = {
            "user_role": UserRole.ADMIN.value,
            "db_user": self.admin_user
        }
        
        # Вызываем middleware
        result = await self.middleware(self.handler, self.message, data)
        
        # Проверяем, что обработчик был вызван
        self.handler.assert_called_once_with(self.message, data)
        
        # Проверяем, что сообщение об ошибке не отправлялось
        self.message.answer.assert_not_called()
    
    async def test_targetologist_access_denied(self):
        """Тест запрета доступа для партнера к функциям таргетолога."""
        # Данные с ролью партнера
        data = {
            "user_role": UserRole.PARTNER.value,
            "db_user": self.partner_user
        }
        
        # Вызываем middleware
        result = await self.middleware(self.handler, self.message, data)
        
        # Проверяем, что обработчик не был вызван
        self.handler.assert_not_called()
        
        # Проверяем, что было отправлено сообщение об ошибке
        self.message.answer.assert_called_once()
        self.assertEqual(
            "Эта команда доступна только таргетологам и администраторам",
            self.message.answer.call_args[0][0]
        )


class TestPartnerMiddleware(BaseMiddlewareTest):
    """Тесты для PartnerMiddleware."""
    
    def setUp(self):
        """Настройка тестов."""
        super().setUp()
        self.middleware = PartnerMiddleware()
    
    async def test_partner_access_granted(self):
        """Тест успешного доступа партнера."""
        # Данные с ролью партнера
        data = {
            "user_role": UserRole.PARTNER.value,
            "db_user": self.partner_user
        }
        
        # Вызываем middleware
        result = await self.middleware(self.handler, self.message, data)
        
        # Проверяем, что обработчик был вызван
        self.handler.assert_called_once_with(self.message, data)
        
        # Проверяем, что сообщение об ошибке не отправлялось
        self.message.answer.assert_not_called()
    
    async def test_targetologist_access_to_partner_function(self):
        """Тест доступа таргетолога к функциям партнера."""
        # Данные с ролью таргетолога
        data = {
            "user_role": UserRole.TARGETOLOGIST.value,
            "db_user": self.targetologist_user
        }
        
        # Вызываем middleware
        result = await self.middleware(self.handler, self.message, data)
        
        # Проверяем, что обработчик был вызван
        self.handler.assert_called_once_with(self.message, data)
        
        # Проверяем, что сообщение об ошибке не отправлялось
        self.message.answer.assert_not_called()
    
    async def test_admin_access_to_partner_function(self):
        """Тест доступа администратора к функциям партнера."""
        # Данные с ролью администратора
        data = {
            "user_role": UserRole.ADMIN.value,
            "db_user": self.admin_user
        }
        
        # Вызываем middleware
        result = await self.middleware(self.handler, self.message, data)
        
        # Проверяем, что обработчик был вызван
        self.handler.assert_called_once_with(self.message, data)
        
        # Проверяем, что сообщение об ошибке не отправлялось
        self.message.answer.assert_not_called()
    
    async def test_invalid_role_access_denied(self):
        """Тест запрета доступа для пользователя с недопустимой ролью."""
        # Данные с недопустимой ролью
        data = {
            "user_role": "invalid_role",
            "db_user": self.partner_user
        }
        
        # Вызываем middleware
        result = await self.middleware(self.handler, self.message, data)
        
        # Проверяем, что обработчик не был вызван
        self.handler.assert_not_called()
        
        # Проверяем, что было отправлено сообщение об ошибке
        self.message.answer.assert_called_once()
        self.assertEqual(
            "Доступ запрещен. Свяжитесь с администратором.",
            self.message.answer.call_args[0][0]
        )


class TestCampaignAccessMiddleware(BaseMiddlewareTest):
    """Тесты для CampaignAccessMiddleware."""
    
    def setUp(self):
        """Настройка тестов."""
        super().setUp()
        # Патчим репозиторий контроля доступа
        self.access_control_repo_mock = MagicMock(spec=AccessControlRepository)
        self.patcher = patch(
            'src.middleware.specialized_middleware.AccessControlRepository',
            return_value=self.access_control_repo_mock
        )
        self.access_control_repo_class_mock = self.patcher.start()
        
        # Создаем middleware
        self.middleware = CampaignAccessMiddleware()
    
    def tearDown(self):
        """Очистка после тестов."""
        super().tearDown()
        self.patcher.stop()
    
    async def test_admin_access_to_campaign(self):
        """Тест доступа администратора к кампании."""
        # Данные с ролью администратора и ID кампании
        data = {
            "user_role": UserRole.ADMIN.value,
            "db_user": self.admin_user,
            "campaign_id": "123456789"
        }
        
        # Вызываем middleware
        result = await self.middleware(self.handler, self.message, data)
        
        # Проверяем, что обработчик был вызван
        self.handler.assert_called_once_with(self.message, data)
        
        # Проверяем, что сообщение об ошибке не отправлялось
        self.message.answer.assert_not_called()
        
        # Проверяем, что метод проверки доступа не вызывался (администраторы имеют доступ ко всем кампаниям)
        self.access_control_repo_mock.check_access.assert_not_called()
    
    async def test_targetologist_access_to_campaign(self):
        """Тест доступа таргетолога к кампании."""
        # Данные с ролью таргетолога и ID кампании
        data = {
            "user_role": UserRole.TARGETOLOGIST.value,
            "db_user": self.targetologist_user,
            "campaign_id": "123456789"
        }
        
        # Вызываем middleware
        result = await self.middleware(self.handler, self.message, data)
        
        # Проверяем, что обработчик был вызван
        self.handler.assert_called_once_with(self.message, data)
        
        # Проверяем, что сообщение об ошибке не отправлялось
        self.message.answer.assert_not_called()
        
        # Проверяем, что метод проверки доступа не вызывался (таргетологи имеют доступ ко всем кампаниям)
        self.access_control_repo_mock.check_access.assert_not_called()
    
    async def test_partner_with_access_to_campaign(self):
        """Тест доступа партнера к кампании, к которой у него есть доступ."""
        # Данные с ролью партнера и ID кампании
        data = {
            "user_role": UserRole.PARTNER.value,
            "db_user": self.partner_user,
            "campaign_id": "123456789"
        }
        
        # Настраиваем метод проверки доступа на возврат True
        self.access_control_repo_mock.check_access.return_value = True
        
        # Вызываем middleware
        result = await self.middleware(self.handler, self.message, data)
        
        # Проверяем, что обработчик был вызван
        self.handler.assert_called_once_with(self.message, data)
        
        # Проверяем, что сообщение об ошибке не отправлялось
        self.message.answer.assert_not_called()
        
        # Проверяем, что метод проверки доступа был вызван с правильными параметрами
        self.access_control_repo_mock.check_access.assert_called_once_with(
            user_id=self.partner_user.telegram_id,
            resource_type="campaign",
            resource_id="123456789"
        )
    
    async def test_partner_without_access_to_campaign(self):
        """Тест запрета доступа партнера к кампании, к которой у него нет доступа."""
        # Данные с ролью партнера и ID кампании
        data = {
            "user_role": UserRole.PARTNER.value,
            "db_user": self.partner_user,
            "campaign_id": "123456789"
        }
        
        # Настраиваем метод проверки доступа на возврат False
        self.access_control_repo_mock.check_access.return_value = False
        
        # Вызываем middleware
        result = await self.middleware(self.handler, self.message, data)
        
        # Проверяем, что обработчик не был вызван
        self.handler.assert_not_called()
        
        # Проверяем, что было отправлено сообщение об ошибке
        self.message.answer.assert_called_once()
        self.assertEqual(
            "У вас нет доступа к кампании 123456789",
            self.message.answer.call_args[0][0]
        )
        
        # Проверяем, что метод проверки доступа был вызван с правильными параметрами
        self.access_control_repo_mock.check_access.assert_called_once_with(
            user_id=self.partner_user.telegram_id,
            resource_type="campaign",
            resource_id="123456789"
        )
    
    async def test_campaign_id_extractor(self):
        """Тест использования функции извлечения ID кампании."""
        # Создаем функцию извлечения ID кампании
        def campaign_id_extractor(event, data):
            return "987654321"
        
        # Создаем middleware с функцией извлечения ID
        middleware = CampaignAccessMiddleware(campaign_id_extractor=campaign_id_extractor)
        
        # Данные с ролью партнера без ID кампании
        data = {
            "user_role": UserRole.PARTNER.value,
            "db_user": self.partner_user,
        }
        
        # Настраиваем метод проверки доступа на возврат True
        self.access_control_repo_mock.check_access.return_value = True
        
        # Вызываем middleware
        result = await middleware(self.handler, self.message, data)
        
        # Проверяем, что обработчик был вызван
        self.handler.assert_called_once_with(self.message, data)
        
        # Проверяем, что метод проверки доступа был вызван с правильными параметрами
        self.access_control_repo_mock.check_access.assert_called_once_with(
            user_id=self.partner_user.telegram_id,
            resource_type="campaign",
            resource_id="987654321"
        )
    
    async def test_missing_campaign_id(self):
        """Тест обработки отсутствия ID кампании."""
        # Данные с ролью партнера без ID кампании
        data = {
            "user_role": UserRole.PARTNER.value,
            "db_user": self.partner_user,
        }
        
        # Вызываем middleware
        result = await self.middleware(self.handler, self.message, data)
        
        # Проверяем, что обработчик не был вызван
        self.handler.assert_not_called()
        
        # Проверяем, что было отправлено сообщение об ошибке
        self.message.answer.assert_called_once()
        self.assertEqual(
            "Не указан ID кампании",
            self.message.answer.call_args[0][0]
        )


if __name__ == "__main__":
    unittest.main() 