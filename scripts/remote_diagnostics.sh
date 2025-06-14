#!/bin/bash

# Автоматическая диагностика Facebook Ads Bot на удаленном сервере

SERVER="188.166.221.59"
USER="root"
PROJECT_DIR="/root/fb_ads_tg_bot_clean"

echo "🚀 Подключение к серверу $SERVER..."
echo "======================================"

# Функция для выполнения команд на сервере
run_remote() {
    echo "📡 Выполняю: $1"
    ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no $USER@$SERVER "$1"
    echo ""
}

# Проверка подключения
echo "🔍 Проверка подключения к серверу..."
if ! ssh -o ConnectTimeout=10 -o BatchMode=yes -o StrictHostKeyChecking=no $USER@$SERVER exit 2>/dev/null; then
    echo "❌ Не удается подключиться к серверу"
    echo "💡 Убедитесь, что:"
    echo "   - SSH ключ настроен"
    echo "   - Сервер доступен"
    echo "   - Порт 22 открыт"
    exit 1
fi

echo "✅ Подключение установлено!"
echo ""

# Диагностика системы
echo "🖥️  СИСТЕМНАЯ ИНФОРМАЦИЯ"
echo "========================="
run_remote "uname -a"
run_remote "uptime"
run_remote "df -h"
run_remote "free -h"

# Проверка Docker
echo "🐳 DOCKER СТАТУС"
echo "================"
run_remote "docker --version"
run_remote "docker-compose --version"
run_remote "docker ps -a"

# Проверка проекта
echo "📁 ПРОЕКТ"
echo "========="
run_remote "ls -la $PROJECT_DIR"
run_remote "cd $PROJECT_DIR && pwd"

# Проверка .env файла
echo "⚙️  КОНФИГУРАЦИЯ"
echo "================"
run_remote "cd $PROJECT_DIR && ls -la .env*"
run_remote "cd $PROJECT_DIR && head -10 .env.prod 2>/dev/null || echo 'Файл .env.prod не найден'"

# Docker Compose статус
echo "🔧 DOCKER COMPOSE"
echo "================="
run_remote "cd $PROJECT_DIR && docker-compose -f docker-compose.prod.yml ps"

# Логи контейнеров
echo "📋 ЛОГИ КОНТЕЙНЕРОВ"
echo "==================="
run_remote "cd $PROJECT_DIR && docker logs fb_ads_bot_app --tail=20 2>/dev/null || echo 'Контейнер fb_ads_bot_app не найден'"

# Проверка портов
echo "🌐 СЕТЕВЫЕ ПОРТЫ"
echo "================"
run_remote "netstat -tlnp | grep -E ':(8000|8080|5432|6379)' || echo 'Порты не прослушиваются'"

# Проверка процессов
echo "⚡ ПРОЦЕССЫ"
echo "=========="
run_remote "ps aux | grep -E '(python|docker|postgres|redis)' | grep -v grep"

echo ""
echo "🎯 РЕКОМЕНДАЦИИ:"
echo "================"
echo "Если контейнеры не запущены, выполните:"
echo "ssh $USER@$SERVER"
echo "cd $PROJECT_DIR"
echo "docker-compose -f docker-compose.prod.yml up -d"
echo ""
echo "Для просмотра логов в реальном времени:"
echo "docker-compose -f docker-compose.prod.yml logs -f" 