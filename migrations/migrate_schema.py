#!/usr/bin/env python
"""
Скрипт для миграции схемы базы данных.
Выполняет SQL-скрипты из директории migrations/sql в порядке их номеров.
"""
import sqlite3
import os
import sys
import shutil
import argparse
from datetime import datetime
from pathlib import Path

# Добавляем корневую директорию проекта в Python path
sys.path.append(str(Path(__file__).parent.parent))

from src.utils.logger import get_logger

logger = get_logger(__name__)

# Путь к БД
DB_PATH = "database_dev.sqlite"
SQL_DIR = os.path.join(os.path.dirname(__file__), "sql")

def backup_database():
    """Создаёт резервную копию базы данных перед миграцией."""
    if not os.path.exists(DB_PATH):
        logger.warning(f"База данных не найдена по пути: {DB_PATH}, копия не создана")
        return None
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"database_backup_{timestamp}.sqlite"
    
    try:
        shutil.copy2(DB_PATH, backup_file)
        logger.info(f"Резервная копия базы данных создана: {backup_file}")
        return backup_file
    except Exception as e:
        logger.error(f"Не удалось создать резервную копию базы данных: {str(e)}")
        return None

def execute_sql_file(conn, file_path):
    """Выполняет SQL-скрипт из файла."""
    with open(file_path, 'r') as f:
        sql = f.read()
    
    cursor = conn.cursor()
    try:
        cursor.executescript(sql)
        conn.commit()
        logger.info(f"SQL-скрипт {os.path.basename(file_path)} успешно выполнен")
        return True
    except sqlite3.Error as e:
        logger.error(f"Ошибка при выполнении SQL-скрипта {os.path.basename(file_path)}: {str(e)}")
        conn.rollback()
        return False

def get_sql_files():
    """Получает список SQL-файлов миграции, отсортированных по номеру."""
    if not os.path.exists(SQL_DIR):
        logger.error(f"Директория с SQL-скриптами не найдена: {SQL_DIR}")
        return []
    
    files = [f for f in os.listdir(SQL_DIR) if f.endswith('.sql') and f[0].isdigit()]
    files.sort(key=lambda f: int(f.split('_')[0]))
    
    return [os.path.join(SQL_DIR, f) for f in files]

def migrate_db(args):
    """Выполняет миграцию базы данных."""
    backup_file = backup_database()
    
    # Проверяем готовность к миграции
    if not args.force and not backup_file:
        logger.error("Миграция отменена: не удалось создать резервную копию и не указан флаг --force")
        return False
    
    sql_files = get_sql_files()
    if not sql_files:
        logger.error("Миграция отменена: не найдены SQL-скрипты миграции")
        return False
    
    logger.info(f"Найдено {len(sql_files)} SQL-скриптов для выполнения")
    
    # Выполняем миграцию
    success = True
    conn = sqlite3.connect(DB_PATH)
    
    for file_path in sql_files:
        file_name = os.path.basename(file_path)
        logger.info(f"Выполнение SQL-скрипта: {file_name}")
        
        if not execute_sql_file(conn, file_path):
            success = False
            if not args.continue_on_error:
                logger.error(f"Миграция прервана при выполнении {file_name}")
                break
    
    conn.close()
    
    # Проверяем результат миграции
    if success:
        logger.info("Миграция успешно завершена")
    else:
        logger.error("Миграция завершилась с ошибками")
        
        if backup_file and args.rollback_on_error:
            logger.info(f"Восстановление из резервной копии: {backup_file}")
            try:
                shutil.copy2(backup_file, DB_PATH)
                logger.info("База данных успешно восстановлена из резервной копии")
            except Exception as e:
                logger.error(f"Не удалось восстановить базу данных: {str(e)}")
    
    return success

def parse_arguments():
    """Парсит аргументы командной строки."""
    parser = argparse.ArgumentParser(description="Миграция схемы базы данных")
    parser.add_argument("--force", action="store_true", help="Выполнить миграцию, даже если не удалось создать резервную копию")
    parser.add_argument("--continue-on-error", action="store_true", help="Продолжить выполнение скриптов, даже если один из них завершился с ошибкой")
    parser.add_argument("--rollback-on-error", action="store_true", help="Восстановить БД из резервной копии в случае ошибки")
    
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_arguments()
    success = migrate_db(args)
    sys.exit(0 if success else 1) 