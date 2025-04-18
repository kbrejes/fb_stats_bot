"""
Ad-related keyboard builders.
"""
from typing import List, Dict, Any, Optional

from src.bot.keyboards.base import KeyboardBuilder
from src.bot.keyboards.utils import format_button_text, create_callback_data


def build_ad_keyboard(ads: List[Dict], campaign_id: str, add_stats: bool = False):
    """
    Build a keyboard with ad selection buttons.
    
    Args:
        ads: List of ad data.
        campaign_id: The campaign ID to return to.
        add_stats: Whether to add stats buttons.
        
    Returns:
        Keyboard with ad buttons.
    """
    kb = KeyboardBuilder()
    
    for ad in ads:
        ad_id = ad.get('id')
        ad_name = ad.get('name', 'Unnamed Ad')
        
        # Format button text
        button_text = format_button_text(ad_name)
        callback_data = create_callback_data("ad", None, ad_id)
            
        kb.add_button(text=button_text, callback_data=callback_data)
        
        # Add stats button if requested
        if add_stats:
            stats_text = "📊 Статистика"
            stats_callback_data = create_callback_data(
                "ad_stats", None, ad_id, ad_name
            )
            kb.add_button(text=stats_text, callback_data=stats_callback_data)
    
    # Add navigation buttons - используем меню вместо back
    kb.add_back_button(to_type="campaign", to_id=campaign_id)
    kb.add_main_menu_button()
    
    # Build grid - всегда по 2 кнопкам в ряду
    return kb.build(row_width=2) 