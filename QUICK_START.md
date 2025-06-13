# 🚀 Быстрый старт

Краткое руководство для запуска Facebook Ads Telegram Bot.

## ⚡ Минимальная настройка

### 1. Клонирование и установка
```bash
git clone https://github.com/yourusername/fb_ads_tg_bot_clean.git
cd fb_ads_tg_bot_clean
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Создание .env файла
```bash
# Скопируйте ваши существующие значения из .env.dev или создайте новый:
cp .env.dev .env

# Или создайте минимальный .env:
cat > .env << EOF
TELEGRAM_TOKEN=your_bot_token_from_botfather
OWNER_ID=your_telegram_id
FB_APP_ID=your_facebook_app_id
FB_APP_SECRET=your_facebook_app_secret
OPENAI_API_KEY=your_openai_key
ENCRYPTION_KEY=$(python -c "import os; print(os.urandom(32).hex())")
ENVIRONMENT=development
DEBUG=True
EOF
```

### 3. Инициализация и запуск
```bash
# Инициализация БД
ENVIRONMENT=development python initialize_db.py

# Запуск бота
ENVIRONMENT=development python main.py
```

## 🧪 Быстрая проверка

### Проверка импортов
```bash
python -c "from main import main; print('✅ Все модули работают!')"
```

### Запуск тестов
```bash
python -m pytest tests/ -v --tb=short
```

## 📱 Тестирование в Telegram

1. Идите к боту в Telegram
2. Отправьте `/start`
3. Следуйте инструкциям для авторизации
4. Тестируйте основные команды:
   - `/menu` — главное меню
   - `/auth` — авторизация Facebook
   - `/accounts` — список аккаунтов
   - `/notifications` — настройка уведомлений

## 🔧 Основные переменные окружения

| Переменная | Описание | Обязательная |
|------------|----------|--------------|
| `TELEGRAM_TOKEN` | Токен бота от @BotFather | ✅ |
| `OWNER_ID` | Ваш Telegram ID | ✅ |
| `FB_APP_ID` | Facebook App ID | ✅ |
| `FB_APP_SECRET` | Facebook App Secret | ✅ |
| `OPENAI_API_KEY` | OpenAI API ключ | ✅ |
| `ENCRYPTION_KEY` | 32-байтный ключ шифрования | ✅ |
| `ENVIRONMENT` | development/production | ⚠️ |
| `DEBUG` | true/false | ⚠️ |

## 🐛 Решение проблем

### Бот не запускается
```bash
# Проверьте логи
tail -f bot.log

# Проверьте переменные окружения
env | grep -E "(TELEGRAM|FB_|OPENAI)"

# Проверьте БД
python print_db_structure.py
```

### Ошибки импорта
```bash
# Переустановите зависимости
pip install -r requirements.txt --force-reinstall

# Проверьте виртуальное окружение
which python
```

### Проблемы с БД
```bash
# Пересоздайте БД
rm database_dev.sqlite
python initialize_db.py
```

## 📚 Дополнительная информация

- Полная документация: [README.md](README.md)
- Архитектура проекта: см. раздел "Архитектура" в README
- API документация: см. файлы в `src/api/`
- Тесты: см. директорию `tests/`

---

**Время запуска: ~5 минут** ⏱️ 