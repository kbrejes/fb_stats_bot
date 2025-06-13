# Facebook Ads Telegram Bot 🤖

Продвинутый Telegram бот для работы с Facebook Ads Manager, включающий AI-анализ статистики, систему уведомлений и экспорт данных.

## ✨ Возможности

### 🔐 Базовая функциональность
- **OAuth авторизация** в Facebook Ads Manager
- **Просмотр рекламных аккаунтов** с поддержкой множественных аккаунтов
- **Управление кампаниями и объявлениями**
- **Детальная статистика** с расчетом ключевых метрик
- **Экспорт данных** в CSV, JSON, Excel форматах

### 🤖 AI-Анализ статистики
- **Умный анализ** данных через OpenAI GPT
- **Сравнительная аналитика** (текущий vs предыдущий период)
- **Автоматические инсайты** и рекомендации
- **Интерпретация трендов** и метрик производительности

### 🔔 Система уведомлений
- **Push-уведомления** о статистике
- **Настройка времени** и часового пояса
- **Типы уведомлений**: ежедневная статистика, алерты производительности, бюджетные предупреждения
- **Планировщик задач** с поддержкой множественных аккаунтов

### 👥 Система ролей и разрешений
- **Роли**: Owner, Admin, User
- **Гибкие разрешения** на основе ролей
- **Безопасный доступ** к функциям бота
- **Управление пользователями**

### 🌍 Дополнительные возможности
- **Мультиязычность** (русский/английский)
- **Кэширование данных** для оптимизации
- **Шифрование токенов** для безопасности
- **Интерактивные клавиатуры** и меню

## 🏗️ Архитектура

```
fb_ads_tg_bot_clean/
├── src/                        # Основной код приложения
│   ├── bot/                    # Telegram bot логика
│   │   ├── handlers/           # Обработчики команд
│   │   ├── keyboards/          # Клавиатуры и меню
│   │   └── callbacks/          # Callback handlers
│   ├── services/               # Бизнес-логика
│   │   ├── notifications.py    # Система уведомлений
│   │   └── analytics.py        # AI аналитика
│   ├── storage/                # Работа с БД
│   │   ├── models.py           # SQLAlchemy модели
│   │   └── database.py         # Настройка БД
│   ├── utils/                  # Утилиты и помощники
│   └── api/                    # Facebook API интеграция
├── config/                     # Конфигурация
├── tests/                      # Тесты
├── migrations/                 # Миграции БД
└── alembic/                    # Alembic конфигурация
```

## 🛠️ Технологический стек

- **Python 3.11+** — основной язык
- **aiogram 3.0+** — Telegram Bot API
- **SQLAlchemy 2.0** — ORM для работы с БД  
- **SQLite/PostgreSQL** — база данных
- **Facebook Business API** — работа с рекламными данными
- **OpenAI API** — AI анализ статистики
- **APScheduler** — планировщик уведомлений
- **pytest** — тестирование

## 📦 Установка

### 1. Клонирование репозитория
```bash
git clone https://github.com/yourusername/fb_ads_tg_bot_clean.git
cd fb_ads_tg_bot_clean
```

### 2. Создание виртуального окружения
```bash
python3 -m venv venv
source venv/bin/activate  # На Windows: venv\Scripts\activate
```

### 3. Установка зависимостей
```bash
pip install -r requirements.txt
```

### 4. Настройка переменных окружения

Создайте файлы конфигурации для разных окружений:

**`.env` (базовая конфигурация):**
```env
# Telegram Bot
TELEGRAM_TOKEN=your_bot_token_from_botfather
OWNER_ID=your_telegram_id
OWNER_USERNAME=your_username
OWNER_FIRST_NAME=Your Name

# Facebook API
FB_APP_ID=your_facebook_app_id
FB_APP_SECRET=your_facebook_app_secret
FB_REDIRECT_URI=http://localhost:8000/callback
FB_API_VERSION=v19.0

# OpenAI API
OPENAI_API_KEY=your_openai_api_key

# Security
ENCRYPTION_KEY=your_32_byte_hex_key

# Database
DB_CONNECTION_STRING=sqlite:///database_dev.sqlite

# Debug
DEBUG=True
LOG_LEVEL=DEBUG
```

**`.env.dev` (разработка):**
```env
ENVIRONMENT=development
DB_CONNECTION_STRING=sqlite:///database_dev.sqlite
DEBUG=True
LOG_LEVEL=DEBUG
```

**`.env.prod` (продакшн):**
```env
ENVIRONMENT=production
DB_CONNECTION_STRING=postgresql://user:password@localhost/dbname
DEBUG=False
LOG_LEVEL=INFO
```

### 5. Инициализация базы данных
```bash
# Для разработки
ENVIRONMENT=development python initialize_db.py

# Для продакшна
ENVIRONMENT=production python initialize_db.py --env production
```

### 6. Запуск бота
```bash
# Разработка
ENVIRONMENT=development python main.py

# Продакшн
ENVIRONMENT=production python main.py
```

## 🚀 Использование

### Основные команды
- `/start` — регистрация и приветствие
- `/help` — справка по всем командам
- `/menu` — интерактивное главное меню
- `/auth` — авторизация в Facebook Ads

### Работа с данными
- `/accounts` — список рекламных аккаунтов
- `/campaigns [account_id]` — кампании по аккаунту
- `/ads [campaign_id]` — объявления по кампании
- `/stats [object_id] [period]` — детальная статистика
- `/export [format]` — экспорт в CSV/JSON/Excel

### Система уведомлений
- `/notifications` — настройка push-уведомлений
  - Включение/выключение уведомлений
  - Настройка времени отправки
  - Выбор часового пояса
  - Типы уведомлений

### AI-Аналитика
- Автоматический анализ статистики через OpenAI
- Сравнительная аналитика по периодам  
- Умные инсайты и рекомендации
- Интерпретация трендов

## 🧪 Тестирование

### Запуск тестов
```bash
# Все тесты
python -m pytest tests/ -v

# Тесты с покрытием
python -m pytest tests/ --cov=src --cov-report=html

# Тесты конкретного модуля
python -m pytest tests/services/test_analytics.py -v
```

### Линтеры и форматирование
```bash
# Форматирование кода
black src/ tests/

# Проверка стиля
flake8 src/ tests/

# Проверка типов
mypy src/
```

## 🔐 Безопасность

- **Шифрование токенов** — все Facebook токены шифруются в БД
- **Система ролей** — разграничение доступа по ролям
- **Валидация данных** — проверка всех входящих данных
- **Логирование** — детальное логирование всех операций

## 📈 Мониторинг

### Логи
- **Основные логи**: `bot.log`
- **Уведомления**: `notifications.log`
- **Уровни логирования**: DEBUG, INFO, WARNING, ERROR, CRITICAL

### База данных
```bash
# Просмотр структуры БД
python print_db_structure.py

# Миграции
alembic upgrade head
alembic downgrade -1
```

## 🌍 Окружения

### Development (разработка)
- Отдельная БД `database_dev.sqlite`
- Подробное логирование
- Debug режим включен

### Production (продакшн)
- PostgreSQL или SQLite
- Оптимизированное логирование
- Безопасные настройки

### Test (тестирование)
- Тестовая БД в памяти
- Моки для внешних API
- Изолированные тесты

## 📊 Статистика проекта

- **Версия**: 1.0.0
- **Python**: 3.11+
- **Общее кол-во файлов**: 50+
- **Покрытие тестами**: 80%+
- **Архитектурный стиль**: Модульная архитектура

## 🤝 Разработка

### Workflow
1. Создать feature branch
2. Написать тесты
3. Реализовать функциональность
4. Запустить тесты и линтеры
5. Создать Pull Request

### Структура коммитов
```
feat: новая функциональность
fix: исправление бага
refactor: рефакторинг кода
chore: технические изменения
docs: обновление документации
```

## 📝 Лицензия

MIT License - см. файл [LICENSE](LICENSE)

## 🆘 Поддержка

При возникновении проблем:
1. Проверьте логи в `bot.log`
2. Убедитесь, что все переменные окружения настроены
3. Проверьте статус Facebook App и токенов
4. Создайте Issue в репозитории

---

**Создано с ❤️ для эффективной работы с Facebook Ads** 