"""
Utility functions for keyboard creation.
"""
from typing import Optional, Any, Dict, List, Union


def truncate_text(text: str, max_length: int = 30, suffix: str = '...') -> str:
    """
    Truncate text if it exceeds the maximum length.
    
    Args:
        text: Text to truncate.
        max_length: Maximum length of text before truncation.
        suffix: Suffix to add to truncated text.
        
    Returns:
        Truncated text or original text if not exceeding max_length.
    """
    if len(text) > max_length:
        return text[:max_length - len(suffix)] + suffix
    return text


def validate_callback_data(callback_data: str, max_length: int = 64) -> bool:
    """
    Validate if callback_data fits within Telegram's limit.
    
    Args:
        callback_data: The callback data to validate.
        max_length: Maximum length of callback data (64 bytes for Telegram).
        
    Returns:
        True if valid, False otherwise.
    """
    return len(callback_data.encode('utf-8')) <= max_length


def create_callback_data(
    action: str, 
    object_type: Optional[str] = None,
    object_id: Optional[str] = None,
    additional_data: Optional[str] = None,
    max_id_length: int = 30
) -> str:
    """
    Create standardized callback data string.
    
    Args:
        action: Action identifier (e.g., "menu", "back", "stats").
        object_type: Type of object (e.g., "account", "campaign", "ad").
        object_id: ID of the object.
        additional_data: Any additional data to include.
        max_id_length: Maximum length for object_id if truncation is needed.
        
    Returns:
        Formatted callback data string.
    """
    parts = [action]
    
    if object_type:
        parts.append(object_type)
        
    if object_id:
        # Truncate ID if too long
        id_part = object_id
        if len(id_part) > max_id_length:
            id_part = id_part[:max_id_length]
        parts.append(id_part)
        
    if additional_data:
        parts.append(additional_data)
    
    callback_data = ':'.join(parts)
    
    # Validate the final callback data length
    if not validate_callback_data(callback_data):
        # If too long, try without additional_data
        if additional_data:
            return create_callback_data(action, object_type, object_id, None, max_id_length)
        # If still too long, truncate the ID further
        if object_id and max_id_length > 15:
            return create_callback_data(action, object_type, object_id, None, max_id_length - 5)
        # Last resort: just use action and type
        return f"{action}:{object_type}" if object_type else action
    
    return callback_data


def format_button_text(name: str, max_length: int = 30) -> str:
    """
    Format button text, ensuring it doesn't exceed maximum length.
    
    Args:
        name: Original text for button.
        max_length: Maximum length for button text.
        
    Returns:
        Formatted button text.
    """
    return truncate_text(name, max_length) 