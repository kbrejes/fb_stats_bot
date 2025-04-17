"""
Utility functions for formatting messages for Telegram.
"""
from typing import Dict, List, Any, Optional

from src.utils.logger import get_logger
from src.utils.languages import get_text, get_language

logger = get_logger(__name__)

def format_insights(insights: List[Dict[str, Any]], object_type: str, date_preset: str = 'last_7d', user_id: int = None) -> str:
    """
    Format insights data for display in Telegram.
    
    Args:
        insights: The insights data to format.
        object_type: The type of object (account, campaign, adset, ad).
        date_preset: The date preset used for the insights.
        user_id: The user's Telegram ID for language settings.
        
    Returns:
        A formatted string with the insights.
    """
    # Get the user's language
    lang = "ru"
    if user_id:
        lang = get_language(user_id)
    
    if not insights:
        return f"<b>{get_text('no_stats_found', lang, object_type=get_text(object_type, lang))}</b>"
    
    # Get date label based on user's language
    date_label = get_text(date_preset, lang)
    
    # Start building the formatted message
    obj_type_display = get_text(object_type, lang)
    message = f"<b>{get_text('insights_for', lang, type=obj_type_display.capitalize(), name='')}</b>\n"
    message += f"<b>{get_text('period', lang)}:</b> {date_label}\n\n"
    
    # Helper function to format currency values
    def format_currency(value, currency="USD"):
        try:
            value = float(value)
            if value >= 1000000:
                return f"{value/1000000:.2f}M {currency}"
            elif value >= 1000:
                return f"{value/1000:.2f}K {currency}"
            else:
                return f"{value:.2f} {currency}"
        except (ValueError, TypeError):
            return f"{value} {currency}"
    
    # Summary of key metrics
    total_impressions = sum(float(i.get('impressions', 0)) for i in insights)
    total_clicks = sum(float(i.get('clicks', 0)) for i in insights)
    total_reach = sum(float(i.get('reach', 0)) for i in insights)
    total_spend = sum(float(i.get('spend', 0)) for i in insights)
    
    currency = insights[0].get('currency', 'USD') if insights else 'USD'
    
    message += f"<b>{get_text('summary', lang)}:</b>\n"
    message += f"• <b>{get_text('impressions', lang)}:</b> {int(total_impressions):,}\n"
    message += f"• <b>{get_text('clicks', lang)}:</b> {int(total_clicks):,}\n"
    message += f"• <b>{get_text('reach', lang)}:</b> {int(total_reach):,}\n"
    message += f"• <b>{get_text('spend', lang)}:</b> {format_currency(total_spend, currency)}\n"
    
    if total_impressions > 0:
        ctr = (total_clicks / total_impressions) * 100
        message += f"• <b>{get_text('ctr', lang)}:</b> {ctr:.2f}%\n"
        
    if total_impressions > 0:
        cpm = (total_spend / total_impressions) * 1000
        message += f"• <b>{get_text('cpm', lang)}:</b> {format_currency(cpm, currency)}\n"
        
    if total_clicks > 0:
        cpc = total_spend / total_clicks
        message += f"• <b>{get_text('cpc', lang)}:</b> {format_currency(cpc, currency)}\n"
    
    # Check for conversions data
    conversion_data = False
    for insight in insights:
        if 'actions' in insight or 'conversions' in insight or 'cost_per_action_type' in insight:
            conversion_data = True
            break
            
    if conversion_data:
        message += f"\n<b>{get_text('conversion_data', lang)}:</b>\n"
        
        # Extract conversion data
        action_types = {}
        cost_per_action = {}
        custom_conversions = {}
        
        # First collect all cost_per_action_type
        for insight in insights:
            costs = insight.get('cost_per_action_type', [])
            for cost in costs:
                action_type = cost.get('action_type', 'unknown')
                value = float(cost.get('value', 0))
                
                if action_type in cost_per_action:
                    # Take average if multiple entries
                    cost_per_action[action_type] = (cost_per_action[action_type] + value) / 2
                else:
                    cost_per_action[action_type] = value
        
        # Process actions and conversions
        for insight in insights:
            # Process actions
            actions = insight.get('actions', [])
            for action in actions:
                action_type = action.get('action_type', 'unknown')
                value = float(action.get('value', 0))
                
                if action_type in action_types:
                    action_types[action_type] += value
                else:
                    action_types[action_type] = value
                    
            # Process conversions - focus on custom conversions
            conversions = insight.get('conversions', [])
            for conversion in conversions:
                action_type = conversion.get('action_type', 'unknown')
                value = float(conversion.get('value', 0))
                
                # Store custom conversions separately
                if action_type.startswith('offsite_conversion.fb_pixel_custom.'):
                    custom_name = action_type.split('.')[-1]
                    custom_conversions[custom_name] = value
                    
                    # Find corresponding cost
                    base_type = '.'.join(action_type.split('.')[:-1])  # Get offsite_conversion.fb_pixel_custom
                    if base_type in cost_per_action:
                        # Link cost to specific custom conversion type
                        cost_per_action[action_type] = cost_per_action[base_type]
                
                # Add to general list for display
                if action_type in action_types:
                    action_types[action_type] += value
                else:
                    action_types[action_type] = value
        
        # Format custom conversions first if available
        if custom_conversions:
            message += f"\n<b>{get_text('custom_conversions', lang)}:</b>\n"
            for custom_name, value in custom_conversions.items():
                full_type = f"offsite_conversion.fb_pixel_custom.{custom_name}"
                message += f"• <b>{custom_name}:</b> {int(value):,}"
                
                # Add cost if known
                if full_type in cost_per_action:
                    cost = cost_per_action[full_type]
                    message += f" (<b>{get_text('cost', lang)}:</b> {format_currency(cost, currency)})"
                elif "offsite_conversion.fb_pixel_custom" in cost_per_action:
                    # Use general cost if specific one not available
                    cost = cost_per_action["offsite_conversion.fb_pixel_custom"]
                    message += f" (<b>{get_text('est_cost', lang)}:</b> {format_currency(cost, currency)})"
                
                message += "\n"
        
        # Then main conversions
        message += f"\n<b>{get_text('all_conversions', lang)}:</b>\n"
        
        # Dictionary for nicer conversion type names
        conversion_labels = {
            'link_click': get_text('link_clicks', lang),
            'landing_page_view': get_text('landing_page_view', lang),
            'lead': get_text('lead', lang),
            'purchase': get_text('purchase', lang),
            'offsite_conversion.fb_pixel_lead': get_text('offsite_conversion.fb_pixel_lead', lang),
            'offsite_conversion.fb_pixel_purchase': get_text('offsite_conversion.fb_pixel_purchase', lang)
        }
        
        # List of important conversions to show first
        important_conversions = [
            'lead', 'purchase', 'offsite_conversion.fb_pixel_lead', 
            'offsite_conversion.fb_pixel_purchase', 'landing_page_view'
        ]
        
        # Show important conversions first
        for action_type in important_conversions:
            if action_type in action_types:
                value = action_types[action_type]
                label = conversion_labels.get(action_type, action_type.replace('_', ' ').title())
                
                message += f"• <b>{label}:</b> {int(value):,}"
                
                # Add cost if known
                if action_type in cost_per_action:
                    cost = cost_per_action[action_type]
                    message += f" (<b>{get_text('cost', lang)}:</b> {format_currency(cost, currency)})"
                
                message += "\n"
                
                # Remove to avoid repeating in general list
                del action_types[action_type]
        
        # Then show remaining actions, except unimportant ones
        skip_types = ['page_engagement', 'post_engagement', 'post_reaction', 'video_view']
        for action_type, value in action_types.items():
            # Skip custom conversions (already shown above)
            if action_type.startswith('offsite_conversion.fb_pixel_custom.'):
                continue
                
            # Skip unimportant action types
            if action_type in skip_types:
                continue
                
            readable_type = action_type.replace('_', ' ').title()
            # Use nice names if available
            readable_type = conversion_labels.get(action_type, readable_type)
                
            message += f"• <b>{readable_type}:</b> {int(value):,}"
            
            # Add cost if known
            if action_type in cost_per_action:
                cost = cost_per_action[action_type]
                message += f" (<b>{get_text('cost', lang)}:</b> {format_currency(cost, currency)})"
            
            message += "\n"
    
    # Add export note
    message += f"\n<i>{get_text('export_note', lang)}</i>"
    
    return message 