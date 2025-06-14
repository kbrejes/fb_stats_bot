#!/bin/bash

# Скрипт для проверки кода перед деплоем
# Использование: ./scripts/pre_deploy_check.sh

set -e  # Остановить выполнение при любой ошибке

echo "🚀 Запуск проверки перед деплоем..."

# Проверяем, что мы в правильной директории
if [ ! -f "requirements.txt" ]; then
    echo "❌ Ошибка: Запустите скрипт из корневой директории проекта"
    exit 1
fi

# Устанавливаем зависимости для тестирования
echo "📦 Установка зависимостей для тестирования..."
python3 -m pip install -q pytest pytest-asyncio pytest-cov black flake8 mypy isort

# Форматирование кода
echo "🎨 Форматирование кода..."
python3 -m black src/ tests/ --quiet || {
    echo "❌ Ошибка форматирования кода"
    exit 1
}

python3 -m isort src/ tests/ --quiet || {
    echo "❌ Ошибка сортировки импортов"
    exit 1
}

# Линтинг
echo "🔍 Проверка линтерами..."
python3 -m flake8 src/ tests/ --max-line-length=88 --extend-ignore=E203,W503 || {
    echo "❌ Ошибки линтинга"
    exit 1
}

# Проверка типов (не критично, только предупреждения)
echo "🔬 Проверка типов..."
python3 -m mypy src/ --ignore-missing-imports || {
    echo "⚠️  Предупреждения проверки типов (не критично)"
}

# Запуск тестов
echo "🧪 Запуск тестов..."
python3 -m pytest tests/ -v --tb=short || {
    echo "❌ Тесты не прошли"
    exit 1
}

# Проверка импортов
echo "📋 Проверка импортов..."
python3 -c "
import sys
sys.path.append('src')
try:
    from services.analytics import AnalyticsService, ComparisonPeriod
    from api.facebook import FacebookAdsClient
    from data.processor import DataProcessor
    print('✅ Все основные модули импортируются корректно')
except ImportError as e:
    print(f'❌ Ошибка импорта: {e}')
    sys.exit(1)
"

echo ""
echo "✅ Все проверки пройдены успешно!"
echo "🚀 Код готов к деплою в production"
echo ""
echo "Для деплоя выполните:"
echo "  git add ."
echo "  git commit -m 'fix: исправление тестов и добавление pre-deploy проверок'"
echo "  git push origin production" 