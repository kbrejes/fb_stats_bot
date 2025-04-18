"""
Utility keyboard builders for specific functions.
"""
from typing import List

from config.settings import EXPORT_FORMATS
from src.bot.keyboards.base import KeyboardBuilder
from src.bot.keyboards.utils import create_callback_data


def build_export_format_keyboard(data_key: str):
    """
    Build a keyboard with export format buttons.
    
    Args:
        data_key: The key for the cached data to export.
        
    Returns:
        InlineKeyboardMarkup with export format buttons.
    """
    kb = KeyboardBuilder()
    
    # Format buttons
    for format in EXPORT_FORMATS:
        kb.add_button(
            text=format.upper(),
            callback_data=create_callback_data("export", data_key, format)
        )
    
    # Back button
    kb.add_back_button(to_type="cancel")
    
    # Build grid with 3 buttons in first row, 1 in second
    return kb.build(row_width=[3, 1], check_parity=False)


def build_confirmation_keyboard(action: str, object_id: str):
    """
    Build a confirmation keyboard.
    
    Args:
        action: The action to confirm.
        object_id: The object ID associated with the action.
        
    Returns:
        InlineKeyboardMarkup with confirm/cancel buttons.
    """
    kb = KeyboardBuilder()
    
    # Confirm button
    kb.add_button(
        text="✅ Подтвердить",
        callback_data=create_callback_data("confirm", action, object_id)
    )
    
    # Cancel button
    kb.add_button(
        text="❌ Отмена",
        callback_data=create_callback_data("back", "cancel")
    )
    
    # Build grid with 2 buttons per row
    return kb.build(row_width=2, check_parity=True)


def build_language_keyboard():
    """
    Build a keyboard for language selection.
    
    Returns:
        InlineKeyboardMarkup with language buttons.
    """
    kb = KeyboardBuilder()
    
    # Add language buttons
    kb.add_button(
        text="🇷🇺 Русский",
        callback_data=create_callback_data("language", "ru")
    )
    
    kb.add_button(
        text="🇬🇧 English",
        callback_data=create_callback_data("language", "en")
    )
    
    # Add back button
    kb.add_button(
        text="↩️ Назад / Back",
        callback_data=create_callback_data("menu", "main")
    )
    
    # Build grid with 2 buttons per row for languages, 1 for back
    return kb.build(row_width=[2, 1], check_parity=False) 