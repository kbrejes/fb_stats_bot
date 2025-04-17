#!/usr/bin/env python
"""
Скрипт для исправления проблемы с пользователем
"""
import os
import sys
from sqlalchemy import inspect

from src.storage.database import get_session, init_db
from src.storage.models import User
from src.utils.logger import get_logger

logger = get_logger(__name__)

def create_user_direct(telegram_id, username=None, first_name=None, last_name=None):
    """Создать пользователя напрямую"""
    print(f"Создаем пользователя с ID {telegram_id}...")
    
    session = get_session()
    try:
        # Проверяем, существует ли пользователь
        user = session.query(User).filter_by(telegram_id=telegram_id).first()
        
        if user:
            print(f"Пользователь с ID {telegram_id} уже существует")
            print(f"Имя: {user.first_name or 'Не указано'}")
            print(f"Токен установлен: {'Да' if user.fb_access_token else 'Нет'}")
            
            # Спросим, хочет ли пользователь обновить данные
            update = input("Обновить данные пользователя? (y/n): ").lower() == 'y'
            if update:
                if first_name:
                    user.first_name = first_name
                if last_name:
                    user.last_name = last_name
                if username:
                    user.username = username
                session.commit()
                print("Данные пользователя обновлены")
        else:
            # Создаем нового пользователя
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name
            )
            session.add(user)
            session.commit()
            print(f"Пользователь с ID {telegram_id} успешно создан")
    finally:
        session.close()

def list_users():
    """Вывести список пользователей"""
    print("\nСписок всех пользователей в базе данных:")
    
    session = get_session()
    try:
        users = session.query(User).all()
        
        if not users:
            print("Пользователей в базе данных нет")
            return
        
        for user in users:
            print(f"ID: {user.telegram_id}, Имя: {user.first_name or 'Не указано'}")
    finally:
        session.close()

def check_database():
    """Проверить, существует ли база данных"""
    if not os.path.exists("database.sqlite"):
        print("База данных не найдена. Инициализируем...")
        init_db()
        print("База данных успешно создана.")

def main():
    """Главная функция скрипта"""
    print("=== Исправление проблемы с пользователем ===")
    
    # Проверяем базу данных
    check_database()
    
    # Выводим текущих пользователей
    list_users()
    
    # Запрашиваем ID пользователя
    try:
        telegram_id = int(input("\nВведите ваш Telegram ID: "))
    except ValueError:
        print("Неверный формат ID. Используем значение по умолчанию.")
        telegram_id = 123456789
    
    # Запрашиваем имя пользователя
    first_name = input("Введите ваше имя (или нажмите Enter для пропуска): ")
    if not first_name:
        first_name = "Пользователь бота"
    
    # Создаем или обновляем пользователя
    create_user_direct(telegram_id, first_name=first_name)
    
    # Выводим обновленный список пользователей
    list_users()
    
    print("\n=== Исправление завершено ===")
    print("Теперь запустите бота командой 'python3 main.py' и попробуйте использовать его.")

if __name__ == "__main__":
    main() 