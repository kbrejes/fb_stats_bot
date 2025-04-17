"""
Bridge file for backward compatibility.
This file re-exports components from the handlers/ package.
"""
import logging
from warnings import warn

# Import routers from the new location
from src.bot.handlers.common import router
from src.bot.handlers.common import (
    cmd_start,
    cmd_menu,
    cmd_language,
    process_back_callback,
    process_language_callback
)

# Log a deprecation warning
logger = logging.getLogger(__name__)
logger.warning(
    "The module 'src.bot.handlers' is deprecated and will be removed in a future version. "
    "Please use the modules in 'src.bot.handlers/' package instead."
)

# Export router for backward compatibility
__all__ = [
    'router',
    'cmd_start',
    'cmd_menu',
    'cmd_language',
    'process_back_callback',
    'process_language_callback'
] 