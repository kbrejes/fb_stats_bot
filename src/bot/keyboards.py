"""
Keyboard builders for Telegram bot.
"""
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton
from typing import List, Dict, Any, Optional

from config.settings import DATE_PRESETS, EXPORT_FORMATS

def build_account_keyboard(accounts: List[Dict], add_stats: bool = False):
    """
    Build a keyboard with account selection buttons.
    
    Args:
        accounts: List of account data.
        add_stats: Whether to add stats buttons.
        
    Returns:
        Keyboard with account buttons.
    """
    builder = InlineKeyboardBuilder()
    button_count = 0
    
    for account in accounts:
        account_id = account.get('id')
        account_name = account.get('name', 'Unnamed Account')
        
        # Trim name if too long
        if len(account_name) > 30:
            account_name = account_name[:27] + '...'
            
        builder.add(InlineKeyboardButton(
            text=account_name,
            callback_data=f"account:{account_id}"
        ))
        button_count += 1
        
    
    # Добавляем кнопку для возврата в главное меню
    builder.add(InlineKeyboardButton(
        text="🌎 Меню",
        callback_data="menu:main"
    ))
    button_count += 1
    
    # Добавляем пустую кнопку для сохранения парности
    if button_count % 2 != 0:
        builder.add(InlineKeyboardButton(
            text=" ", 
            callback_data="empty:action"
        ))
    
    # Build grid - всегда по 2 кнопкам в ряду
    builder.adjust(2)
    
    return builder.as_markup()

def build_campaign_keyboard(campaigns: List[Dict], add_stats: bool = False):
    """
    Build a keyboard with campaign selection buttons.
    
    Args:
        campaigns: List of campaign data.
        add_stats: Whether to add stats buttons.
        
    Returns:
        Keyboard with campaign buttons.
    """
    builder = InlineKeyboardBuilder()
    button_count = 0
    
    for campaign in campaigns:
        campaign_id = campaign.get('id')
        campaign_name = campaign.get('name', 'Unnamed Campaign')
        
        # Trim name if too long
        if len(campaign_name) > 30:
            campaign_name = campaign_name[:27] + '...'
            
        builder.add(InlineKeyboardButton(
            text=campaign_name,
            callback_data=f"campaign:{campaign_id}"
        ))
        button_count += 1
        
        # Add stats button if requested
        if add_stats:
            builder.add(InlineKeyboardButton(
                text="📊 Статистика",
                callback_data=f"campaign_stats:{campaign_id}:{campaign_name}"
            ))
            button_count += 1
    
    # Add "Back to accounts" button
    builder.add(InlineKeyboardButton(
        text="⬅️",
        callback_data="menu:accounts"
    ))
    button_count += 1
    
    # Добавляем кнопку для возврата в главное меню
    builder.add(InlineKeyboardButton(
        text="🌎 Меню",
        callback_data="menu:main"
    ))
    button_count += 1
    
    # Проверяем, нужно ли добавить пустую кнопку для сохранения парности
    if button_count % 2 != 0:
        builder.add(InlineKeyboardButton(
            text=" ", 
            callback_data="empty:action"
        ))
    
    # Build grid - всегда по 2 кнопкам в ряду
    builder.adjust(2)
    
    return builder.as_markup()

def build_ad_keyboard(ads: List[Dict], campaign_id: str, add_stats: bool = False):
    """
    Build a keyboard with ad selection buttons.
    
    Args:
        ads: List of ad data.
        campaign_id: The campaign ID to return to.
        add_stats: Whether to add stats buttons.
        
    Returns:
        Keyboard with ad buttons.
    """
    builder = InlineKeyboardBuilder()
    button_count = 0
    
    for ad in ads:
        ad_id = ad.get('id')
        ad_name = ad.get('name', 'Unnamed Ad')
        
        # Trim name if too long
        if len(ad_name) > 30:
            ad_name = ad_name[:27] + '...'
            
        builder.add(InlineKeyboardButton(
            text=ad_name,
            callback_data=f"ad:{ad_id}"
        ))
        button_count += 1
        
        # Add stats button if requested
        if add_stats:
            builder.add(InlineKeyboardButton(
                text="📊 Статистика",
                callback_data=f"ad_stats:{ad_id}:{ad_name}"
            ))
            button_count += 1
    
    # Add "Back to campaign" button
    builder.add(InlineKeyboardButton(
        text="⬅️",
        callback_data=f"menu:campaign:{campaign_id}"
    ))
    button_count += 1
    
    # Добавляем кнопку для возврата в главное меню
    builder.add(InlineKeyboardButton(
        text="🌎 Меню",
        callback_data="menu:main"
    ))
    button_count += 1
    
    # Проверяем, нужно ли добавить пустую кнопку для сохранения парности
    if button_count % 2 != 0:
        builder.add(InlineKeyboardButton(
            text=" ", 
            callback_data="empty:action"
        ))
    
    # Build grid - всегда по 2 кнопкам в ряду
    builder.adjust(2)
    
    return builder.as_markup()

def build_date_preset_keyboard(object_id: str, object_type: str, object_name: str = None):
    """
    Build a keyboard with date preset buttons.
    
    Args:
        object_id: The object ID.
        object_type: The object type (account, campaign, ad).
        object_name: Optional object name to pass in callback data.
        
    Returns:
        Keyboard with date preset buttons.
    """
    builder = InlineKeyboardBuilder()
    button_count = 0
    
    # Группируем пресеты дат по категориям для лучшей навигации
    date_groups = {
        'Сегодня/Вчера': {
            'today': '📅 Сегодня',
            'yesterday': '📅 Вчера',
        },
        'Последние дни': {
            'last_3d': '📅 3 дня',
            'last_7d': '📅 7 дней',
            'last_14d': '📅 14 дней',
            'last_30d': '📅 30 дней',
        },
        'Месяцы': {
            'this_month': '📅 Этот месяц',
            'last_month': '📅 Прошлый месяц',
        },
        'Недели': {
            'this_week_mon_today': '📅 Текущая неделя',
            'last_week_mon_sun': '📅 Прошлая неделя',
        }
    }
    
    # ВАЖНЫЙ FIX: Telegram имеет ограничение в 64 байта для callback_data
    # Для решения проблемы BUTTON_DATA_INVALID полностью убираем имя объекта из callback_data
    # Вместо этого будем использовать только ID и тип
    
    # Добавляем кнопки по группам
    for group_name, presets in date_groups.items():
        for preset, label in presets.items():
            # Используем минимальный callback_data без имени объекта
            callback_data = f"stats:{object_type}:{object_id}:{preset}"
            
            # Проверяем длину callback_data
            if len(callback_data) > 64:
                # Если даже без имени объекта длина превышает 64 байта, создаем укороченную версию
                id_part = object_id
                if len(id_part) > 30:  # Оставляем запас для остальной части callback_data
                    id_part = id_part[:30]
                
                callback_data = f"stats:{object_type}:{id_part}:{preset}"
                
            builder.add(InlineKeyboardButton(
                text=label,
                callback_data=callback_data
            ))
            button_count += 1
    
    # Add "Back" button
    if object_type == 'account':
        builder.add(InlineKeyboardButton(
            text="⬅️",
            callback_data="menu:accounts"
        ))
        button_count += 1
    elif object_type == 'campaign':
        # Учитываем возможную длину account_id
        account_id = object_id.split('_')[0] if '_' in object_id else object_id
        if len(account_id) > 30:
            account_id = account_id[:30]
        
        builder.add(InlineKeyboardButton(
            text="⬅️",
            callback_data=f"back:account:{account_id}"
        ))
        button_count += 1
    elif object_type == 'ad':
        # Учитываем возможную длину campaign_id
        campaign_id = object_id.split('_')[0] if '_' in object_id else object_id
        if len(campaign_id) > 30:
            campaign_id = campaign_id[:30]
            
        builder.add(InlineKeyboardButton(
            text="⬅️",
            callback_data=f"menu:campaign:{campaign_id}"
        ))
        button_count += 1
    elif object_type == 'account_campaigns':
        # Для таблицы кампаний аккаунта
        builder.add(InlineKeyboardButton(
            text="⬅️",
            callback_data=f"menu:account:{object_id}"
        ))
        button_count += 1
    
    # Добавляем кнопку для возврата в главное меню
    builder.add(InlineKeyboardButton(
        text="🌎 Меню",
        callback_data="menu:main"
    ))
    button_count += 1
    
    # Проверяем, нужно ли добавить пустую кнопку для сохранения парности
    if button_count % 2 != 0:
        builder.add(InlineKeyboardButton(
            text=" ",
            callback_data="empty:action"
        ))
    
    # Build grid - всегда по 2 кнопкам в ряду
    builder.adjust(2)
    
    return builder.as_markup()

def build_export_format_keyboard(data_key: str):
    """
    Build a keyboard with export format buttons.
    
    Args:
        data_key: The key for the cached data to export.
        
    Returns:
        InlineKeyboardMarkup with export format buttons.
    """
    builder = InlineKeyboardBuilder()
    
    # Format buttons
    for format in EXPORT_FORMATS:
        builder.add(InlineKeyboardButton(
            text=format.upper(),
            callback_data=f"export:{data_key}:{format}"
        ))
    
    # Back button
    builder.add(InlineKeyboardButton(
        text="⬅️",
        callback_data="back:cancel"
    ))
    
    # Build grid with 3 buttons in first row, 1 in second
    builder.adjust(3, 1)
    
    return builder.as_markup()

def build_main_menu_keyboard():
    """
    Build the main menu keyboard.
    
    Returns:
        InlineKeyboardMarkup with menu buttons.
    """
    builder = InlineKeyboardBuilder()
    
    # Main menu buttons
    builder.add(InlineKeyboardButton(
        text="📊 Аккаунты",
        callback_data="menu:accounts"
    ))
    
    builder.add(InlineKeyboardButton(
        text="🔐 Авторизация",
        callback_data="menu:auth"
    ))
    
    builder.add(InlineKeyboardButton(
        text="🪆 Язык",
        callback_data="menu:language"
    ))
    
    # Build grid with 2 buttons per row
    builder.adjust(2)
    
    return builder.as_markup()

def build_confirmation_keyboard(action: str, object_id: str):
    """
    Build a confirmation keyboard.
    
    Args:
        action: The action to confirm.
        object_id: The object ID associated with the action.
        
    Returns:
        InlineKeyboardMarkup with confirm/cancel buttons.
    """
    builder = InlineKeyboardBuilder()
    
    # Confirm button
    builder.add(InlineKeyboardButton(
        text="✅ Подтвердить",
        callback_data=f"confirm:{action}:{object_id}"
    ))
    
    # Cancel button
    builder.add(InlineKeyboardButton(
        text="⬅️",
        callback_data="back:cancel"
    ))
    
    # Build grid with 2 buttons per row
    builder.adjust(2)
    
    return builder.as_markup()

def build_language_keyboard():
    """
    Build a keyboard for language selection.
    
    Returns:
        InlineKeyboardMarkup with language buttons.
    """
    builder = InlineKeyboardBuilder()
    
    # Add language buttons
    builder.add(InlineKeyboardButton(
        text="🇷🇺 Русский",
        callback_data="language:ru"
    ))
    
    builder.add(InlineKeyboardButton(
        text="🇬🇧 English",
        callback_data="language:en"
    ))
    
    # Add back button
    builder.add(InlineKeyboardButton(
        text="⬅️",
        callback_data="menu:main"
    ))
    
    # Build grid with 2 buttons per row
    builder.adjust(2, 1)
    
    return builder.as_markup() 