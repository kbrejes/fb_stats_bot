"""
Health check module для мониторинга состояния приложения.
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Any, Dict, Optional

import psutil
from aiohttp import ClientSession, ClientTimeout, web
from sqlalchemy import text

from config.settings import ENVIRONMENT, FB_APP_ID, OPENAI_API_KEY
from src.storage.database import engine, get_session
from src.utils.logger import get_logger

logger = get_logger(__name__)


class HealthChecker:
    """Класс для проверки состояния различных компонентов системы."""

    def __init__(self):
        self.start_time = time.time()

    async def check_database(self) -> Dict[str, Any]:
        """Проверка состояния базы данных."""
        try:
            session = get_session()
            # Простой запрос для проверки подключения
            session.execute(text("SELECT 1"))
            session.close()

            return {
                "status": "healthy",
                "message": "Database connection successful",
                "response_time_ms": 0,  # TODO: измерить время ответа
            }
        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "message": f"Database error: {str(e)}",
                "response_time_ms": None,
            }

    async def check_openai_api(self) -> Dict[str, Any]:
        """Проверка доступности OpenAI API."""
        try:
            timeout = ClientTimeout(total=10)
            async with ClientSession(timeout=timeout) as session:
                headers = {
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                }

                start_time = time.time()
                async with session.get(
                    "https://api.openai.com/v1/models", headers=headers
                ) as response:
                    response_time = (time.time() - start_time) * 1000

                    if response.status == 200:
                        return {
                            "status": "healthy",
                            "message": "OpenAI API accessible",
                            "response_time_ms": round(response_time, 2),
                        }
                    else:
                        return {
                            "status": "unhealthy",
                            "message": f"OpenAI API returned status {response.status}",
                            "response_time_ms": round(response_time, 2),
                        }
        except Exception as e:
            logger.error(f"OpenAI API health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "message": f"OpenAI API error: {str(e)}",
                "response_time_ms": None,
            }

    async def check_facebook_api(self) -> Dict[str, Any]:
        """Проверка доступности Facebook API."""
        try:
            timeout = ClientTimeout(total=10)
            async with ClientSession(timeout=timeout) as session:
                start_time = time.time()
                async with session.get(
                    f"https://graph.facebook.com/v19.0/{FB_APP_ID}",
                    params={"fields": "name"},
                ) as response:
                    response_time = (time.time() - start_time) * 1000

                    if response.status == 200:
                        return {
                            "status": "healthy",
                            "message": "Facebook API accessible",
                            "response_time_ms": round(response_time, 2),
                        }
                    else:
                        return {
                            "status": "unhealthy",
                            "message": f"Facebook API returned status {response.status}",
                            "response_time_ms": round(response_time, 2),
                        }
        except Exception as e:
            logger.error(f"Facebook API health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "message": f"Facebook API error: {str(e)}",
                "response_time_ms": None,
            }

    def get_system_metrics(self) -> Dict[str, Any]:
        """Получение системных метрик."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)

            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_available_gb = memory.available / (1024**3)

            # Disk usage
            disk = psutil.disk_usage("/")
            disk_percent = disk.percent
            disk_free_gb = disk.free / (1024**3)

            # Uptime
            uptime_seconds = time.time() - self.start_time

            return {
                "cpu": {"usage_percent": round(cpu_percent, 2)},
                "memory": {
                    "usage_percent": round(memory_percent, 2),
                    "available_gb": round(memory_available_gb, 2),
                },
                "disk": {
                    "usage_percent": round(disk_percent, 2),
                    "free_gb": round(disk_free_gb, 2),
                },
                "uptime_seconds": round(uptime_seconds, 2),
                "uptime_human": self._format_uptime(uptime_seconds),
            }
        except Exception as e:
            logger.error(f"Failed to get system metrics: {str(e)}")
            return {"error": f"Failed to get system metrics: {str(e)}"}

    def _format_uptime(self, seconds: float) -> str:
        """Форматирование времени работы в человеко-читаемый вид."""
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        minutes = int((seconds % 3600) // 60)

        if days > 0:
            return f"{days}d {hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"

    async def get_full_health_status(self) -> Dict[str, Any]:
        """Получение полного статуса здоровья системы."""
        # Запускаем все проверки параллельно
        db_check, openai_check, facebook_check = await asyncio.gather(
            self.check_database(),
            self.check_openai_api(),
            self.check_facebook_api(),
            return_exceptions=True,
        )

        # Обработка возможных исключений
        if isinstance(db_check, Exception):
            db_check = {"status": "unhealthy", "message": str(db_check)}
        if isinstance(openai_check, Exception):
            openai_check = {"status": "unhealthy", "message": str(openai_check)}
        if isinstance(facebook_check, Exception):
            facebook_check = {"status": "unhealthy", "message": str(facebook_check)}

        # Определение общего статуса
        all_healthy = all(
            check.get("status") == "healthy"
            for check in [db_check, openai_check, facebook_check]
        )

        overall_status = "healthy" if all_healthy else "unhealthy"

        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "environment": ENVIRONMENT,
            "version": "1.0.0",
            "services": {
                "database": db_check,
                "openai_api": openai_check,
                "facebook_api": facebook_check,
            },
            "system": self.get_system_metrics(),
        }


# Глобальный экземпляр health checker
health_checker = HealthChecker()


# HTTP endpoints для health check
async def health_endpoint(request):
    """Простой health check endpoint."""
    return web.json_response(
        {"status": "ok", "timestamp": datetime.utcnow().isoformat()}
    )


async def health_detailed_endpoint(request):
    """Детальный health check endpoint."""
    health_status = await health_checker.get_full_health_status()
    status_code = 200 if health_status["status"] == "healthy" else 503
    return web.json_response(health_status, status=status_code)


async def metrics_endpoint(request):
    """Endpoint для Prometheus метрик."""
    system_metrics = health_checker.get_system_metrics()

    # Формат Prometheus metrics
    metrics_text = f"""# HELP cpu_usage_percent CPU usage percentage
# TYPE cpu_usage_percent gauge
cpu_usage_percent {system_metrics['cpu']['usage_percent']}

# HELP memory_usage_percent Memory usage percentage  
# TYPE memory_usage_percent gauge
memory_usage_percent {system_metrics['memory']['usage_percent']}

# HELP disk_usage_percent Disk usage percentage
# TYPE disk_usage_percent gauge
disk_usage_percent {system_metrics['disk']['usage_percent']}

# HELP uptime_seconds Application uptime in seconds
# TYPE uptime_seconds counter
uptime_seconds {system_metrics['uptime_seconds']}
"""

    return web.Response(text=metrics_text, content_type="text/plain")


async def create_health_check_app() -> web.Application:
    """Создание aiohttp приложения для health check endpoints."""
    app = web.Application()

    # Добавляем routes
    app.router.add_get("/health", health_endpoint)
    app.router.add_get("/health/detailed", health_detailed_endpoint)
    app.router.add_get("/metrics", metrics_endpoint)

    return app


async def start_health_check_server(port: int = 8080):
    """Запуск HTTP сервера для health check."""
    try:
        app = await create_health_check_app()
        runner = web.AppRunner(app)
        await runner.setup()

        site = web.TCPSite(runner, "0.0.0.0", port)
        await site.start()

        logger.info(f"Health check server started on port {port}")
        logger.info(f"Health check endpoints:")
        logger.info(f"  - http://localhost:{port}/health")
        logger.info(f"  - http://localhost:{port}/health/detailed")
        logger.info(f"  - http://localhost:{port}/metrics")

        return runner
    except Exception as e:
        logger.error(f"Failed to start health check server: {str(e)}")
        raise
