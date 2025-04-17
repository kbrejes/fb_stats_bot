"""
Handlers package for the Facebook Ads Telegram Bot.
"""
from src.bot.handlers.auth import router as auth_router

# Export routers to be used in main bot module
__all__ = ['auth_router'] 