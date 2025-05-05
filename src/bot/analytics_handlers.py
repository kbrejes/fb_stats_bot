"""
Обработчики для аналитики и сравнения периодов.
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

from src.services.analytics import AnalyticsService, ComparisonPeriod
from src.data.processor import DataProcessor
from src.api.facebook import FacebookAdsClient, FacebookAdsApiError
from src.utils.logger import get_logger
from config.settings import OPENAI_API_KEY

logger = get_logger(__name__)
router = Router()

# Создаем инстанс сервиса аналитики
analytics_service = AnalyticsService(OPENAI_API_KEY)

@router.callback_query(F.data.startswith("analytics:"))
async def handle_analytics_callback(callback: CallbackQuery):
    """Обработчик для кнопок аналитики."""
    try:
        action = callback.data.split(":")[1]
        user_id = callback.from_user.id
        
        if action == "menu":
            # Показываем меню выбора периода
            builder = InlineKeyboardBuilder()
            
            # Добавляем кнопки для разных периодов
            builder.add(InlineKeyboardButton(
                text="Вчера vs Позавчера",
                callback_data="period:daily"
            ))
            builder.add(InlineKeyboardButton(
                text="Эта vs Прошлая неделя",
                callback_data="period:weekly"
            ))
            builder.add(InlineKeyboardButton(
                text="Прошлая vs Позапрошлая",
                callback_data="period:prev_weekly"
            ))
            builder.add(InlineKeyboardButton(
                text="2 Недели vs Месяц",
                callback_data="period:biweekly_vs_monthly"
            ))
            
            # Добавляем кнопку возврата
            builder.add(InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data="menu:main"
            ))
            
            builder.adjust(1)  # Размещаем кнопки в один столбец
            
            await callback.message.edit_text(
                "📊 Выберите период для сравнения:",
                reply_markup=builder.as_markup()
            )
            
        else:
            logger.warning(f"Неизвестное действие аналитики: {action}")
            await callback.answer("⚠️ Неизвестное действие")
            
    except Exception as e:
        logger.error(f"Ошибка в обработчике аналитики: {str(e)}")
        await callback.message.edit_text(
            f"⚠️ Произошла ошибка: {str(e)}",
            reply_markup=InlineKeyboardBuilder().add(
                InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:main")
            ).as_markup()
        )

@router.callback_query(F.data.startswith("period:"))
async def handle_period_selection(callback: CallbackQuery):
    """Обработчик выбора периода сравнения."""
    try:
        period_type = callback.data.split(":")[1]
        user_id = callback.from_user.id
        
        # Показываем меню выбора аккаунта
        fb_client = FacebookAdsClient(user_id)
        accounts = await fb_client.get_ad_accounts()
        
        if not accounts:
            await callback.message.edit_text(
                "⚠️ У вас нет доступных рекламных аккаунтов",
                reply_markup=InlineKeyboardBuilder().add(
                    InlineKeyboardButton(text="⬅️ Назад", callback_data="analytics:menu")
                ).as_markup()
            )
            return
            
        builder = InlineKeyboardBuilder()
        
        # Добавляем кнопки для каждого аккаунта
        for account in accounts:
            account_id = account.get('id')
            account_name = account.get('name', f"Аккаунт {account_id}")
            builder.add(InlineKeyboardButton(
                text=account_name,
                callback_data=f"compare:{period_type}:{account_id}"
            ))
            
        # Добавляем кнопку возврата
        builder.add(InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data="analytics:menu"
        ))
        
        builder.adjust(1)  # Размещаем кнопки в один столбец
        
        await callback.message.edit_text(
            "🗿 Выберите аккаунт для анализа:",
            reply_markup=builder.as_markup()
        )
        
    except FacebookAdsApiError as e:
        logger.error(f"Ошибка Facebook API: {str(e)}")
        await callback.message.edit_text(
            f"⚠️ Ошибка API Facebook: {str(e)}",
            reply_markup=InlineKeyboardBuilder().add(
                InlineKeyboardButton(text="⬅️ Назад", callback_data="analytics:menu")
            ).as_markup()
        )
    except Exception as e:
        logger.error(f"Ошибка при выборе периода: {str(e)}")
        await callback.message.edit_text(
            f"⚠️ Произошла ошибка: {str(e)}",
            reply_markup=InlineKeyboardBuilder().add(
                InlineKeyboardButton(text="⬅️ Назад", callback_data="analytics:menu")
            ).as_markup()
        )

@router.callback_query(F.data.startswith("compare:"))
async def handle_comparison(callback: CallbackQuery):
    """Обработчик сравнения периодов для выбранного аккаунта."""
    try:
        _, period_type, account_id = callback.data.split(":")
        user_id = callback.from_user.id
        
        # Получаем название аккаунта
        fb_client = FacebookAdsClient(user_id)
        accounts = await fb_client.get_ad_accounts()
        account_name = next(
            (acc.get('name', f"Аккаунт {account_id}") 
             for acc in accounts if acc.get('id') == account_id),
            f"Аккаунт {account_id}"
        )
        
        # Конвертируем строковый тип периода в enum
        period = ComparisonPeriod(period_type)
        
        # Получаем комплексный анализ
        analysis = await analytics_service.get_comprehensive_analysis(
            user_id, account_id, account_name
        )
        
        if not analysis:
            await callback.message.edit_text(
                f"⚠️ Аккаунт {account_name} неактивен\n\n"
                "Для получения статистики необходимо наличие расходов и конверсий за последние 2 недели.",
                reply_markup=InlineKeyboardBuilder().add(
                    InlineKeyboardButton(text="⬅️ Назад", callback_data="analytics:menu")
                ).as_markup()
            )
            return
            
        # Разбиваем длинное сообщение на части, если нужно
        message_parts = DataProcessor.truncate_for_telegram(analysis)
        
        # Создаем клавиатуру с дополнительными опциями
        builder = InlineKeyboardBuilder()
        
        builder.add(InlineKeyboardButton(
            text="🤖 Анализ OpenAI",
            callback_data=f"analyze:{period_type}:{account_id}"
        ))
        builder.add(InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data="analytics:menu"
        ))
        
        builder.adjust(1)
        
        # Отправляем первую часть с кнопками
        await callback.message.edit_text(
            message_parts[0],
            reply_markup=builder.as_markup()
        )
        
        # Отправляем остальные части, если есть
        for part in message_parts[1:]:
            await callback.message.answer(part)
            
    except FacebookAdsApiError as e:
        logger.error(f"Ошибка Facebook API: {str(e)}")
        await callback.message.edit_text(
            f"⚠️ Ошибка API Facebook: {str(e)}",
            reply_markup=InlineKeyboardBuilder().add(
                InlineKeyboardButton(text="⬅️ Назад", callback_data="analytics:menu")
            ).as_markup()
        )
    except Exception as e:
        logger.error(f"Ошибка при сравнении периодов: {str(e)}")
        await callback.message.edit_text(
            f"⚠️ Произошла ошибка: {str(e)}",
            reply_markup=InlineKeyboardBuilder().add(
                InlineKeyboardButton(text="⬅️ Назад", callback_data="analytics:menu")
            ).as_markup()
        )

@router.callback_query(F.data.startswith("details:"))
async def handle_details(callback: CallbackQuery):
    """Обработчик показа детальной статистики."""
    try:
        _, period_type, account_id = callback.data.split(":")
        user_id = callback.from_user.id
        
        # Получаем название аккаунта
        fb_client = FacebookAdsClient(user_id)
        accounts = await fb_client.get_ad_accounts()
        account_name = next(
            (acc.get('name', f"Аккаунт {account_id}") 
             for acc in accounts if acc.get('id') == account_id),
            f"Аккаунт {account_id}"
        )
        
        # Получаем комплексный анализ
        analysis = await analytics_service.get_comprehensive_analysis(
            user_id, account_id, account_name
        )
        
        if not analysis:
            await callback.message.edit_text(
                f"⚠️ Аккаунт {account_name} неактивен\n\n"
                "Для получения статистики необходимо наличие расходов и конверсий за последние 2 недели.",
                reply_markup=InlineKeyboardBuilder().add(
                    InlineKeyboardButton(text="⬅️ Назад", callback_data=f"compare:{period_type}:{account_id}")
                ).as_markup()
            )
            return
            
        # Разбиваем длинное сообщение на части, если нужно
        message_parts = DataProcessor.truncate_for_telegram(analysis)
        
        # Отправляем первую часть с кнопками
        builder = InlineKeyboardBuilder()
        builder.add(InlineKeyboardButton(
            text="🤖 Анализ OpenAI",
            callback_data=f"analyze:{period_type}:{account_id}"
        ))
        builder.add(InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data=f"compare:{period_type}:{account_id}"
        ))
        builder.adjust(1)
        
        await callback.message.edit_text(
            message_parts[0],
            reply_markup=builder.as_markup()
        )
        
        # Отправляем остальные части, если есть
        for part in message_parts[1:]:
            await callback.message.answer(part)
            
    except Exception as e:
        logger.error(f"Ошибка при показе деталей: {str(e)}")
        await callback.message.edit_text(
            f"⚠️ Произошла ошибка: {str(e)}",
            reply_markup=InlineKeyboardBuilder().add(
                InlineKeyboardButton(text="⬅️ Назад", callback_data=f"compare:{period_type}:{account_id}")
            ).as_markup()
        )

@router.callback_query(F.data.startswith("analyze:"))
async def handle_analysis(callback: CallbackQuery):
    """Обработчик анализа OpenAI."""
    try:
        _, period_type, account_id = callback.data.split(":")
        user_id = callback.from_user.id
        
        # Получаем название аккаунта
        fb_client = FacebookAdsClient(user_id)
        accounts = await fb_client.get_ad_accounts()
        account_name = next(
            (acc.get('name', f"Аккаунт {account_id}") 
             for acc in accounts if acc.get('id') == account_id),
            f"Аккаунт {account_id}"
        )
        
        # Отправляем сообщение о начале анализа
        await callback.message.edit_text(
            "🤖 Анализирую данные с помощью OpenAI...",
            reply_markup=None
        )
        
        # Конвертируем строковый тип периода в enum
        period = ComparisonPeriod(period_type)
        
        # Получаем сравнительную статистику
        current_insights, previous_insights = await analytics_service.get_comparative_insights(
            user_id, account_id, period
        )
        
        # Проверяем активность аккаунта
        if not current_insights or not previous_insights:
            await callback.message.edit_text(
                f"⚠️ Аккаунт {account_name} неактивен\n\n"
                "Для получения статистики необходимо наличие расходов и конверсий за последние 2 недели.",
                reply_markup=InlineKeyboardBuilder().add(
                    InlineKeyboardButton(text="⬅️ Назад", callback_data=f"compare:{period_type}:{account_id}")
                ).as_markup()
            )
            return
        
        # Получаем анализ от OpenAI
        analysis = await analytics_service.analyze_insights(
            current_insights,
            previous_insights,
            account_name
        )
        
        if not analysis:
            await callback.message.edit_text(
                "⚠️ Не удалось получить анализ от OpenAI",
                reply_markup=InlineKeyboardBuilder().add(
                    InlineKeyboardButton(text="⬅️ Назад", callback_data=f"compare:{period_type}:{account_id}")
                ).as_markup()
            )
            return
        
        # Разбиваем длинное сообщение на части, если нужно
        message_parts = DataProcessor.truncate_for_telegram(analysis)
        
        # Отправляем первую часть с кнопками
        builder = InlineKeyboardBuilder()
        builder.add(InlineKeyboardButton(
            text="📊 Статистика",
            callback_data=f"compare:{period_type}:{account_id}"
        ))
        builder.add(InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data="analytics:menu"
        ))
        builder.adjust(1)
        
        await callback.message.edit_text(
            message_parts[0],
            reply_markup=builder.as_markup()
        )
        
        # Отправляем остальные части, если есть
        for part in message_parts[1:]:
            await callback.message.answer(part)
            
    except Exception as e:
        logger.error(f"Ошибка при анализе OpenAI: {str(e)}")
        await callback.message.edit_text(
            f"⚠️ Произошла ошибка при анализе: {str(e)}",
            reply_markup=InlineKeyboardBuilder().add(
                InlineKeyboardButton(text="⬅️ Назад", callback_data=f"compare:{period_type}:{account_id}")
            ).as_markup()
        ) 