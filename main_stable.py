"""
Main entry point for the Facebook Ads Telegram Bot.
"""
import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from config.settings import BOT_TOKEN
from src.storage.database import init_db
from src.bot.handlers import router as common_router
from src.bot.callbacks import callback_router
from src.bot.account_handlers import router as account_router
from src.bot.campaign_handlers import router as campaign_router
from src.bot.ad_handlers import router as ad_router
from src.bot.auth_handlers import router as auth_router
from src.utils.logger import setup_logging

# Configure logging
logger = logging.getLogger(__name__)

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Include routers
dp.include_router(common_router)  # Base router
dp.include_router(callback_router)  # Callbacks
dp.include_router(account_router)  # Account-related handlers
dp.include_router(campaign_router)  # Campaign-related handlers
dp.include_router(ad_router)  # Ad-related handlers
dp.include_router(auth_router)  # Auth-related handlers


async def main():
    """
    Main function to start the bot.
    """
    # Setup logging
    setup_logging()
    
    # Initialize the database
    init_db()
    
    # Start the bot
    logger.info("Starting Facebook Ads Telegram Bot")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped manually")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"Unexpected error: {str(e)}")
        sys.exit(1) 