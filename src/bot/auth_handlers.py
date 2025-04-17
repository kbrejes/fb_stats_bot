"""
Bridge file for backward compatibility.
This file re-exports components from the handlers/auth.py package.
"""
import logging

# Import router from the new location
from src.bot.handlers.auth import router
from src.bot.handlers.auth import (
    cmd_auth,
    process_auth_code,
    AuthStates
)

# Log a deprecation warning
logger = logging.getLogger(__name__)
logger.warning(
    "The module 'src.bot.auth_handlers' is deprecated and will be removed in a future version. "
    "Please use 'src.bot.handlers.auth' instead."
)

# Export router for backward compatibility
__all__ = ['router', 'AuthStates', 'cmd_auth', 'process_auth_code'] 