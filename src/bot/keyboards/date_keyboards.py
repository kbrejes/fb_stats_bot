"""
Date-related keyboard builders.
"""
from typing import Optional

from config.settings import DATE_PRESETS
from src.bot.keyboards.base import KeyboardBuilder
from src.bot.keyboards.utils import create_callback_data


def build_date_preset_keyboard(object_id: str, object_type: str, object_name: str = None):
    """
    Build a keyboard with date preset buttons.
    
    Args:
        object_id: The object ID.
        object_type: The object type (account, campaign, ad).
        object_name: Optional object name to pass in callback data.
        
    Returns:
        Keyboard with date preset buttons.
    """
    kb = KeyboardBuilder()
    
    # Friendly names for date presets
    date_labels = {
        'today': 'Сегодня',
        'yesterday': 'Вчера',
        'last_3d': 'Последние 3 дня',
        'last_7d': 'Последние 7 дней',
        'last_14d': 'Последние 14 дней',
        'last_28d': 'Последние 28 дней',
        'last_30d': 'Последние 30 дней',
        'this_month': 'Текущий месяц',
        'last_month': 'Прошлый месяц'
    }
    
    # Add date preset buttons
    for preset, value in DATE_PRESETS.items():
        # Only add buttons for presets we have labels for
        if preset in date_labels:
            # Create callback data without object name to avoid BUTTON_DATA_INVALID error
            callback_data = create_callback_data("stats", object_type, object_id, preset)
            
            kb.add_button(
                text=date_labels.get(preset, preset),
                callback_data=callback_data
            )
    
    # Add navigation buttons based on object type
    if object_type == 'account':
        kb.add_back_button(to_type="accounts")
    elif object_type == 'campaign':
        # Extract account_id from campaign_id if present
        account_id = object_id.split('_')[0] if '_' in object_id else object_id
        kb.add_back_button(to_type="account", to_id=account_id)
    elif object_type == 'ad':
        # Extract campaign_id from ad_id if present
        campaign_id = object_id.split('_')[0] if '_' in object_id else object_id
        kb.add_back_button(to_type="campaign", to_id=campaign_id)
    elif object_type == 'account_campaigns':
        # For campaign tables of an account
        kb.add_back_button(to_type="account", to_id=object_id)
    
    # Add main menu button
    kb.add_main_menu_button()
    
    # Build grid - всегда по 2 кнопкам в ряду
    return kb.build(row_width=2) 