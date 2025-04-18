"""
Keyboard builders for Telegram bot.

This file provides backward compatibility with the original keyboard functions.
All implementations have been moved to the keyboards/ package.
"""

# Re-export all keyboard builders from the keyboards package
from src.bot.keyboards import (
    build_account_keyboard,
    build_campaign_keyboard,
    build_ad_keyboard,
    build_date_preset_keyboard,
    build_main_menu_keyboard,
    build_export_format_keyboard,
    build_confirmation_keyboard,
    build_language_keyboard,
)

# For backward compatibility
__all__ = [
    'build_account_keyboard',
    'build_campaign_keyboard',
    'build_ad_keyboard',
    'build_date_preset_keyboard',
    'build_main_menu_keyboard',
    'build_export_format_keyboard',
    'build_confirmation_keyboard',
    'build_language_keyboard',
] 