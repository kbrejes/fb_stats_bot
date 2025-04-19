from datetime import datetime, timezone
from typing import Optional

from aiogram.types import CallbackQuery

from src.bot.callbacks import account_callbacks
from src.bot.exceptions import handle_exceptions
from src.bot.types import CampaignCallbackData
from src.db.enums import StatisticalMetric
from src.models.campaign import Campaign
from src.services.fbservice import FBService
from src.utils.dates import subtract_days_from_today
from src.utils.logger import setup_logger

logger = setup_logger("campaign_callbacks")


async def process_campaign_stats_callback(
    callback_query: CallbackQuery,
    user_id: int,
    action: str,
    campaign_id: Optional[str] = None,
    metric: Optional[StatisticalMetric] = None,
) -> None:
    """Process the campaign stats callback."""
    logger.info(f"Processing campaign stats callback: {action} for user {user_id}")
    
    # For campaign level statistics, we delegate to the account callback handler
    # since the implementation is the same
    if action == "stats":
        await account_callbacks.campaign_stats_callback(
            callback_query, user_id, campaign_id
        )
    elif action == "detailed_stats" and campaign_id and metric:
        await campaign_detailed_stats_callback(
            callback_query, user_id, campaign_id, metric
        )
    else:
        logger.error(f"Unknown campaign stats action: {action}")
        await callback_query.answer("Unknown action")


@handle_exceptions(notify_user=True, log_error=True)
async def campaign_detailed_stats_callback(
    callback_query: CallbackQuery,
    user_id: int,
    campaign_id: str,
    metric: StatisticalMetric,
) -> None:
    """Show detailed campaign statistics for a specific metric."""
    logger.info(f"Getting detailed campaign stats for {campaign_id}, metric: {metric}")
    
    # Handle date range - default to last 7 days
    end_date = datetime.now(timezone.utc)
    start_date = subtract_days_from_today(7)
    
    # Get the campaign from database
    campaign = await Campaign.get_by_id(campaign_id)
    if not campaign:
        await callback_query.answer("Campaign not found")
        return
    
    fb_service = FBService()
    stats = await fb_service.get_campaign_stats(
        user_id=user_id,
        campaign_id=campaign_id,
        start_date=start_date,
        end_date=end_date,
        metrics=[metric]
    )
    
    if not stats:
        await callback_query.answer("No statistics available")
        return
    
    # Prepare message with detailed stats
    message = f"📊 Detailed stats for campaign: {campaign.name}\n"
    message += f"Metric: {metric.value}\n\n"
    
    for date, values in stats.items():
        if metric.value in values:
            message += f"{date}: {values[metric.value]}\n"
    
    # Send the detailed stats
    await callback_query.message.answer(message)
    await callback_query.answer()


@handle_exceptions(notify_user=True, log_error=True)
async def process_campaign_callback(
    callback_query: CallbackQuery, callback_data: CampaignCallbackData
) -> None:
    """Process campaign callbacks."""
    logger.info(f"Processing campaign callback: {callback_data.type}")
    
    user_id = callback_query.from_user.id
    
    if callback_data.type == "stats":
        await process_campaign_stats_callback(
            callback_query, user_id, "stats", callback_data.id
        )
    elif callback_data.type == "detailed_stats":
        # Assuming metric would be passed in the callback_data
        # This would need to be added to CampaignCallbackData if not present
        metric_str = getattr(callback_data, "metric", StatisticalMetric.SPEND.value)
        metric = StatisticalMetric(metric_str)
        
        await process_campaign_stats_callback(
            callback_query, user_id, "detailed_stats", callback_data.id, metric
        )
    else:
        logger.warning(f"Unknown campaign callback type: {callback_data.type}")
        await callback_query.answer("This action is not implemented yet") 