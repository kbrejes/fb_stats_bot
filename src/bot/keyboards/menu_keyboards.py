"""
Menu-related keyboard builders.
"""
from src.bot.keyboards.base import KeyboardBuilder
from src.bot.keyboards.utils import create_callback_data


def build_main_menu_keyboard():
    """
    Build the main menu keyboard.
    
    Returns:
        InlineKeyboardMarkup with menu buttons.
    """
    kb = KeyboardBuilder()
    
    # Main menu buttons
    kb.add_button(
        text="📊 Аккаунты",
        callback_data=create_callback_data("menu", "accounts")
    )
    
    kb.add_button(
        text="🔐 Авторизация",
        callback_data=create_callback_data("menu", "auth")
    )
    
    kb.add_button(
        text="🌐 Язык / Language",
        callback_data=create_callback_data("menu", "language")
    )
    
    # Build grid with 2 buttons per row
    return kb.build(row_width=2, check_parity=True) 