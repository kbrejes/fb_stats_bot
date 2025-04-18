"""
Examples of using the error handling system in various contexts.

This module contains examples of applying error handling decorators
for different types of functions: Telegram handlers, API clients, etc.
"""
from typing import Dict, List, Optional, Any

from aiogram import types
from aiogram.dispatcher import Dispatcher
from aiogram.types import Message, CallbackQuery

from src.api.facebook.client import FacebookAdsClient
from src.utils.error_handlers import (
    handle_exceptions,
    api_error_handler,
    db_error_handler,
    auth_required,
    FacebookAPIError,
    DatabaseError,
    AuthorizationError,
    ValidationError,
    send_error_message
)


# Example 1: Handling errors in a Telegram command handler
@handle_exceptions()
async def cmd_start(message: Message):
    """Command handler for /start with automatic error handling."""
    # Code that might raise an exception
    user_id = message.from_user.id
    
    # If user is not authorized, raise AuthorizationError
    is_authorized = await check_user_auth(user_id)
    if not is_authorized:
        raise AuthorizationError(f"User {user_id} is not authorized")
    
    # Continue execution if user is authorized
    await message.answer("Welcome to the bot! Use /help for assistance.")


# Example 2: Handling errors in a callback handler with custom error handlers
@handle_exceptions(
    error_handler=custom_validation_error_handler,
    exception_types=(ValidationError,)
)
async def process_ad_selection(callback_query: CallbackQuery, state: Any):
    """Ad selection handler with custom validation error handler."""
    ad_id = callback_query.data.split(":")[1]
    
    # Check data validity
    if not is_valid_ad_id(ad_id):
        raise ValidationError(
            f"Invalid ad_id format: {ad_id}",
            field="ad_id"
        )
    
    # Get ad data via Facebook API
    try:
        ad_data = await get_ad_details(ad_id)
        await callback_query.message.answer(f"Ad data: {ad_data}")
    except FacebookAPIError as e:
        # This error will be caught and handled by the handle_exceptions decorator
        raise e


# Example 3: API client with API error handling decorator
@api_error_handler(api_name="Facebook Marketing API")
async def get_ad_details(ad_id: str) -> Dict[str, Any]:
    """
    Get detailed information about an ad via Facebook API.
    
    Args:
        ad_id: Facebook ad ID
    
    Returns:
        Dictionary with ad data
    
    Raises:
        FacebookAPIError: When Facebook API error occurs
    """
    client = FacebookAdsClient()
    
    try:
        # Try to get ad data
        response = await client.get_ad(ad_id)
        return response
    except Exception as e:
        # Convert any exception to FacebookAPIError
        # It will be automatically handled by the api_error_handler decorator
        # and propagated for handle_exceptions
        raise FacebookAPIError(
            f"Error getting ad details: {str(e)}",
            error_code=getattr(e, "error_code", None),
            details={"ad_id": ad_id}
        )


# Example 4: Database function with DB error handling decorator
@db_error_handler(operation="save user preferences")
async def save_user_preferences(user_id: int, preferences: Dict[str, Any]) -> bool:
    """
    Save user preferences to the database.
    
    Args:
        user_id: User ID
        preferences: Dictionary with user preferences
    
    Returns:
        True if operation was successful
    
    Raises:
        DatabaseError: When database error occurs
    """
    try:
        # Code to save preferences to DB
        # ...
        return True
    except Exception as e:
        # Convert exception to DatabaseError
        # It will be handled by the db_error_handler decorator
        raise DatabaseError(
            f"Error saving user preferences: {str(e)}",
            operation="save_preferences"
        )


# Example 5: Combining decorators for functions working with API and DB
@handle_exceptions()
@api_error_handler(api_name="Facebook Ads API")
@db_error_handler(operation="sync ads data")
async def sync_user_ads_data(user_id: int) -> List[Dict[str, Any]]:
    """
    Synchronize user's ad data.
    
    Gets data from Facebook API and saves it to the database.
    
    Args:
        user_id: User ID
    
    Returns:
        List with ad data
    
    Raises:
        FacebookAPIError: When Facebook API error occurs
        DatabaseError: When database error occurs
    """
    # Check user API credentials
    credentials = await get_user_credentials(user_id)
    if not credentials:
        raise AuthorizationError(f"User {user_id} has no Facebook credentials")
    
    # Get data from API
    # If an exception occurs, it will be handled by api_error_handler
    client = FacebookAdsClient(access_token=credentials["access_token"])
    ads_data = await client.get_ads()
    
    # Save data to DB
    # If an exception occurs, it will be handled by db_error_handler
    await save_ads_to_db(user_id, ads_data)
    
    return ads_data


# Example 6: Using authorization required decorator
@auth_required()
async def cmd_stats(message: Message):
    """
    Command that requires user to be authorized.
    The auth_required decorator will check authorization
    and handle the error automatically.
    """
    user_id = message.from_user.id
    stats = await get_user_stats(user_id)
    await message.answer(f"Your stats: {stats}")


# Example dummy helper functions for the examples above
async def check_user_auth(user_id: int) -> bool:
    """Check user authorization."""
    # In real code, this would access DB or cache
    return True

def is_valid_ad_id(ad_id: str) -> bool:
    """Check ad ID validity."""
    # In real code, this would check ID format
    return len(ad_id) > 5

async def custom_validation_error_handler(error: ValidationError, update: types.Message, context: Any):
    """Custom validation error handler."""
    # Validation error handling logic
    field_name = error.field or "value"
    if update:
        if isinstance(update, types.CallbackQuery):
            await update.answer()
            await update.message.answer(f"❗ Invalid {field_name}. Please check your input.")
        elif isinstance(update, types.Message):
            await update.answer(f"❗ Invalid {field_name}. Please check your input.")

async def get_user_credentials(user_id: int) -> Optional[Dict[str, str]]:
    """Get user credentials for Facebook API."""
    # In real code, this would access DB
    return {"access_token": "dummy_token"}

async def save_ads_to_db(user_id: int, ads_data: List[Dict[str, Any]]) -> bool:
    """Save ad data to DB."""
    # In real code, this would access DB
    return True

async def get_user_stats(user_id: int) -> Dict[str, Any]:
    """Get user statistics."""
    # In real code, this would access DB or API
    return {"impressions": 1000, "clicks": 50}


# Register handlers in the dispatcher
def register_handlers(dp: Dispatcher):
    """Register handlers with error handling decorators."""
    dp.register_message_handler(cmd_start, commands=["start"])
    dp.register_message_handler(cmd_stats, commands=["stats"])
    dp.register_callback_query_handler(
        process_ad_selection,
        lambda c: c.data and c.data.startswith("ad:")
    ) 