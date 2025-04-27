"""
Utility functions for formatting messages for Telegram.
"""
from typing import Dict, List, Any, Optional
import json

from src.utils.logger import get_logger
from src.utils.languages import get_text, get_language

logger = get_logger(__name__)

def format_insights(insights: List[Dict[str, Any]], object_type: str, date_preset: str = 'last_7d', user_id: int = None) -> str:
    """
    Format insights data for display in Telegram.
    
    Args:
        insights: The insights data to format.
        object_type: The type of object (account, campaign, adset, ad).
        date_preset: The date preset used for the insights.
        user_id: The user's Telegram ID for language settings.
        
    Returns:
        A formatted string with the insights.
    """
    # Get the user's language
    lang = "ru"
    if user_id:
        lang = get_language(user_id)
    
    if not insights:
        return f"<b>{get_text('no_stats_found', lang, object_type=get_text(object_type, lang))}</b>"
    
    # Get date label based on user's language
    date_label = get_text(date_preset, lang)
    
    # Start building the formatted message
    obj_type_display = get_text(object_type, lang)
    message = f"<b>{get_text('insights_for', lang, type=obj_type_display.capitalize(), name='')}</b>\n"
    message += f"<b>{get_text('period', lang)}:</b> {date_label}\n\n"
    
    # Helper function to format currency values
    def format_currency(value, currency="USD"):
        try:
            value = float(value)
            if value >= 1000000:
                return f"{value/1000000:.2f}M {currency}"
            elif value >= 1000:
                return f"{value/1000:.2f}K {currency}"
            else:
                return f"{value:.2f} {currency}"
        except (ValueError, TypeError):
            return f"{value} {currency}"
    
    # Summary of key metrics
    total_impressions = sum(float(i.get('impressions', 0)) for i in insights)
    total_clicks = sum(float(i.get('clicks', 0)) for i in insights)
    total_reach = sum(float(i.get('reach', 0)) for i in insights)
    total_spend = sum(float(i.get('spend', 0)) for i in insights)
    
    currency = insights[0].get('currency', 'USD') if insights else 'USD'
    
    message += f"<b>{get_text('summary', lang)}:</b>\n"
    message += f"• <b>{get_text('impressions', lang)}:</b> {int(total_impressions):,}\n"
    message += f"• <b>{get_text('clicks', lang)}:</b> {int(total_clicks):,}\n"
    message += f"• <b>{get_text('reach', lang)}:</b> {int(total_reach):,}\n"
    message += f"• <b>{get_text('spend', lang)}:</b> {format_currency(total_spend, currency)}\n"
    
    if total_impressions > 0:
        ctr = (total_clicks / total_impressions) * 100
        message += f"• <b>{get_text('ctr', lang)}:</b> {ctr:.2f}%\n"
        
    if total_impressions > 0:
        cpm = (total_spend / total_impressions) * 1000
        message += f"• <b>{get_text('cpm', lang)}:</b> {format_currency(cpm, currency)}\n"
        
    if total_clicks > 0:
        cpc = total_spend / total_clicks
        message += f"• <b>{get_text('cpc', lang)}:</b> {format_currency(cpc, currency)}\n"
    
    # Check for conversions data
    conversion_data = False
    for insight in insights:
        if 'actions' in insight or 'conversions' in insight or 'cost_per_action_type' in insight:
            conversion_data = True
            break
            
    if conversion_data:
        message += f"\n<b>{get_text('conversion_data', lang)}:</b>\n"
        
        # Extract conversion data
        action_types = {}
        cost_per_action = {}
        custom_conversions = {}
        
        # First collect all cost_per_action_type
        for insight in insights:
            costs = insight.get('cost_per_action_type', [])
            for cost in costs:
                action_type = cost.get('action_type', 'unknown')
                value = float(cost.get('value', 0))
                
                if action_type in cost_per_action:
                    # Take average if multiple entries
                    cost_per_action[action_type] = (cost_per_action[action_type] + value) / 2
                else:
                    cost_per_action[action_type] = value
        
        # Process actions and conversions
        for insight in insights:
            # Process actions
            actions = insight.get('actions', [])
            for action in actions:
                action_type = action.get('action_type', 'unknown')
                value = float(action.get('value', 0))
                
                if action_type in action_types:
                    action_types[action_type] += value
                else:
                    action_types[action_type] = value
                    
            # Process conversions - focus on custom conversions
            conversions = insight.get('conversions', [])
            for conversion in conversions:
                action_type = conversion.get('action_type', 'unknown')
                value = float(conversion.get('value', 0))
                
                # Store custom conversions separately
                if action_type.startswith('offsite_conversion.fb_pixel_custom.'):
                    custom_name = action_type.split('.')[-1]
                    custom_conversions[custom_name] = value
                    
                    # Find corresponding cost
                    base_type = '.'.join(action_type.split('.')[:-1])  # Get offsite_conversion.fb_pixel_custom
                    if base_type in cost_per_action:
                        # Link cost to specific custom conversion type
                        cost_per_action[action_type] = cost_per_action[base_type]
                
                # Add to general list for display
                if action_type in action_types:
                    action_types[action_type] += value
                else:
                    action_types[action_type] = value
        
        # Format custom conversions first if available
        if custom_conversions:
            message += f"\n<b>{get_text('custom_conversions', lang)}:</b>\n"
            for custom_name, value in custom_conversions.items():
                full_type = f"offsite_conversion.fb_pixel_custom.{custom_name}"
                message += f"• <b>{custom_name}:</b> {int(value):,}"
                
                # Add cost if known
                if full_type in cost_per_action:
                    cost = cost_per_action[full_type]
                    message += f" (<b>{get_text('cost', lang)}:</b> {format_currency(cost, currency)})"
                elif "offsite_conversion.fb_pixel_custom" in cost_per_action:
                    # Use general cost if specific one not available
                    cost = cost_per_action["offsite_conversion.fb_pixel_custom"]
                    message += f" (<b>{get_text('est_cost', lang)}:</b> {format_currency(cost, currency)})"
                
                message += "\n"
        
        # Then main conversions
        message += f"\n<b>{get_text('all_conversions', lang)}:</b>\n"
        
        # Dictionary for nicer conversion type names
        conversion_labels = {
            'link_click': get_text('link_clicks', lang),
            'landing_page_view': get_text('landing_page_view', lang),
            'lead': get_text('lead', lang),
            'purchase': get_text('purchase', lang),
            'offsite_conversion.fb_pixel_lead': get_text('offsite_conversion.fb_pixel_lead', lang),
            'offsite_conversion.fb_pixel_purchase': get_text('offsite_conversion.fb_pixel_purchase', lang)
        }
        
        # List of important conversions to show first
        important_conversions = [
            'lead', 'purchase', 'offsite_conversion.fb_pixel_lead', 
            'offsite_conversion.fb_pixel_purchase', 'landing_page_view'
        ]
        
        # Show important conversions first
        for action_type in important_conversions:
            if action_type in action_types:
                value = action_types[action_type]
                label = conversion_labels.get(action_type, action_type.replace('_', ' ').title())
                
                message += f"• <b>{label}:</b> {int(value):,}"
                
                # Add cost if known
                if action_type in cost_per_action:
                    cost = cost_per_action[action_type]
                    message += f" (<b>{get_text('cost', lang)}:</b> {format_currency(cost, currency)})"
                
                message += "\n"
                
                # Remove to avoid repeating in general list
                del action_types[action_type]
        
        # Then show remaining actions, except unimportant ones
        skip_types = ['page_engagement', 'post_engagement', 'post_reaction', 'video_view']
        for action_type, value in action_types.items():
            # Skip custom conversions (already shown above)
            if action_type.startswith('offsite_conversion.fb_pixel_custom.'):
                continue
                
            # Skip unimportant action types
            if action_type in skip_types:
                continue
                
            readable_type = action_type.replace('_', ' ').title()
            # Use nice names if available
            readable_type = conversion_labels.get(action_type, readable_type)
                
            message += f"• <b>{readable_type}:</b> {int(value):,}"
            
            # Add cost if known
            if action_type in cost_per_action:
                cost = cost_per_action[action_type]
                message += f" (<b>{get_text('cost', lang)}:</b> {format_currency(cost, currency)})"
            
            message += "\n"
    
    # Add export note
    message += f"\n<i>{get_text('export_note', lang)}</i>"
    
    return message


def format_campaign_table(campaigns: List[Dict], insights: List[Dict], date_preset: str = 'last_7d', user_id: int = None) -> str:
    """
    Format campaign data into a plain text layout according to specified requirements.
    Shows only active campaigns or those with activity in the selected period.
    
    Args:
        campaigns: List of campaign data.
        insights: List of insights data for the campaigns.
        date_preset: The date preset used for the insights.
        user_id: The user's Telegram ID for language settings.
        
    Returns:
        A formatted string with the campaign data.
    """
    # Get the user's language
    lang = "ru"
    if user_id:
        lang = get_language(user_id)
    
    if not campaigns or not insights:
        return f"<b>{get_text('no_campaigns_found', lang)}</b>"
    
    # Get date label
    date_label = get_text(date_preset, lang)
    
    # Start building the message
    message = f"<b>Статистика кампаний</b>\n"
    message += f"<b>Период:</b> {date_label}\n\n"
    
    # Helper function to format currency values
    def format_currency(value, currency="USD"):
        try:
            value = float(value)
            if value >= 1000000:
                return f"{value/1000000:.2f}M"
            elif value >= 1000:
                return f"{value/1000:.2f}K"
            else:
                return f"{value:.2f}"
        except (ValueError, TypeError):
            return "0.00"
    
    # Create a mapping of campaign_id to insights data
    insights_by_campaign = {}
    for insight in insights:
        campaign_id = insight.get('campaign_id')
        if campaign_id:
            if campaign_id in insights_by_campaign:
                insights_by_campaign[campaign_id].append(insight)
            else:
                insights_by_campaign[campaign_id] = [insight]
    
    # Process each campaign
    campaign_blocks = []
    active_campaigns_count = 0
    
    # Переменные для расчета общей суммы по всем кампаниям
    total_all_conversions = 0
    total_all_reach = 0
    total_all_spend = 0
    total_all_impressions = 0
    total_all_clicks = 0
    
    # Данные для расчета взвешенных средних
    weighted_frequency_data = []
    weighted_ctr_data = []
    weighted_cpm_data = []
    weighted_cost_per_conversion_data = []
    conversion_type_counts = {}
    
    # First pass - collect totals
    campaigns_data = []
    for campaign in campaigns:
        campaign_id = campaign.get('id')
        campaign_name = campaign.get('name', 'Без имени')
        status = campaign.get('status', 'Неизвестно')
        
        # Check status for a friendlier display
        if status == 'ACTIVE':
            status = 'Активна'
        elif status == 'PAUSED':
            status = 'Пауза'
        elif status == 'ARCHIVED':
            status = 'Архив'
        
        # Get insights for this campaign
        campaign_insights = insights_by_campaign.get(campaign_id, [])
        
        # Default values
        results = 0
        reach = 0
        frequency = 0
        cost_per_conversion = 0
        spend = 0
        cpm = 0
        ctr = 0
        had_activity = False
        used_conversion_type = "Нет"
        total_impressions = 0
        total_clicks = 0
        total_reach = 0
        total_spend = 0

        
        if campaign_insights:
            # Get currency from first insight
            currency = campaign_insights[0].get('currency', 'USD')
            
            # Log entire insight data for debugging
            logger.info(f"Кампания {campaign_name} ({campaign_id}): получены сырые данные insights: {json.dumps(campaign_insights, indent=2)}")
            
            # Sum up metrics across all insights for this campaign
            total_impressions = sum(float(i.get('impressions', 0)) for i in campaign_insights)
            total_clicks = sum(float(i.get('clicks', 0)) for i in campaign_insights)
            total_reach = sum(float(i.get('reach', 0)) for i in campaign_insights)
            total_spend = sum(float(i.get('spend', 0)) for i in campaign_insights)
            
            # Проверяем, была ли активность в выбранный период
            had_activity = (total_impressions > 0 or total_clicks > 0 or total_spend > 0)
            
            # Calculate derived metrics
            if total_impressions > 0:
                ctr = (total_clicks / total_impressions) * 100
                cpm = (total_spend / total_impressions) * 1000
            
            if total_reach > 0:
                frequency = total_impressions / total_reach
            
            reach = total_reach
            spend = total_spend
            
            # Выводим в лог информацию о найденных типах конверсий
            for insight in campaign_insights:
                conversions = insight.get('conversions', [])
                for conversion in conversions:
                    action_type = conversion.get('action_type', '')
                    value = conversion.get('value', 0)
                    logger.info(f"Кампания {campaign_name} ({campaign_id}): найдена конверсия {action_type} = {value}")
                
                costs = insight.get('cost_per_action_type', [])
                for cost in costs:
                    action_type = cost.get('action_type', '')
                    value = cost.get('value', 0)
                    logger.info(f"Кампания {campaign_name} ({campaign_id}): найдена стоимость конверсии {action_type} = {value}")
            
            # Extract custom conversion data
            custom_conversion_found = False
            custom_conversion_types = ['userDidSubscribe', 'subtotg']
            
            # Сначала проверяем наличие кастомных конверсий
            for insight in campaign_insights:
                # Check for custom conversions
                conversions = insight.get('conversions', [])
                for conversion in conversions:
                    action_type = conversion.get('action_type', '')
                    value = float(conversion.get('value', 0))
                    
                    # Проверяем, является ли конверсия кастомной
                    if action_type.startswith('offsite_conversion.fb_pixel_custom.'):
                        conversion_name = action_type.split('.')[-1]
                        
                        # Проверяем, соответствует ли конверсия одному из известных типов
                        if conversion_name in custom_conversion_types:
                            results = value
                            custom_conversion_found = True
                            logger.info(f"Используем конверсию {action_type} со значением {value}")
                            if value > 0:
                                had_activity = True
                            break
                        # Если конкретное название не найдено, сохраняем первую найденную кастомную конверсию
                        elif not custom_conversion_found:
                            results = value
                            custom_conversion_found = True
                            logger.info(f"Используем первую найденную кастомную конверсию {action_type} со значением {value}")
                            if value > 0:
                                had_activity = True
                
                # Если нашли кастомную конверсию, не нужно проверять другие инсайты
                if custom_conversion_found:
                    break
            
            # Если кастомная конверсия не найдена, проверяем стандартные лиды
            if not custom_conversion_found:
                for insight in campaign_insights:
                    conversions = insight.get('conversions', [])
                    for conversion in conversions:
                        action_type = conversion.get('action_type', '')
                        value = float(conversion.get('value', 0))
                        
                        if action_type in ['lead', 'offsite_conversion.fb_pixel_lead']:
                            results += value
                            logger.info(f"Используем стандартную конверсию {action_type} со значением {value}")
                            if value > 0:
                                had_activity = True
                
            # Поиск стоимости конверсии с приоритетом на кастомные конверсии
            custom_cost_found = False
            
            # Попытка найти стоимость для offsite_conversion.fb_pixel_custom без дополнительного уточнения
            for insight in campaign_insights:
                costs = insight.get('cost_per_action_type', [])
                logger.info(f"Кампания {campaign_name} ({campaign_id}): все стоимости конверсий: {json.dumps(costs, indent=2)}")
                for cost in costs:
                    action_type = cost.get('action_type', '')
                    if action_type == 'offsite_conversion.fb_pixel_custom':
                        cost_per_conversion = float(cost.get('value', 0))
                        used_conversion_type = action_type
                        custom_cost_found = True
                        logger.info(f"Используем стоимость базовой кастомной конверсии {action_type} со значением {cost_per_conversion}")
                        break
                
                if custom_cost_found:
                    break
            
            # Если не нашли базовую стоимость, ищем для известных кастомных конверсий
            if not custom_cost_found:
                for insight in campaign_insights:
                    costs = insight.get('cost_per_action_type', [])
                    
                    for cost in costs:
                        action_type = cost.get('action_type', '')
                        
                        for conv_type in custom_conversion_types:
                            if action_type == f'offsite_conversion.fb_pixel_custom.{conv_type}':
                                cost_per_conversion = float(cost.get('value', 0))
                                used_conversion_type = action_type
                                custom_cost_found = True
                                logger.info(f"Используем стоимость конверсии {action_type} со значением {cost_per_conversion}")
                                break
                        
                        if custom_cost_found:
                            break
                    
                    if custom_cost_found:
                        break
            
            # Если не нашли стоимость для известных типов, ищем для любых других кастомных конверсий
            if not custom_cost_found:
                for insight in campaign_insights:
                    costs = insight.get('cost_per_action_type', [])
                    for cost in costs:
                        action_type = cost.get('action_type', '')
                        if action_type.startswith('offsite_conversion.fb_pixel_custom.'):
                            cost_per_conversion = float(cost.get('value', 0))
                            used_conversion_type = action_type
                            custom_cost_found = True
                            logger.info(f"Используем стоимость для другой кастомной конверсии {action_type} со значением {cost_per_conversion}")
                            break
                    
                    if custom_cost_found:
                        break
            
            # Используем только стоимость лидов если совсем не нашли кастомных конверсий
            # и это необходимо для отображения какой-то стоимости
            if not custom_cost_found and results > 0:
                for insight in campaign_insights:
                    costs = insight.get('cost_per_action_type', [])
                    for cost in costs:
                        action_type = cost.get('action_type', '')
                        if action_type in ['lead', 'offsite_conversion.fb_pixel_lead']:
                            cost_per_conversion = float(cost.get('value', 0))
                            used_conversion_type = action_type
                            logger.info(f"Используем стоимость стандартного лида {action_type} со значением {cost_per_conversion} только потому, что не нашли кастомных конверсий")
                            break
                    
                    # Если нашли хотя бы что-то, прекращаем поиск
                    if cost_per_conversion > 0:
                        break
            
            # Если есть результаты, но нет стоимости конверсии, рассчитываем ее вручную
            if results > 0 and cost_per_conversion == 0 and total_spend > 0:
                cost_per_conversion = total_spend / results
                used_conversion_type = "Расчетная"
            
            # Удостоверимся, что данные по охвату корректны
            # Иногда Facebook API может возвращать некорректные данные, проверим это
            if reach == 0 and total_impressions > 0:
                # Если охват 0, но есть показы, устанавливаем охват равным показам
                reach = total_impressions
        
        # Пропускаем кампании, которые не ACTIVE и не имели активности
        if status != 'Активна' and not had_activity:
            continue
        
        active_campaigns_count += 1
        
        # Суммируем данные для общей статистики
        total_all_conversions += results
        total_all_reach += reach
        total_all_spend += spend
        total_all_impressions += total_impressions
        total_all_clicks += total_clicks
        
        # Для средневзвешенных значений
        if reach > 0:
            weighted_frequency_data.append((frequency, reach))
        if total_impressions > 0:
            weighted_cpm_data.append((cpm, total_impressions))
            weighted_ctr_data.append((ctr, total_impressions))
        if results > 0 and cost_per_conversion > 0:
            weighted_cost_per_conversion_data.append((cost_per_conversion, spend))
            
        # Считаем типы конверсий
        if used_conversion_type in conversion_type_counts:
            conversion_type_counts[used_conversion_type] += 1
        else:
            conversion_type_counts[used_conversion_type] = 1
            
        # Сохраняем данные о кампании для последующего форматирования
        campaigns_data.append({
            'name': campaign_name,
            'status': status,
            'results': results,
            'results_str': str(int(results)),
            'reach': reach,
            'reach_str': f"{int(reach):,}".replace(',', ' '),
            'frequency': frequency,
            'frequency_str': f"{frequency:.2f}",
            'cost_per_conversion': cost_per_conversion,
            'cost_str': f"{format_currency(cost_per_conversion)} USD",
            'used_conversion_type': used_conversion_type,
            'spend': spend,
            'spend_str': f"{format_currency(spend)} USD",
            'cpm': cpm,
            'cpm_str': f"{format_currency(cpm)} USD",
            'ctr': ctr,
            'ctr_str': f"{ctr:.2f}%"
        })
    
    # Если не нашли активных кампаний
    if active_campaigns_count == 0:
        return f"<b>Статистика кампаний</b>\n<b>Период:</b> {date_label}\n\n<i>Нет активных кампаний или кампаний с активностью за выбранный период.</i>"
    
    # Рассчитываем средневзвешенные значения
    weighted_frequency = sum(f * w for f, w in weighted_frequency_data) / sum(w for _, w in weighted_frequency_data) if weighted_frequency_data else 0
    weighted_ctr = sum(c * w for c, w in weighted_ctr_data) / sum(w for _, w in weighted_ctr_data) if weighted_ctr_data else 0
    weighted_cpm = sum(c * w for c, w in weighted_cpm_data) / sum(w for _, w in weighted_cpm_data) if weighted_cpm_data else 0
    weighted_cost_per_conversion = sum(c * w for c, w in weighted_cost_per_conversion_data) / sum(w for _, w in weighted_cost_per_conversion_data) if weighted_cost_per_conversion_data else 0
    
    # Определяем самый часто используемый тип конверсии
    most_common_conversion_type = max(conversion_type_counts.items(), key=lambda x: x[1])[0] if conversion_type_counts else "Нет"
    
    # Создаем общий блок со статистикой
    summary_block = "<b>Общая статистика:</b>\n"
    summary_block += f"<b>Конверсии:</b> {int(total_all_conversions)}\n"
    summary_block += f"<b>Охват:</b> {int(total_all_reach):,}".replace(',', ' ') + "\n"
    summary_block += f"<b>Частота:</b> {weighted_frequency:.2f}\n"
    summary_block += f"<b>Цена конверсии:</b> {format_currency(weighted_cost_per_conversion)} USD (Тип: {most_common_conversion_type})\n"
    summary_block += f"<b>Расход:</b> {format_currency(total_all_spend)} USD\n"
    summary_block += f"<b>CPM:</b> {format_currency(weighted_cpm)} USD\n"
    summary_block += f"<b>CTR:</b> {weighted_ctr:.2f}%\n"
    
    # Добавляем общую статистику в начало сообщения
    message += summary_block + "\n"
    
    # Добавляем визуальный разделитель
    message += "<b>▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬</b>\n\n"
    
    # Добавляем заголовок "Статистика по кампаниям"
    message += "<b>Статистика по кампаниям:</b>\n\n"
    
    # Теперь форматируем блоки для каждой кампании
    for campaign_data in campaigns_data:
        campaign_text = f"<b>{campaign_data['name']}</b>\n"
        campaign_text += f"<b>Статус:</b> {campaign_data['status']}\n"
        campaign_text += f"<b>Конверсии:</b> {campaign_data['results_str']}\n"
        campaign_text += f"<b>Охват:</b> {campaign_data['reach_str']}\n"
        campaign_text += f"<b>Частота:</b> {campaign_data['frequency_str']}\n"
        campaign_text += f"<b>Цена конверсии:</b> {campaign_data['cost_str']} (Тип: {campaign_data['used_conversion_type']})\n"
        campaign_text += f"<b>Расход:</b> {campaign_data['spend_str']}\n"
        campaign_text += f"<b>CPM:</b> {campaign_data['cpm_str']}\n"
        campaign_text += f"<b>CTR:</b> {campaign_data['ctr_str']}\n"
        
        campaign_blocks.append(campaign_text)
    
    # Join campaign blocks with double line breaks
    message += "\n\n".join(campaign_blocks)
    
    return message 