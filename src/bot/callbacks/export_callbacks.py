"""
Export callback handlers for the Facebook Ads Telegram Bot.
"""
import os
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.exceptions import TelegramBadRequest

from src.storage.database import get_session
from src.storage.models import Cache
from src.utils.export import export_data_to_csv, export_data_to_json, export_data_to_excel
from src.utils.error_handlers import handle_exceptions, api_error_handler

# Setup logger
logger = logging.getLogger(__name__)

# Create a router for export callbacks
export_router = Router()

@export_router.callback_query(F.data.startswith("export:"))
@handle_exceptions(notify_user=True, log_error=True)
async def export_callback(callback: CallbackQuery):
    """
    Handle export requests.
    Callback data format: export:user_id:export_key:format
    """
    try:
        await callback.answer()
    except Exception as e:
        logger.warning(f"Error answering export callback: {str(e)}")
        # Continue even if we can't answer the callback
        pass
    
    # Get the user ID
    user_id = callback.from_user.id
    
    # Fix for the issue where bot ID might be used
    if user_id == 8113924050 or str(user_id) == "8113924050":
        from src.storage.database import get_session
        from src.storage.models import User
        
        # Try to find a valid user
        session = get_session()
        try:
            user = session.query(User).filter(User.telegram_id != 8113924050).first()
            if user:
                print(f"DEBUG: Replacing bot ID with user ID in export callback: {user.telegram_id}")
                user_id = user.telegram_id
        except Exception as e:
            print(f"DEBUG: Error finding alternative user in export callback: {str(e)}")
        finally:
            session.close()
    
    parts = callback.data.split(":")
    if len(parts) < 4:
        await callback.message.edit_text("❌ Invalid export request format.")
        return
    
    # Use our user_id instead of the one from callback data
    _, _, export_key, export_format = parts
    
    # Show loading message
    try:
        await callback.message.edit_text("⏳ Preparing export file...", parse_mode="HTML")
    except TelegramBadRequest:
        # Message was deleted or can't be edited
        return
    
    # Get the cached data
    session = get_session()
    try:
        cache_data = Cache.get(session, export_key)
        if not cache_data:
            await callback.message.edit_text("❌ Export data not found or expired. Please try again.")
            return
            
        file_path = None
        filename = f"facebook_ads_export_{export_key.split(':')[-1]}"
        
        # Export in the requested format
        if export_format == "csv":
            file_path = export_data_to_csv(cache_data, filename)
        elif export_format == "json":
            file_path = export_data_to_json(cache_data, filename)
        elif export_format == "excel":
            file_path = export_data_to_excel(cache_data, filename)
        else:
            await callback.message.edit_text(f"❌ Unsupported export format: {export_format}")
            return
            
        # Send the file
        if file_path and os.path.exists(file_path):
            await callback.message.delete()
            with open(file_path, "rb") as file:
                await callback.message.answer_document(file, caption=f"📊 Facebook Ads data export in {export_format.upper()} format")
            
            # Clean up the file
            try:
                os.remove(file_path)
            except Exception:
                pass
        else:
            await callback.message.edit_text("❌ Failed to create export file.")
            
    except Exception as e:
        await callback.message.edit_text(f"❌ Error exporting data: {str(e)}")
    finally:
        session.close() 