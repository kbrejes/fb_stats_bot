# 🌊 DigitalOcean Production Deployment

Пошаговое руководство по развертыванию Facebook Ads Telegram Bot на сервере DigitalOcean.

## 📋 Подготовка

### 1. Создание Droplet на DigitalOcean

**Рекомендуемая конфигурация:**
- **OS**: Ubuntu 22.04 LTS
- **Plan**: Basic Droplet
- **CPU**: 2 vCPUs  
- **RAM**: 4GB
- **SSD**: 80GB
- **Datacenter**: Ближайший к вашим пользователям

### 2. Настройка домена (опционально)

Если у вас есть домен, настройте DNS записи:
```
A запись: your-domain.com → IP_ВАШЕГО_СЕРВЕРА
A запись: www.your-domain.com → IP_ВАШЕГО_СЕРВЕРА
```

## 🔐 Первоначальная настройка сервера

### 1. Подключение к серверу
```bash
# Подключитесь к серверу через SSH
ssh root@YOUR_SERVER_IP

# Или если у вас настроен SSH ключ
ssh -i ~/.ssh/your_key root@YOUR_SERVER_IP
```

### 2. Создание пользователя (рекомендуется)
```bash
# Создание нового пользователя
adduser botuser
usermod -aG sudo botuser

# Настройка SSH ключей для нового пользователя
mkdir -p /home/botuser/.ssh
cp ~/.ssh/authorized_keys /home/botuser/.ssh/
chown -R botuser:botuser /home/botuser/.ssh
chmod 700 /home/botuser/.ssh
chmod 600 /home/botuser/.ssh/authorized_keys

# Переключение на нового пользователя
su - botuser
```

### 3. Обновление системы
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl wget git ufw fail2ban
```

### 4. Настройка файрвола
```bash
# Разрешаем SSH
sudo ufw allow ssh

# Разрешаем HTTP и HTTPS
sudo ufw allow 80
sudo ufw allow 443

# Разрешаем порты для мониторинга (только с вашего IP)
sudo ufw allow from YOUR_LOCAL_IP to any port 9090  # Prometheus
sudo ufw allow from YOUR_LOCAL_IP to any port 3000  # Grafana

# Включаем файрвол
sudo ufw --force enable

# Проверяем статус
sudo ufw status
```

## 🐳 Установка Docker

```bash
# Установка Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Добавление пользователя в группу docker
sudo usermod -aG docker $USER

# Установка Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Проверка установки
docker --version
docker-compose --version

# Перелогиниться для применения группы docker
exit
# Подключиться снова
ssh botuser@YOUR_SERVER_IP
```

## 📁 Развертывание проекта

### 1. Клонирование проекта
```bash
# Клонирование в домашнюю директорию
cd ~
git clone https://github.com/yourusername/fb_ads_tg_bot_clean.git
cd fb_ads_tg_bot_clean
```

### 2. Настройка .env.prod для DigitalOcean
```bash
# Копирование шаблона
cp env-production.template .env.prod

# Редактирование конфигурации
nano .env.prod
```

**Обновите следующие параметры в .env.prod:**
```env
# ===== TELEGRAM BOT SETTINGS =====
TELEGRAM_TOKEN=7595294156:AAFcKTYzTt0h0xEt-BiVs-otrmYB6dAL7LY
OWNER_ID=400133981
ADMIN_USERS=400133981

# ===== FACEBOOK API SETTINGS =====
FB_APP_ID=639419165542707
FB_APP_SECRET=73af4e475afddfbd61fb74628481eb28

# ВАЖНО: Замените на ваш реальный домен или IP
FB_REDIRECT_URI=https://YOUR_DOMAIN_OR_IP/api/facebook/callback

# ===== DEPLOYMENT SETTINGS =====
# Ваш домен или IP адрес сервера
PRODUCTION_DOMAIN=YOUR_DOMAIN_OR_IP
PRODUCTION_PORT=443

# SSL settings
SSL_ENABLED=true
SSL_CERT_PATH=/etc/ssl/certs/bot.crt
SSL_KEY_PATH=/etc/ssl/private/bot.key

# ===== DATABASE SETTINGS =====
# Используем более безопасный пароль для продакшна
DB_CONNECTION_STRING=postgresql://fb_ads_user:$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)@localhost:5432/fb_ads_bot_prod
```

### 3. Обновление nginx.conf для вашего домена
```bash
# Замена localhost на ваш домен
sed -i 's/localhost/YOUR_DOMAIN_OR_IP/g' nginx.conf

# Или редактирование вручную
nano nginx.conf
```

## 🔒 Настройка SSL сертификатов

### Опция 1: Let's Encrypt (для домена)
```bash
# Установка Certbot
sudo apt install -y certbot

# Временная остановка nginx если он запущен
sudo systemctl stop nginx 2>/dev/null || true

# Получение сертификата
sudo certbot certonly --standalone -d YOUR_DOMAIN.com -d www.YOUR_DOMAIN.com

# Копирование сертификатов
sudo mkdir -p ssl
sudo cp /etc/letsencrypt/live/YOUR_DOMAIN.com/fullchain.pem ssl/bot.crt
sudo cp /etc/letsencrypt/live/YOUR_DOMAIN.com/privkey.pem ssl/bot.key
sudo chown $USER:$USER ssl/bot.*
sudo chmod 644 ssl/bot.crt
sudo chmod 600 ssl/bot.key

# Настройка автообновления сертификатов
echo "0 12 * * * /usr/bin/certbot renew --quiet" | sudo crontab -
```

### Опция 2: Самоподписанный сертификат (для IP адреса)
```bash
# Создание директории
mkdir -p ssl

# Генерация самоподписанного сертификата
openssl req -x509 -newkey rsa:4096 -keyout ssl/bot.key -out ssl/bot.crt -days 365 -nodes \
    -subj "/C=US/ST=State/L=City/O=Organization/CN=YOUR_SERVER_IP"

chmod 600 ssl/bot.key
chmod 644 ssl/bot.crt
```

## 🚀 Развертывание

### 1. Запуск развертывания
```bash
# Сделать скрипты исполняемыми
chmod +x scripts/*.sh

# Запуск полного развертывания
./scripts/deploy.sh
```

### 2. Проверка развертывания
```bash
# Проверка запущенных контейнеров
docker-compose -f docker-compose.prod.yml ps

# Проверка health check
curl http://localhost:8080/health

# Проверка веб-интерфейса
curl -k https://YOUR_DOMAIN_OR_IP/health
```

## 🔧 Настройка Facebook App

### Обновление Webhook URL в Facebook App
1. Перейдите в [Facebook Developers Console](https://developers.facebook.com/)
2. Выберите ваше приложение
3. В разделе "Webhooks" обновите URL:
   ```
   https://YOUR_DOMAIN_OR_IP/api/facebook/callback
   ```

## 📊 Мониторинг

### Доступные endpoints:
- **Health Check**: `https://YOUR_DOMAIN_OR_IP/health`
- **Detailed Health**: `https://YOUR_DOMAIN_OR_IP/health/detailed`  
- **Prometheus**: `http://YOUR_SERVER_IP:9090`
- **Grafana**: `http://YOUR_SERVER_IP:3000` (admin/admin123)

## 🛡️ Дополнительная безопасность

### 1. Настройка Fail2Ban
```bash
# Создание конфигурации для Docker
sudo tee /etc/fail2ban/jail.local << EOF
[DEFAULT]
bantime = 10m
findtime = 10m
maxretry = 5

[sshd]
enabled = true
port = ssh
logpath = %(sshd_log)s
backend = %(sshd_backend)s

[nginx-http-auth]
enabled = true
port = http,https
logpath = /home/botuser/fb_ads_tg_bot_clean/logs/nginx/error.log
EOF

# Перезапуск Fail2Ban
sudo systemctl restart fail2ban
```

### 2. Настройка автоматических обновлений
```bash
# Установка unattended-upgrades
sudo apt install -y unattended-upgrades

# Настройка автообновлений безопасности
echo 'Unattended-Upgrade::Automatic-Reboot "false";' | sudo tee -a /etc/apt/apt.conf.d/50unattended-upgrades
```

### 3. Настройка бекапов
```bash
# Создание cron задачи для бекапов
crontab -e

# Добавьте строку:
0 2 * * * cd /home/botuser/fb_ads_tg_bot_clean && ./scripts/backup.sh
```

## 🔄 Обслуживание

### Полезные команды для управления:
```bash
# Просмотр логов
cd ~/fb_ads_tg_bot_clean
./scripts/deploy.sh logs

# Перезапуск бота
./scripts/deploy.sh restart bot

# Обновление бота
git pull origin main
./scripts/deploy.sh update

# Создание бекапа
./scripts/backup.sh

# Мониторинг ресурсов
htop
docker stats
```

### Мониторинг дискового пространства:
```bash
# Проверка места на диске
df -h

# Очистка старых Docker образов
docker system prune -f

# Очистка логов
sudo journalctl --vacuum-time=7d
```

## 🚨 Troubleshooting

### Проблемы с подключением:
```bash
# Проверка портов
sudo netstat -tlnp | grep -E ':80|:443|:8080'

# Проверка файрвола
sudo ufw status

# Проверка DNS (если используете домен)
nslookup YOUR_DOMAIN.com

# Проверка SSL сертификатов
openssl x509 -in ssl/bot.crt -text -noout
```

### Проблемы с Docker:
```bash
# Проверка Docker сервиса
sudo systemctl status docker

# Перезапуск Docker
sudo systemctl restart docker

# Проверка логов Docker
sudo journalctl -u docker.service
```

## 📞 Поддержка

### Контакты:
- **Telegram**: @kbrejes
- **Server IP**: `YOUR_SERVER_IP`
- **SSH**: `ssh botuser@YOUR_SERVER_IP`

---

## ✅ Checklist DigitalOcean развертывания

- [ ] Droplet создан и настроен
- [ ] Пользователь и SSH настроены  
- [ ] Файрвол настроен
- [ ] Docker установлен
- [ ] Проект склонирован
- [ ] .env.prod настроен с правильным доменом/IP
- [ ] SSL сертификаты получены
- [ ] nginx.conf обновлен
- [ ] Facebook webhook URL обновлен
- [ ] Бот развернут и запущен
- [ ] Health checks проходят
- [ ] Мониторинг работает
- [ ] Бекапы настроены
- [ ] Безопасность настроена

**🎉 Ваш бот успешно развернут на DigitalOcean! 🎉** 