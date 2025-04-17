"""
Bridge file for backward compatibility.
This file re-exports components from the handlers/ad.py package.
"""
import logging

# Import router from the new location
from src.bot.handlers.ad import router
from src.bot.handlers.ad import (
    cmd_ads,
    process_ads
)

# Log a deprecation warning
logger = logging.getLogger(__name__)
logger.warning(
    "The module 'src.bot.ad_handlers' is deprecated and will be removed in a future version. "
    "Please use 'src.bot.handlers.ad' instead."
)

# Export router for backward compatibility
__all__ = ['router', 'process_ads', 'cmd_ads'] 