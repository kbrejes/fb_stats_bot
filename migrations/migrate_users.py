#!/usr/bin/env python
"""
Скрипт для миграции данных пользователей.
Выполняет присвоение ролей пользователям на основе конфигурации.
"""
import sqlite3
import os
import sys
import argparse
import json
import logging
from datetime import datetime
from pathlib import Path

# Добавляем корневую директорию проекта в Python path
sys.path.append(str(Path(__file__).parent.parent))

from src.utils.logger import get_logger

logger = get_logger(__name__)

# Путь к БД
DB_PATH = "database_dev.sqlite"

# Путь к файлу лога миграции
LOG_FILE = f"user_migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

class UserMigration:
    """Класс для миграции данных пользователей."""
    
    def __init__(self, db_path, config_path=None, log_file=LOG_FILE):
        self.db_path = db_path
        self.config_path = config_path
        self.log_file = log_file
        
        # Настраиваем логирование в файл
        self.file_handler = logging.FileHandler(log_file)
        self.file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        logger.addHandler(self.file_handler)
        
        # Загружаем конфигурацию
        self.config = self._load_config()
        
        # Подключаемся к БД
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
    
    def _load_config(self):
        """Загружает конфигурацию из файла или использует значения по умолчанию."""
        default_config = {
            "admin_ids": [],
            "targetologist_ids": []
        }
        
        if not self.config_path:
            logger.info("Файл конфигурации не указан, используются значения по умолчанию.")
            return default_config
        
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                logger.info(f"Конфигурация загружена из {self.config_path}")
                return config
        except Exception as e:
            logger.error(f"Ошибка при загрузке конфигурации: {str(e)}")
            return default_config
    
    def _get_all_users(self):
        """Получает список всех пользователей из базы данных."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT telegram_id, username, role FROM users")
        return cursor.fetchall()
    
    def _update_user_role(self, telegram_id, role):
        """Обновляет роль пользователя."""
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                "UPDATE users SET role = ? WHERE telegram_id = ?",
                (role, telegram_id)
            )
            self.conn.commit()
            logger.info(f"Пользователю {telegram_id} установлена роль {role}")
            return True
        except sqlite3.Error as e:
            logger.error(f"Ошибка при обновлении роли пользователя {telegram_id}: {str(e)}")
            self.conn.rollback()
            return False
    
    def migrate_all_to_partner(self):
        """Присваивает роль 'partner' всем пользователям, у которых не установлена роль."""
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                "UPDATE users SET role = 'partner' WHERE role IS NULL OR role = ''"
            )
            affected = cursor.rowcount
            self.conn.commit()
            logger.info(f"Роль 'partner' установлена для {affected} пользователей")
            return affected
        except sqlite3.Error as e:
            logger.error(f"Ошибка при установке роли 'partner': {str(e)}")
            self.conn.rollback()
            return 0
    
    def set_admins(self):
        """Устанавливает роль 'admin' для пользователей из списка администраторов."""
        admin_ids = self.config.get("admin_ids", [])
        if not admin_ids:
            logger.warning("Список администраторов пуст")
            return 0
        
        set_count = 0
        for admin_id in admin_ids:
            if self._update_user_role(admin_id, 'admin'):
                set_count += 1
        
        logger.info(f"Роль 'admin' установлена для {set_count} пользователей из {len(admin_ids)}")
        return set_count
    
    def set_targetologists(self):
        """Устанавливает роль 'targetologist' для пользователей из списка таргетологов."""
        targetologist_ids = self.config.get("targetologist_ids", [])
        if not targetologist_ids:
            logger.warning("Список таргетологов пуст")
            return 0
        
        set_count = 0
        for targetologist_id in targetologist_ids:
            if self._update_user_role(targetologist_id, 'targetologist'):
                set_count += 1
        
        logger.info(f"Роль 'targetologist' установлена для {set_count} пользователей из {len(targetologist_ids)}")
        return set_count
    
    def verify_migration(self):
        """Проверяет корректность миграции данных."""
        users = self._get_all_users()
        admin_ids = self.config.get("admin_ids", [])
        targetologist_ids = self.config.get("targetologist_ids", [])
        
        errors = 0
        
        # Проверяем, что все пользователи имеют роль
        for user in users:
            if not user['role'] or user['role'] == '':
                logger.error(f"Пользователь {user['telegram_id']} не имеет роли")
                errors += 1
        
        # Проверяем, что все администраторы установлены корректно
        for admin_id in admin_ids:
            found = False
            for user in users:
                if user['telegram_id'] == admin_id:
                    found = True
                    if user['role'] != 'admin':
                        logger.error(f"Пользователь {admin_id} должен иметь роль 'admin', но имеет роль '{user['role']}'")
                        errors += 1
                    break
            
            if not found:
                logger.warning(f"Администратор {admin_id} не найден в базе данных")
        
        # Проверяем, что все таргетологи установлены корректно
        for targetologist_id in targetologist_ids:
            found = False
            for user in users:
                if user['telegram_id'] == targetologist_id:
                    found = True
                    if user['role'] != 'targetologist':
                        logger.error(f"Пользователь {targetologist_id} должен иметь роль 'targetologist', но имеет роль '{user['role']}'")
                        errors += 1
                    break
            
            if not found:
                logger.warning(f"Таргетолог {targetologist_id} не найден в базе данных")
        
        if errors == 0:
            logger.info("Верификация миграции данных успешно завершена")
            return True
        else:
            logger.error(f"Верификация миграции данных завершена с {errors} ошибками")
            return False
    
    def run_migration(self):
        """Выполняет миграцию данных пользователей."""
        logger.info("Начало миграции данных пользователей")
        
        # Присваиваем всем пользователям роль "partner" по умолчанию
        self.migrate_all_to_partner()
        
        # Устанавливаем администраторов
        self.set_admins()
        
        # Устанавливаем таргетологов
        self.set_targetologists()
        
        # Проверяем результаты миграции
        success = self.verify_migration()
        
        logger.info("Миграция данных пользователей завершена")
        return success
    
    def close(self):
        """Закрывает соединение с БД и завершает логирование."""
        self.conn.close()
        logger.removeHandler(self.file_handler)
        logger.info(f"Лог миграции сохранен в файле: {self.log_file}")

def parse_arguments():
    """Парсит аргументы командной строки."""
    parser = argparse.ArgumentParser(description="Миграция данных пользователей")
    parser.add_argument(
        "--config", "-c",
        help="Путь к файлу конфигурации с ID администраторов и таргетологов"
    )
    parser.add_argument(
        "--db", "-d",
        default=DB_PATH,
        help=f"Путь к базе данных (по умолчанию: {DB_PATH})"
    )
    parser.add_argument(
        "--verify-only", "-v",
        action="store_true",
        help="Только проверить корректность миграции без внесения изменений"
    )
    
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_arguments()
    
    migration = UserMigration(args.db, args.config)
    
    try:
        if args.verify_only:
            success = migration.verify_migration()
        else:
            success = migration.run_migration()
        
        sys.exit(0 if success else 1)
    finally:
        migration.close() 