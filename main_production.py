"""
Production entry point for the Facebook Ads Telegram Bot with health monitoring.
"""
import asyncio
import logging
import sys
import signal
import os
from datetime import datetime

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
from src.utils.health_check import start_health_check_server
from src.storage.models import NotificationSettings, User
from config.settings import ENVIRONMENT, LOG_LEVEL

# Initialize Sentry for error monitoring in production
if ENVIRONMENT == "production":
    try:
        import sentry_sdk
        from sentry_sdk.integrations.logging import LoggingIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
        
        # Configure Sentry (добавьте свой DSN)
        sentry_logging = LoggingIntegration(
            level=logging.INFO,        # Capture info and above as breadcrumbs
            event_level=logging.ERROR  # Send errors as events
        )
        
        # Uncomment and add your Sentry DSN
        # sentry_sdk.init(
        #     dsn="YOUR_SENTRY_DSN_HERE",
        #     integrations=[sentry_logging, SqlalchemyIntegration()],
        #     traces_sample_rate=0.1,
        #     environment=ENVIRONMENT
        # )
        
        print("Sentry monitoring initialized")
    except ImportError:
        print("Sentry not available, continuing without error monitoring")

# Production logging configuration
def setup_production_logging():
    """Настройка логирования для продакшна."""
    # Создаем директорию для логов
    os.makedirs('logs', exist_ok=True)
    
    # Основной logger
    root_logger = logging.getLogger()
    root_logger.setLevel(LOG_LEVEL)
    
    # Форматтер
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(LOG_LEVEL)
    console_handler.setFormatter(formatter)
    
    # File handler для обычных логов
    file_handler = logging.FileHandler('logs/bot_production.log')
    file_handler.setLevel(LOG_LEVEL)
    file_handler.setFormatter(formatter)
    
    # File handler для ошибок
    error_handler = logging.FileHandler('logs/error_production.log')
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    
    # Добавляем handlers
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(error_handler)
    
    return logging.getLogger(__name__)

logger = setup_production_logging()

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

# Global variables for graceful shutdown
health_check_runner = None
bot_task = None

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

async def startup_sequence():
    """Последовательность запуска приложения."""
    global health_check_runner
    
    logger.info("="*50)
    logger.info("Starting Facebook Ads Telegram Bot - PRODUCTION")
    logger.info(f"Environment: {ENVIRONMENT}")
    logger.info(f"Timestamp: {datetime.utcnow().isoformat()}")
    logger.info("="*50)
    
    try:
        # Initialize database
        logger.info("Initializing database...")
        init_db()
        logger.info("✅ Database initialized successfully")
        
        # Start health check server
        logger.info("Starting health check server...")
        health_check_runner = await start_health_check_server(port=8080)
        logger.info("✅ Health check server started on port 8080")
        
        # Setup notifications
        logger.info("Setting up notifications...")
        await setup_notifications()
        logger.info("✅ Notifications setup completed")
        
        # Log startup completion
        logger.info("🚀 All services started successfully")
        logger.info("Bot is ready to receive messages!")
        
    except Exception as e:
        logger.critical(f"❌ Failed to start services: {str(e)}")
        raise

async def shutdown_sequence():
    """Последовательность остановки приложения."""
    global health_check_runner, bot_task
    
    logger.info("="*50)
    logger.info("Shutting down Facebook Ads Telegram Bot...")
    logger.info("="*50)
    
    try:
        # Stop bot polling
        if bot_task:
            bot_task.cancel()
            try:
                await bot_task
            except asyncio.CancelledError:
                logger.info("✅ Bot polling stopped")
        
        # Shutdown notifications
        logger.info("Shutting down notification service...")
        await NotificationService.shutdown()
        logger.info("✅ Notification service stopped")
        
        # Stop health check server
        if health_check_runner:
            logger.info("Stopping health check server...")
            await health_check_runner.cleanup()
            logger.info("✅ Health check server stopped")
        
        # Close bot session
        logger.info("Closing bot session...")
        await bot.session.close()
        logger.info("✅ Bot session closed")
        
        logger.info("🏁 Shutdown completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Error during shutdown: {str(e)}")

def setup_signal_handlers():
    """Настройка обработчиков сигналов для graceful shutdown."""
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        # Создаем новый event loop для shutdown если текущий закрыт
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        loop.create_task(shutdown_sequence())
    
    # Регистрируем обработчики сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

async def run_bot():
    """Запуск бота с обработкой ошибок."""
    global bot_task
    
    try:
        logger.info("Starting bot polling...")
        bot_task = asyncio.create_task(dp.start_polling(bot))
        await bot_task
    except asyncio.CancelledError:
        logger.info("Bot polling was cancelled")
    except Exception as e:
        logger.error(f"Bot polling error: {str(e)}")
        raise

async def main():
    """Main function to run the bot in production."""
    try:
        # Setup signal handlers
        setup_signal_handlers()
        
        # Run startup sequence
        await startup_sequence()
        
        # Run bot
        await run_bot()
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.critical(f"Critical error: {str(e)}")
        # Send to Sentry if available
        if ENVIRONMENT == "production":
            try:
                import sentry_sdk
                sentry_sdk.capture_exception(e)
            except ImportError:
                pass
        sys.exit(1)
    finally:
        await shutdown_sequence()

if __name__ == "__main__":
    try:
        # Ensure environment is set to production
        os.environ["ENVIRONMENT"] = "production"
        
        # Run the application
        asyncio.run(main())
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.critical(f"Unexpected error: {str(e)}")
        sys.exit(1) 