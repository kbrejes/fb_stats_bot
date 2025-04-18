#!/usr/bin/env python3
"""
Комплексный тестовый скрипт для проверки функциональности Telegram бота.
Этот скрипт проверяет работоспособность команд, колбеков и обработку ошибок.
"""
import asyncio
import sys
import logging
import random
import string
from datetime import datetime

from aiogram import Bot, types
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from config.settings import BOT_TOKEN
from src.storage.database import get_session
from src.storage.models import User
from src.utils.bot_helpers import fix_user_id

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Цвета для вывода в терминал
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
ENDC = '\033[0m'

# Инициализация бота
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

# Получаем ID тестового пользователя из базы данных
async def get_test_user_id() -> int:
    """Получение ID тестового пользователя из базы данных."""
    session = get_session()
    try:
        # Найдем пользователя с действительным токеном
        user = session.query(User).filter(User.fb_access_token.isnot(None)).first()
        if user:
            return user.telegram_id
        else:
            logger.error(f"{RED}В базе данных нет пользователей с валидным токеном для тестирования{ENDC}")
            return None
    finally:
        session.close()

async def test_basic_commands():
    """Тестирование основных команд бота."""
    logger.info(f"{BLUE}Тестирование основных команд...{ENDC}")
    
    test_user_id = await get_test_user_id()
    if not test_user_id:
        return False, "Нет тестового пользователя"
    
    commands = [
        ("/start", "команды приветствия"),
        ("/menu", "главного меню"),
        ("/help", "справки"),
        ("/accounts", "списка аккаунтов"),
    ]
    
    success_count = 0
    for cmd, description in commands:
        try:
            await bot.send_message(test_user_id, cmd)
            logger.info(f"{GREEN}Отправлена команда {cmd} для тестирования {description}{ENDC}")
            success_count += 1
            # Небольшая пауза между командами
            await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"{RED}Ошибка при отправке команды {cmd}: {str(e)}{ENDC}")
    
    return success_count == len(commands), f"Успешно выполнено {success_count}/{len(commands)} основных команд"

async def test_error_handling():
    """Тестирование обработки ошибок."""
    logger.info(f"{BLUE}Тестирование обработки ошибок...{ENDC}")
    
    test_user_id = await get_test_user_id()
    if not test_user_id:
        return False, "Нет тестового пользователя"
    
    error_test_cases = [
        ("/campaigns", "команды без параметров"),
        ("/campaigns invalid_id", "команды с неверным ID"),
        ("/ads", "команды ads без параметров"),
        ("/ads invalid_id", "команды ads с неверным ID"),
    ]
    
    success_count = 0
    for cmd, description in error_test_cases:
        try:
            await bot.send_message(test_user_id, cmd)
            logger.info(f"{GREEN}Отправлена команда {cmd} для тестирования {description}{ENDC}")
            success_count += 1
            # Пауза между командами
            await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"{RED}Ошибка при отправке команды {cmd}: {str(e)}{ENDC}")
    
    return success_count == len(error_test_cases), f"Успешно выполнено {success_count}/{len(error_test_cases)} тестов обработки ошибок"

async def test_edge_cases():
    """Тестирование граничных случаев."""
    logger.info(f"{BLUE}Тестирование граничных случаев...{ENDC}")
    
    test_user_id = await get_test_user_id()
    if not test_user_id:
        return False, "Нет тестового пользователя"
    
    # Длинная строка, специальные символы, SQL-инъекция
    edge_cases = [
        ("/campaigns " + "a" * 100, "очень длинного аргумента"),
        ("/campaigns !@#$%^&*()", "специальных символов"),
        ("/campaigns ' OR 1=1 --", "попытки SQL-инъекции"),
    ]
    
    success_count = 0
    for cmd, description in edge_cases:
        try:
            await bot.send_message(test_user_id, cmd)
            logger.info(f"{GREEN}Отправлена команда для тестирования {description}{ENDC}")
            success_count += 1
            # Пауза между командами
            await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"{RED}Ошибка при тестировании {description}: {str(e)}{ENDC}")
    
    return success_count == len(edge_cases), f"Успешно выполнено {success_count}/{len(edge_cases)} тестов граничных случаев"

async def main():
    """Основная функция для запуска всех тестов."""
    logger.info(f"{YELLOW}Начало комплексного тестирования бота{ENDC}")
    
    test_results = []
    
    # Запуск тестов
    basic_result, basic_msg = await test_basic_commands()
    test_results.append(("Основные команды", basic_result, basic_msg))
    
    error_result, error_msg = await test_error_handling()
    test_results.append(("Обработка ошибок", error_result, error_msg))
    
    edge_result, edge_msg = await test_edge_cases()
    test_results.append(("Граничные случаи", edge_result, edge_msg))
    
    # Вывод результатов
    logger.info(f"{YELLOW}Результаты тестирования:{ENDC}")
    
    success_count = sum(1 for _, result, _ in test_results if result)
    total_count = len(test_results)
    
    for test_name, result, message in test_results:
        status = f"{GREEN}УСПЕХ{ENDC}" if result else f"{RED}ОШИБКА{ENDC}"
        logger.info(f"{test_name}: {status} - {message}")
    
    logger.info(f"{YELLOW}Общий результат: {success_count}/{total_count} тестов пройдено успешно{ENDC}")
    
    # Пауза для обработки ботом всех сообщений
    logger.info(f"{YELLOW}Ожидание 10 секунд для обработки ботом всех сообщений...{ENDC}")
    await asyncio.sleep(10)
    
    logger.info(f"{YELLOW}Тестирование завершено{ENDC}")
    
    # Создаем отчет о тестировании в файле
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    with open(f"test_report_{timestamp}.txt", "w") as f:
        f.write(f"Отчет о тестировании бота от {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"Общий результат: {success_count}/{total_count} тестов пройдено успешно\n\n")
        for test_name, result, message in test_results:
            status = "УСПЕХ" if result else "ОШИБКА"
            f.write(f"{test_name}: {status} - {message}\n")
    
    logger.info(f"{GREEN}Отчет о тестировании сохранен в файл test_report_{timestamp}.txt{ENDC}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Тестирование остановлено вручную")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"Непредвиденная ошибка: {str(e)}")
        sys.exit(1) 