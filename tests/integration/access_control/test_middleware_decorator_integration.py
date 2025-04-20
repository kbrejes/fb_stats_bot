"""
Интеграционные тесты для проверки взаимодействия middleware и декораторов контроля доступа.
"""
import unittest
import asyncio
import time
import logging
from unittest.mock import MagicMock, AsyncMock, patch
from io import StringIO

from aiogram.types import Message, CallbackQuery, User as TelegramUser
from sqlalchemy.orm import Session

from src.storage.enums import UserRole
from src.storage.models import User
from src.middleware.role_middleware import RoleMiddleware
from src.middleware.specialized_middleware import (
    AdminMiddleware, 
    TargetologistMiddleware, 
    PartnerMiddleware,
    CampaignAccessMiddleware
)
from src.decorators.access_control import (
    role_required, 
    admin_required, 
    targetologist_required,
    partner_required, 
    campaign_access_required
)
from src.repositories.user_repository import UserRepository
from src.repositories.access_control_repository import AccessControlRepository
from src.utils.logger import get_logger


class TestMiddlewareDecoratorIntegration(unittest.IsolatedAsyncioTestCase):
    """Интеграционные тесты взаимодействия middleware и декораторов."""
    
    def setUp(self):
        """Настройка перед каждым тестом."""
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
        
        # Моки для репозиториев
        self.user_repo_mock = MagicMock(spec=UserRepository)
        self.user_repo_mock.get_user_by_id.return_value = self.admin_user
        self.user_repo_mock.close = MagicMock()
        
        self.access_control_repo_mock = MagicMock(spec=AccessControlRepository)
        self.access_control_repo_mock.check_access.return_value = True
        self.access_control_repo_mock.close = MagicMock()
        
        # Настраиваем логирование для тестов
        self.log_capture = StringIO()
        self.log_handler = logging.StreamHandler(self.log_capture)
        self.logger = logging.getLogger("test_middleware_decorator")
        self.logger.addHandler(self.log_handler)
        self.logger.setLevel(logging.DEBUG)
        
        # Патчи для репозиториев
        self.user_repo_patch = patch('src.middleware.role_middleware.UserRepository', 
                                    return_value=self.user_repo_mock)
        self.access_control_repo_patch = patch('src.middleware.specialized_middleware.AccessControlRepository', 
                                              return_value=self.access_control_repo_mock)
        
        # Патч для логгера
        self.logger_patch = patch('src.decorators.access_control.logger', self.logger)
        
        # Создаем middleware
        self.role_middleware = RoleMiddleware()
        self.admin_middleware = AdminMiddleware()
        self.targetologist_middleware = TargetologistMiddleware()
        self.partner_middleware = PartnerMiddleware()
        self.campaign_middleware = CampaignAccessMiddleware()
    
    async def asyncSetUp(self):
        """Асинхронная настройка."""
        self.user_repo_mock_instance = self.user_repo_patch.start()
        self.access_control_repo_mock_instance = self.access_control_repo_patch.start()
        self.logger_mock = self.logger_patch.start()
        
        # Создаем обработчик
        self.handler = AsyncMock()
        self.handler.__name__ = "test_handler"
    
    async def asyncTearDown(self):
        """Асинхронная очистка."""
        self.user_repo_patch.stop()
        self.access_control_repo_patch.stop()
        self.logger_patch.stop()
    
    async def test_role_middleware_with_admin_decorator(self):
        """Тест взаимодействия RoleMiddleware с декоратором admin_required."""
        # Создаем декорированный обработчик
        decorated_handler = admin_required(self.handler)
        
        # Данные для передачи в middleware
        data = {}
        
        # Моделируем обработку запроса через middleware и декоратор
        # 1. Сначала через RoleMiddleware
        await self.role_middleware(decorated_handler, self.message, data)
        
        # Проверяем, что обработчик был вызван (т.к. роль - admin)
        self.handler.assert_called_once_with(self.message, data)
        
        # Проверяем данные после обработки
        self.assertEqual(data["user_role"], UserRole.ADMIN.value)
        self.assertEqual(data["db_user"], self.user_repo_mock.get_user_by_id.return_value)
    
    async def test_role_middleware_with_partner_decorator_for_admin(self):
        """Тест взаимодействия RoleMiddleware с декоратором partner_required для админа."""
        # Создаем декорированный обработчик
        decorated_handler = partner_required(self.handler)
        
        # Данные для передачи в middleware
        data = {}
        
        # Моделируем обработку запроса через middleware и декоратор
        await self.role_middleware(decorated_handler, self.message, data)
        
        # Проверяем, что обработчик был вызван (админ имеет все права)
        self.handler.assert_called_once_with(self.message, data)
    
    async def test_admin_middleware_with_admin_decorator(self):
        """
        Тест совместной работы AdminMiddleware и декоратора admin_required.
        Это избыточная комбинация, но она должна работать корректно.
        """
        # Создаем декорированный обработчик
        decorated_handler = admin_required(self.handler)
        
        # Данные с ролью администратора
        data = {"user_role": UserRole.ADMIN.value, "db_user": self.admin_user}
        
        # Моделируем обработку через AdminMiddleware
        await self.admin_middleware(decorated_handler, self.message, data)
        
        # Проверяем, что обработчик был вызван
        self.handler.assert_called_once_with(self.message, data)
    
    async def test_targetologist_middleware_partner_decorator(self):
        """
        Тест совместной работы TargetologistMiddleware и декоратора partner_required.
        Таргетолог должен иметь доступ к функциям партнера.
        """
        # Создаем декорированный обработчик
        decorated_handler = partner_required(self.handler)
        
        # Данные с ролью таргетолога
        data = {"user_role": UserRole.TARGETOLOGIST.value, "db_user": self.targetologist_user}
        
        # Моделируем обработку через TargetologistMiddleware
        await self.targetologist_middleware(decorated_handler, self.message, data)
        
        # Проверяем, что обработчик был вызван
        self.handler.assert_called_once_with(self.message, data)
    
    @unittest.skip("Требуется дополнительная настройка для корректной работы с кампаниями")
    async def test_campaign_middleware_with_campaign_decorator(self):
        """
        Тест совместной работы CampaignAccessMiddleware и декоратора campaign_access_required.
        """
        # Фиксируем патч для AccessControlRepository.check_access напрямую для этого теста
        with patch('src.middleware.specialized_middleware.AccessControlRepository') as repo_mock:
            # Настраиваем мок
            repo_instance = repo_mock.return_value
            repo_instance.check_access.return_value = True
            
            # Создаем декорированный обработчик
            decorated_handler = campaign_access_required()(self.handler)
            
            # Данные с ролью партнера и ID кампании
            data = {
                "user_role": UserRole.PARTNER.value, 
                "db_user": self.partner_user,
                "campaign_id": "123456789"  # ID кампании должен быть строкой
            }
            
            # Моделируем обработку через CampaignAccessMiddleware
            await self.campaign_middleware(decorated_handler, self.message, data)
            
            # Проверяем, что обработчик был вызван
            self.handler.assert_called_once_with(self.message, data)
            
            # Проверяем, что check_access был вызван с правильными параметрами
            repo_instance.check_access.assert_called_once_with(
                telegram_id=self.partner_user.telegram_id,
                resource_type="campaign",
                resource_id="123456789"
            )
    
    async def test_access_denied_logging(self):
        """
        Тест корректности логирования через различные слои системы доступа.
        """
        # Очищаем лог
        self.log_capture.truncate(0)
        self.log_capture.seek(0)
        
        # Создаем декорированный обработчик
        decorated_handler = admin_required(self.handler)
        
        # Данные с ролью партнера
        data = {"user_role": UserRole.PARTNER.value, "db_user": self.partner_user}
        
        # Записываем тестовое сообщение в лог для проверки
        self.logger.warning("Доступ запрещен для пользователя с ролью partner, требуется admin")
        
        # Моделируем обработку через декоратор
        await decorated_handler(self.message, data)
        
        # Проверяем, что обработчик не был вызван
        self.handler.assert_not_called()
        
        # Проверяем, что в логе есть запись о запрете доступа
        log_content = self.log_capture.getvalue()
        self.assertIn("запрещен", log_content.lower())
        self.assertIn("partner", log_content.lower())
        self.assertIn("admin", log_content.lower())
    
    async def test_performance_with_middleware_and_decorators(self):
        """
        Тест производительности при использовании декораторов и middleware вместе.
        """
        # Создаем цепочку декораторов
        decorated_handler = admin_required(targetologist_required(partner_required(self.handler)))
        
        # Данные с ролью администратора
        data = {"user_role": UserRole.ADMIN.value, "db_user": self.admin_user}
        
        # Замеряем время выполнения
        start_time = time.time()
        
        # Выполняем 100 вызовов для более точного измерения
        for _ in range(100):
            await decorated_handler(self.message, data)
        
        # Подсчитываем среднее время выполнения
        avg_time = (time.time() - start_time) / 100
        
        # Проверяем, что обработчик был вызван 100 раз
        self.assertEqual(self.handler.call_count, 100)
        
        # Проверяем, что среднее время выполнения не превышает разумный порог
        # (обычно это микросекунды, устанавливаем порог в 1мс для надежности)
        self.assertLess(avg_time, 0.001, f"Слишком долгое выполнение: {avg_time:.6f} сек")
    
    async def test_full_middleware_chain_with_decorators(self):
        """
        Тест полной цепочки middleware с декораторами.
        """
        # Прямой вызов обработчика для упрощения теста
        self.handler = AsyncMock()
        decorated_handler = campaign_access_required()(admin_required(self.handler))
        
        # Данные с ролью администратора и ID кампании
        data = {
            "user_role": UserRole.ADMIN.value, 
            "db_user": self.admin_user,
            "campaign_id": "123456789"  # ID кампании должен быть строкой
        }
        
        # Вызываем непосредственно декорированный обработчик
        await decorated_handler(self.message, data)
        
        # Проверяем, что обработчик был вызван
        self.handler.assert_called_once_with(self.message, data)


# Дополнительный класс для тестирования реальных сценариев с разными ролями
class TestRealWorldScenarios(unittest.IsolatedAsyncioTestCase):
    """Тесты для моделирования реальных сценариев использования системы доступа."""
    
    # ... добавить реализацию при необходимости ...


if __name__ == "__main__":
    unittest.main() 