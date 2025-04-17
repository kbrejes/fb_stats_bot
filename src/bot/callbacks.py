"""
Callback query handlers for the Facebook Ads Telegram Bot.
This file now imports the modular callback handler system from the callbacks package.
"""

# Import the combined callback router from the callbacks package
from src.bot.callbacks.__init__ import callback_router

# The callback_router will be used by the main bot module 