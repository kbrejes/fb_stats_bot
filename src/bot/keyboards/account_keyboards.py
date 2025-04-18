"""
Account-related keyboard builders.
"""
from typing import List, Dict, Any, Optional
from aiogram.types import InlineKeyboardMarkup

from src.bot.keyboards.base import KeyboardBuilder
from src.bot.keyboards.utils import format_button_text, create_callback_data
from src.bot.types import AccountList, AccountData


def build_account_keyboard(accounts: AccountList, add_stats: bool = False) -> InlineKeyboardMarkup:
    """
    Build a keyboard with account selection buttons.
    
    Args:
        accounts: List of account data.
        add_stats: Whether to add stats buttons (parameter kept for compatibility, but no longer used).
        
    Returns:
        Keyboard with account buttons in a single column.
    """
    kb = KeyboardBuilder()
    
    for account in accounts:
        account_id = account.get('id')
        account_name = account.get('name', 'Unnamed Account')
        
        # Format button text - using a more generous limit since we have a single column
        button_text = format_button_text(account_name, max_length=40)
        callback_data = create_callback_data("account", None, account_id)
            
        kb.add_button(text=button_text, callback_data=callback_data)
    
    # Add main menu button
    kb.add_main_menu_button()
    
    # Build grid - 1 кнопка в ряду для лучшей читаемости
    return kb.build(row_width=1, check_parity=False) 