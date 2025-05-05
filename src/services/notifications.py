"""
Сервис для работы с уведомлениями пользователей.
"""
import logging
from datetime import datetime, time
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
from aiogram import Bot

from src.storage.models import User, NotificationSettings, Account, accounts_to_users
from src.utils.logger import get_logger
from src.api.facebook import FacebookAdsClient, FacebookAdsApiError
from src.data.processor import DataProcessor
from src.services.analytics import AnalyticsService
from config.settings import BOT_TOKEN, OPENAI_API_KEY
from src.storage.database import get_session

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('notifications.log')
    ]
)
logger = logging.getLogger(__name__)

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
            logger.info("[DEBUG] Creating new scheduler instance")
            cls._scheduler_instance = AsyncIOScheduler()
            
        if not cls._scheduler_instance.running:
            logger.info("[DEBUG] Starting scheduler")
            cls._scheduler_instance.start()
            logger.info("[DEBUG] Scheduler started successfully")
        else:
            logger.info("[DEBUG] Scheduler is already running")
            
        # Проверяем состояние планировщика
        jobs = cls._scheduler_instance.get_jobs()
        logger.info(f"[DEBUG] Current scheduler state: running={cls._scheduler_instance.running}, jobs={len(jobs)}")
        for job in jobs:
            logger.info(f"[DEBUG] Job: {job.id}, Next run: {job.next_run_time}")
            
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
            logger.info(f"Removing jobs for disabled notifications (user {settings.user_id})")
            self._remove_user_jobs(settings.user_id)
            return
            
        logger.info(
            f"Scheduling notifications for user {settings.user_id} at "
            f"{settings.notification_time} {settings.timezone}"
        )
            
        # Создаем триггер с учетом часового пояса
        trigger = CronTrigger(
            hour=settings.notification_time.hour,
            minute=settings.notification_time.minute,
            timezone=pytz.timezone(settings.timezone)
        )
        
        # Удаляем все старые задачи пользователя
        self._remove_user_jobs(settings.user_id)
        
        # Добавляем новую задачу с уникальным ID
        job_id = f"notifications_{settings.user_id}"  # Упрощаем ID задачи
        
        # Проверяем, нет ли уже такой задачи
        existing_job = self.scheduler.get_job(job_id)
        if existing_job:
            logger.info(f"Removing existing job {job_id}")
            self.scheduler.remove_job(job_id)
        
        self.scheduler.add_job(
            self._send_notifications,
            trigger=trigger,
            args=[settings.user_id],
            id=job_id,
            replace_existing=True  # Заменяем существующую задачу, если она есть
        )
        
        # Получаем следующее время запуска для проверки
        next_run = self.scheduler.get_job(job_id).next_run_time
        
        logger.info(
            f"Scheduled notifications for user {settings.user_id}:\n"
            f"Job ID: {job_id}\n"
            f"Time: {settings.notification_time}\n"
            f"Timezone: {settings.timezone}\n"
            f"Next run: {next_run}"
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
        """Отправляет уведомления пользователю с аналитикой по его аккаунтам."""
        session = None
        try:
            logger.info(f"[DEBUG] Starting notifications for user {user_id}")
            # Создаем новую сессию для этого вызова
            session = get_session()
            
            # Получаем настройки уведомлений
            settings = (session.query(NotificationSettings)
                      .filter(NotificationSettings.user_id == user_id)
                      .first())
            logger.info(f"[DEBUG] Settings for user {user_id}: {settings.enabled if settings else None}")
                      
            if not settings:
                logger.info(f"[DEBUG] No notification settings found for user {user_id}")
                return
                
            if not settings.enabled:
                logger.info(f"[DEBUG] Notifications are disabled for user {user_id}")
                return
                
            # Получаем пользователя
            user = session.query(User).filter_by(telegram_id=user_id).first()
            logger.info(f"[DEBUG] User {user_id} found: {user is not None}, role: {user.role if user else None}")
            
            if not user:
                logger.error(f"User {user_id} not found in database")
                return

            logger.info(f"[DEBUG] Processing notifications for user {user_id} with role {user.role}")

            # Создаем инстанс сервиса аналитики
            analytics_service = AnalyticsService(OPENAI_API_KEY)
            
            # Получаем аккаунты пользователя с учетом прав доступа
            if user.role == "owner":
                # Для owner получаем все аккаунты
                logger.info(f"[DEBUG] Getting all accounts for owner {user_id}")
                fb_client = FacebookAdsClient(user_id)
                accounts = await fb_client.get_ad_accounts()
                logger.info(f"[DEBUG] Found {len(accounts) if accounts else 0} accounts for owner {user_id}")
            else:
                # Для остальных ролей получаем только доступные аккаунты через accounts_to_users
                logger.info(f"[DEBUG] Getting shared accounts for user {user_id}")
                try:
                    # Получаем аккаунты через таблицу accounts_to_users
                    shared_accounts = (session.query(Account)
                                     .join(accounts_to_users)
                                     .filter(accounts_to_users.c.user_id == user_id)
                                     .all())
                    
                    logger.info(f"[DEBUG] Found {len(shared_accounts)} shared accounts for user {user_id}")
                    
                    # Получаем owner_id из базы данных
                    owner = session.query(User).filter_by(role="owner").first()
                    if not owner:
                        logger.error("[DEBUG] Owner not found in database")
                        return
                    
                    owner_id = owner.telegram_id
                    logger.info(f"[DEBUG] Using owner's token (ID: {owner_id}) for API requests")
                    
                    # Получаем данные из Facebook API
                    fb_client = FacebookAdsClient(owner_id)  # Используем токен owner'а
                    accounts = []
                    
                    for account in shared_accounts:
                        try:
                            # Получаем данные аккаунта из Facebook
                            all_accounts = await fb_client.get_ad_accounts()
                            account_data = next(
                                (acc for acc in all_accounts if acc['id'] == account.fb_account_id),
                                None
                            )
                            
                            if account_data:
                                accounts.append(account_data)
                        except Exception as e:
                            logger.error(f"[DEBUG] Error getting data for account {account.fb_account_id}: {str(e)}")
                    
                    logger.info(f"[DEBUG] Successfully retrieved data for {len(accounts)} accounts")
                    
                except Exception as e:
                    logger.error(f"[DEBUG] Error getting shared accounts: {str(e)}")
                    accounts = []
            
            if not accounts:
                logger.info(f"[DEBUG] No accounts found for user {user_id}")
                return
            
            logger.info(f"[DEBUG] Starting to process {len(accounts)} accounts for user {user_id}")
            
            for account in accounts:
                account_id = account.get('id')
                account_name = account.get('name', f"Аккаунт {account_id}")
                logger.info(f"[DEBUG] Processing account {account_id} ({account_name}) for user {user_id}")
                
                try:
                    # Получаем комплексный анализ
                    analysis = await analytics_service.get_comprehensive_analysis(
                        user_id,
                        account_id,
                        account_name
                    )
                    
                    # Пропускаем неактивные аккаунты
                    if analysis is None:
                        logger.info(f"[DEBUG] Account {account_id} is inactive")
                        continue
                    
                    logger.info(f"[DEBUG] Got analysis for account {account_id}, sending notification")
                    
                    # Отправляем уведомление с анализом
                    message = (
                        f"{analysis}"
                    )
                    
                    # Разбиваем длинное сообщение на части
                    message_parts = DataProcessor.truncate_for_telegram(message)
                    
                    # Отправляем каждую часть
                    for part in message_parts:
                        await self.bot.send_message(user_id, part, parse_mode="HTML")
                        logger.info(f"[DEBUG] Sent notification part for account {account_id} to user {user_id}")
                        
                except Exception as e:
                    logger.error(f"[DEBUG] Error processing account {account_id}: {str(e)}")
                    continue
                    
        except Exception as e:
            logger.error(f"[DEBUG] Error in send_notifications: {str(e)}")
            
        finally:
            if session:
                session.close()
            logger.info(f"[DEBUG] Finished notifications for user {user_id}")
    
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