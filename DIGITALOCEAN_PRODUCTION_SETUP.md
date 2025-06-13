# 🌊 Настройка продакшн на DigitalOcean

## 📋 Информация о сервере
- **IP адрес**: `188.166.221.59`
- **Ваш IP**: `1.46.148.179` (для доступа к мониторингу)
- **GitHub репозиторий**: `kbrejes/fb_stats_bot`
- **Production ветка**: `production`

## 🚀 Пошаговая настройка

### Шаг 1: Подключение к серверу

```bash
# Подключение к серверу
ssh root@188.166.221.59

# Создание пользователя для бота
adduser botuser
usermod -aG sudo botuser

# Добавление SSH ключа для GitHub Actions
mkdir -p /home/botuser/.ssh
echo "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQDBLXEOUiLGpNjt9K4a8XHNm5B3Zav1o7Gx2q3jvK2hgomDMVgW3mZJKVX2OWj8qCWJORMOw8/HQG4PjQU4jZr0Aq3MBgLl9n0wM3rVrtfGxcZ1HmWLR5rPEJy5/A2chftYb4IZuCaiLfz5gjTTZefHL7mYqE0j6gE1UkxY2mr9H4tBie3kxWvQpm3BZiPl3CWzX2HOJB5hWao8HQWoDRJ//R4iqVrf+FmhxpswJMMX5htWRa9zvJJfSteEzM4LcY9gwlXaT9QjS4Zkclj4wzhJiJcpnpDnOCObThIxNMDkvikz+BdYQaGrWWnJdPdSnYWGk8evoFwPs7hXiMBY3jsdm7EMRDFJ4hKHXSJuxSgeSvIgHnjqposi+FuYZL1H2BX+sb8gSH4pF2vmf3kx+8oz0OfVLGEo58z2ZC7mHayuPeEzBPEnwqkK5/tpbcRYpH8J0gb6plXgO762SgbRdBiCnI9RAS5v0W+b70FlfYSHIsMDgXIhAMOhBJtYiQB6KlJrCpXl19wWLYzSL436bOyNUg7C4wqrs1yuRxXiGgaM1a+q195qcqmyqrv6Gqj8kpT/vUUq/b4f/sufc6L81xTX7j9y3Z0S0BDBZVb7BEdQb4j9guEAMCCHCUw2pYPzaoJ0r4VTZTg2kwMxloWjkL0lkxYwVUxyMsX+Z3JIZCIgrw== github-actions@fb-bot" >> /home/botuser/.ssh/authorized_keys

chown -R botuser:botuser /home/botuser/.ssh
chmod 700 /home/botuser/.ssh
chmod 600 /home/botuser/.ssh/authorized_keys

# Переключение на пользователя botuser
su - botuser
```

### Шаг 2: Настройка системы

```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl wget git ufw fail2ban htop

# Настройка файрвола
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443
sudo ufw allow from 1.46.148.179 to any port 9090  # Prometheus
sudo ufw allow from 1.46.148.179 to any port 3000  # Grafana
sudo ufw --force enable

# Установка Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker botuser

# Установка Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Перелогиниться для применения Docker группы
exit
ssh botuser@188.166.221.59
```

### Шаг 3: Клонирование проекта

```bash
# На сервере
cd ~
git clone https://github.com/kbrejes/fb_stats_bot.git
cd fb_stats_bot
git checkout production

# Создание необходимых директорий
mkdir -p logs data ssl
```

### Шаг 4: Создание SSL сертификатов

```bash
# На сервере
cd ~/fb_stats_bot
openssl req -x509 -newkey rsa:4096 -keyout ssl/bot.key -out ssl/bot.crt -days 365 -nodes \
    -subj "/C=US/ST=State/L=City/O=Organization/CN=188.166.221.59"
chmod 600 ssl/bot.key
chmod 644 ssl/bot.crt
```

### Шаг 5: Настройка переменных окружения

```bash
# На сервере
cp env-production.template .env.prod

# Отредактируйте .env.prod с вашими токенами:
nano .env.prod
```

Обновите следующие переменные:
```env
TELEGRAM_TOKEN=7595294156:AAFcKTYzTt0h0xEt-BiVs-otrmYB6dAL7LY
OPENAI_API_KEY=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
FB_APP_ID=639419165542707
FB_APP_SECRET=73af4e475afddfbd61fb74628481eb28
OWNER_ID=400133981
```

### Шаг 6: Настройка GitHub Secrets

Перейдите в GitHub: **Settings** → **Secrets and variables** → **Actions**

Добавьте следующие секреты:

```
# Сервер
PROD_HOST=188.166.221.59
PROD_USER=botuser
PROD_SSH_KEY=-----BEGIN OPENSSH PRIVATE KEY-----
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
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
```

### Шаг 7: Настройка GitHub Environments

**Settings** → **Environments** → **New environment**

Создайте environment **`production`**:
- ✅ **Required reviewers**: добавьте себя
- ✅ **Wait timer**: 5 minutes
- ✅ **Deployment branches**: Only protected branches → production

### Шаг 8: Первый запуск

```bash
# На сервере
cd ~/fb_stats_bot
docker-compose -f docker-compose.prod.yml up -d

# Проверка статуса
docker-compose -f docker-compose.prod.yml ps
docker-compose -f docker-compose.prod.yml logs bot
```

### Шаг 9: Проверка работы

1. **Бот**: Напишите боту в Telegram
2. **Мониторинг**: 
   - Prometheus: `http://188.166.221.59:9090` (доступ только с вашего IP)
   - Grafana: `http://188.166.221.59:3000` (admin/admin)
3. **Health Check**: `curl http://188.166.221.59:8080/health`

## 🔄 Автоматический деплой

После настройки GitHub Secrets и Environments:

1. Внесите изменения в код
2. Сделайте push в `production` ветку
3. GitHub Actions автоматически:
   - Запустит тесты
   - Проведет security scan
   - Соберет Docker образ
   - Развернет на сервере
   - Отправит уведомления

## 📊 Мониторинг

- **Логи**: `docker-compose -f docker-compose.prod.yml logs -f bot`
- **Метрики**: Prometheus + Grafana
- **Алерты**: Настроены в `monitoring/alert_rules.yml`
- **Backup**: Автоматический backup БД каждые 6 часов

## 🚨 Troubleshooting

### Проблемы с SSL
```bash
# Пересоздание сертификатов
cd ~/fb_stats_bot/ssl
rm bot.key bot.crt
openssl req -x509 -newkey rsa:4096 -keyout bot.key -out bot.crt -days 365 -nodes \
    -subj "/C=US/ST=State/L=City/O=Organization/CN=188.166.221.59"
```

### Проблемы с Docker
```bash
# Перезапуск всех сервисов
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d

# Очистка системы
docker system prune -f
```

### Проблемы с БД
```bash
# Backup БД
./scripts/backup.sh

# Восстановление из backup
docker-compose -f docker-compose.prod.yml exec postgres psql -U postgres -d fb_ads_bot < backup_file.sql
```

## ✅ Готово!

Ваш Facebook Ads Telegram Bot теперь работает в продакшн на DigitalOcean с полным CI/CD пайплайном, мониторингом и автоматическими backup'ами.

**Доступ к боту**: [@your_bot_name](https://t.me/your_bot_name)  
**Мониторинг**: http://188.166.221.59:3000  
**GitHub Actions**: https://github.com/kbrejes/fb_stats_bot/actions 