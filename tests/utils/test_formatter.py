"""
Скрипт для тестирования обновленного форматтера сообщений stats_callback.

Симулирует обработку и отображение данных о статистике, включая кастомные конверсии.
"""

import argparse
import asyncio
import json
from typing import Any, Dict, List, Optional

from src.api.facebook import FacebookAdsClient
from src.utils.message_formatter import format_insights


async def test_formatter(
    user_id: int,
    object_id: str,
    object_type: str = "account",
    date_preset: str = "yesterday",
):
    """
    Получить данные инсайтов и отобразить их с помощью нового форматтера.

    Args:
        user_id: ID пользователя в Telegram
        object_id: ID объекта (аккаунта, кампании, adset, объявления)
        object_type: Тип объекта (account, campaign, adset, ad)
        date_preset: Период данных (today, yesterday, last_7d, etc.)
    """
    print(f"\n=== Testing Message Formatter ===")
    print(f"User ID: {user_id}")
    print(f"Object Type: {object_type}")
    print(f"Object ID: {object_id}")
    print(f"Date Preset: {date_preset}")

    # Создаем клиента Facebook API
    client = FacebookAdsClient(user_id)

    # Получаем insights в зависимости от типа объекта
    insights = []
    try:
        if object_type == "account":
            insights = await client.get_account_insights(object_id, date_preset)
        elif object_type == "campaign":
            insights = await client.get_campaign_insights(object_id, date_preset)
        elif object_type == "adset":
            insights = await client.get_adset_insights(object_id, date_preset)
        elif object_type == "ad":
            insights = await client.get_ad_insights(object_id, date_preset)
        else:
            print(f"Unknown object type: {object_type}")
            return

        if not insights:
            print(f"No insights found for this {object_type}.")
            return

        # Применяем форматтер и отображаем результат
        formatted_text = format_insights(insights, object_type, date_preset)

        print("\n=== Formatted Message ===")
        print(formatted_text)

    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback

        traceback.print_exc()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Test the message formatter with custom conversions"
    )
    parser.add_argument(
        "--user_id", type=int, default=400133981, help="Telegram user ID"
    )
    parser.add_argument(
        "--object_id",
        type=str,
        default="act_8774430319299378",
        help="Object ID (account, campaign, etc.)",
    )
    parser.add_argument(
        "--object_type",
        type=str,
        choices=["account", "campaign", "adset", "ad"],
        default="account",
        help="Object type",
    )
    parser.add_argument(
        "--date_preset",
        type=str,
        default="yesterday",
        help="Date preset (today, yesterday, last_7d, etc.)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(
        test_formatter(args.user_id, args.object_id, args.object_type, args.date_preset)
    )
