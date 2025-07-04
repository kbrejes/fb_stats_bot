# Facebook Ads Telegram Bot

Телеграм бот для управления рекламными кампаниями в Facebook Ads.

## Особенности

- Интеграция с Facebook Marketing API
- Просмотр рекламных аккаунтов, кампаний, наборов объявлений и объявлений
- Получение статистики по рекламным кампаниям
- Управление рекламными объявлениями (включение/отключение)
- Система обработки ошибок с уведомлением пользователей

## Возможности

- Авторизация в Facebook Ads через OAuth
- Просмотр списка рекламных аккаунтов
- Получение данных о кампаниях и объявлениях
- Выгрузка статистики за выбранный период
- Экспорт данных в CSV, JSON, Excel

## Установка

1. Клонировать репозиторий:
```bash
git clone https://github.com/yourusername/fb_ads_tg_bot.git
cd fb_ads_tg_bot
```

2. Создать виртуальное окружение и установить зависимости:
```bash
python -m venv venv
source venv/bin/activate  # На Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. Скопировать `.env.example` в `.env` и заполнить необходимые переменные окружения:
```bash
cp .env.example .env
```

4. Инициализировать базу данных:
```bash
python initialize_db.py
```

5. Запустить бота:
```bash
python main.py
```

## Структура проекта

```
fb_ads_tg_bot/
├── src/
│   ├── api/
│   │   ├── facebook/
│   │   │   ├── mixins/
│   │   │   │   ├── account.py
│   │   │   │   ├── ad.py
│   │   │   │   ├── adset.py
│   │   │   │   ├── campaign.py
│   │   │   │   ├── insights.py
│   │   │   ├── client.py
│   │   │   ├── __init__.py
│   ├── bot/
│   │   ├── callbacks/
│   │   ├── handlers/
│   │   ├── keyboards/
│   │   ├── __init__.py
│   ├── db/
│   │   ├── models/
│   │   ├── repositories/
│   │   ├── __init__.py
│   ├── utils/
│   │   ├── error_handlers.py
│   │   ├── logger.py
│   ├── main.py
├── .env
├── requirements.txt
├── README.md
```

## Система обработки ошибок

Проект включает централизованную систему обработки ошибок, позволяющую:

- Унифицировать обработку исключений разных типов
- Автоматически логировать ошибки с контекстом
- Отправлять пользователям уведомления об ошибках
- Применять декораторы для простого добавления обработчиков ошибок

### Типы ошибок

- `APIError` - базовый класс для ошибок API
- `FacebookAPIError` - ошибки Facebook API
- `TelegramAPIError` - ошибки Telegram API
- `DatabaseError` - ошибки базы данных
- `AuthorizationError` - ошибки авторизации
- `ValidationError` - ошибки валидации данных

### Использование декораторов

```python
# Декоратор для общей обработки ошибок
@handle_exceptions()
async def some_handler(message: Message):
    # Код обработчика

# Декоратор для обработки ошибок API
@api_error_handler(api_name="Facebook API")
async def api_function():
    # Код функции API

# Декоратор для обработки ошибок базы данных
@db_error_handler(operation="save user data")
async def db_function():
    # Код функции базы данных

# Комбинирование декораторов
@handle_exceptions()
@api_error_handler(api_name="Facebook API")
@db_error_handler(operation="sync data")
async def complex_function():
    # Код с обращениями к API и базе данных
```

Примеры использования см. в файле `src/utils/error_handlers_examples.py`.

## Лицензия

MIT 

## Environment Setup

The bot supports multiple environments (development and production) to ensure a clear separation between production and local development.

### Environment Files

- `.env.dev` - Development environment configuration
- `.env.prod` - Production environment configuration

### Running in Different Environments

To run the bot in development mode:
```bash
./run_dev.sh
```

To run the bot in production mode:
```bash
./run_prod.sh
```

Alternatively, you can set the environment variable manually:
```bash
export ENVIRONMENT=development  # or production
python main.py
```

### Database Management

Each environment uses its own database:
- Production: `database.sqlite` (or configured PostgreSQL in production)
- Development: `database_dev.sqlite`

To initialize the database using the provided script:
```bash
# For development (default)
python initialize_db.py

# For production
python initialize_db.py --env production
# or
python initialize_db.py -e production
```

To initialize the development database using the shell script:
```bash
./init_dev_db.sh
```

To manually initialize either database:
```bash
# For development
export ENVIRONMENT=development
python -c "from src.storage.database import init_db; init_db()"

# For production
export ENVIRONMENT=production
python -c "from src.storage.database import init_db; init_db()"
```

### Configuration Differences

- Development environment uses a separate database (`database_dev.sqlite`)
- Development has DEBUG mode enabled
- Each environment can have its own Telegram bot token
- Production should have appropriate callback URLs for Facebook API 

## Пример изменения для демонстрации коммита

Это пример изменения файла для демонстрации коммита в Git. 