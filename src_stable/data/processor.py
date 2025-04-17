"""
Process and format data for display in Telegram.
"""
import pandas as pd
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

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
    def format_insights(insights: List[Dict], level: str = 'campaign') -> str:
        """
        Format insights data into a text table.
        
        Args:
            insights: List of insights data.
            level: The level of insights (account, campaign, adset, ad).
            
        Returns:
            Formatted text table.
        """
        if not insights:
            return "Нет доступных данных статистики"
        
        # Extract key metrics
        metrics = ['date_start', 'impressions', 'reach', 'clicks', 'ctr', 'cpc', 'spend']
        
        rows = []
        for entry in insights:
            row = {}
            for metric in metrics:
                if metric in entry:
                    # Format numbers
                    value = entry[metric]
                    if metric in ['impressions', 'reach', 'clicks']:
                        value = f"{int(value):,}".replace(',', ' ')
                    elif metric in ['ctr']:
                        value = f"{float(value)*100:.2f}%"
                    elif metric in ['cpc', 'spend']:
                        value = f"{float(value):.2f}"
                    elif metric in ['date_start']:
                        try:
                            dt = datetime.strptime(value, '%Y-%m-%d')
                            value = dt.strftime('%d.%m.%Y')
                        except ValueError:
                            pass
                    
                    row[metric] = value
            
            rows.append(row)
        
        if not rows:
            return "Данные статистики не содержат необходимых метрик"
        
        # Create DataFrame
        df = pd.DataFrame(rows)
        
        # Rename columns
        column_names = {
            'date_start': 'Дата',
            'impressions': 'Показы',
            'reach': 'Охват',
            'clicks': 'Клики',
            'ctr': 'CTR',
            'cpc': 'CPC',
            'spend': 'Расходы'
        }
        
        df.rename(columns=column_names, inplace=True)
        
        # Format as text table
        header = " | ".join(df.columns)
        separator = "-" * len(header)
        
        rows = []
        for _, row in df.iterrows():
            rows.append(" | ".join(map(str, row)))
        
        return f"{header}\n{separator}\n" + "\n".join(rows)
    
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