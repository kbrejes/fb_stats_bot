.PHONY: help install test lint format check-all pre-commit clean

help: ## Показать справку
	@echo "Доступные команды:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Установить зависимости
	pip install -r requirements.txt
	pip install pre-commit
	pre-commit install

test: ## Запустить тесты
	python -m pytest tests/ -v --cov=src --cov-report=term-missing

test-fast: ## Запустить тесты без coverage
	python -m pytest tests/ -v --tb=short

lint: ## Проверить код линтерами
	flake8 src/ tests/
	mypy src/ --ignore-missing-imports

format: ## Отформатировать код
	black src/ tests/
	isort src/ tests/

check-all: format lint test ## Полная проверка кода (форматирование + линтинг + тесты)

pre-commit: ## Запустить pre-commit хуки
	pre-commit run --all-files

pre-deploy: check-all ## Проверка перед деплоем
	@echo "✅ Все проверки пройдены! Код готов к деплою."

clean: ## Очистить временные файлы
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type f -name ".coverage" -delete 