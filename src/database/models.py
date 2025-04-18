"""
Database models for the Facebook Ads Telegram Bot.
Temporary stub for testing the keyboards module.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class User:
    """User model (stub for testing)"""
    
    def __init__(self, id: int, language_code: str = 'en'):
        self.id = id
        self.language_code = language_code
        self.telegram_id = id
    
    async def save(self):
        """Stub for save method"""
        logger.info(f"User {self.id} saved (stub)")
        return True


async def get_user(user_id: int) -> Optional[User]:
    """
    Get user by ID (stub function for testing)
    
    Args:
        user_id: User ID
    
    Returns:
        User object or None
    """
    # In a real implementation, this would query the database
    # For testing, we'll create a stub user
    return User(id=user_id, language_code='en') 