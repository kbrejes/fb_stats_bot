"""
Bridge file for backward compatibility.
This file re-exports components from the handlers/campaign.py package.
"""
import logging

# Import router from the new location
from src.bot.handlers.campaign import router
from src.bot.handlers.campaign import (
    cmd_campaigns,
    process_campaign_callback,
    process_campaigns
)

# Log a deprecation warning
logger = logging.getLogger(__name__)
logger.warning(
    "The module 'src.bot.campaign_handlers' is deprecated and will be removed in a future version. "
    "Please use 'src.bot.handlers.campaign' instead."
)

# Export router for backward compatibility
__all__ = ['router', 'cmd_campaigns', 'process_campaign_callback', 'process_campaigns'] 