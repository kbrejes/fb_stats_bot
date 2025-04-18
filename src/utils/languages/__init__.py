"""
Language support for the Telegram bot.
"""
import warnings

# Import from new localization system
from src.utils.localization import (
    get_text, 
    set_language, 
    get_language, 
    get_available_languages as _get_available_languages,
    _
)

# Keep fix_user_id in original location for backward compatibility
from src.utils.languages.new_language_manager import fix_user_id

# For backward compatibility
SUPPORTED_LANGUAGES = _get_available_languages()

# Show deprecation warning
warnings.warn(
    "The module 'src.utils.languages' is deprecated. "
    "Please use 'src.utils.localization' instead.",
    DeprecationWarning,
    stacklevel=2
) 