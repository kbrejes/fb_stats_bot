"""
Callback handlers package for the Facebook Ads Telegram Bot.
"""

from aiogram import Router
from src.bot.callbacks.stats_callbacks import stats_router
from src.bot.callbacks.export_callbacks import export_router
from src.bot.callbacks.menu_callbacks import menu_router
from src.bot.callbacks.account_callbacks import account_router

# Create a combined router for all callbacks
callback_router = Router()

# Include all sub-routers
callback_router.include_router(stats_router)
callback_router.include_router(export_router)
callback_router.include_router(menu_router)
callback_router.include_router(account_router) 