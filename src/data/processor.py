"""
Process and format data for display in Telegram.
"""
import pandas as pd
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime, timedelta
import random

from src.utils.logger import get_logger

logger = get_logger(__name__)

class DataProcessor:
    """
    Process and format data for display.
    """
    
    @staticmethod
    def format_accounts(accounts: List[Dict]) -> str:
        """
        Format a list of accounts into a text table.
        
        Args:
            accounts: List of account data.
            
        Returns:
            Formatted text table.
        """
        if not accounts:
            return "Нет доступных рекламных аккаунтов"
        
        # Create a DataFrame
        df = pd.DataFrame(accounts)
        
        # Select and rename columns
        selected_columns = ['id', 'name', 'status', 'currency']
        if all(col in df.columns for col in selected_columns):
            df = df[selected_columns]
            df.columns = ['ID', 'Название', 'Статус', 'Валюта']
            
            # Convert status codes to human-readable
            status_map = {
                1: 'Активный',
                2: 'Отключен',
                3: 'Не подтвержден',
                7: 'Заблокирован',
                9: 'На рассмотрении',
                100: 'Закрыт',
                101: 'Любой'
            }
            if 'Статус' in df.columns:
                df['Статус'] = df['Статус'].map(lambda x: status_map.get(x, f'Неизвестный ({x})'))
            
            # Format as text table
            header = " | ".join(df.columns)
            separator = "-" * len(header)
            rows = [" | ".join(map(str, row)) for _, row in df.iterrows()]
            
            return f"{header}\n{separator}\n" + "\n".join(rows)
        else:
            # Fallback if expected columns are not found
            return "\n".join([f"{account.get('name', 'Без имени')} ({account.get('id', 'Без ID')})" 
                             for account in accounts])
    
    @staticmethod
    def format_campaigns(campaigns: List[Dict]) -> str:
        """
        Format a list of campaigns into a text table.
        
        Args:
            campaigns: List of campaign data.
            
        Returns:
            Formatted text table.
        """
        if not campaigns:
            return "Нет доступных кампаний"
        
        # Create a DataFrame
        df = pd.DataFrame(campaigns)
        
        # Select and rename columns
        selected_columns = ['id', 'name', 'status', 'objective']
        if all(col in df.columns for col in selected_columns):
            df = df[selected_columns]
            df.columns = ['ID', 'Название', 'Статус', 'Цель']
            
            # Format as text table
            header = " | ".join(df.columns)
            separator = "-" * len(header)
            rows = [" | ".join(map(str, row)) for _, row in df.iterrows()]
            
            return f"{header}\n{separator}\n" + "\n".join(rows)
        else:
            # Fallback if expected columns are not found
            return "\n".join([f"{campaign.get('name', 'Без имени')} ({campaign.get('id', 'Без ID')})" 
                             for campaign in campaigns])
    
    @staticmethod
    def format_ads(ads: List[Dict]) -> str:
        """
        Format a list of ads into a text table.
        
        Args:
            ads: List of ad data.
            
        Returns:
            Formatted text table.
        """
        if not ads:
            return "Нет доступных объявлений"
        
        # Create a DataFrame
        df = pd.DataFrame(ads)
        
        # Select and rename columns
        selected_columns = ['id', 'name', 'status']
        if all(col in df.columns for col in selected_columns):
            df = df[selected_columns]
            df.columns = ['ID', 'Название', 'Статус']
            
            # Format as text table
            header = " | ".join(df.columns)
            separator = "-" * len(header)
            rows = [" | ".join(map(str, row)) for _, row in df.iterrows()]
            
            return f"{header}\n{separator}\n" + "\n".join(rows)
        else:
            # Fallback if expected columns are not found
            return "\n".join([f"{ad.get('name', 'Без имени')} ({ad.get('id', 'Без ID')})" 
                             for ad in ads])
    
    @staticmethod
    def format_insights(insights: List[Dict], account_name: str = "Без имени") -> Optional[str]:
        """
        Форматирует данные инсайтов в новый формат уведомлений.
        
        Args:
            insights: Список инсайтов
            account_name: Название аккаунта
            
        Returns:
            Отформатированный текст уведомления или None если нет данных
        """
        if not insights:
            return None
        
        # Получаем даты из первого инсайта
        try:
            date_start = insights[0].get('date_start')
            date_stop = insights[0].get('date_stop')
            
            if not date_start or not date_stop:
                return None
                
            # Преобразуем строки дат в объекты datetime
            start_date = datetime.strptime(date_start, '%Y-%m-%d')
            end_date = datetime.strptime(date_stop, '%Y-%m-%d')
            
            # Словарь русских названий месяцев
            MONTHS = {
                1: 'января', 2: 'февраля', 3: 'марта', 4: 'апреля',
                5: 'мая', 6: 'июня', 7: 'июля', 8: 'августа',
                9: 'сентября', 10: 'октября', 11: 'ноября', 12: 'декабря'
            }
            
            # Форматируем даты в нужном формате
            start_str = start_date.strftime('%d')
            end_str = end_date.strftime('%d')
            
            # Если месяцы разные, добавляем названия месяцев
            if start_date.month != end_date.month:
                start_str = f"{start_str} {MONTHS[start_date.month]}"
                end_str = f"{end_str} {MONTHS[end_date.month]}"
            else:
                end_str = f"{end_str} {MONTHS[end_date.month]}"
                
        except Exception as e:
            logger.error(f"Error parsing dates: {str(e)}")
            return None
            
        # Собираем статистику
        total_spend = sum(float(i.get('spend', 0)) for i in insights)
        total_reach = sum(float(i.get('reach', 0)) for i in insights)
        total_clicks = sum(float(i.get('clicks', 0)) for i in insights)
        total_impressions = sum(float(i.get('impressions', 0)) for i in insights)
        
        # Вычисляем CTR и CPC
        ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
        cpc = total_spend / total_clicks if total_clicks > 0 else 0
        
        # Получаем данные о конверсиях
        conversion_type = None
        conversions = 0
        
        # Сначала ищем кастомные конверсии
        for insight in insights:
            for conversion in insight.get('conversions', []):
                action_type = conversion.get('action_type', '')
                if action_type.startswith('offsite_conversion.fb_pixel_custom.'):
                    conversion_type = action_type
                    conversions += float(conversion.get('value', 0))
                    break
            if conversion_type:
                break
        
        # Если кастомных конверсий нет, ищем обычные лиды
        if not conversion_type:
            for insight in insights:
                for conversion in insight.get('conversions', []):
                    action_type = conversion.get('action_type', '')
                    if action_type in ['lead', 'offsite_conversion.fb_pixel_lead']:
                        conversion_type = action_type
                        conversions += float(conversion.get('value', 0))
                        break
                if conversion_type:
                    break
        
        # Если нет данных о конверсиях, возвращаем None
        if not conversion_type or conversions == 0:
            return None
            
        # Рассчитываем цену конверсии вручную
        conversion_cost = total_spend / conversions if conversions > 0 else None
        logger.info(f"Calculated conversion cost for {account_name}: {conversion_cost} (spend: {total_spend}, conversions: {conversions})")
            
        # Выбираем случайный эмодзи
        emojis = ['📜', '💌', '🧧']
        random_emoji = random.choice(emojis)
            
        # Форматируем сообщение
        message = [
            f"{random_emoji} Статистика за {start_str} - {end_str} ({account_name}):",
            "",
            f"Конверсий: {int(conversions)}",
            f"Цена конверсии: ${conversion_cost:.2f}" if conversion_cost is not None else "Цена конверсии: н/д",
            f"Спенд: ${total_spend:.2f}\n",
            f"Охват: {int(total_reach):,}".replace(",", " "),
            f"Клики: {int(total_clicks):,}".replace(",", " "),
            f"CTR: {ctr:.2f}%",
            f"CPC: ${cpc:.2f}\n",
            f"Тип конверсий: {conversion_type}"
        ]
        
        return "\n".join(message)
    
    @staticmethod
    def _get_overall_trend(metrics: Dict[str, Tuple[float, str]]) -> str:
        """
        Анализирует динамику эффективности на основе стоимости конверсии.
        
        Args:
            metrics: Словарь с метриками и их изменениями
            
        Returns:
            Строка с описанием динамики эффективности
        """
        # Получаем изменение стоимости конверсии
        conversion_cost_change, direction = metrics.get('conversion_cost', (0.0, '='))
        
        # Если стоимость конверсии снизилась (↓), это позитивно
        if direction == '↓':
            return "🟢 Рост эффективности"
        # Если стоимость конверсии выросла (↑), это негативно
        elif direction == '↑':
            return "🔴 Снижение эффективности"
        
        # Если нет изменений
        return "⚪️ Стабильная эффективность"

    @staticmethod
    def get_metrics(insights: List[Dict], normalize_by_days: bool = False, days_count: Optional[int] = None) -> Dict[str, float]:
        """
        Извлекает и обрабатывает метрики из инсайтов.
        
        Args:
            insights: Список инсайтов
            normalize_by_days: Нужно ли нормализовать значения по дням
            days_count: Количество дней для нормализации (если None, вычисляется автоматически)
            
        Returns:
            Словарь с обработанными метриками
        """
        # Инициализируем базовые метрики
        total_spend = 0
        total_reach = 0
        total_clicks = 0
        total_impressions = 0
        total_conversions = 0
        
        # Собираем данные из всех инсайтов
        for insight in insights:
            total_spend += float(insight.get('spend', 0))
            total_reach += float(insight.get('reach', 0))
            total_clicks += float(insight.get('clicks', 0))
            total_impressions += float(insight.get('impressions', 0))
            
            # Обрабатываем конверсии
            for conversion in insight.get('conversions', []):
                action_type = conversion.get('action_type', '')
                # Сначала проверяем кастомные конверсии
                if action_type.startswith('offsite_conversion.fb_pixel_custom.'):
                    total_conversions += float(conversion.get('value', 0))
                # Затем проверяем стандартные лиды
                elif action_type in ['lead', 'offsite_conversion.fb_pixel_lead']:
                    total_conversions += float(conversion.get('value', 0))
        
        # Если нужно нормализовать значения по дням
        if normalize_by_days and insights:
            if days_count is None:
                # Вычисляем количество дней
                start_date = datetime.strptime(insights[0]['date_start'], '%Y-%m-%d')
                end_date = datetime.strptime(insights[0]['date_stop'], '%Y-%m-%d')
                days_count = (end_date - start_date).days + 1
            
            if days_count > 0:
                total_spend /= days_count
                total_reach /= days_count
                total_clicks /= days_count
                total_impressions /= days_count
                total_conversions /= days_count
        
        # Вычисляем производные метрики
        ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
        cpc = total_spend / total_clicks if total_clicks > 0 else 0
        conversion_cost = total_spend / total_conversions if total_conversions > 0 else 0
        
        # Возвращаем словарь с метриками
        return {
            'spend': total_spend,
            'reach': total_reach,
            'clicks': total_clicks,
            'impressions': total_impressions,
            'conversions': total_conversions,
            'ctr': ctr,
            'cpc': cpc,
            'conversion_cost': conversion_cost
        }

    @staticmethod
    def format_comparative_insights(
        current_insights: List[Dict],
        previous_insights: List[Dict],
        account_name: str = "Без имени",
        show_details: bool = True,
        normalize_by_days: bool = False,
        period_type: str = "daily"
    ) -> Optional[str]:
        """
        Форматирует сравнительную статистику между двумя периодами.
        
        Args:
            current_insights: Статистика текущего периода
            previous_insights: Статистика предыдущего периода
            account_name: Название аккаунта
            show_details: Показывать ли детальную статистику
            normalize_by_days: Нужно ли нормализовать значения по дням
            period_type: Тип периода (daily, weekly, monthly)
            
        Returns:
            Отформатированный текст сравнения или None если нет данных
        """
        if not current_insights or not previous_insights:
            return None
            
        # Получаем даты из инсайтов
        try:
            current_start = datetime.strptime(current_insights[0]['date_start'], '%Y-%m-%d')
            current_end = datetime.strptime(current_insights[0]['date_stop'], '%Y-%m-%d')
            previous_start = datetime.strptime(previous_insights[0]['date_start'], '%Y-%m-%d')
            previous_end = datetime.strptime(previous_insights[0]['date_stop'], '%Y-%m-%d')
            
            current_days = (current_end - current_start).days + 1
            previous_days = (previous_end - previous_start).days + 1
        except (KeyError, IndexError, ValueError):
            return None
            
        # Получаем метрики
        current_metrics = DataProcessor.get_metrics(current_insights, normalize_by_days, current_days)
        previous_metrics = DataProcessor.get_metrics(previous_insights, normalize_by_days, previous_days)
        
        # Вычисляем изменения и сохраняем их для анализа общей динамики
        metrics_changes = {}
        for metric in ['conversions', 'conversion_cost', 'spend', 'reach', 'clicks', 'ctr', 'cpc']:
            change, direction = DataProcessor.calc_change(
                current_metrics[metric],
                previous_metrics[metric]
            )
            metrics_changes[metric] = (change, direction)
        
        # Получаем общую динамику
        overall_trend = DataProcessor._get_overall_trend(metrics_changes)
        
        # Определяем заголовок в зависимости от типа периода
        period_headers = {
            'daily': '📉  Дневка',
            'weekly': '📉  Неделька',
            'monthly': '📉  Месяц'
        }
        period_header = period_headers.get(period_type, '📊 Анализ периода')

        # Получаем эмодзи для тренда
        trend_emoji = "🦍" if "Рост" in overall_trend else "💩"
        trend_text = "лид подешевел" if "Рост" in overall_trend else "лид подорожал"
        
        # Форматируем даты в новом формате
        def format_date(date: datetime) -> str:
            return f"{date.day:02d}/{date.month:02d}"

        # Форматируем строку с датами в зависимости от типа периода
        if period_type == 'daily':
            # Для быстрых изменений показываем только дни
            date_str = f"{format_date(previous_start)} vs {format_date(current_start)}"
        else:
            # Для остальных периодов показываем диапазоны
            date_str = f"{format_date(previous_start)}-{format_date(previous_end)} vs {format_date(current_start)}-{format_date(current_end)}"
        
        # Формируем сообщение
        message = [
            f"{period_header}: {trend_text} {trend_emoji}",
            f"{date_str}\n",
        ]
        
        # Добавляем метрики
        message.extend([
            f"Конверсии: {previous_metrics['conversions']:.1f} → {current_metrics['conversions']:.1f} {metrics_changes['conversions'][1]} {metrics_changes['conversions'][0]:.1f}%",
            f"Цена конверсии: ${previous_metrics['conversion_cost']:.2f} → ${current_metrics['conversion_cost']:.2f} {metrics_changes['conversion_cost'][1]} {metrics_changes['conversion_cost'][0]:.1f}%",
            f"Расход: ${previous_metrics['spend']:.2f} → ${current_metrics['spend']:.2f} {metrics_changes['spend'][1]} {metrics_changes['spend'][0]:.1f}%"
        ])
        
        return "\n".join(message)
    
    @staticmethod
    def truncate_for_telegram(text: str, max_length: int = 4000) -> List[str]:
        """
        Разбивает длинный текст на части с учетом HTML-разметки.
        
        Args:
            text: Исходный текст
            max_length: Максимальная длина одного сообщения
            
        Returns:
            Список частей текста
        """
        if len(text) <= max_length:
            return [text]
        
        parts = []
        current_part = ""
        current_tags = []  # Стек открытых HTML тегов
        
        # Разбиваем текст на строки
        lines = text.split('\n')
        
        for line in lines:
            # Если текущая строка содержит открывающий тег, добавляем его в стек
            if '<b>' in line:
                current_tags.append('<b>')
            if '<i>' in line:
                current_tags.append('<i>')
            if '<code>' in line:
                current_tags.append('<code>')
                
            # Если добавление строки превысит лимит
            if len(current_part + line + '\n') > max_length:
                # Закрываем все открытые теги
                for tag in reversed(current_tags):
                    if tag == '<b>':
                        current_part += '</b>'
                    elif tag == '<i>':
                        current_part += '</i>'
                    elif tag == '<code>':
                        current_part += '</code>'
                
                # Добавляем часть в результат
                parts.append(current_part)
                
                # Начинаем новую часть, открывая все необходимые теги
                current_part = ""
                for tag in current_tags:
                    current_part += tag
                    
            # Добавляем строку к текущей части
            current_part += line + '\n'
            
            # Если строка содержит закрывающий тег, удаляем его из стека
            if '</b>' in line:
                current_tags.remove('<b>')
            if '</i>' in line:
                current_tags.remove('<i>')
            if '</code>' in line:
                current_tags.remove('<code>')
                
        # Добавляем последнюю часть
        if current_part:
            parts.append(current_part)
        
        return parts
    
    @staticmethod
    def convert_to_dataframe(data: List[Dict], 
                             level: str = 'campaign', 
                             date_field: str = 'date_start') -> pd.DataFrame:
        """
        Convert API data to a pandas DataFrame.
        
        Args:
            data: List of data dictionaries.
            level: The level of data (account, campaign, adset, ad).
            date_field: The name of the date field.
            
        Returns:
            A pandas DataFrame.
        """
        if not data:
            return pd.DataFrame()
        
        # Create DataFrame
        df = pd.DataFrame(data)
        
        # Convert date if present
        if date_field in df.columns:
            try:
                df[date_field] = pd.to_datetime(df[date_field])
            except Exception as e:
                logger.warning(f"Failed to convert dates: {str(e)}")
        
        return df 

    @staticmethod
    def calc_change(current_value: float, previous_value: float) -> Tuple[float, str]:
        """
        Вычисляет процентное изменение между двумя значениями и определяет направление изменения.
        
        Args:
            current_value: Текущее значение
            previous_value: Предыдущее значение
            
        Returns:
            Кортеж из процента изменения и символа направления (↑ или ↓)
        """
        if previous_value == 0:
            if current_value == 0:
                return 0.0, "="
            return 100.0, "↑"
            
        change = ((current_value - previous_value) / previous_value) * 100
        direction = "↑" if change >= 0 else "↓"
        
        return abs(change), direction 