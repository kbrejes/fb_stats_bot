# Facebook Ads Bot - Handlers

Эта директория содержит все обработчики (handlers) для телеграм-бота Facebook Ads.

## Структура

- `__init__.py` - Инициализация пакета, экспортирует все маршрутизаторы (routers)
- `account.py` - Обработчики для работы с рекламными аккаунтами
- `ad.py` - Обработчики для работы с объявлениями
- `auth.py` - Обработчики авторизации в Facebook
- `campaign.py` - Обработчики для работы с рекламными кампаниями
- `common.py` - Общие обработчики (start, menu, language и т.д.)
- `main.py` - Обработчики для главного меню и навигации

## Использование

Все обработчики экспортируются через специальные маршрутизаторы (routers), которые затем используются в main.py:

```python
from src.bot.handlers import (
    common_router,
    auth_router,
    account_router,
    campaign_router,
    ad_router,
    main_router
)

# Include routers
dp.include_router(common_router)
dp.include_router(account_router)
...
```

## Bridge файлы

Для обеспечения обратной совместимости в корневой директории `/src/bot/` созданы bridge файлы, которые переадресуют импорты из старой структуры в новую.

## Типы маршрутизаторов

- `common_router` - Базовые команды (/start, /menu, /language)
- `auth_router` - Авторизация (/auth)
- `account_router` - Работа с аккаунтами (/accounts)
- `campaign_router` - Работа с кампаниями (/campaigns)
- `ad_router` - Работа с объявлениями (/ads)
- `main_router` - Навигация и главное меню 