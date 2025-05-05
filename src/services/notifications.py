"""
Сервис для работы с уведомлениями пользователей.
"""
from datetime import datetime, time
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
from aiogram import Bot

from src.storage.models import User, NotificationSettings
from src.utils.logger import get_logger
from src.api.facebook import FacebookAdsClient, FacebookAdsApiError
from src.data.processor import DataProcessor
from config.settings import BOT_TOKEN

logger = get_logger(__name__)

class NotificationService:
    """Сервис для управления уведомлениями пользователей."""
    
    _scheduler_instance = None  # Синглтон для планировщика
    
    @classmethod
    def get_scheduler(cls) -> AsyncIOScheduler:
        """
        Получить единый экземпляр планировщика.
        
        Returns:
            AsyncIOScheduler: Экземпляр планировщика
        """
        if cls._scheduler_instance is None:
            cls._scheduler_instance = AsyncIOScheduler()
            if not cls._scheduler_instance.running:
                cls._scheduler_instance.start()
                logger.info("Started global notification scheduler")
        return cls._scheduler_instance
    
    @classmethod
    async def shutdown(cls):
        """Остановить планировщик и очистить все задачи."""
        if cls._scheduler_instance and cls._scheduler_instance.running:
            cls._scheduler_instance.shutdown(wait=False)
            cls._scheduler_instance = None
            logger.info("Notification scheduler shutdown complete")
    
    def __init__(self, session: Session, scheduler: Optional[AsyncIOScheduler] = None):
        """
        Инициализация сервиса уведомлений.
        
        Args:
            session: Сессия базы данных
            scheduler: Планировщик задач (опционально)
        """
        self.session = session
        self.scheduler = scheduler or self.get_scheduler()
        self.bot = Bot(token=BOT_TOKEN)
    
    async def create_user_notifications(
        self,
        user_id: int,
        notification_time: time,
        timezone: str = "UTC",
        enabled: bool = True,
        notification_types: Optional[Dict[str, bool]] = None
    ) -> NotificationSettings:
        """
        Создать или обновить настройки уведомлений для пользователя.
        
        Args:
            user_id: Telegram ID пользователя
            notification_time: Время отправки уведомлений
            timezone: Часовой пояс пользователя
            enabled: Включены ли уведомления
            notification_types: Типы уведомлений и их статус
            
        Returns:
            Объект настроек уведомлений
        """
        # Проверяем существование пользователя
        user = self.session.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            raise ValueError(f"User with telegram_id {user_id} not found")
            
        # Проверяем валидность часового пояса
        try:
            pytz.timezone(timezone)
        except pytz.exceptions.UnknownTimeZoneError:
            raise ValueError(f"Invalid timezone: {timezone}")
            
        # Получаем или создаем настройки
        settings = (self.session.query(NotificationSettings)
                   .filter(NotificationSettings.user_id == user_id)
                   .first())
                   
        if not settings:
            settings = NotificationSettings(
                user_id=user_id,
                notification_time=notification_time,
                timezone=timezone,
                enabled=enabled,
                notification_types=notification_types or {
                    'daily_stats': True,
                    'performance_alerts': True,
                    'budget_alerts': True
                }
            )
            self.session.add(settings)
        else:
            settings.notification_time = notification_time
            settings.timezone = timezone
            settings.enabled = enabled
            if notification_types:
                settings.notification_types = notification_types
                
        self.session.commit()
        
        # Обновляем расписание для пользователя
        await self._schedule_user_notifications(settings)
        
        return settings
    
    async def _schedule_user_notifications(self, settings: NotificationSettings):
        """
        Настроить расписание уведомлений для пользователя.
        
        Args:
            settings: Настройки уведомлений пользователя
        """
        if not settings.enabled:
            # Удаляем существующие задачи для пользователя
            self._remove_user_jobs(settings.user_id)
            return
            
        # Создаем триггер с учетом часового пояса
        trigger = CronTrigger(
            hour=settings.notification_time.hour,
            minute=settings.notification_time.minute,
            timezone=pytz.timezone(settings.timezone)
        )
        
        # Удаляем все старые задачи пользователя
        self._remove_user_jobs(settings.user_id)
        
        # Добавляем новую задачу с уникальным ID
        job_id = f"notifications_{settings.user_id}_{datetime.utcnow().timestamp()}"
        self.scheduler.add_job(
            self._send_notifications,
            trigger=trigger,
            args=[settings.user_id],
            id=job_id,
            replace_existing=False  # Изменено на False, так как мы уже удалили старые задачи
        )
        
        logger.info(
            f"Scheduled notifications for user {settings.user_id} at "
            f"{settings.notification_time} {settings.timezone} with job_id {job_id}"
        )
    
    def _remove_user_jobs(self, user_id: int):
        """
        Удалить все задачи планировщика для пользователя.
        
        Args:
            user_id: ID пользователя
        """
        # Находим все задачи, связанные с пользователем
        user_jobs = [job for job in self.scheduler.get_jobs() 
                    if job.id.startswith(f"notifications_{user_id}")]
        
        # Удаляем все найденные задачи
        for job in user_jobs:
            self.scheduler.remove_job(job.id)
            logger.info(f"Removed job {job.id} for user {user_id}")
    
    async def _send_notifications(self, user_id: int):
        """Отправляет уведомления пользователю."""
        try:
            # Получаем настройки уведомлений из сессии
            settings = (self.session.query(NotificationSettings)
                      .filter(NotificationSettings.user_id == user_id)
                      .first())
                      
            if not settings or not settings.enabled:
                return
                
            # Получаем пользователя из БД
            user = self.session.query(User).filter_by(telegram_id=user_id).first()
            if not user:
                logger.error(f"User {user_id} not found in database")
                return
                
            # Создаем клиент Facebook API
            fb_client = FacebookAdsClient(user_id)
            
            # Получаем список рекламных аккаунтов пользователя
            accounts, error = await fb_client.get_accounts()
            if error:
                logger.error(f"Error getting accounts for user {user_id}: {error}")
                return
            
            if not accounts:
                return
                
            messages = []
            
            # Для каждого аккаунта получаем статистику
            for account in accounts:
                account_id = account.get('id')
                account_name = account.get('name', account_id)
                
                try:
                    # Получаем статистику аккаунта
                    insights = await fb_client.get_account_insights(account_id, 'last_7d')
                    
                    if not insights:
                        continue

                    # Форматируем данные
                    formatted_data = DataProcessor.format_insights(insights, account_name)
                    messages.append(formatted_data)
                    
                except Exception as e:
                    logger.error(f"Ошибка при получении статистики для аккаунта {account_id}: {str(e)}")
                    continue
            
            if messages:
                # Объединяем сообщения с разделителем и двойными переносами строк
                final_message = "\n\n***\n\n".join(messages)
                
                # Отправляем сообщение пользователю
                await self.bot.send_message(user_id, final_message)
                
        except Exception as e:
            logger.error(f"Error sending notifications to user {user_id}: {str(e)}")
            if isinstance(e, FacebookAdsApiError):
                logger.error(f"Facebook API Error Code: {e.code}")
    
    async def disable_notifications(self, user_id: int) -> bool:
        """
        Отключить уведомления для пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            True если уведомления были отключены, False если настройки не найдены
        """
        settings = (self.session.query(NotificationSettings)
                   .filter(NotificationSettings.user_id == user_id)
                   .first())
                   
        if not settings:
            return False
            
        settings.enabled = False
        self.session.commit()
        
        # Удаляем задачи планировщика
        self._remove_user_jobs(user_id)
        
        return True
    
    async def get_user_settings(self, user_id: int) -> Optional[NotificationSettings]:
        """
        Получить настройки уведомлений пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Настройки уведомлений или None, если не найдены
        """
        return (self.session.query(NotificationSettings)
                .filter(NotificationSettings.user_id == user_id)
                .first()) 