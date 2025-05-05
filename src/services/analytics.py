"""
Сервис для анализа статистики и интеграции с OpenAI.
"""
from typing import Dict, List, Optional, Tuple, Union
from datetime import datetime, timedelta
from enum import Enum
import openai
from dataclasses import dataclass

from src.utils.logger import get_logger
from src.api.facebook import FacebookAdsClient
from src.data.processor import DataProcessor

logger = get_logger(__name__)

class ComparisonPeriod(str, Enum):
    """Периоды для сравнения статистики."""
    DAILY = "daily"  # вчера vs позавчера
    WEEKLY = "weekly"  # эта неделя vs прошлая
    BIWEEKLY = "biweekly"  # 2 недели vs 4 недели

@dataclass
class PeriodDates:
    """Даты для сравнения периодов."""
    current_start: datetime
    current_end: datetime
    previous_start: datetime
    previous_end: datetime

class AnalyticsService:
    """Сервис для анализа статистики и генерации рекомендаций."""
    
    def __init__(self, openai_api_key: str):
        """
        Инициализация сервиса.
        
        Args:
            openai_api_key: API ключ для OpenAI
        """
        self.openai_client = openai.OpenAI(api_key=openai_api_key)
        
    def _get_period_dates(self, period: ComparisonPeriod) -> PeriodDates:
        """
        Получает даты для сравнения на основе выбранного периода.
        
        Args:
            period: Тип периода для сравнения
            
        Returns:
            Объект с датами для текущего и предыдущего периодов
        """
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        if period == ComparisonPeriod.DAILY:
            yesterday = today - timedelta(days=1)
            day_before = today - timedelta(days=2)
            return PeriodDates(
                current_start=yesterday,
                current_end=yesterday,  # Только один день
                previous_start=day_before,
                previous_end=day_before  # Только один день
            )
            
        elif period == ComparisonPeriod.WEEKLY:
            # Находим начало текущей недели (понедельник)
            current_week_start = today - timedelta(days=today.weekday())
            prev_week_start = current_week_start - timedelta(weeks=1)
            prev_week_end = current_week_start - timedelta(days=1)
            
            return PeriodDates(
                current_start=current_week_start,
                current_end=today,
                previous_start=prev_week_start,
                previous_end=prev_week_end
            )
            
        elif period == ComparisonPeriod.BIWEEKLY:
            # Последние 14 дней vs последние 28 дней
            two_weeks_ago = today - timedelta(days=14)
            four_weeks_ago = today - timedelta(days=28)
            
            return PeriodDates(
                current_start=two_weeks_ago,
                current_end=today,
                previous_start=four_weeks_ago,
                previous_end=today
            )
            
        raise ValueError(f"Неподдерживаемый период сравнения: {period}")
    
    async def get_comparative_insights(
        self,
        user_id: int,
        account_id: str,
        period: ComparisonPeriod
    ) -> Tuple[Dict, Dict]:
        """
        Получает и сравнивает статистику за два периода.
        
        Args:
            user_id: ID пользователя
            account_id: ID рекламного аккаунта
            period: Период для сравнения
            
        Returns:
            Кортеж из статистики текущего и предыдущего периодов
        """
        dates = self._get_period_dates(period)
        
        async with FacebookAdsClient(user_id) as fb_client:
            # Получаем статистику за текущий период
            current_insights = await fb_client.get_account_insights(
                account_id,
                date_preset=None,  # Используем кастомные даты
                start_date=dates.current_start,
                end_date=dates.current_end
            )
            
            # Получаем статистику за предыдущий период
            previous_insights = await fb_client.get_account_insights(
                account_id,
                date_preset=None,
                start_date=dates.previous_start,
                end_date=dates.previous_end
            )
            
            return current_insights, previous_insights
            
    async def analyze_insights(
        self,
        current_insights: List[Dict],
        previous_insights: List[Dict],
        account_name: str
    ) -> str:
        """
        Анализирует статистику и генерирует рекомендации с помощью OpenAI.
        
        Args:
            current_insights: Статистика текущего периода
            previous_insights: Статистика предыдущего периода
            account_name: Название аккаунта
            
        Returns:
            Текст с анализом и рекомендациями
        """
        # Форматируем статистику для обоих периодов
        current_stats = DataProcessor.format_insights(current_insights, account_name)
        previous_stats = DataProcessor.format_insights(previous_insights, account_name)
        
        if not current_stats or not previous_stats:
            return "Недостаточно данных для анализа"
            
        # Готовим промпт для OpenAI
        prompt = f"""
        Проанализируй статистику рекламного аккаунта Facebook и предоставь рекомендации по улучшению.
        
        Текущий период:
        {current_stats}
        
        Предыдущий период:
        {previous_stats}
        
        Пожалуйста, проанализируй:
        1. Основные изменения в метриках
        2. Возможные причины изменений
        3. Конкретные рекомендации по улучшению
        4. На что стоит обратить особое внимание
        
        Формат ответа:
        - Краткое описание изменений
        - Анализ причин
        - 3-4 конкретные рекомендации
        - Важные замечания
        """
        
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "Ты - опытный специалист по Facebook рекламе. Анализируешь статистику и даешь конкретные рекомендации по улучшению."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Ошибка при получении рекомендаций от OpenAI: {str(e)}")
            return "Не удалось получить рекомендации. Пожалуйста, попробуйте позже."

    async def get_comprehensive_analysis(
        self,
        user_id: int,
        account_id: str,
        account_name: str
    ) -> str:
        """
        Получает комплексный анализ по трем периодам сравнения.
        
        Args:
            user_id: ID пользователя
            account_id: ID рекламного аккаунта
            account_name: Название аккаунта
            
        Returns:
            Текст с комплексным анализом
        """
        analysis_texts = []
        header = f"Отчет для аккаунта {account_name}\n\n"
        
        # Анализируем все три периода
        periods = [
            (ComparisonPeriod.DAILY, "daily", False),  # Не нормализуем дневные данные
            (ComparisonPeriod.WEEKLY, "weekly", True),  # Нормализуем недельные данные
            (ComparisonPeriod.BIWEEKLY, "monthly", True)  # Нормализуем двухнедельные данные
        ]
        
        # Проверяем активность аккаунта за последние 2 недели
        try:
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            two_weeks_ago = today - timedelta(days=14)
            
            async with FacebookAdsClient(user_id) as fb_client:
                recent_insights = await fb_client.get_account_insights(
                    account_id,
                    date_preset=None,
                    start_date=two_weeks_ago,
                    end_date=today
                )
            
            if recent_insights:
                # Проверяем наличие активности
                total_spend = sum(float(i.get('spend', 0)) for i in recent_insights)
                total_conversions = 0
                
                # Подсчитываем общее количество конверсий
                for insight in recent_insights:
                    for conversion in insight.get('conversions', []):
                        action_type = conversion.get('action_type', '')
                        # Проверяем как кастомные конверсии, так и стандартные лиды
                        if action_type.startswith('offsite_conversion.fb_pixel_custom.') or \
                           action_type in ['lead', 'offsite_conversion.fb_pixel_lead']:
                            total_conversions += float(conversion.get('value', 0))
                
                logger.info(f"Account {account_id} activity check: spend={total_spend}, conversions={total_conversions}")
                
                # Аккаунт считается неактивным, если нет расходов ИЛИ конверсий за последние 2 недели
                if total_spend <= 0 or total_conversions <= 0:
                    logger.info(f"Account {account_id} marked as inactive: no spend or conversions in last 2 weeks")
                    return None
            else:
                logger.info(f"Account {account_id} marked as inactive: no insights data")
                return None
                
        except Exception as e:
            logger.error(f"Ошибка при проверке активности аккаунта {account_id}: {str(e)}")
            return None
        
        # Собираем статистику по всем периодам
        for period, period_type, should_normalize in periods:
            try:
                current_insights, previous_insights = await self.get_comparative_insights(
                    user_id, account_id, period
                )
                
                # Проверяем наличие данных
                if not current_insights or not previous_insights:
                    continue
                    
                # Форматируем статистику
                comparison_text = DataProcessor.format_comparative_insights(
                    current_insights,
                    previous_insights,
                    account_name,
                    show_details=True,
                    normalize_by_days=should_normalize,
                    period_type=period_type
                )
                
                if comparison_text:
                    # Добавляем разделитель между периодами
                    if analysis_texts:
                        analysis_texts.append("")
                    analysis_texts.append(comparison_text)
                    
            except Exception as e:
                logger.error(f"Ошибка при анализе периода {period}: {str(e)}")
                continue
        
        if not analysis_texts:
            return None
        
        return header + "\n".join(analysis_texts) 