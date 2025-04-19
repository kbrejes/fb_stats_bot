#!/usr/bin/env python
"""
Скрипт для тестирования миграции данных пользователей.
Проверяет корректность присвоения ролей пользователям.
"""
import sqlite3
import sys
import os
import json
import tempfile
import unittest
from pathlib import Path

# Добавляем корневую директорию проекта в Python path
sys.path.append(str(Path(__file__).parent.parent))

from src.utils.logger import get_logger
from migrations.migrate_users import UserMigration

logger = get_logger(__name__)

class TestUserMigration(unittest.TestCase):
    """Тесты для миграции данных пользователей."""
    
    def setUp(self):
        """Подготовка тестовой среды."""
        # Создаем временную БД для тестов
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.sqlite')
        self.temp_db.close()
        
        # Создаем тестовую конфигурацию
        self.test_config = {
            "admin_ids": [111, 222],
            "targetologist_ids": [333, 444]
        }
        
        self.temp_config = tempfile.NamedTemporaryFile(delete=False, suffix='.json', mode='w')
        json.dump(self.test_config, self.temp_config)
        self.temp_config.close()
        
        # Создаем тестовые таблицы
        conn = sqlite3.connect(self.temp_db.name)
        cursor = conn.cursor()
        
        # Создаем таблицу users БЕЗ ограничения NOT NULL для поля role
        cursor.execute('''
        CREATE TABLE users (
            telegram_id INTEGER PRIMARY KEY,
            username VARCHAR(255),
            first_name VARCHAR(255),
            last_name VARCHAR(255),
            role VARCHAR(20) DEFAULT 'partner'
        )
        ''')
        
        # Добавляем тестовых пользователей
        test_users = [
            (111, 'admin1', 'Admin', 'One', ''),    # Будущий админ с пустой ролью
            (222, 'admin2', 'Admin', 'Two', 'partner'),  # Будущий админ с ролью partner
            (333, 'target1', 'Target', 'One', ''),   # Будущий таргетолог с пустой ролью
            (444, 'target2', 'Target', 'Two', 'admin'),  # Будущий таргетолог с ролью admin
            (555, 'user1', 'User', 'One', ''),      # Обычный пользователь с пустой ролью
            (666, 'user2', 'User', 'Two', 'partner')   # Обычный пользователь с ролью partner
        ]
        
        cursor.executemany('''
        INSERT INTO users (telegram_id, username, first_name, last_name, role)
        VALUES (?, ?, ?, ?, ?)
        ''', test_users)
        
        conn.commit()
        conn.close()
        
        # Создаем временный файл для лога
        self.temp_log = tempfile.NamedTemporaryFile(delete=False, suffix='.log')
        self.temp_log.close()
        
        # Инициализируем объект миграции
        self.migration = UserMigration(
            db_path=self.temp_db.name,
            config_path=self.temp_config.name,
            log_file=self.temp_log.name
        )
    
    def tearDown(self):
        """Очистка после тестов."""
        self.migration.close()
        
        # Удаляем временные файлы
        os.unlink(self.temp_db.name)
        os.unlink(self.temp_config.name)
        os.unlink(self.temp_log.name)
    
    def test_migrate_all_to_partner(self):
        """Тест присвоения роли 'partner' всем пользователям без роли."""
        # Проверяем начальное состояние
        conn = sqlite3.connect(self.temp_db.name)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE role = ''")
        empty_roles_before = cursor.fetchone()[0]
        self.assertEqual(empty_roles_before, 3, "Должно быть 3 пользователя с пустой ролью")
        
        # Выполняем миграцию
        affected = self.migration.migrate_all_to_partner()
        self.assertEqual(affected, 3, "Должно быть обновлено 3 пользователя")
        
        # Проверяем результат
        cursor.execute("SELECT COUNT(*) FROM users WHERE role = ''")
        empty_roles_after = cursor.fetchone()[0]
        self.assertEqual(empty_roles_after, 0, "После миграции не должно быть пользователей с пустой ролью")
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'partner'")
        partner_roles = cursor.fetchone()[0]
        self.assertEqual(partner_roles, 5, "Должно быть 5 пользователей с ролью 'partner'")
        
        conn.close()
    
    def test_set_admins(self):
        """Тест установки роли 'admin' для администраторов."""
        # Выполняем миграцию
        affected = self.migration.set_admins()
        self.assertEqual(affected, 2, "Должно быть обновлено 2 пользователя-администратора")
        
        # Проверяем результат
        conn = sqlite3.connect(self.temp_db.name)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
        admin_count = cursor.fetchone()[0]
        self.assertEqual(admin_count, 3, "Должно быть 3 пользователя с ролью 'admin' (2 новых + 1 существующий)")
        
        for admin_id in self.test_config["admin_ids"]:
            cursor.execute("SELECT role FROM users WHERE telegram_id = ?", (admin_id,))
            role = cursor.fetchone()['role']
            self.assertEqual(role, 'admin', f"Пользователь {admin_id} должен иметь роль 'admin'")
        
        conn.close()
    
    def test_set_targetologists(self):
        """Тест установки роли 'targetologist' для таргетологов."""
        # Выполняем миграцию
        affected = self.migration.set_targetologists()
        self.assertEqual(affected, 2, "Должно быть обновлено 2 пользователя-таргетолога")
        
        # Проверяем результат
        conn = sqlite3.connect(self.temp_db.name)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'targetologist'")
        targetologist_count = cursor.fetchone()[0]
        self.assertEqual(targetologist_count, 2, "Должно быть 2 пользователя с ролью 'targetologist'")
        
        for targetologist_id in self.test_config["targetologist_ids"]:
            cursor.execute("SELECT role FROM users WHERE telegram_id = ?", (targetologist_id,))
            role = cursor.fetchone()['role']
            self.assertEqual(role, 'targetologist', f"Пользователь {targetologist_id} должен иметь роль 'targetologist'")
        
        conn.close()
    
    def test_full_migration(self):
        """Тест полной миграции данных."""
        # Выполняем полную миграцию
        success = self.migration.run_migration()
        self.assertTrue(success, "Миграция должна завершиться успешно")
        
        # Проверяем результат
        conn = sqlite3.connect(self.temp_db.name)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Все пользователи должны иметь роль
        cursor.execute("SELECT COUNT(*) FROM users WHERE role = ''")
        empty_roles = cursor.fetchone()[0]
        self.assertEqual(empty_roles, 0, "После миграции не должно быть пользователей с пустой ролью")
        
        # Проверяем количество пользователей с разными ролями
        cursor.execute("SELECT role, COUNT(*) as count FROM users GROUP BY role")
        role_counts = {row['role']: row['count'] for row in cursor.fetchall()}
        
        expected_counts = {
            'admin': 2,  # Два администратора из конфигурации
            'targetologist': 2,  # Два таргетолога из конфигурации
            'partner': 2  # Два обычных пользователя
        }
        
        for role, expected_count in expected_counts.items():
            self.assertEqual(role_counts.get(role, 0), expected_count, f"Должно быть {expected_count} пользователей с ролью '{role}'")
        
        conn.close()
    
    def test_verify_migration(self):
        """Тест верификации миграции."""
        # Сначала выполняем полную миграцию
        self.migration.run_migration()
        
        # Проверяем верификацию
        success = self.migration.verify_migration()
        self.assertTrue(success, "Верификация должна быть успешной после полной миграции")
        
        # Портим данные и проверяем, что верификация обнаружит проблему
        conn = sqlite3.connect(self.temp_db.name)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET role = '' WHERE telegram_id = 111")  # Портим роль администратора
        conn.commit()
        conn.close()
        
        # Проверяем верификацию с испорченными данными
        success = self.migration.verify_migration()
        self.assertFalse(success, "Верификация должна обнаружить испорченные данные")

if __name__ == "__main__":
    unittest.main() 