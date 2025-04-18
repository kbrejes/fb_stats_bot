"""
Centralized error handling system for the Facebook Ads Telegram Bot.

Provides decorators and utilities for handling exceptions across different parts
of the application, including API clients, Telegram handlers, and database operations.
"""

import functools
import logging
import traceback
from typing import Callable, Optional, Type, TypeVar, Union, Any

from aiogram import types
from aiogram.types import Message, CallbackQuery

# Configure logger
logger = logging.getLogger(__name__)

# Type definitions
F = TypeVar('F', bound=Callable[..., Any])
Handler = Callable[[Exception, Any, Any], Any]


class APIError(Exception):
    """Base class for API-related exceptions."""
    pass


class FacebookAPIError(APIError):
    """Exception raised for Facebook API errors."""
    def __init__(self, message: str, error_code: Optional[str] = None, details: Optional[dict] = None):
        self.error_code = error_code
        self.details = details or {}
        super().__init__(message)


class TelegramAPIError(APIError):
    """Exception raised for Telegram API errors."""
    pass


class DatabaseError(Exception):
    """Exception raised for database-related errors."""
    def __init__(self, message: str, operation: Optional[str] = None):
        self.operation = operation
        super().__init__(message)


class AuthorizationError(Exception):
    """Exception raised for authorization errors."""
    pass


class ValidationError(Exception):
    """Exception raised for data validation errors."""
    def __init__(self, message: str, field: Optional[str] = None, value: Optional[Any] = None):
        self.field = field
        self.value = value
        super().__init__(message)


def default_error_handler(
    exception: Exception, 
    update: Optional[Union[types.Message, types.CallbackQuery]] = None,
    context: Optional[Any] = None
) -> None:
    """
    Default handler for unhandled exceptions.
    
    Args:
        exception: The exception that was raised
        update: The update that caused the exception (Message or CallbackQuery)
        context: Additional context (usually from the handler)
    """
    error_text = f"Error: {str(exception)}"
    error_traceback = "".join(traceback.format_exception(type(exception), exception, exception.__traceback__))
    
    logger.error(f"Unhandled exception: {error_text}\n{error_traceback}")

    if update:
        if isinstance(update, types.CallbackQuery):
            update.answer(text="An error occurred during processing", show_alert=True)
        elif isinstance(update, types.Message):
            update.answer("Sorry, an error occurred while processing your request.")


async def send_error_message(
    update: Union[types.Message, types.CallbackQuery], 
    text: str, 
    show_alert: bool = False
) -> None:
    """
    Send an error message to the user.
    
    Args:
        update: The update to respond to (Message or CallbackQuery)
        text: Error message text
        show_alert: Whether to show as alert (for CallbackQuery only)
    """
    try:
        if isinstance(update, types.CallbackQuery):
            await update.answer(text=text, show_alert=show_alert)
        elif isinstance(update, types.Message):
            await update.answer(text)
    except Exception as e:
        logger.error(f"Failed to send error message: {e}")


def handle_exceptions(
    error_handler: Optional[Handler] = None,
    notify_user: bool = True,
    log_error: bool = True,
    exception_types: tuple = (Exception,)
) -> Callable[[F], F]:
    """
    Decorator to handle exceptions in handler functions.
    
    Args:
        error_handler: Custom error handler function
        notify_user: Whether to notify the user about the error
        log_error: Whether to log the error
        exception_types: Tuple of exception types to catch
        
    Returns:
        Decorated function
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            update = None
            
            # Try to find the update object (Message or CallbackQuery)
            for arg in args:
                if isinstance(arg, (types.Message, types.CallbackQuery)):
                    update = arg
                    break
            
            try:
                return await func(*args, **kwargs)
            except exception_types as e:
                if log_error:
                    logger.error(
                        f"Error in {func.__name__}: {str(e)}\n"
                        f"{''.join(traceback.format_exception(type(e), e, e.__traceback__))}"
                    )
                
                if error_handler:
                    return await error_handler(e, update, {'args': args, 'kwargs': kwargs})
                elif notify_user and update:
                    error_message = "Sorry, an error occurred while processing your request."
                    
                    if isinstance(e, FacebookAPIError):
                        error_message = f"Facebook API Error: {str(e)}"
                    elif isinstance(e, AuthorizationError):
                        error_message = f"Authorization Error: {str(e)}"
                    elif isinstance(e, ValidationError):
                        error_message = f"Invalid input: {str(e)}"
                    
                    await send_error_message(update, error_message)
                
                # Return None or raise the exception depending on needs
                return None
                
        return wrapper
    return decorator


def api_error_handler(
    api_name: str = "API", 
    notify_user: bool = True,
    log_error: bool = True
) -> Callable[[F], F]:
    """
    Decorator to handle API-related exceptions.
    
    Args:
        api_name: Name of the API for logging purposes
        notify_user: Whether to notify the user about the error
        log_error: Whether to log the error
        
    Returns:
        Decorated function
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            update = None
            
            # Try to find the update object
            for arg in args:
                if isinstance(arg, (types.Message, types.CallbackQuery)):
                    update = arg
                    break
                    
            try:
                return await func(*args, **kwargs)
            except APIError as e:
                if log_error:
                    logger.error(
                        f"{api_name} error in {func.__name__}: {str(e)}\n"
                        f"{''.join(traceback.format_exception(type(e), e, e.__traceback__))}"
                    )
                
                if notify_user and update:
                    error_message = f"{api_name} Error: {str(e)}"
                    await send_error_message(update, error_message)
                    
                raise
                
        return wrapper
    return decorator


def db_error_handler(
    operation: str = "database operation",
    notify_user: bool = True,
    log_error: bool = True
) -> Callable[[F], F]:
    """
    Decorator to handle database-related exceptions.
    
    Args:
        operation: Description of the database operation
        notify_user: Whether to notify the user about the error
        log_error: Whether to log the error
        
    Returns:
        Decorated function
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            update = None
            
            # Try to find the update object
            for arg in args:
                if isinstance(arg, (types.Message, types.CallbackQuery)):
                    update = arg
                    break
                    
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                db_error = DatabaseError(f"Failed during {operation}: {str(e)}", operation=operation)
                
                if log_error:
                    logger.error(
                        f"Database error in {func.__name__}: {str(db_error)}\n"
                        f"{''.join(traceback.format_exception(type(e), e, e.__traceback__))}"
                    )
                
                if notify_user and update:
                    error_message = f"Database Error: Failed to {operation}."
                    await send_error_message(update, error_message)
                    
                raise db_error from e
                
        return wrapper
    return decorator


def auth_required(
    error_message: str = "You need to authorize first. Use /auth command."
) -> Callable[[F], F]:
    """
    Decorator to check if user is authorized before proceeding.
    
    Args:
        error_message: Message to show when user is not authorized
        
    Returns:
        Decorated function
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            from src.db.repositories.user_repository import UserRepository
            
            update = None
            user_id = None
            
            # Try to find the update object and user_id
            for arg in args:
                if isinstance(arg, types.Message):
                    update = arg
                    user_id = update.from_user.id
                    break
                elif isinstance(arg, types.CallbackQuery):
                    update = arg
                    user_id = update.from_user.id
                    break
            
            if not user_id:
                raise ValueError("Could not determine user ID from arguments")
            
            user_repo = UserRepository()
            user = await user_repo.get_by_telegram_id(user_id)
            
            if not user or not user.facebook_token:
                if update:
                    await send_error_message(update, error_message)
                raise AuthorizationError("User is not authorized with Facebook")
            
            return await func(*args, **kwargs)
                
        return wrapper
    return decorator


def register_error_handlers(dp) -> None:
    """
    Register error handlers for the dispatcher.
    
    Args:
        dp: Aiogram Dispatcher instance
    """
    # Register your error handlers here
    pass 