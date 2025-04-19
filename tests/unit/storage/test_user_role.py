"""
Тесты для функциональности ролей в модели User.
"""
import unittest
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from src.storage.database import Base
from src.storage.models import User
from src.storage.enums import UserRole


class TestUserRoles(unittest.TestCase):
    """Тестирование функциональности ролей в модели User."""
    
    def setUp(self):
        """Настройка тестовой среды."""
        # Создаем временную базу данных в памяти
        self.engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(self.engine)
        
        # Создаем фабрику сессий
        self.SessionFactory = sessionmaker(bind=self.engine)
        self.session = self.SessionFactory()
        
        # Создаем тестовых пользователей с разными ролями
        self.admin_user = User(
            telegram_id=111,
            username="admin_user",
            first_name="Admin",
            last_name="User",
            role=UserRole.ADMIN.value
        )
        
        self.targetologist_user = User(
            telegram_id=222,
            username="target_user",
            first_name="Target",
            last_name="User",
            role=UserRole.TARGETOLOGIST.value
        )
        
        self.partner_user = User(
            telegram_id=333,
            username="partner_user",
            first_name="Partner",
            last_name="User",
            role=UserRole.PARTNER.value
        )
        
        self.invalid_role_user = User(
            telegram_id=444,
            username="invalid_user",
            first_name="Invalid",
            last_name="User",
            role="invalid_role"
        )
        
        # Добавляем пользователей в сессию
        self.session.add(self.admin_user)
        self.session.add(self.targetologist_user)
        self.session.add(self.partner_user)
        self.session.add(self.invalid_role_user)
        self.session.commit()
    
    def tearDown(self):
        """Очистка после тестов."""
        self.session.close()
        Base.metadata.drop_all(self.engine)
    
    def test_default_role(self):
        """Тест роли по умолчанию для нового пользователя."""
        # Создаем нового пользователя и сохраняем в БД, чтобы применилось значение по умолчанию
        new_user = User(telegram_id=555, username="new_user")
        self.session.add(new_user)
        self.session.commit()
        
        # Загружаем пользователя из БД и проверяем роль
        loaded_user = self.session.query(User).filter_by(telegram_id=555).first()
        self.assertEqual(loaded_user.role, UserRole.PARTNER.value)
    
    def test_get_user_role(self):
        """Тест получения роли пользователя как объекта UserRole."""
        self.assertEqual(self.admin_user.get_user_role(), UserRole.ADMIN)
        self.assertEqual(self.targetologist_user.get_user_role(), UserRole.TARGETOLOGIST)
        self.assertEqual(self.partner_user.get_user_role(), UserRole.PARTNER)
        
        # Проверяем, что при неверной роли возвращается PARTNER
        self.assertEqual(self.invalid_role_user.get_user_role(), UserRole.PARTNER)
    
    def test_set_user_role(self):
        """Тест установки роли пользователя."""
        # Установка роли через объект перечисления
        self.partner_user.set_user_role(UserRole.TARGETOLOGIST)
        self.assertEqual(self.partner_user.role, UserRole.TARGETOLOGIST.value)
        
        # Установка роли через строковое значение
        self.partner_user.set_user_role("admin")
        self.assertEqual(self.partner_user.role, UserRole.ADMIN.value)
        
        # Проверяем отказ установки недопустимой роли
        result = self.partner_user.set_user_role("invalid_role")
        self.assertFalse(result)
        self.assertEqual(self.partner_user.role, UserRole.ADMIN.value)  # Роль не должна измениться
    
    def test_is_admin(self):
        """Тест метода is_admin."""
        self.assertTrue(self.admin_user.is_admin())
        self.assertFalse(self.targetologist_user.is_admin())
        self.assertFalse(self.partner_user.is_admin())
    
    def test_is_targetologist(self):
        """Тест метода is_targetologist."""
        self.assertTrue(self.admin_user.is_targetologist())  # Админ имеет права таргетолога
        self.assertTrue(self.targetologist_user.is_targetologist())
        self.assertFalse(self.partner_user.is_targetologist())
    
    def test_is_partner(self):
        """Тест метода is_partner."""
        self.assertTrue(self.admin_user.is_partner())  # Все пользователи имеют права партнера
        self.assertTrue(self.targetologist_user.is_partner())
        self.assertTrue(self.partner_user.is_partner())
    
    def test_has_financial_access(self):
        """Тест метода has_financial_access."""
        self.assertTrue(self.admin_user.has_financial_access())  # Только админ имеет финансовый доступ
        self.assertFalse(self.targetologist_user.has_financial_access())
        self.assertFalse(self.partner_user.has_financial_access())
    
    def test_has_creative_access(self):
        """Тест метода has_creative_access."""
        self.assertTrue(self.admin_user.has_creative_access())  # Админ и таргетолог могут управлять креативами
        self.assertTrue(self.targetologist_user.has_creative_access())
        self.assertFalse(self.partner_user.has_creative_access())
    
    def test_has_permission(self):
        """Тест метода has_permission."""
        # Админ имеет все права
        self.assertTrue(self.admin_user.has_permission(UserRole.ADMIN))
        self.assertTrue(self.admin_user.has_permission(UserRole.TARGETOLOGIST))
        self.assertTrue(self.admin_user.has_permission(UserRole.PARTNER))
        
        # Таргетолог имеет права таргетолога и партнера
        self.assertFalse(self.targetologist_user.has_permission(UserRole.ADMIN))
        self.assertTrue(self.targetologist_user.has_permission(UserRole.TARGETOLOGIST))
        self.assertTrue(self.targetologist_user.has_permission(UserRole.PARTNER))
        
        # Партнер имеет только права партнера
        self.assertFalse(self.partner_user.has_permission(UserRole.ADMIN))
        self.assertFalse(self.partner_user.has_permission(UserRole.TARGETOLOGIST))
        self.assertTrue(self.partner_user.has_permission(UserRole.PARTNER))
    
    def test_saving_and_loading(self):
        """Тест сохранения и загрузки пользователя с ролью."""
        # Создаем нового пользователя с ролью администратора
        new_admin = User(
            telegram_id=666,
            username="new_admin",
            role=UserRole.ADMIN.value
        )
        
        # Сохраняем в базу данных
        self.session.add(new_admin)
        self.session.commit()
        
        # Загружаем из базы данных
        loaded_user = self.session.query(User).filter_by(telegram_id=666).first()
        
        # Проверяем, что роль сохранилась
        self.assertEqual(loaded_user.role, UserRole.ADMIN.value)
        self.assertEqual(loaded_user.get_user_role(), UserRole.ADMIN)
        self.assertTrue(loaded_user.is_admin())
    
    def test_has_campaign_access(self):
        """Тест метода has_campaign_access."""
        # Админ и таргетолог имеют доступ ко всем кампаниям
        self.assertTrue(self.admin_user.has_campaign_access("any_campaign_id"))
        self.assertTrue(self.targetologist_user.has_campaign_access("any_campaign_id"))
        
        # Партнер по умолчанию не имеет доступа (пока не реализована проверка в AccessControlRepository)
        self.assertFalse(self.partner_user.has_campaign_access("any_campaign_id"))


if __name__ == '__main__':
    unittest.main() 