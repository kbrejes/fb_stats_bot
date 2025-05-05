"""
Обработчики команд для управления уведомлениями.
"""
import logging
from datetime import time
from typing import Optional, Dict

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from src.storage.database import get_session
from src.services.notifications import NotificationService
from src.storage.models import NotificationSettings
from src.utils.logger import get_logger
from src.utils.bot_helpers import fix_user_id
from src.utils.languages import get_text, get_language

logger = get_logger(__name__)

# Создаем роутер для обработчиков уведомлений
router = Router()

# Маппинг часовых поясов
TIMEZONE_MAPPING: Dict[str, str] = {
    "UTC+2": "Europe/Kiev",
    "UTC+3": "Europe/Moscow",
    "UTC+4": "Asia/Baku",
    "UTC+5": "Asia/Tashkent",
    "UTC+6": "Asia/Almaty",
    "UTC+7": "Asia/Bangkok",
    "UTC+8": "Asia/Shanghai",
    "UTC+9": "Asia/Tokyo"
}

# Обратный маппинг для отображения
TIMEZONE_DISPLAY: Dict[str, str] = {v: k for k, v in TIMEZONE_MAPPING.items()}

# Состояния для настройки уведомлений
class NotificationStates(StatesGroup):
    """Состояния для настройки уведомлений."""
    waiting_for_time = State()

def format_notification_settings(settings: Optional[NotificationSettings]) -> str:
    """
    Форматирует сообщение с настройками уведомлений.
    
    Args:
        settings: Объект настроек уведомлений или None
        
    Returns:
        Отформатированное сообщение
    """
    if not settings:
        return (
            "<b>Настройки уведомлений:</b>\n\n"
            "🔕 Отключены\n"
            "Время отправки: 10:00\n"
            "Часовой пояс: UTC\n\n"
        )
    
    status = "🔔 Включены" if settings.enabled else "🔕 Отключены"
    notification_time = settings.notification_time.strftime("%H:%M")
    timezone_display = TIMEZONE_DISPLAY.get(settings.timezone, settings.timezone)
    
    types_map = {
        'daily_stats': 'Ежедневная статистика',
        'campaigns': 'Информация о кампаниях',
        'budget_alerts': 'Оповещения о бюджете'
    }
    
    types_text = ""
    for type_key, type_name in types_map.items():
        enabled = settings.notification_types.get(type_key, True)
        status_icon = "✅" if enabled else "❌"
        types_text += f"• {type_name}: {status_icon}\n"
    
    return (
        "<b>Настройки уведомлений:</b>\n\n"
        f"{status}\n\n"
        f"Сводка приходит в {notification_time} ({timezone_display})\n\n"
    )

def build_notification_keyboard(enabled: bool = True) -> InlineKeyboardBuilder:
    """
    Создать клавиатуру для управления уведомлениями.
    
    Args:
        enabled: Текущий статус уведомлений
        
    Returns:
        Клавиатура с кнопками управления
    """
    builder = InlineKeyboardBuilder()
    
    # Кнопка включения/выключения
    builder.button(
        text="🔕 Отключить" if enabled else "🔔 Включить",
        callback_data=f"notifications:{'disable' if enabled else 'enable'}"
    )
    
    # Кнопка настройки времени
    builder.button(
        text="🕑 Изменить время",
        callback_data="notifications:set_time"
    )
    
    # Кнопка настройки часового пояса
    builder.button(
        text="🌍 Часовой пояс",
        callback_data="notifications:set_timezone"
    )
    
    # Кнопка возврата в меню
    builder.button(
        text="⬅️",
        callback_data="menu:main"
    )
    
    # Устанавливаем сетку кнопок 2x2
    builder.adjust(2)
    return builder

def build_timezone_keyboard() -> InlineKeyboardBuilder:
    """
    Создать клавиатуру для выбора часового пояса.
    
    Returns:
        Клавиатура с кнопками выбора часового пояса
    """
    builder = InlineKeyboardBuilder()
    
    # Добавляем кнопки с часовыми поясами
    for display_name, tz_name in TIMEZONE_MAPPING.items():
        builder.button(
            text=display_name,
            callback_data=f"timezone:{tz_name}"
        )
    
    # Кнопка отмены
    builder.button(
        text="🔙 Отмена",
        callback_data="timezone:cancel"
    )
    
    # Устанавливаем сетку кнопок по 2 в ряд
    builder.adjust(2)
    return builder

@router.message(Command("notifications"))
async def cmd_notifications(message: Message):
    """
    Обработчик команды /notifications.
    Показывает текущие настройки уведомлений и кнопки управления.
    """
    user_id = await fix_user_id(message.from_user.id)
    session = get_session()
    
    try:
        # Создаем сервис уведомлений
        notification_service = NotificationService(session)
        
        # Получаем текущие настройки
        settings = session.query(NotificationSettings).filter_by(user_id=user_id).first()
        
        if not settings:
            # Если настроек нет, создаем их с значениями по умолчанию
            settings = await notification_service.create_user_notifications(
                user_id,
                time(10, 0),  # 10:00 по умолчанию
                "UTC"
            )
        
        # Формируем сообщение с текущими настройками
        message_text = format_notification_settings(settings)
        
        # Отправляем сообщение с клавиатурой
        await message.answer(
            message_text,
            reply_markup=build_notification_keyboard(settings.enabled).as_markup()
        )
        
    except Exception as e:
        logger.error(f"Error in notifications command: {str(e)}")
        await message.answer(
            "❌ Произошла ошибка при получении настроек уведомлений. "
            "Пожалуйста, попробуйте позже."
        )
    finally:
        session.close()

@router.callback_query(F.data.startswith("notifications:"))
async def notification_callback(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик кнопок управления уведомлениями.
    
    Args:
        callback: Объект callback query
        state: Контекст FSM
    """
    action = callback.data.split(":")[1]
    user_id = await fix_user_id(callback.from_user.id)
    session = get_session()
    
    try:
        notification_service = NotificationService(session)
        
        if action == "enable":
            # Получаем текущие настройки
            current_settings = session.query(NotificationSettings).filter_by(user_id=user_id).first()
            
            # Включаем уведомления, сохраняя текущие настройки времени и часового пояса
            settings = await notification_service.create_user_notifications(
                user_id,
                current_settings.notification_time if current_settings else time(10, 0),
                current_settings.timezone if current_settings else "UTC",
                enabled=True,
                notification_types=current_settings.notification_types if current_settings else None
            )
            await callback.answer("✅ Уведомления включены")
            
        elif action == "disable":
            # Отключаем уведомления
            await notification_service.disable_notifications(user_id)
            await callback.answer("❌ Уведомления отключены")
            
        elif action == "set_time":
            # Переходим в состояние ожидания времени
            await state.set_state(NotificationStates.waiting_for_time)
            # Отправляем сообщение и сохраняем его ID
            msg = await callback.message.edit_text(
                "🕑 Во сколько вы хотите получать сводку по статистике?\n\nВведите время в формате ЧЧ:ММ, например: 16:20"
            )
            # Сохраняем ID сообщения в состоянии
            await state.update_data(prev_message_id=msg.message_id)
            return
            
        elif action == "set_timezone":
            # Показываем клавиатуру выбора часового пояса
            await callback.message.edit_text(
                "🌍 Выберите ваш часовой пояс:\n\n"
                "Выберите ближайший к вам город:",
                reply_markup=build_timezone_keyboard().as_markup()
            )
            return
        
        # Обновляем сообщение с настройками
        settings = session.query(NotificationSettings).filter_by(user_id=user_id).first()
        message_text = format_notification_settings(settings)
        
        await callback.message.edit_text(
            message_text,
            reply_markup=build_notification_keyboard(settings.enabled).as_markup(),
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Error in notification callback: {str(e)}")
        await callback.answer(
            "❌ Произошла ошибка. Пожалуйста, попробуйте позже.",
            show_alert=True
        )
    finally:
        session.close()

@router.callback_query(F.data.startswith("timezone:"))
async def timezone_callback(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик выбора часового пояса.
    """
    action = callback.data.split(":")[1]
    user_id = await fix_user_id(callback.from_user.id)
    session = get_session()
    
    try:
        if action == "cancel":
            # Возвращаемся к основным настройкам
            settings = session.query(NotificationSettings).filter_by(user_id=user_id).first()
            if settings:
                message_text = format_notification_settings(settings)
                
                await callback.message.edit_text(
                    message_text,
                    reply_markup=build_notification_keyboard(settings.enabled).as_markup(),
                    parse_mode="HTML"
                )
            return
        
        # Получаем текущие настройки
        settings = session.query(NotificationSettings).filter_by(user_id=user_id).first()
        
        # Обновляем настройки
        notification_service = NotificationService(session)
        settings = await notification_service.create_user_notifications(
            user_id,
            settings.notification_time if settings else time(10, 0),
            action,  # Используем выбранный часовой пояс
            settings.enabled if settings else True,
            settings.notification_types if settings else None
        )
        
        # Отправляем обновленные настройки
        message_text = format_notification_settings(settings)
        
        await callback.message.edit_text(
            message_text,
            reply_markup=build_notification_keyboard(settings.enabled).as_markup(),
            parse_mode="HTML"
        )
        
        await callback.answer("✅ Часовой пояс обновлен")
        
    except Exception as e:
        logger.error(f"Error in timezone callback: {str(e)}")
        await callback.answer(
            "❌ Произошла ошибка. Пожалуйста, попробуйте позже.",
            show_alert=True
        )
    finally:
        session.close()

@router.message(NotificationStates.waiting_for_time)
async def process_notification_time(message: Message, state: FSMContext):
    """
    Обработчик ввода времени уведомлений.
    
    Args:
        message: Объект сообщения
        state: Контекст FSM
    """
    user_id = await fix_user_id(message.from_user.id)
    session = get_session()
    
    try:
        # Парсим время из сообщения
        hours, minutes = map(int, message.text.split(":"))
        notification_time = time(hours, minutes)
        
        # Проверяем валидность времени
        if not (0 <= hours <= 23 and 0 <= minutes <= 59):
            raise ValueError("Invalid time format")
        
        # Получаем текущие настройки
        settings = session.query(NotificationSettings).filter_by(user_id=user_id).first()
        
        # Обновляем настройки
        notification_service = NotificationService(session)
        settings = await notification_service.create_user_notifications(
            user_id,
            notification_time,
            settings.timezone if settings else "UTC",  # Используем текущий часовой пояс или UTC по умолчанию
            settings.enabled if settings else True,  # Используем текущий статус или True по умолчанию
            settings.notification_types if settings else None  # Используем текущие типы уведомлений или None для значений по умолчанию
        )
        
        # Получаем ID предыдущего сообщения из состояния
        data = await state.get_data()
        prev_message_id = data.get('prev_message_id')
        
        # Сбрасываем состояние ПОСЛЕ получения данных
        await state.clear()
        
        # Если есть предыдущее сообщение, удаляем его
        if prev_message_id:
            try:
                await message.bot.delete_message(message.chat.id, prev_message_id)
                # Удаляем также сообщение пользователя с временем
                await message.delete()
            except Exception as e:
                logger.error(f"Error deleting messages: {str(e)}")
        
        # Отправляем обновленные настройки
        message_text = format_notification_settings(settings)
        
        await message.answer(
            message_text,
            reply_markup=build_notification_keyboard(settings.enabled).as_markup(),
            parse_mode="HTML"
        )
        
    except (ValueError, IndexError):
        await message.answer(
            "❌ Неверный формат времени. Пожалуйста, используйте формат ЧЧ:ММ\n"
            "Например: 10:00"
        )
    finally:
        session.close() 