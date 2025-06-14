"""
Telegram bot module for the Facebook Ads Telegram Bot.
"""

from aiogram import Bot, Dispatcher, Router
from aiogram.client.bot import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config.settings import BOT_TOKEN

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Create main router
main_router = Router(name="main_router")

# Export bot, dispatcher and main router
__all__ = ["bot", "dp", "main_router"]
