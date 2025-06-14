#!/bin/bash

# Быстрая проверка тестов перед деплоем
# Использование: ./scripts/quick_test.sh

set -e  # Остановить выполнение при любой ошибке

echo "🧪 Быстрая проверка тестов перед деплоем..."

# Устанавливаем тестовое окружение
export ENVIRONMENT=test

# Проверяем, что мы в правильной директории
if [ ! -f "requirements.txt" ]; then
    echo "❌ Ошибка: Запустите скрипт из корневой директории проекта"
    exit 1
fi

# Устанавливаем зависимости из requirements.txt
echo "📦 Установка зависимостей..."
python3 -m pip install -q -r requirements.txt

# Проверка импортов
echo "📋 Проверка основных импортов..."
ENVIRONMENT=test python3 -c "
import sys
sys.path.append('src')
try:
    from services.analytics import AnalyticsService, ComparisonPeriod
    print('✅ analytics импортируется корректно')
except ImportError as e:
    print(f'❌ Ошибка импорта analytics: {e}')
    sys.exit(1)

try:
    from api.facebook import FacebookAdsClient
    print('✅ facebook API импортируется корректно')
except ImportError as e:
    print(f'❌ Ошибка импорта facebook API: {e}')
    sys.exit(1)

try:
    from data.processor import DataProcessor
    print('✅ data processor импортируется корректно')
except ImportError as e:
    print(f'❌ Ошибка импорта data processor: {e}')
    sys.exit(1)
"

# Запуск только тестов analytics (самые важные)
echo "🧪 Запуск тестов analytics..."
ENVIRONMENT=test python3 -m pytest tests/services/test_analytics.py -v --tb=short || {
    echo "❌ Тесты analytics не прошли"
    exit 1
}

echo ""
echo "✅ Быстрая проверка пройдена успешно!"
echo "🚀 Основные тесты работают, можно деплоить"
echo ""
echo "Для деплоя выполните:"
echo "  git add ."
echo "  git commit -m 'fix: исправление импортов и тестов'"
echo "  git push origin production" 