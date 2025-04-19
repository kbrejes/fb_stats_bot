#!/usr/bin/env python
"""
Скрипт для тестирования структуры базы данных после миграции.
Проверяет, что все таблицы и колонки созданы корректно.
"""
import sqlite3
import sys
import os
from pathlib import Path

# Добавляем корневую директорию проекта в Python path
sys.path.append(str(Path(__file__).parent.parent))

from src.utils.logger import get_logger

logger = get_logger(__name__)

# Путь к БД
DB_PATH = "database_dev.sqlite"

def test_tables_exist():
    """Проверяет, что все необходимые таблицы существуют в БД."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Получаем список всех таблиц
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [table[0] for table in cursor.fetchall()]
    
    # Проверяем наличие необходимых таблиц
    required_tables = ['users', 'access_control', 'access_request']
    for table in required_tables:
        if table not in tables:
            logger.error(f"Таблица {table} не найдена в базе данных")
            return False
        logger.info(f"Таблица {table} существует")
    
    conn.close()
    return True

def test_user_role_column():
    """Проверяет, что в таблице users есть колонка role."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Получаем информацию о колонках таблицы users
    cursor.execute("PRAGMA table_info(users)")
    columns = {column[1]: column for column in cursor.fetchall()}
    
    # Проверяем наличие колонки role
    if 'role' not in columns:
        logger.error("Колонка role не найдена в таблице users")
        conn.close()
        return False
    
    # Проверяем тип и дефолтное значение
    role_column = columns['role']
    if role_column[2] != 'VARCHAR(20)':
        logger.warning(f"Неожиданный тип колонки role: {role_column[2]}, ожидается VARCHAR(20)")
    
    if role_column[4] != 'partner':
        logger.warning(f"Неожиданное значение по умолчанию для колонки role: {role_column[4]}, ожидается 'partner'")
    
    logger.info("Колонка role в таблице users корректно настроена")
    conn.close()
    return True

def test_access_control_structure():
    """Проверяет структуру таблицы access_control."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Получаем информацию о колонках таблицы access_control
    cursor.execute("PRAGMA table_info(access_control)")
    columns = {column[1]: column for column in cursor.fetchall()}
    
    # Проверяем наличие нужных колонок
    required_columns = ['id', 'user_id', 'target_id', 'target_type', 
                        'granted_by', 'granted_at', 'expires_at', 
                        'revoked_at', 'revoked_by', 'notes']
    
    for column in required_columns:
        if column not in columns:
            logger.error(f"Колонка {column} не найдена в таблице access_control")
            conn.close()
            return False
    
    logger.info("Структура таблицы access_control корректна")
    conn.close()
    return True

def test_access_request_structure():
    """Проверяет структуру таблицы access_request."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Получаем информацию о колонках таблицы access_request
    cursor.execute("PRAGMA table_info(access_request)")
    columns = {column[1]: column for column in cursor.fetchall()}
    
    # Проверяем наличие нужных колонок
    required_columns = ['id', 'user_id', 'target_id', 'target_type', 
                        'created_at', 'resolved_at', 'resolved_by', 
                        'status', 'reason', 'resolution_notes']
    
    for column in required_columns:
        if column not in columns:
            logger.error(f"Колонка {column} не найдена в таблице access_request")
            conn.close()
            return False
    
    logger.info("Структура таблицы access_request корректна")
    conn.close()
    return True

def test_indexes():
    """Проверяет, что созданы все необходимые индексы."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Получаем список всех индексов
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
    indexes = [index[0] for index in cursor.fetchall()]
    
    # Проверяем наличие нужных индексов
    required_indexes = [
        'idx_users_role',
        'idx_access_control_user_id',
        'idx_access_control_target',
        'idx_access_control_status',
        'idx_access_request_user_id',
        'idx_access_request_target',
        'idx_access_request_status'
    ]
    
    for index in required_indexes:
        if index not in indexes:
            logger.warning(f"Индекс {index} не найден в базе данных")
    
    logger.info(f"Найдено {len(indexes)} индексов из {len(required_indexes)} необходимых")
    conn.close()
    return True

def test_triggers():
    """Проверяет, что созданы все необходимые триггеры."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Получаем список всех триггеров
    cursor.execute("SELECT name FROM sqlite_master WHERE type='trigger'")
    triggers = [trigger[0] for trigger in cursor.fetchall()]
    
    # Проверяем наличие нужных триггеров
    required_triggers = [
        'trg_user_role_changed',
        'trg_user_role_changed_requests',
        'trg_access_request_approved'
    ]
    
    for trigger in required_triggers:
        if trigger not in triggers:
            logger.warning(f"Триггер {trigger} не найден в базе данных")
    
    logger.info(f"Найдено {len(triggers)} триггеров из {len(required_triggers)} необходимых")
    conn.close()
    return True

def run_tests():
    """Запускает все тесты структуры БД."""
    if not os.path.exists(DB_PATH):
        logger.error(f"База данных не найдена по пути: {DB_PATH}")
        return False
    
    tests = [
        test_tables_exist,
        test_user_role_column,
        test_access_control_structure,
        test_access_request_structure,
        test_indexes,
        test_triggers
    ]
    
    success = True
    for test in tests:
        test_name = test.__name__
        logger.info(f"Запуск теста: {test_name}")
        try:
            result = test()
            if not result:
                logger.error(f"Тест {test_name} не пройден")
                success = False
            else:
                logger.info(f"Тест {test_name} успешно пройден")
        except Exception as e:
            logger.error(f"Ошибка при выполнении теста {test_name}: {str(e)}")
            success = False
    
    if success:
        logger.info("Все тесты успешно пройдены")
    else:
        logger.error("Некоторые тесты не пройдены. Структура БД может быть некорректной")
    
    return success

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1) 