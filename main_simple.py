"""
Simplified main entry point for the Facebook Ads Telegram Bot.
Only essential functionality for production.
"""
import asyncio
import logging
import sys
import os

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/app/logs/bot.log')
    ]
)
logger = logging.getLogger(__name__)

async def start_health_server():
    """Запуск простого health check сервера."""
    from aiohttp import web
    
    async def health_handler(request):
        return web.json_response({
            "status": "ok", 
            "timestamp": "2024-01-01T00:00:00Z",
            "service": "facebook-ads-bot"
        })
    
    app = web.Application()
    app.router.add_get('/health', health_handler)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()
    
    logger.info("Health check server started on port 8080")
    return runner

async def start_bot():
    """Запуск Telegram бота."""
    try:
        from src.bot import bot, dp, main_router
        from src.bot.handlers import router as common_router
        
        # Подключаем основные роутеры
        main_router.include_router(common_router)
        dp.include_router(main_router)
        
        logger.info("Starting bot polling...")
        await dp.start_polling(bot)
        
    except Exception as e:
        logger.error(f"Bot error: {e}")
        raise

async def main():
    """Главная функция."""
    try:
        logger.info("🚀 Starting Facebook Ads Telegram Bot (Simple Mode)")
        
        # Запускаем health check сервер
        health_runner = await start_health_server()
        
        # Запускаем бота
        await start_bot()
        
    except Exception as e:
        logger.error(f"Application error: {e}")
        sys.exit(1)
    finally:
        logger.info("Shutting down...")
        if 'health_runner' in locals():
            await health_runner.cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.critical(f"Critical error: {e}")
        sys.exit(1) 