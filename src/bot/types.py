"""
Type definitions for the Telegram bot.

This module defines common types used throughout the bot, including API data structures,
callback data types, and more. Using these types improves code readability and type safety.
"""
from typing import TypedDict, Dict, List, Any, Union, Optional, Literal, Tuple, TypeVar, NewType
from datetime import datetime

# User and ID types
UserId = int
TelegramId = int
FacebookUserId = str

# API Response types
APIResponse = Dict[str, Any]  # Base type for API responses

# Account types
class AccountData(TypedDict):
    """Type definition for Facebook Ad Account data."""
    id: str  # Format: act_XXXXXX
    account_id: str  # Format: XXXXXX (without "act_" prefix)
    name: str
    status: int  # 1 = active, 2 = disabled, etc.
    currency: str
    spent: float
    balance: float

AccountList = List[AccountData]
AccountId = str  # Format: act_XXXXXX

# Campaign types
class CampaignData(TypedDict):
    """Type definition for Facebook Campaign data."""
    id: str
    name: str
    status: str
    objective: str
    created_time: str
    start_time: Optional[str]
    stop_time: Optional[str]
    spend_cap: Optional[float]
    budget_remaining: Optional[float]
    daily_budget: Optional[float]

CampaignList = List[CampaignData]
CampaignId = str

# Ad types
class AdData(TypedDict):
    """Type definition for Facebook Ad data."""
    id: str
    name: str
    status: str
    created_time: str
    updated_time: str
    creative: Optional[Dict[str, Any]]
    adset_id: str
    campaign_id: str

AdList = List[AdData]
AdId = str

# Insights types
class InsightMetric(TypedDict):
    """Type definition for a single insight metric."""
    value: str
    date_start: Optional[str]
    date_stop: Optional[str]

class InsightData(TypedDict):
    """Type definition for Facebook Insights data."""
    impressions: int
    clicks: int
    spend: float
    ctr: float
    cpc: float
    reach: int
    date_start: str
    date_stop: str
    actions: Optional[List[Dict[str, Any]]]

# Callback data types
CallbackData = str  # Base type for all callback data

# Type for specific callback data formats
class AccountCallbackData(TypedDict):
    """Type for account callback data."""
    type: Literal['account']
    id: str

class CampaignCallbackData(TypedDict):
    """Type for campaign callback data."""
    type: Literal['campaign']
    id: str
    account_id: Optional[str]

class AdCallbackData(TypedDict):
    """Type for ad callback data."""
    type: Literal['ad']
    id: str
    campaign_id: Optional[str]

class DatePresetCallbackData(TypedDict):
    """Type for date preset callback data."""
    type: Literal['date_preset']
    preset: str
    target_id: Optional[str]
    target_type: Optional[Literal['account', 'campaign', 'ad']]

class FilterCallbackData(TypedDict):
    """Type for filter callback data."""
    type: Literal['filter']
    filter_type: str
    value: str

# Menu callback data
class MenuCallbackData(TypedDict):
    """Type for menu callback data."""
    type: Literal['menu']
    action: str

# Time range for insights
class TimeRange(TypedDict):
    """Type for time range selections."""
    since: str  # Format: YYYY-MM-DD
    until: str  # Format: YYYY-MM-DD

# Date preset for insights
DatePreset = Literal[
    'today', 'yesterday', 'this_week', 'last_7_days', 
    'last_14_days', 'last_28_days', 'last_30_days', 
    'last_90_days', 'this_month', 'last_month', 
    'this_quarter', 'last_quarter', 'this_year', 
    'last_year', 'lifetime'
]

# Error types
class ErrorResponse(TypedDict):
    """Type for formatted error responses."""
    success: Literal[False]
    error: str
    code: Optional[str]
    details: Optional[Dict[str, Any]]

# Success response
class SuccessResponse(TypedDict, total=False):
    """Type for formatted success responses."""
    success: Literal[True]
    data: Any
    message: Optional[str]

# Combined response type
Response = Union[ErrorResponse, SuccessResponse]

# Handler types
class CommandHandler:
    """Type definition for command handlers."""
    pass

class CallbackHandler:
    """Type definition for callback handlers."""
    pass 