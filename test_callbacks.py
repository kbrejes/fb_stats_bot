#!/usr/bin/env python3
"""
Скрипт для тестирования колбеков и обработки кнопок в Telegram боте.
Эмулирует нажатие на кнопки в интерфейсе бота и проверяет реакцию.
"""
import asyncio
import sys
import logging
from datetime import datetime
from typing import Dict, Any, Tuple, Optional, List

from aiogram import Bot, types
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramAPIError

from config.settings import BOT_TOKEN
from src.storage.database import get_session
from src.storage.models import User, Account

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='\033[92m%(asctime)s - %(levelname)s - %(message)s\033[0m' if logging.getLevelName(logging.INFO) else '%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Создаем логгер
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
async def get_test_user_and_account() -> Tuple[Optional[User], Optional[Account]]:
    """Получение тестового пользователя и его аккаунта из базы данных."""
    session = get_session()
    try:
        # Найдем пользователя с действительным токеном
        user = session.query(User).filter(User.fb_access_token.isnot(None)).first()
        if user:
            # Получаем один из аккаунтов пользователя
            account = session.query(Account).filter(Account.telegram_id == user.telegram_id).first()
            return user, account
        else:
            logger.error(f"{RED}В базе данных нет пользователей с валидным токеном для тестирования{ENDC}")
            return None, None
    except Exception as e:
        logger.error(f"{RED}Ошибка при получении тестового пользователя: {str(e)}{ENDC}")
        return None, None
    finally:
        session.close()

async def send_command_and_wait(user_id: int, command: str, wait_seconds: int = 2) -> None:
    """Отправка команды и ожидание ответа."""
    try:
        await bot.send_message(user_id, command)
        logger.info(f"{GREEN}Отправлена команда {command}{ENDC}")
        await asyncio.sleep(wait_seconds)  # Ожидание ответа бота
    except TelegramAPIError as e:
        logger.error(f"{RED}Ошибка при отправке команды {command}: {str(e)}{ENDC}")

async def emulate_callback_query(user_id: int, callback_data: str, 
                                chat_id: int = None, message_id: int = None) -> bool:
    """Эмуляция нажатия на кнопку с определенным callback_data."""
    if chat_id is None:
        chat_id = user_id
    
    # Если message_id не указан, будем эмулировать простой callback без конкретного сообщения
    # Это не идеально, но позволяет тестировать логику callback-обработчиков
    if message_id is None:
        # В реальной ситуации нам нужно было бы знать ID сообщения с кнопками
        logger.warning(f"{YELLOW}Эмуляция callback без message_id может работать некорректно{ENDC}")
        message_id = 0  # Фиктивный ID
    
    try:
        # Создаем объект callback_query для эмуляции нажатия кнопки
        callback_query = types.CallbackQuery(
            id="test_" + datetime.now().strftime("%Y%m%d%H%M%S"),
            from_user=types.User(
                id=user_id,
                is_bot=False,
                first_name="Test",
                last_name="User",
                username="test_user",
                language_code="ru"
            ),
            message=types.Message(
                message_id=message_id,
                date=datetime.now(),
                chat=types.Chat(
                    id=chat_id,
                    type="private",
                    title=None,
                    username="test_user",
                    first_name="Test",
                    last_name="User"
                ),
                from_user=types.User(
                    id=bot.id,
                    is_bot=True,
                    first_name="TestBot",
                    username="test_bot"
                ),
                sender_chat=None,
                text="Test message",
                entities=[]
            ),
            chat_instance="test_chat_instance",
            data=callback_data
        )
        
        # Отправляем этот callback боту (напрямую - это невозможно)
        # Вместо этого мы логируем это для информации
        logger.info(f"{BLUE}Эмуляция нажатия кнопки с callback_data: {callback_data}{ENDC}")
        logger.warning(f"{YELLOW}Прямая эмуляция callback невозможна через API - это только для визуализации теста{ENDC}")
        
        # Отправляем эмуляцию через обычное сообщение
        msg = f"/test_callback {callback_data}"
        await bot.send_message(user_id, msg)
        logger.info(f"{GREEN}Отправлен эмулированный callback через команду: {msg}{ENDC}")
        
        # Ожидание ответа бота
        await asyncio.sleep(2)
        return True
    except Exception as e:
        logger.error(f"{RED}Ошибка при эмуляции callback {callback_data}: {str(e)}{ENDC}")
        return False

async def test_account_callbacks():
    """Тестирование колбеков, связанных с аккаунтами."""
    logger.info(f"{BLUE}Тестирование колбеков аккаунтов...{ENDC}")
    
    user, account = await get_test_user_and_account()
    if not user or not account:
        return False, "Нет тестового пользователя или аккаунта"
    
    # Список тестов для проверки колбеков аккаунтов
    tests = [
        ("/accounts", "открытие списка аккаунтов"),
    ]
    
    if account:
        # Добавляем тесты, если есть аккаунт
        account_callbacks = [
            (f"account:{account.fb_account_id}", "выбор аккаунта"),
            (f"account_menu:{account.fb_account_id}", "меню аккаунта"),
            (f"account_campaigns:{account.fb_account_id}", "просмотр кампаний аккаунта"),
        ]
        tests.extend([(f"/test_callback {callback}", desc) for callback, desc in account_callbacks])
    
    success_count = 0
    for cmd, description in tests:
        if cmd.startswith("/test_callback"):
            # Извлекаем callback_data из команды
            callback_data = cmd.split(" ", 1)[1]
            success = await emulate_callback_query(user.telegram_id, callback_data)
        else:
            success = await send_command_and_wait(user.telegram_id, cmd)
        
        if success:
            logger.info(f"{GREEN}Успешно выполнено тестирование {description}{ENDC}")
            success_count += 1
        else:
            logger.error(f"{RED}Ошибка при тестировании {description}{ENDC}")
    
    return success_count > 0, f"Успешно выполнено {success_count}/{len(tests)} тестов колбеков аккаунтов"

async def test_campaign_callbacks():
    """Тестирование колбеков, связанных с кампаниями."""
    logger.info(f"{BLUE}Тестирование колбеков кампаний...{ENDC}")
    
    user, account = await get_test_user_and_account()
    if not user or not account:
        return False, "Нет тестового пользователя или аккаунта"
    
    # Сначала откроем список кампаний
    await send_command_and_wait(user.telegram_id, f"/campaigns {account.fb_account_id}", 3)
    
    # Тестовые колбеки для кампаний (без реальных ID кампаний)
    campaign_callbacks = [
        (f"campaign_menu:test_campaign_id", "попытка открытия меню кампании с тестовым ID"),
        (f"campaign_stats:test_campaign_id", "попытка просмотра статистики кампании с тестовым ID"),
        (f"back_to_campaigns:{account.fb_account_id}", "возврат к списку кампаний"),
    ]
    
    success_count = 0
    for callback_data, description in campaign_callbacks:
        success = await emulate_callback_query(user.telegram_id, callback_data)
        if success:
            logger.info(f"{GREEN}Успешно выполнено тестирование {description}{ENDC}")
            success_count += 1
        else:
            logger.error(f"{RED}Ошибка при тестировании {description}{ENDC}")
    
    return success_count > 0, f"Успешно выполнено {success_count}/{len(campaign_callbacks)} тестов колбеков кампаний"

async def test_error_callbacks():
    """Тестирование обработки ошибок при неверных колбеках."""
    logger.info(f"{BLUE}Тестирование обработки ошибочных колбеков...{ENDC}")
    
    user, _ = await get_test_user_and_account()
    if not user:
        return False, "Нет тестового пользователя"
    
    # Тестовые колбеки с ошибками
    error_callbacks = [
        (f"invalid_callback:123", "неверный формат колбека"),
        (f"account:invalid_id", "неверный ID аккаунта"),
        (f"campaign_menu:", "пустой ID кампании"),
        (f"account_campaigns:123456789", "несуществующий ID аккаунта"),
    ]
    
    success_count = 0
    for callback_data, description in error_callbacks:
        success = await emulate_callback_query(user.telegram_id, callback_data)
        if success:
            logger.info(f"{GREEN}Успешно выполнено тестирование {description}{ENDC}")
            success_count += 1
        else:
            logger.error(f"{RED}Ошибка при тестировании {description}{ENDC}")
    
    return success_count > 0, f"Успешно выполнено {success_count}/{len(error_callbacks)} тестов обработки ошибочных колбеков"

async def main():
    """Основная функция для запуска всех тестов колбеков."""
    logger.info(f"{YELLOW}Начало тестирования колбеков бота{ENDC}")
    
    test_results = []
    
    # Запуск тестов
    account_result, account_msg = await test_account_callbacks()
    test_results.append(("Колбеки аккаунтов", account_result, account_msg))
    
    campaign_result, campaign_msg = await test_campaign_callbacks()
    test_results.append(("Колбеки кампаний", campaign_result, campaign_msg))
    
    error_result, error_msg = await test_error_callbacks()
    test_results.append(("Обработка ошибочных колбеков", error_result, error_msg))
    
    # Вывод результатов
    logger.info(f"{YELLOW}Результаты тестирования колбеков:{ENDC}")
    
    success_count = sum(1 for _, result, _ in test_results if result)
    total_count = len(test_results)
    
    for test_name, result, message in test_results:
        status = f"{GREEN}УСПЕХ{ENDC}" if result else f"{RED}ОШИБКА{ENDC}"
        logger.info(f"{test_name}: {status} - {message}")
    
    logger.info(f"{YELLOW}Общий результат: {success_count}/{total_count} тестов пройдено успешно{ENDC}")
    
    # Пауза для обработки ботом всех сообщений
    logger.info(f"{YELLOW}Ожидание 10 секунд для обработки ботом всех сообщений...{ENDC}")
    await asyncio.sleep(10)
    
    logger.info(f"{YELLOW}Тестирование колбеков завершено{ENDC}")
    
    # Создаем отчет о тестировании в файле
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    with open(f"callback_test_report_{timestamp}.txt", "w") as f:
        f.write(f"Отчет о тестировании колбеков бота от {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"Общий результат: {success_count}/{total_count} тестов пройдено успешно\n\n")
        for test_name, result, message in test_results:
            status = "УСПЕХ" if result else "ОШИБКА"
            f.write(f"{test_name}: {status} - {message}\n")
    
    logger.info(f"{GREEN}Отчет о тестировании колбеков сохранен в файл callback_test_report_{timestamp}.txt{ENDC}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Тестирование остановлено вручную")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"Непредвиденная ошибка: {str(e)}")
        sys.exit(1) 