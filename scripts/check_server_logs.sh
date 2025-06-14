#!/bin/bash

# Скрипт для проверки логов и статуса Facebook Ads Telegram Bot на сервере

echo "🔍 Facebook Ads Bot - Диагностика сервера"
echo "=========================================="

# Проверка доступности сервера
echo "📡 Проверка доступности сервера..."
if ping -c 1 188.166.221.59 > /dev/null 2>&1; then
    echo "✅ Сервер доступен"
else
    echo "❌ Сервер недоступен"
    exit 1
fi

# Проверка health endpoint
echo ""
echo "🏥 Проверка health endpoint..."
if curl -f -s http://188.166.221.59:8080/health > /dev/null 2>&1; then
    echo "✅ Health endpoint отвечает"
    curl -s http://188.166.221.59:8080/health | jq . 2>/dev/null || curl -s http://188.166.221.59:8080/health
else
    echo "❌ Health endpoint не отвечает"
fi

echo ""
echo "📋 Команды для проверки логов на сервере:"
echo "=========================================="

echo ""
echo "1️⃣ Подключение к серверу:"
echo "ssh root@188.166.221.59"

echo ""
echo "2️⃣ Переход в директорию проекта:"
echo "cd /root/fb_ads_tg_bot_clean"

echo ""
echo "3️⃣ Проверка статуса Docker контейнеров:"
echo "docker ps -a"

echo ""
echo "4️⃣ Просмотр логов бота (последние 50 строк):"
echo "docker logs fb_ads_bot_app --tail=50"

echo ""
echo "5️⃣ Просмотр логов бота в реальном времени:"
echo "docker logs fb_ads_bot_app -f"

echo ""
echo "6️⃣ Просмотр логов всех сервисов:"
echo "docker-compose -f docker-compose.prod.yml logs --tail=50"

echo ""
echo "7️⃣ Проверка файлов логов (если есть):"
echo "ls -la logs/"
echo "tail -50 logs/bot_production.log"
echo "tail -50 logs/error_production.log"

echo ""
echo "8️⃣ Проверка .env.prod файла:"
echo "cat .env.prod | head -20"

echo ""
echo "9️⃣ Перезапуск бота:"
echo "docker-compose -f docker-compose.prod.yml restart bot"

echo ""
echo "🔟 Полный перезапуск всех сервисов:"
echo "docker-compose -f docker-compose.prod.yml down"
echo "docker-compose -f docker-compose.prod.yml up -d"

echo ""
echo "📊 Мониторинг ресурсов:"
echo "========================"
echo "htop                    # Процессы и память"
echo "df -h                   # Дисковое пространство"
echo "docker stats            # Статистика контейнеров"

echo ""
echo "🚨 В случае проблем:"
echo "===================="
echo "# Очистка Docker"
echo "docker system prune -f"
echo ""
echo "# Пересборка образа"
echo "docker-compose -f docker-compose.prod.yml build --no-cache bot"
echo ""
echo "# Проверка сети"
echo "docker network ls"
echo "docker network inspect fb_ads_tg_bot_clean_bot_network" 