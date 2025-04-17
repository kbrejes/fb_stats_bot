"""
Handlers package for the Facebook Ads Telegram Bot.
"""
from src.bot.handlers.auth import router as auth_router
from src.bot.handlers.common import router as common_router
from src.bot.handlers.account import router as account_router
from src.bot.handlers.campaign import router as campaign_router
from src.bot.handlers.ad import router as ad_router
from src.bot.handlers.main import router as main_router

# Export routers to be used in main bot module
__all__ = [
    'auth_router',
    'common_router',
    'account_router', 
    'campaign_router', 
    'ad_router',
    'main_router'
] 