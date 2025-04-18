#!/usr/bin/env python3
"""
Тестовый скрипт для проверки исправления функции fix_user_id.
"""
import asyncio
import sys
import logging

from src.utils.bot_helpers import fix_user_id, BOT_ID, BOT_ID_DEV
from src.storage.database import get_session
from src.storage.models import User

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_fix_user_id():
    """Тестирование функции fix_user_id с разными ID."""
    # Сначала проверим с ID бота
    bot_id_fixed = await fix_user_id(BOT_ID)
    logger.info(f"Original BOT_ID: {BOT_ID}, Fixed: {bot_id_fixed}")
    
    # Проверим с ID DEV бота
    bot_id_dev_fixed = await fix_user_id(BOT_ID_DEV)
    logger.info(f"Original BOT_ID_DEV: {BOT_ID_DEV}, Fixed: {bot_id_dev_fixed}")
    
    # Теперь проверим с нормальным пользовательским ID
    session = get_session()
    try:
        # Найдем ID первого пользователя в базе
        user = session.query(User).first()
        if user:
            user_id = user.telegram_id
            fixed_user_id = await fix_user_id(user_id)
            logger.info(f"Original User ID: {user_id}, Fixed: {fixed_user_id}")
            if user_id == fixed_user_id:
                logger.info("Успех! Нормальный ID пользователя не изменился.")
            else:
                logger.error("Ошибка! ID пользователя был изменен, хотя не должен был.")
        else:
            logger.warning("В базе данных нет пользователей для тестирования.")
    finally:
        session.close()
    
    # Проверим все пользовательские ID в базе данных
    session = get_session()
    try:
        users = session.query(User).all()
        logger.info(f"Всего пользователей в базе: {len(users)}")
        for user in users:
            logger.info(f"User ID: {user.telegram_id}, has token: {user.fb_access_token is not None}")
    finally:
        session.close()

async def main():
    """Основная функция для запуска тестов."""
    logger.info("Начало тестирования функции fix_user_id")
    await test_fix_user_id()
    logger.info("Тестирование завершено")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Ошибка при выполнении тестов: {str(e)}")
        sys.exit(1) 