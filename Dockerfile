# Facebook Ads Telegram Bot - Production Dockerfile
FROM python:3.11-slim

# Метаданные
LABEL maintainer="kbrejes"
LABEL description="Facebook Ads Telegram Bot - Production"
LABEL version="1.0.0"

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Создание пользователя для безопасности
RUN useradd --create-home --shell /bin/bash bot

# Создание рабочей директории
WORKDIR /app

# Копирование requirements и установка Python зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Добавление дополнительных production зависимостей
RUN pip install --no-cache-dir \
    psycopg2-binary \
    sentry-sdk \
    gunicorn \
    prometheus-client

# Копирование исходного кода
COPY . .

# Создание необходимых директорий
RUN mkdir -p logs data backups && \
    chown -R bot:bot /app

# Переключение на пользователя bot
USER bot

# Переменные окружения
ENV ENVIRONMENT=production
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Открытие портов
EXPOSE 8000 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Запуск приложения
CMD ["python", "main_simple.py"] 