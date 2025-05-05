"""
Process and format data for display in Telegram.
"""
import pandas as pd
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta

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
                
            start_date = datetime.strptime(date_start, '%Y-%m-%d')
            end_date = datetime.strptime(date_stop, '%Y-%m-%d')
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to parse dates for account {account_name}: {str(e)}")
            return None
        
        # Словарь русских названий месяцев
        MONTHS = {
            1: 'января', 2: 'февраля', 3: 'марта', 4: 'апреля',
            5: 'мая', 6: 'июня', 7: 'июля', 8: 'августа',
            9: 'сентября', 10: 'октября', 11: 'ноября', 12: 'декабря'
        }
        
        # Форматируем даты
        start_str = f"{start_date.day} {MONTHS[start_date.month]} {start_date.year}"
        end_str = f"{end_date.day} {MONTHS[end_date.month]} {end_date.year}"
        
        # Суммируем метрики
        total_spend = sum(float(i.get('spend', 0)) for i in insights)
        total_reach = sum(float(i.get('reach', 0)) for i in insights)
        total_clicks = sum(float(i.get('clicks', 0)) for i in insights)
        total_impressions = sum(float(i.get('impressions', 0)) for i in insights)
        
        # Рассчитываем CTR
        ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
        
        # Рассчитываем CPC
        cpc = total_spend / total_clicks if total_clicks > 0 else 0
        
        # Собираем информацию о конверсиях
        conversions = 0
        conversion_type = None
        conversion_cost = None
        
        # Сначала собираем все конверсии
        for insight in insights:
            for conversion in insight.get('conversions', []):
                if conversion.get('action_type', '').startswith('offsite_conversion.fb_pixel_custom'):
                    conversions += float(conversion.get('value', 0))
                    conversion_type = conversion.get('action_type')
        
        # Если нашли конверсии, ищем их стоимость
        if conversion_type and conversions > 0:
            # Сначала пытаемся найти стоимость в cost_per_action_type
            for insight in insights:
                for cost in insight.get('cost_per_action_type', []):
                    if cost.get('action_type') == conversion_type:
                        if conversion_cost is None:
                            conversion_cost = float(cost.get('value', 0))
                        else:
                            conversion_cost = (conversion_cost + float(cost.get('value', 0))) / 2
            
            # Если стоимость не найдена в cost_per_action_type, рассчитываем вручную
            if conversion_cost is None and total_spend > 0:
                conversion_cost = total_spend / conversions
                logger.info(f"Calculated manual conversion cost for {account_name}: {conversion_cost} (spend: {total_spend}, conversions: {conversions})")
        
        # Если нет данных о конверсиях, возвращаем None
        if not conversion_type or conversions == 0:
            return None
            
        # Форматируем сообщение
        message = [
            f"📊 Статистика по аккаунту {account_name} за период {start_str} - {end_str}:",
            "",
            f"Конверсий: {int(conversions)}",
            f"Тип конверсий: {conversion_type}",
            f"Цена конверсии: ${conversion_cost:.2f}" if conversion_cost is not None else "Цена конверсии: н/д",
            f"Спенд: ${total_spend:.2f}",
            f"Охват: {int(total_reach):,}".replace(",", " "),
            f"Клики: {int(total_clicks):,}".replace(",", " "),
            f"CTR: {ctr:.2f}%",
            f"CPC: ${cpc:.2f}"
        ]
        
        return "\n".join(message)
    
    @staticmethod
    def truncate_for_telegram(text: str, max_length: int = 4000) -> List[str]:
        """
        Truncate text to fit Telegram message limits.
        
        Args:
            text: The text to truncate.
            max_length: Maximum length of a message.
            
        Returns:
            List of message parts.
        """
        if len(text) <= max_length:
            return [text]
        
        # Split by lines to avoid cutting in the middle of a row
        lines = text.split('\n')
        
        parts = []
        current_part = []
        current_length = 0
        
        for line in lines:
            if current_length + len(line) + 1 > max_length:  # +1 for the newline
                # Current part is full, add it to parts and start a new one
                if current_part:
                    parts.append('\n'.join(current_part))
                current_part = [line]
                current_length = len(line)
            else:
                # Add line to the current part
                current_part.append(line)
                current_length += len(line) + 1  # +1 for the newline
        
        # Don't forget the last part
        if current_part:
            parts.append('\n'.join(current_part))
        
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