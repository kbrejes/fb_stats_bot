# 🚀 Production Deployment Guide

Полное руководство по развертыванию Facebook Ads Telegram Bot в продакшн-среде.

## 📋 Содержание

1. [Предварительные требования](#предварительные-требования)
2. [Подготовка сервера](#подготовка-сервера)
3. [Настройка окружения](#настройка-окружения)
4. [Развертывание](#развертывание)
5. [Мониторинг и обслуживание](#мониторинг-и-обслуживание)
6. [Troubleshooting](#troubleshooting)

---

## 📦 Предварительные требования

### Системные требования
- **OS**: Ubuntu 20.04+ / CentOS 8+ / Debian 11+
- **RAM**: Минимум 2GB, рекомендуется 4GB+
- **Disk**: Минимум 20GB свободного места
- **CPU**: 2+ ядра рекомендуется

### Необходимое ПО
- Docker 20.10+
- Docker Compose 2.0+
- Git
- OpenSSL (для SSL сертификатов)

### Внешние сервисы
- **Telegram Bot Token** от @BotFather
- **Facebook App** (App ID, App Secret)
- **OpenAI API Key** (для AI-анализа)
- **Домен** с SSL сертификатом (опционально)

---

## 🔧 Подготовка сервера

### 1. Обновление системы
```bash
# Ubuntu/Debian
sudo apt update && sudo apt upgrade -y

# CentOS/RHEL
sudo yum update -y
```

### 2. Установка Docker
```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# CentOS/RHEL
sudo yum install -y docker
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER
```

### 3. Установка Docker Compose
```bash
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### 4. Клонирование проекта
```bash
git clone https://github.com/yourusername/fb_ads_tg_bot_clean.git
cd fb_ads_tg_bot_clean
```

---

## ⚙️ Настройка окружения

### 1. Создание .env.prod файла
```bash
# Скопируйте шаблон
cp env-production.template .env.prod

# Отредактируйте файл
nano .env.prod
```

### 2. Обязательные настройки в .env.prod

```env
# === TELEGRAM BOT ===
TELEGRAM_TOKEN=your_real_bot_token_from_botfather
OWNER_ID=your_telegram_user_id
ADMIN_USERS=your_telegram_user_id

# === FACEBOOK API ===
FB_APP_ID=your_facebook_app_id
FB_APP_SECRET=your_facebook_app_secret
FB_REDIRECT_URI=https://yourdomain.com/api/facebook/callback

# === OPENAI ===
OPENAI_API_KEY=your_openai_api_key

# === DOMAIN ===
PRODUCTION_DOMAIN=yourdomain.com
PRODUCTION_PORT=443

# === DATABASE ===
DB_CONNECTION_STRING=postgresql://fb_ads_user:secure_password_123@localhost:5432/fb_ads_bot_prod
```

### 3. Настройка SSL сертификатов

#### Опция A: Let's Encrypt (рекомендуется)
```bash
# Установка Certbot
sudo apt install certbot

# Получение сертификата
sudo certbot certonly --standalone -d yourdomain.com

# Копирование сертификатов
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem ssl/bot.crt
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem ssl/bot.key
sudo chown $USER:$USER ssl/bot.*
```

#### Опция B: Самоподписанные (только для тестирования)
```bash
# Создание самоподписанного сертификата
openssl req -x509 -newkey rsa:4096 -keyout ssl/bot.key -out ssl/bot.crt -days 365 -nodes \
    -subj "/C=US/ST=State/L=City/O=Organization/CN=yourdomain.com"
```

### 4. Настройка Nginx (опционально)
```bash
# Обновите server_name в nginx.conf
sed -i 's/localhost/yourdomain.com/g' nginx.conf
```

---

## 🚀 Развертывание

### 1. Автоматическое развертывание
```bash
# Запуск полного развертывания
./scripts/deploy.sh

# Скрипт автоматически:
# - Проверит зависимости
# - Создаст SSL сертификаты (если отсутствуют)
# - Настроит директории
# - Проверит конфигурацию
# - Запустит все сервисы
```

### 2. Ручное развертывание (пошагово)

#### Шаг 1: Создание директорий
```bash
mkdir -p logs data backups ssl monitoring/grafana
chmod 755 logs data backups
chmod 777 monitoring/grafana
```

#### Шаг 2: Запуск PostgreSQL
```bash
docker-compose -f docker-compose.prod.yml up -d postgres
```

#### Шаг 3: Инициализация БД
```bash
# Дождитесь готовности PostgreSQL (30-60 секунд)
docker-compose -f docker-compose.prod.yml run --rm bot python initialize_db.py
```

#### Шаг 4: Запуск всех сервисов
```bash
docker-compose -f docker-compose.prod.yml up -d
```

### 3. Проверка развертывания
```bash
# Проверка статуса контейнеров
docker-compose -f docker-compose.prod.yml ps

# Проверка логов
docker-compose -f docker-compose.prod.yml logs -f bot

# Проверка health check
curl http://localhost:8080/health
```

---

## 📊 Мониторинг и обслуживание

### Доступные endpoints
- **Bot Health**: http://localhost:8080/health
- **Detailed Health**: http://localhost:8080/health/detailed
- **Metrics**: http://localhost:8080/metrics
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin123)

### Полезные команды
```bash
# Просмотр логов
./scripts/deploy.sh logs
./scripts/deploy.sh logs bot

# Перезапуск сервиса
./scripts/deploy.sh restart bot

# Остановка всех сервисов
./scripts/deploy.sh stop

# Обновление приложения
./scripts/deploy.sh update

# Создание бекапа БД
./scripts/backup.sh

# Просмотр доступных бекапов
./scripts/backup.sh list

# Восстановление из бекапа
./scripts/backup.sh restore /backups/backup_file.sql.gz
```

### Мониторинг в Grafana
1. Откройте http://localhost:3000
2. Войдите: admin/admin123
3. Импортируйте dashboard для мониторинга бота
4. Настройте алерты для критических метрик

### Логи и диагностика
```bash
# Основные логи бота
tail -f logs/bot_production.log

# Логи ошибок
tail -f logs/error_production.log

# Логи Nginx
tail -f logs/nginx/access.log
tail -f logs/nginx/error.log

# Системные ресурсы
docker stats
```

---

## 🛠️ Troubleshooting

### Часто встречающиеся проблемы

#### 1. Бот не запускается
```bash
# Проверьте логи
docker-compose -f docker-compose.prod.yml logs bot

# Часто бывает:
# - Неверный TELEGRAM_TOKEN
# - Проблемы с БД
# - Неправильные права доступа
```

#### 2. База данных недоступна
```bash
# Проверьте статус PostgreSQL
docker-compose -f docker-compose.prod.yml ps postgres

# Переподключитесь к БД
docker-compose -f docker-compose.prod.yml restart postgres

# Проверьте подключение
docker-compose -f docker-compose.prod.yml exec postgres psql -U fb_ads_user -d fb_ads_bot_prod -c "\dt"
```

#### 3. SSL проблемы
```bash
# Проверьте сертификаты
openssl x509 -in ssl/bot.crt -text -noout

# Обновите сертификаты Let's Encrypt
sudo certbot renew
```

#### 4. Высокое использование ресурсов
```bash
# Мониторинг ресурсов
docker stats

# Проверьте метрики
curl http://localhost:8080/metrics

# Оптимизируйте настройки в .env.prod:
# - Уменьшите CACHE_TTL
# - Снизите MAX_CONCURRENT_REQUESTS
```

### Сбор диагностической информации
```bash
# Создание диагностического отчета
cat > diagnostic_report.txt << EOF
=== System Information ===
$(uname -a)
$(df -h)
$(free -h)

=== Docker Information ===
$(docker --version)
$(docker-compose --version)

=== Container Status ===
$(docker-compose -f docker-compose.prod.yml ps)

=== Recent Logs ===
$(docker-compose -f docker-compose.prod.yml logs --tail=50 bot)
EOF
```

---

## 🔄 Обновление и обслуживание

### Регулярные задачи

#### Ежедневно
- Проверка health check: `curl http://localhost:8080/health`
- Мониторинг логов: `tail -f logs/bot_production.log`

#### Еженедельно
- Проверка дискового пространства: `df -h`
- Просмотр метрик в Grafana
- Создание бекапа: `./scripts/backup.sh`

#### Ежемесячно
- Обновление зависимостей
- Проверка SSL сертификатов
- Очистка старых логов и бекапов

### Процедура обновления
```bash
# 1. Создайте бекап
./scripts/backup.sh

# 2. Получите последние изменения
git pull origin main

# 3. Обновите приложение
./scripts/deploy.sh update

# 4. Проверьте работоспособность
curl http://localhost:8080/health/detailed
```

---

## 📞 Поддержка

При возникновении проблем:

1. Проверьте [Troubleshooting](#troubleshooting)
2. Соберите диагностическую информацию
3. Проверьте логи всех сервисов
4. Обратитесь к документации API (Telegram, Facebook, OpenAI)

### Контакты
- **Telegram**: @kbrejes
- **GitHub Issues**: [Создать issue](https://github.com/yourusername/fb_ads_tg_bot_clean/issues)

---

## ✅ Checklist развертывания

- [ ] Сервер настроен и обновлен
- [ ] Docker и Docker Compose установлены
- [ ] Проект склонирован
- [ ] .env.prod файл создан и настроен
- [ ] SSL сертификаты получены
- [ ] Развертывание выполнено успешно
- [ ] Все сервисы запущены
- [ ] Health check проходит успешно
- [ ] Мониторинг настроен
- [ ] Бекапы настроены
- [ ] Документация прочитана
- [ ] Тестирование проведено

**Поздравляем! Ваш Facebook Ads Telegram Bot успешно развернут в продакшне! 🎉** 