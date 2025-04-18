#!/usr/bin/env python3
"""
Тестовый скрипт для проверки функциональности Facebook клиента 
с новой системой обработки ошибок.

Запуск: python test_facebook_client.py

Внимание: для запуска нужен действующий пользователь в базе данных
с действительным Facebook токеном.
"""

import asyncio
import sys
import os
import traceback
from typing import List, Dict, Any, Optional

# Добавляем корневую директорию проекта в PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.storage.database import get_session
from src.storage.models import User
from src.api.facebook import FacebookAdsClient  # Импортируем из пакета, а не из client.py
from src.api.facebook.exceptions import (
    FacebookAdsApiError,
    TokenExpiredError,
    TokenNotSetError,
    InsufficientPermissionsError,
    RateLimitError,
    NetworkError
)

# Цвета для вывода
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BLUE = '\033[94m'
ENDC = '\033[0m'


def print_header(text: str):
    """Вывести заголовок теста"""
    print(f"\n{BLUE}{'=' * 50}{ENDC}")
    print(f"{BLUE}{text.center(50)}{ENDC}")
    print(f"{BLUE}{'=' * 50}{ENDC}\n")


def print_success(text: str):
    """Вывести сообщение об успешном тесте"""
    print(f"{GREEN}✅ {text}{ENDC}")


def print_error(text: str):
    """Вывести сообщение об ошибке"""
    print(f"{RED}❌ {text}{ENDC}")


def print_info(text: str):
    """Вывести информационное сообщение"""
    print(f"{YELLOW}ℹ️ {text}{ENDC}")


async def get_test_user() -> Optional[int]:
    """
    Получить ID тестового пользователя с действительным токеном Facebook
    """
    session = get_session()
    try:
        # Ищем пользователя с валидным токеном
        user = session.query(User).filter(User.fb_access_token != None).first()
        if user:
            return user.telegram_id
        return None
    finally:
        session.close()


async def test_get_user_info(client: FacebookAdsClient) -> bool:
    """
    Тест получения информации о пользователе
    """
    try:
        user_info = await client.get_user_info()
        if user_info and 'id' in user_info:
            print_success(f"Получена информация о пользователе: {user_info.get('name', 'Unknown')}")
            return True
        else:
            print_error(f"Не удалось получить корректную информацию о пользователе: {user_info}")
            return False
    except Exception as e:
        print_error(f"Ошибка при получении информации о пользователе: {str(e)}")
        traceback.print_exc()
        return False


async def test_get_ad_accounts(client: FacebookAdsClient) -> bool:
    """
    Тест получения списка рекламных аккаунтов
    """
    try:
        accounts = await client.get_ad_accounts()
        if accounts and isinstance(accounts, list):
            print_success(f"Получено {len(accounts)} рекламных аккаунтов")
            if accounts:
                print_info(f"Первый аккаунт: {accounts[0].get('name', 'Unknown')}")
            return True
        else:
            print_error(f"Не удалось получить список рекламных аккаунтов: {accounts}")
            return False
    except Exception as e:
        print_error(f"Ошибка при получении списка рекламных аккаунтов: {str(e)}")
        traceback.print_exc()
        return False


async def test_get_accounts_with_error_handling(client: FacebookAdsClient) -> bool:
    """
    Тест метода get_accounts с обработкой ошибок
    """
    try:
        accounts, error_message = await client.get_accounts()
        if error_message:
            print_error(f"Получено сообщение об ошибке: {error_message}")
            return False
        
        if accounts and isinstance(accounts, list):
            print_success(f"Метод get_accounts вернул {len(accounts)} аккаунтов без ошибок")
            return True
        else:
            print_error(f"Метод get_accounts вернул некорректные данные: {accounts}")
            return False
    except Exception as e:
        print_error(f"Необработанная ошибка в методе get_accounts: {str(e)}")
        traceback.print_exc()
        return False


async def test_exception_handling() -> bool:
    """
    Тест обработки исключений
    """
    # Создаем клиент с неверным ID пользователя для проверки обработки ошибок
    client = FacebookAdsClient(user_id=99999999)
    
    try:
        # Этот вызов должен вызвать TokenNotSetError
        await client.get_user_info()
        print_error("Не удалось проверить обработку ошибок - не получено исключение TokenNotSetError")
        return False
    except TokenNotSetError as e:
        print_success(f"Корректно обработано исключение TokenNotSetError: {str(e)}")
        return True
    except Exception as e:
        print_error(f"Получено неправильное исключение: {type(e).__name__}: {str(e)}")
        traceback.print_exc()
        return False


async def run_tests():
    """
    Запуск всех тестов
    """
    test_results = {}
    
    print_header("Тестирование клиента Facebook API с новой системой обработки ошибок")
    
    # Получаем тестового пользователя
    user_id = await get_test_user()
    if not user_id:
        print_error("Не найден тестовый пользователь с токеном Facebook")
        return
    
    print_info(f"Используем пользователя с ID: {user_id}")
    
    # Создаем клиент Facebook API
    client = FacebookAdsClient(user_id=user_id)
    
    # Запускаем тесты
    print_header("1. Тест получения информации о пользователе")
    test_results["get_user_info"] = await test_get_user_info(client)
    
    print_header("4. Тест обработки исключений")
    test_results["exception_handling"] = await test_exception_handling()
    
    # Вывод общих результатов
    print_header("Результаты тестирования")
    
    successful_tests = sum(1 for result in test_results.values() if result)
    total_tests = len(test_results)
    
    for test_name, result in test_results.items():
        status = f"{GREEN}УСПЕШНО{ENDC}" if result else f"{RED}ОШИБКА{ENDC}"
        print(f"{test_name.ljust(20)}: {status}")
    
    print(f"\nУспешно пройдено тестов: {successful_tests}/{total_tests}")
    
    if successful_tests == total_tests:
        print(f"\n{GREEN}ВСЕ ТЕСТЫ УСПЕШНЫ! Система обработки ошибок работает корректно.{ENDC}")
    else:
        print(f"\n{RED}ОБНАРУЖЕНЫ ОШИБКИ! Необходимо исправить проблемы перед внедрением.{ENDC}")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run_tests()) 