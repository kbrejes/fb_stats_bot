"""
Test script for the Facebook Ads Telegram Bot integration with error handling system.
This script sends test requests to the bot to verify it's working properly.
"""
import asyncio
import logging
import sys
from aiogram import Bot, types
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from config.settings import BOT_TOKEN, ADMIN_USERS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Colors for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
ENDC = '\033[0m'

# Test bot setup
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

# Default test user ID if no admin users are specified
DEFAULT_TEST_USER_ID = 400133981  # Реальный Telegram ID пользователя из базы данных

async def test_start_command():
    """Test the /start command."""
    logger.info(f"{BLUE}Testing /start command...{ENDC}")
    try:
        # Use the first admin ID for testing, or default if not available
        admin_id = ADMIN_USERS[0] if ADMIN_USERS else DEFAULT_TEST_USER_ID
        
        # Send /start command
        await bot.send_message(admin_id, "/start")
        logger.info(f"{GREEN}Successfully sent /start command to user {admin_id}{ENDC}")
        return True
    except Exception as e:
        logger.error(f"{RED}Error testing /start command: {str(e)}{ENDC}")
        return False

async def test_menu_command():
    """Test the /menu command."""
    logger.info(f"{BLUE}Testing /menu command...{ENDC}")
    try:
        # Use the first admin ID for testing, or default if not available
        admin_id = ADMIN_USERS[0] if ADMIN_USERS else DEFAULT_TEST_USER_ID
        
        # Send /menu command
        await bot.send_message(admin_id, "/menu")
        logger.info(f"{GREEN}Successfully sent /menu command to user {admin_id}{ENDC}")
        return True
    except Exception as e:
        logger.error(f"{RED}Error testing /menu command: {str(e)}{ENDC}")
        return False

async def test_accounts_command():
    """Test the /accounts command."""
    logger.info(f"{BLUE}Testing /accounts command...{ENDC}")
    try:
        # Use the first admin ID for testing, or default if not available
        admin_id = ADMIN_USERS[0] if ADMIN_USERS else DEFAULT_TEST_USER_ID
        
        # Send /accounts command
        await bot.send_message(admin_id, "/accounts")
        logger.info(f"{GREEN}Successfully sent /accounts command to user {admin_id}{ENDC}")
        return True
    except Exception as e:
        logger.error(f"{RED}Error testing /accounts command: {str(e)}{ENDC}")
        return False

async def test_invalid_campaign_command():
    """Test the /campaigns command with invalid arguments."""
    logger.info(f"{BLUE}Testing /campaigns command with invalid args...{ENDC}")
    try:
        # Use the first admin ID for testing, or default if not available
        admin_id = ADMIN_USERS[0] if ADMIN_USERS else DEFAULT_TEST_USER_ID
        
        # Send /campaigns command with invalid account ID
        await bot.send_message(admin_id, "/campaigns invalid_account_id")
        logger.info(f"{GREEN}Successfully sent invalid /campaigns command to user {admin_id}{ENDC}")
        return True
    except Exception as e:
        logger.error(f"{RED}Error testing invalid /campaigns command: {str(e)}{ENDC}")
        return False

async def test_ads_command_no_args():
    """Test the /ads command with no arguments - should return an error message."""
    logger.info(f"{BLUE}Testing /ads command with no args...{ENDC}")
    try:
        # Use the first admin ID for testing, or default if not available
        admin_id = ADMIN_USERS[0] if ADMIN_USERS else DEFAULT_TEST_USER_ID
        
        # Send /ads command without arguments - should get an error message that we need campaign ID
        await bot.send_message(admin_id, "/ads")
        logger.info(f"{GREEN}Successfully sent /ads command without args to user {admin_id}{ENDC}")
        return True
    except Exception as e:
        logger.error(f"{RED}Error testing /ads command without args: {str(e)}{ENDC}")
        return False

async def main():
    """Run all tests."""
    logger.info(f"{YELLOW}Starting Facebook Ads Telegram Bot integration tests{ENDC}")
    
    # Run tests
    test_results = await asyncio.gather(
        test_start_command(),
        test_menu_command(),
        test_accounts_command(),
        test_invalid_campaign_command(),
        test_ads_command_no_args()
    )
    
    # Report results
    total_tests = len(test_results)
    passed_tests = sum(1 for result in test_results if result)
    
    logger.info(f"{YELLOW}Test results:{ENDC}")
    logger.info(f"{GREEN if passed_tests == total_tests else RED}Passed: {passed_tests}/{total_tests}{ENDC}")
    
    # Wait a bit to let the bot process commands
    logger.info(f"{YELLOW}Waiting for 5 seconds for bot to process commands...{ENDC}")
    await asyncio.sleep(5)
    
    logger.info(f"{YELLOW}Integration tests completed{ENDC}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Tests stopped manually")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"Unexpected error: {str(e)}")
        sys.exit(1) 