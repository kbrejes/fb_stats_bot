# 🚀 CI/CD Setup Guide

Настройка автоматического развертывания Facebook Ads Telegram Bot на DigitalOcean через GitHub Actions.

## 📋 Содержание

1. [Подготовка GitHub репозитория](#подготовка-github-репозитория)
2. [Настройка GitHub Secrets](#настройка-github-secrets)
3. [Настройка сервера](#настройка-сервера)
4. [Настройка окружений](#настройка-окружений)
5. [Workflow описание](#workflow-описание)
6. [Мониторинг и уведомления](#мониторинг-и-уведомления)

---

## 🔧 Подготовка GitHub репозитория

### 1. Push кода в GitHub
```bash
# Инициализация git (если не сделано)
git init
git add .
git commit -m "Initial commit: Facebook Ads Telegram Bot"

# Добавление remote репозитория
git remote add origin https://github.com/USERNAME/fb_ads_tg_bot_clean.git
git branch -M main
git push -u origin main
```

### 2. Создание веток для разработки
```bash
# Создание ветки для разработки
git checkout -b develop
git push -u origin develop

# Создание ветки для staging
git checkout -b staging
git push -u origin staging
```

## 🔐 Настройка GitHub Secrets

Перейдите в **Settings** → **Secrets and variables** → **Actions** в вашем GitHub репозитории.

### Production Secrets
```
# Сервер
PROD_HOST=YOUR_DIGITALOCEAN_SERVER_IP
PROD_USER=botuser
PROD_SSH_KEY=-----BEGIN OPENSSH PRIVATE KEY-----
...
-----END OPENSSH PRIVATE KEY-----
PROD_PORT=22

# API Keys
TELEGRAM_TOKEN=7595294156:AAFcKTYzTt0h0xEt-BiVs-otrmYB6dAL7LY
OPENAI_API_KEY=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
FB_APP_ID=639419165542707
FB_APP_SECRET=73af4e475afddfbd61fb74628481eb28

# Уведомления
TELEGRAM_CHAT_ID=400133981
TELEGRAM_BOT_TOKEN=7595294156:AAFcKTYzTt0h0xEt-BiVs-otrmYB6dAL7LY
NOTIFICATION_EMAIL=your-email@gmail.com
EMAIL_USERNAME=your-email@gmail.com
EMAIL_PASSWORD=your-app-password

# Опционально для качества кода
SONAR_TOKEN=your-sonar-token
```

### Staging Secrets (если используете)
```
STAGING_HOST=YOUR_STAGING_SERVER_IP
STAGING_USER=staginguser
STAGING_SSH_KEY=your-staging-ssh-key
STAGING_PORT=22
```

## 🖥️ Настройка сервера

### 1. Создание SSH ключа для GitHub Actions
```bash
# На вашем локальном компьютере
ssh-keygen -t rsa -b 4096 -C "github-actions@yourdomain.com" -f ~/.ssh/github_actions_key

# Скопируйте публичный ключ на сервер
ssh-copy-id -i ~/.ssh/github_actions_key.pub botuser@YOUR_SERVER_IP

# Приватный ключ добавьте в GitHub Secrets как PROD_SSH_KEY
cat ~/.ssh/github_actions_key
```

### 2. Подготовка сервера для CD
```bash
# На сервере создайте директорию для проекта
ssh botuser@YOUR_SERVER_IP
mkdir -p ~/fb_ads_tg_bot_clean
cd ~/fb_ads_tg_bot_clean

# Клонируйте репозиторий
git clone https://github.com/USERNAME/fb_ads_tg_bot_clean.git .

# Создайте необходимые директории
mkdir -p logs/staging data/staging
chmod 755 logs data
```

### 3. Настройка Docker на сервере
```bash
# Убедитесь что Docker установлен и пользователь в группе docker
sudo usermod -aG docker $USER
# Перелогиньтесь для применения изменений
```

## 🌍 Настройка окружений

### 1. GitHub Environments
В вашем репозитории перейдите в **Settings** → **Environments**:

#### Production Environment
- **Name**: `production`
- **Protection rules**: 
  - ✅ Required reviewers (добавьте себя)
  - ✅ Wait timer: 5 minutes
  - ✅ Restrict to protected branches: `main`

#### Staging Environment
- **Name**: `staging`
- **Protection rules**: 
  - ✅ Wait timer: 2 minutes

### 2. Создание .env файлов
```bash
# На сервере создайте production env файл
cd ~/fb_ads_tg_bot_clean
cp env-production.template .env.prod

# Отредактируйте с правильными значениями
nano .env.prod

# Для staging (если используется)
cp env-production.template .env.staging
# Обновите порты и имена БД для staging
```

## 📊 Workflow описание

### 🧪 Test Workflow (`.github/workflows/test.yml`)
**Триггеры:**
- Pull Request в `main` или `develop`
- Push в `develop`

**Этапы:**
1. **Тестирование** - Запуск pytest с покрытием
2. **Проверка качества** - Форматирование, линтинг, типизация
3. **Безопасность** - Сканирование уязвимостей

### 🚀 Deploy Workflow (`.github/workflows/deploy-production.yml`)
**Триггеры:**
- Push в `main` (автоматически в production)
- Manual trigger с выбором окружения

**Этапы:**
1. **Тестирование** - Полный набор тестов
2. **Безопасность** - Trivy сканирование
3. **Сборка** - Docker образ → GitHub Container Registry
4. **Staging** - Деплой в staging (для веток кроме main)
5. **Production** - Деплой в production (только main)
6. **Уведомления** - Telegram/Email уведомления

## 🔄 Процесс развертывания

### Автоматическое развертывание
```bash
# 1. Работа с feature
git checkout develop
git checkout -b feature/new-feature
# ... разработка ...
git add .
git commit -m "feat: add new feature"
git push origin feature/new-feature

# 2. Create Pull Request
# GitHub → Create PR to develop
# Автоматически запустятся тесты

# 3. Merge to develop
# Автоматически деплой в staging (если настроен)

# 4. Release to production
git checkout main
git merge develop
git push origin main
# Автоматически деплой в production
```

### Ручное развертывание
1. Перейдите в **Actions** → **Deploy to Production**
2. Нажмите **Run workflow**
3. Выберите окружение (production/staging)
4. Нажмите **Run workflow**

## 🔍 Мониторинг развертывания

### GitHub Actions Dashboard
- **Actions** → **Workflows** - статус всех workflow
- **Actions** → **Runs** - детали выполнения
- **Settings** → **Secrets** - управление секретами

### Проверка на сервере
```bash
# Статус контейнеров
docker-compose -f docker-compose.prod.yml ps

# Логи
docker-compose -f docker-compose.prod.yml logs -f bot

# Health check
curl http://localhost:8080/health/detailed
```

## 📱 Настройка уведомлений

### Telegram уведомления
1. Создайте бота для уведомлений (или используйте основного)
2. Получите chat_id: отправьте сообщение боту и вызовите:
   ```
   https://api.telegram.org/bot<TOKEN>/getUpdates
   ```
3. Добавьте в GitHub Secrets:
   - `TELEGRAM_CHAT_ID`
   - `TELEGRAM_BOT_TOKEN`

### Email уведомления
1. Настройте App Password в Gmail
2. Добавьте в GitHub Secrets:
   - `EMAIL_USERNAME`
   - `EMAIL_PASSWORD`
   - `NOTIFICATION_EMAIL`

## 🛠️ Дополнительные настройки

### SonarCloud (качество кода)
1. Зарегистрируйтесь на [SonarCloud](https://sonarcloud.io/)
2. Создайте проект
3. Получите токен
4. Добавьте `SONAR_TOKEN` в GitHub Secrets

### Codecov (покрытие тестами)
1. Зарегистрируйтесь на [Codecov](https://codecov.io/)
2. Подключите репозиторий
3. Получите токен (опционально)

## 🚨 Troubleshooting

### Проблемы с SSH
```bash
# Проверка подключения
ssh -i ~/.ssh/github_actions_key botuser@YOUR_SERVER_IP

# Проверка прав
chmod 600 ~/.ssh/github_actions_key
```

### Проблемы с Docker
```bash
# На сервере
sudo systemctl status docker
docker version

# Проверка прав пользователя
groups $USER
```

### Проблемы с развертыванием
```bash
# Проверка логов GitHub Actions
# GitHub → Actions → Failed run → Logs

# Проверка на сервере
cd ~/fb_ads_tg_bot_clean
./scripts/deploy.sh logs
```

## ✅ Checklist настройки CI/CD

- [ ] GitHub репозиторий создан
- [ ] Ветки (main, develop) настроены
- [ ] GitHub Secrets добавлены
- [ ] SSH ключи настроены
- [ ] Сервер подготовлен
- [ ] Environments настроены
- [ ] .env файлы созданы
- [ ] Первый деплой выполнен успешно
- [ ] Уведомления работают
- [ ] Мониторинг настроен
- [ ] Процесс развертывания протестирован

**🎉 CI/CD настроен! Теперь каждый push в main автоматически развернется в production! 🎉**

---

## 📞 Полезные команды

```bash
# Проверка статуса workflow
gh workflow list
gh workflow view "Deploy to Production"

# Запуск workflow вручную
gh workflow run "Deploy to Production" --ref main

# Просмотр последних runs
gh run list --workflow="Deploy to Production"
``` 