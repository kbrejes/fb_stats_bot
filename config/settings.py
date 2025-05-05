"""
Configuration settings for the application.
"""
import os
from typing import Dict, Any, List
from dotenv import load_dotenv
import logging

# Determine environment
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# Load environment variables from the appropriate .env file
if ENVIRONMENT == "production":
    load_dotenv('.env.prod')
    print("Running in PRODUCTION environment")
elif ENVIRONMENT == "development":
    load_dotenv('.env.dev')
    print("Running in DEVELOPMENT environment")
else:
    # Default to the regular .env file for backward compatibility
    load_dotenv()
    print(f"Running in {ENVIRONMENT} environment with default .env")

# Bot settings
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
BOT_ID = 8113924050  # ID of the bot

# Owner settings
OWNER_ID = int(os.getenv("OWNER_ID", "400133981"))  # Замените YOUR_TELEGRAM_ID на ваш Telegram ID
OWNER_USERNAME = os.getenv("OWNER_USERNAME", "kbrejes")  # Замените на ваш username
OWNER_FIRST_NAME = os.getenv("OWNER_FIRST_NAME", "Owner")

# Admin users
ADMIN_USERS = [int(id) for id in os.getenv("ADMIN_USERS", "").split(",") if id]

# Facebook API settings
FB_APP_ID = os.getenv("FB_APP_ID")
FB_APP_SECRET = os.getenv("FB_APP_SECRET")
FB_REDIRECT_URI = os.getenv("FB_REDIRECT_URI")
FB_API_VERSION = os.getenv("FB_API_VERSION", "v20.0")

# Scope for Facebook permission
FB_SCOPE = [
    "ads_management",
    "ads_read",
    "business_management",
    "public_profile",
    "email"
]

# Date presets for insights
DATE_PRESETS: Dict[str, str] = {
    "today": "today",
    "yesterday": "yesterday",
    "last_3d": "last_3d",
    "last_7d": "last_7d",
    "last_14d": "last_14d",
    "last_28d": "last_28d",
    "last_30d": "last_30d",
    "last_90d": "last_90d",
    "this_month": "this_month",
    "last_month": "last_month",
    "this_quarter": "this_quarter",
    "last_quarter": "last_quarter",
    "this_year": "this_year",
    "last_year": "last_year",
    "last_week_mon_sun": "last_week_mon_sun",
    "last_week_sun_sat": "last_week_sun_sat",
    "this_week_mon_today": "this_week_mon_today", 
    "this_week_sun_today": "this_week_sun_today"
}

# Export formats
EXPORT_FORMATS: List[str] = ["csv", "json", "excel"]

# Database settings
DB_PATH = os.getenv("DB_PATH", "facebook_ads_bot.db")
DB_CONNECTION_STRING = os.getenv('DB_CONNECTION_STRING', 'sqlite:///database.sqlite')

# Security
ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY')
if not ENCRYPTION_KEY:
    raise ValueError("ENCRYPTION_KEY is not set in environment variables")

# Logging settings
DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")
LOG_LEVEL_STR = os.getenv('LOG_LEVEL', 'INFO')
LOG_LEVEL = getattr(logging, LOG_LEVEL_STR) if hasattr(logging, LOG_LEVEL_STR) else logging.INFO 