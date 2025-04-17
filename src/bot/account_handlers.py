"""
Bridge file for backward compatibility.
This file re-exports components from the handlers/account.py package.
"""
import logging

# Import router from the new location
from src.bot.handlers.account import router
from src.bot.handlers.account import (
    cmd_accounts,
    process_account_callback
)

# Log a deprecation warning
logger = logging.getLogger(__name__)
logger.warning(
    "The module 'src.bot.account_handlers' is deprecated and will be removed in a future version. "
    "Please use 'src.bot.handlers.account' instead."
)

# Export router for backward compatibility
__all__ = ['router', 'cmd_accounts', 'process_account_callback'] 