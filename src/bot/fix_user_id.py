"""
Fix for the issue where bot is using its own ID instead of user ID.
This file contains monkey patches to fix the issue at runtime.
"""

from aiogram import Bot
from aiogram.types import Message, Update

# Original update handler
original_feed_update = None
original_feed_webhook_update = None


async def patched_feed_update(self, bot, update):
    """
    Patch to fix the issue where wrong user ID is used.
    """
    # Clear the Bot._me cache to force re-fetch from context
    if hasattr(bot, "_me"):
        delattr(bot, "_me")

    # Call the original method
    return await original_feed_update(self, bot, update)


async def patched_feed_webhook_update(self, bot, update, **kwargs):
    """
    Patch to fix the issue where wrong user ID is used for webhook updates.
    """
    # Clear the Bot._me cache to force re-fetch from context
    if hasattr(bot, "_me"):
        delattr(bot, "_me")

    # Call the original method
    return await original_feed_webhook_update(self, bot, update, **kwargs)


def apply_patches():
    """
    Apply the monkey patches to fix the user ID issue.
    This should be called before starting the bot.
    """
    global original_feed_update, original_feed_webhook_update

    from aiogram.dispatcher.event.telegram import TelegramEventObserver

    # Save original methods
    original_feed_update = TelegramEventObserver.feed_update
    original_feed_webhook_update = TelegramEventObserver.feed_webhook_update

    # Apply patches
    TelegramEventObserver.feed_update = patched_feed_update
    TelegramEventObserver.feed_webhook_update = patched_feed_webhook_update

    print("Applied monkey patches to fix user ID issues")
