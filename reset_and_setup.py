#!/usr/bin/env python
"""
Скрипт для полного сброса базы данных и создания пользователя.
Используется для устранения проблемы с "Пользователь не найден в базе данных".
"""
import os
import sys
import shutil
from datetime import datetime

from src.storage.database import init_db, get_session
from src.storage.models import User

# ID пользователя, которого нужно создать (измените на ваш Telegram ID)
USER_ID = 400133981

def backup_database():
    """Сделать резервную копию базы данных, если она существует"""
    if os.path.exists("database.sqlite"):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"database_backup_{timestamp}.sqlite"
        shutil.copy2("database.sqlite", backup_file)
        print(f"Резервная копия базы данных создана: {backup_file}")

def reset_database():
    """Полностью сбросить базу данных"""
    if os.path.exists("database.sqlite"):
        os.remove("database.sqlite")
        print("Существующая база данных удалена.")
    
    print("Инициализация новой базы данных...")
    init_db()
    print("База данных инициализирована.")

def create_user(user_id, first_name="Пользователь бота", username=None):
    """Создать пользователя с указанным ID"""
    print(f"Создание пользователя с ID {user_id}...")
    
    session = get_session()
    try:
        # Проверяем, не существует ли уже пользователь
        existing_user = session.query(User).filter_by(telegram_id=user_id).first()
        if existing_user:
            print(f"Пользователь с ID {user_id} уже существует.")
            return existing_user
        
        # Создаем нового пользователя
        user = User(
            telegram_id=user_id,
            first_name=first_name,
            username=username
        )
        session.add(user)
        session.commit()
        print(f"Пользователь с ID {user_id} успешно создан.")
        
        # Проверяем, что пользователь действительно создан
        created_user = session.query(User).filter_by(telegram_id=user_id).first()
        if created_user:
            print("Проверка успешна: пользователь действительно создан в базе данных.")
        else:
            print("ОШИБКА: Пользователь не найден после создания!")
        
        return user
    finally:
        session.close()

def main():
    """Основная функция скрипта"""
    print("=== Начало сброса базы данных и настройки пользователя ===")
    
    # Запрашиваем подтверждение
    confirm = input("Вы собираетесь полностью сбросить базу данных. Продолжить? (y/n): ")
    if confirm.lower() != 'y':
        print("Операция отменена.")
        return
    
    # Делаем резервную копию базы
    backup_database()
    
    # Сбрасываем базу
    reset_database()
    
    # Спрашиваем ID пользователя
    try:
        user_id_input = input(f"Введите ваш Telegram ID (или нажмите Enter для использования {USER_ID}): ")
        user_id = int(user_id_input) if user_id_input.strip() else USER_ID
    except ValueError:
        print(f"Неверный формат ID. Используем значение по умолчанию: {USER_ID}")
        user_id = USER_ID
    
    # Создаем пользователя
    create_user(user_id)
    
    print("\n=== База данных сброшена и пользователь создан ===")
    print("Теперь выполните следующие шаги:")
    print("1. Запустите бота: python3 main.py")
    print("2. В Telegram отправьте боту команду /start")
    print("3. Затем отправьте /auth и пройдите авторизацию")
    print("4. После успешной авторизации попробуйте /accounts")

if __name__ == "__main__":
    main() 