"""
Константы для использования в системе Telegram бота
"""
import os
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv(".env.dev")  # Загружаем переменные из .env.dev

# Администраторы (список ID пользователей Telegram)
ADMIN_IDS = []
admin_users_str = os.getenv("ADMIN_USERS", "")
if admin_users_str:
    ADMIN_IDS = [int(user_id.strip()) for user_id in admin_users_str.split(",") if user_id.strip().isdigit()]
    
# Лимиты и ограничения
MAX_MESSAGE_LENGTH = 4096  # Максимальная длина сообщения в Telegram
MAX_ITEMS_PER_PAGE = 10    # Максимальное количество элементов на странице
MAX_BUTTON_TEXT_LENGTH = 64 # Максимальная длина текста для кнопки

# Временные интервалы
CACHE_TIMEOUT = 60 * 60    # Время жизни кэша (1 час в секундах)
TOKEN_REFRESH_INTERVAL = 60 * 60 * 24  # Интервал обновления токена (24 часа в секундах)

# Состояния ответов
SUCCESS = "SUCCESS"
ERROR = "ERROR"
WARNING = "WARNING"
INFO = "INFO"

# Константы фильтров
DATE_PRESET_PREFIX = "date_preset_"
ACCOUNT_PREFIX = "account_"
CAMPAIGN_PREFIX = "campaign_"
AD_PREFIX = "ad_"
FILTER_PREFIX = "filter_"

# Количество попыток повторения API запросов при ошибках
API_RETRY_ATTEMPTS = 3 