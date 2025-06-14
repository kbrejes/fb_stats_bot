"""
Main entry point for the Facebook Ads Telegram Bot.
"""
import asyncio
import logging
import sys

from src.bot import bot, dp, main_router
from src.storage.database import init_db, get_session
from src.bot.handlers import router as common_router
from src.bot.callbacks import callback_router
from src.bot.account_handlers import router as account_router
from src.bot.campaign_handlers import router as campaign_router
from src.bot.ad_handlers import router as ad_router
from src.bot.auth_handlers import router as auth_router
from src.bot.finite_state_machine import router as fsm_router
from src.bot.notification_handlers import router as notification_router
from src.bot.analytics_handlers import router as analytics_router
from src.services.notifications import NotificationService
from src.utils.logger import setup_logging
from src.storage.models import NotificationSettings, User
from src.utils.health_check import start_health_check_server

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log')
    ]
)
logger = logging.getLogger(__name__)

# Подключаем все роутеры к основному
main_router.include_router(common_router)  # Base router
main_router.include_router(callback_router)  # Callbacks
main_router.include_router(account_router)  # Account-related handlers
main_router.include_router(campaign_router)  # Campaign-related handlers
main_router.include_router(ad_router)  # Ad-related handlers
main_router.include_router(auth_router)  # Auth-related handlers
main_router.include_router(fsm_router)  # FSM router
main_router.include_router(notification_router)  # Notification handlers
main_router.include_router(analytics_router)  # Analytics handlers

# Подключаем основной роутер к диспетчеру
dp.include_router(main_router)

async def setup_notifications():
    """Настройка планировщика уведомлений при запуске."""
    session = get_session()
    try:
        logger.info("Setting up notification scheduler...")
        notification_service = NotificationService(session)
        
        # Получаем всех пользователей с включенными уведомлениями
        settings = (session.query(NotificationSettings)
                   .filter(NotificationSettings.enabled == True)
                   .all())
        
        logger.info(f"Found {len(settings)} users with enabled notifications")
        
        # Настраиваем расписание для каждого пользователя
        for user_settings in settings:
            try:
                await notification_service._schedule_user_notifications(user_settings)
            except Exception as e:
                logger.error(f"Error scheduling notifications for user {user_settings.user_id}: {str(e)}")
                continue
        
        # Проверяем все запланированные задачи
        scheduler = notification_service.get_scheduler()
        jobs = scheduler.get_jobs()
        logger.info(f"Total scheduled jobs: {len(jobs)}")
        for job in jobs:
            logger.info(f"Job: {job.id}, Next run: {job.next_run_time}")
            
    except Exception as e:
        logger.error(f"Error setting up notifications: {str(e)}")
    finally:
        session.close()

async def main():
    """Main function to run the bot."""
    try:
        logger.info("Starting Facebook Ads Telegram Bot...")
        
        # Initialize database
        init_db()
        logger.info("Database initialized")
        
        # Start health check server
        health_runner = await start_health_check_server(port=8080)
        logger.info("Health check server started on port 8080")
        
        # Setup notifications
        await setup_notifications()
        logger.info("Notifications setup completed")
        
        # Start polling
        logger.info("Starting bot polling...")
        await dp.start_polling(bot)
    finally:
        logger.info("Shutting down...")
        await NotificationService.shutdown()
        if 'health_runner' in locals():
            await health_runner.cleanup()
        await bot.session.close()
        logger.info("Shutdown complete")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.critical(f"Unexpected error: {str(e)}")
        sys.exit(1) 