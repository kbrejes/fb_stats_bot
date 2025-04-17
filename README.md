# Facebook Ads Telegram Bot

Telegram бот для выгрузки и анализа данных из рекламного кабинета Facebook Ads.

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

## Использование

- `/start` - Начать работу с ботом
- `/auth` - Авторизоваться в Facebook Ads
- `/accounts` - Получить список доступных рекламных аккаунтов
- `/campaigns <account_id>` - Получить список кампаний
- `/ads <campaign_id>` - Получить список объявлений
- `/stats <campaign_id|ad_id> <date_range>` - Получить статистику
- `/export <format>` - Экспортировать данные
- `/help` - Справка по командам

## Требования

- Python 3.10+
- Telegram Bot API Token
- Facebook App с правами на Marketing API

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