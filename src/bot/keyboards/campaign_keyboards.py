"""
Campaign-related keyboard builders.
"""
from typing import List, Dict, Any, Optional

from src.bot.keyboards.base import KeyboardBuilder
from src.bot.keyboards.utils import format_button_text, create_callback_data


def build_campaign_keyboard(campaigns: List[Dict], add_stats: bool = False):
    """
    Build a keyboard with campaign selection buttons.
    
    Args:
        campaigns: List of campaign data.
        add_stats: Whether to add stats buttons.
        
    Returns:
        Keyboard with campaign buttons.
    """
    kb = KeyboardBuilder()
    
    for campaign in campaigns:
        campaign_id = campaign.get('id')
        campaign_name = campaign.get('name', 'Unnamed Campaign')
        
        # Format button text
        button_text = format_button_text(campaign_name)
        callback_data = create_callback_data("campaign", None, campaign_id)
            
        kb.add_button(text=button_text, callback_data=callback_data)
        
        # Add stats button if requested
        if add_stats:
            stats_text = "📊 Статистика"
            stats_callback_data = create_callback_data(
                "campaign_stats", None, campaign_id, campaign_name
            )
            kb.add_button(text=stats_text, callback_data=stats_callback_data)
    
    # Add navigation buttons
    kb.add_back_button(to_type="accounts")
    kb.add_main_menu_button()
    
    # Build grid - всегда по 2 кнопкам в ряду
    return kb.build(row_width=2) 