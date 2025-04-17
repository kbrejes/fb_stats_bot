"""
Utility functions for the Telegram bot.
"""
from typing import Tuple, Optional
import logging

from src.storage.database import get_session
from src.storage.models import User

logger = logging.getLogger(__name__)

BOT_ID = 8113924050

async def fix_user_id(user_id: int) -> int:
    """
    Fix user ID if it's the bot ID.
    
    Args:
        user_id: The user ID to check.
        
    Returns:
        The fixed user ID.
    """
    # Check if we're using the bot ID
    if user_id == BOT_ID or str(user_id) == str(BOT_ID):
        # Try to find a valid user
        session = get_session()
        try:
            user = session.query(User).filter(User.telegram_id != BOT_ID).first()
            if user:
                logger.debug(f"Replacing bot ID with user ID: {user.telegram_id}")
                return user.telegram_id
        except Exception as e:
            logger.error(f"Error finding alternative user: {str(e)}")
        finally:
            session.close()
    
    return user_id

async def check_token_validity(user_id: int) -> Tuple[bool, Optional[str]]:
    """
    Check if the user has a valid token.
    
    Args:
        user_id: The user ID to check.
        
    Returns:
        A tuple of (is_valid, expiration_date)
    """
    session = get_session()
    try:
        user = session.query(User).filter_by(telegram_id=user_id).first()
        if not user:
            logger.debug(f"User {user_id} not found")
            return False, None
            
        is_valid = user.is_token_valid()
        expires_at = user.token_expires_at
        
        logger.debug(f"User {user_id} token valid: {is_valid}, expires: {expires_at}")
        return is_valid, expires_at
    except Exception as e:
        logger.error(f"Error checking token validity: {str(e)}")
        return False, None
    finally:
        session.close() 