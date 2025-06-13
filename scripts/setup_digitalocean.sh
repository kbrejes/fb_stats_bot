#!/bin/bash

# DigitalOcean Setup Script for Facebook Ads Telegram Bot
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
}

# Get server information
get_server_info() {
    echo -e "${BLUE}"
    echo "=========================================="
    echo "DigitalOcean Server Setup"
    echo "=========================================="
    echo -e "${NC}"
    
    # Get server IP or domain
    read -p "Введите IP адрес вашего DigitalOcean сервера или домен: " SERVER_ADDRESS
    
    # Ask if user has a domain
    read -p "У вас есть домен? (y/n): " HAS_DOMAIN
    
    if [[ $HAS_DOMAIN == "y" || $HAS_DOMAIN == "Y" ]]; then
        USE_DOMAIN=true
        DOMAIN=$SERVER_ADDRESS
        log "Будем использовать домен: $DOMAIN"
    else
        USE_DOMAIN=false
        SERVER_IP=$SERVER_ADDRESS
        log "Будем использовать IP адрес: $SERVER_IP"
    fi
    
    # Get your local IP for firewall
    read -p "Введите ваш локальный IP для доступа к мониторингу (или нажмите Enter для автоопределения): " LOCAL_IP
    
    if [[ -z "$LOCAL_IP" ]]; then
        LOCAL_IP=$(curl -s https://api.ipify.org || curl -s https://ipinfo.io/ip || echo "YOUR_LOCAL_IP")
        log "Автоопределенный IP: $LOCAL_IP"
    fi
}

# Update environment configuration
update_env_config() {
    log "Обновление .env.prod конфигурации..."
    
    # Copy template if .env.prod doesn't exist
    if [[ ! -f ".env.prod" ]]; then
        cp env-production.template .env.prod
        log "Создан .env.prod из шаблона"
    fi
    
    # Update domain/IP settings
    if [[ $USE_DOMAIN == true ]]; then
        sed -i "s|FB_REDIRECT_URI=.*|FB_REDIRECT_URI=https://$DOMAIN/api/facebook/callback|" .env.prod
        sed -i "s|PRODUCTION_DOMAIN=.*|PRODUCTION_DOMAIN=$DOMAIN|" .env.prod
        sed -i "s|SSL_ENABLED=.*|SSL_ENABLED=true|" .env.prod
    else
        sed -i "s|FB_REDIRECT_URI=.*|FB_REDIRECT_URI=https://$SERVER_IP/api/facebook/callback|" .env.prod
        sed -i "s|PRODUCTION_DOMAIN=.*|PRODUCTION_DOMAIN=$SERVER_IP|" .env.prod
        sed -i "s|SSL_ENABLED=.*|SSL_ENABLED=true|" .env.prod
    fi
    
    # Generate secure database password
    DB_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
    sed -i "s|secure_password_123|$DB_PASSWORD|g" .env.prod
    
    success "Конфигурация .env.prod обновлена"
}

# Update nginx configuration
update_nginx_config() {
    log "Обновление nginx.conf конфигурации..."
    
    if [[ $USE_DOMAIN == true ]]; then
        sed -i "s|server_name localhost|server_name $DOMAIN|g" nginx.conf
        sed -i "s|# Замените на ваш домен||g" nginx.conf
    else
        sed -i "s|server_name localhost|server_name $SERVER_IP|g" nginx.conf
        sed -i "s|# Замените на ваш домен|# Using IP address|g" nginx.conf
    fi
    
    success "Конфигурация nginx.conf обновлена"
}

# Update docker-compose for production
update_docker_compose() {
    log "Обновление docker-compose.prod.yml..."
    
    # Update env file reference
    sed -i "s|env-production.template|.env.prod|" docker-compose.prod.yml
    
    # Update database password in docker-compose
    DB_PASSWORD=$(grep "secure_password_123" .env.prod | cut -d'=' -f2 | cut -d'@' -f1 | cut -d':' -f2)
    if [[ ! -z "$DB_PASSWORD" ]]; then
        sed -i "s|POSTGRES_PASSWORD=secure_password_123|POSTGRES_PASSWORD=$DB_PASSWORD|" docker-compose.prod.yml
        sed -i "s|PGPASSWORD=secure_password_123|PGPASSWORD=$DB_PASSWORD|" docker-compose.prod.yml
    fi
    
    success "Конфигурация docker-compose.prod.yml обновлена"
}

# Create deployment script for server
create_server_deployment_script() {
    log "Создание скрипта развертывания для сервера..."
    
    cat > setup_server.sh << EOF
#!/bin/bash
# Auto-generated setup script for DigitalOcean server

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "\${BLUE}[\$(date +'%Y-%m-%d %H:%M:%S')] \$1\${NC}"; }
success() { echo -e "\${GREEN}✅ \$1\${NC}"; }
warning() { echo -e "\${YELLOW}⚠️  \$1\${NC}"; }
error() { echo -e "\${RED}❌ \$1\${NC}"; }

log "Настройка сервера DigitalOcean..."

# System update
log "Обновление системы..."
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl wget git ufw fail2ban htop

# Firewall setup
log "Настройка файрвола..."
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443
sudo ufw allow from $LOCAL_IP to any port 9090
sudo ufw allow from $LOCAL_IP to any port 3000
sudo ufw --force enable

# Docker installation
log "Установка Docker..."
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker \$USER

# Docker Compose installation
log "Установка Docker Compose..."
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-\$(uname -s)-\$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

success "Базовая настройка сервера завершена!"
warning "Перелогиньтесь для применения Docker группы: exit && ssh user@server"

EOF

    chmod +x setup_server.sh
    success "Создан скрипт setup_server.sh для сервера"
}

# Create SSL setup instructions
create_ssl_instructions() {
    log "Создание инструкций по SSL..."
    
    cat > ssl_setup_instructions.txt << EOF
# SSL Certificate Setup Instructions

## Option 1: Let's Encrypt (для домена)
EOF
    
    if [[ $USE_DOMAIN == true ]]; then
        cat >> ssl_setup_instructions.txt << EOF

Ваш домен: $DOMAIN

1. Установите Certbot:
   sudo apt install -y certbot

2. Получите сертификат:
   sudo certbot certonly --standalone -d $DOMAIN

3. Скопируйте сертификаты:
   sudo mkdir -p ssl
   sudo cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem ssl/bot.crt
   sudo cp /etc/letsencrypt/live/$DOMAIN/privkey.pem ssl/bot.key
   sudo chown \$USER:\$USER ssl/bot.*
   sudo chmod 644 ssl/bot.crt
   sudo chmod 600 ssl/bot.key

4. Настройте автообновление:
   echo "0 12 * * * /usr/bin/certbot renew --quiet" | sudo crontab -

EOF
    else
        cat >> ssl_setup_instructions.txt << EOF

Ваш IP: $SERVER_IP

1. Создайте самоподписанный сертификат:
   mkdir -p ssl
   openssl req -x509 -newkey rsa:4096 -keyout ssl/bot.key -out ssl/bot.crt -days 365 -nodes \\
       -subj "/C=US/ST=State/L=City/O=Organization/CN=$SERVER_IP"
   
   chmod 600 ssl/bot.key
   chmod 644 ssl/bot.crt

EOF
    fi
    
    success "Создан файл ssl_setup_instructions.txt"
}

# Display summary
show_summary() {
    echo
    echo -e "${BLUE}=========================================="
    echo "Настройка завершена!"
    echo "==========================================${NC}"
    echo
    
    if [[ $USE_DOMAIN == true ]]; then
        echo "🌐 Домен: $DOMAIN"
        echo "🔗 Facebook Callback URL: https://$DOMAIN/api/facebook/callback"
        echo "🔍 Health Check: https://$DOMAIN/health"
    else
        echo "🌐 IP адрес: $SERVER_IP"
        echo "🔗 Facebook Callback URL: https://$SERVER_IP/api/facebook/callback"
        echo "🔍 Health Check: https://$SERVER_IP/health"
    fi
    
    echo "🎯 Мониторинг (только с $LOCAL_IP):"
    echo "   - Prometheus: http://$SERVER_ADDRESS:9090"
    echo "   - Grafana: http://$SERVER_ADDRESS:3000"
    echo
    
    echo -e "${YELLOW}Следующие шаги:${NC}"
    echo "1. Скопируйте setup_server.sh на ваш сервер"
    echo "2. Запустите: chmod +x setup_server.sh && ./setup_server.sh"
    echo "3. Следуйте инструкциям в ssl_setup_instructions.txt"
    echo "4. Скопируйте проект на сервер"
    echo "5. Запустите: ./scripts/deploy.sh"
    echo
    
    echo -e "${GREEN}Файлы готовы к развертыванию! 🚀${NC}"
}

# Main function
main() {
    get_server_info
    update_env_config
    update_nginx_config
    update_docker_compose
    create_server_deployment_script
    create_ssl_instructions
    show_summary
}

# Run main function
main 