#!/bin/bash

# Facebook Ads Telegram Bot - Production Deployment Script
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="docker-compose.prod.yml"
ENV_FILE="env-production.template"
PROJECT_NAME="fb_ads_bot"

# Helper functions
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

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check if Docker Compose is installed
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    # Check if required files exist
    if [[ ! -f "$COMPOSE_FILE" ]]; then
        error "Docker compose file $COMPOSE_FILE not found!"
        exit 1
    fi
    
    if [[ ! -f "$ENV_FILE" ]]; then
        error "Environment file $ENV_FILE not found!"
        exit 1
    fi
    
    success "Prerequisites check passed"
}

# Setup SSL certificates
setup_ssl() {
    log "Setting up SSL certificates..."
    
    if [[ ! -d "ssl" ]]; then
        mkdir -p ssl
    fi
    
    # Check if SSL certificates exist
    if [[ ! -f "ssl/bot.crt" ]] || [[ ! -f "ssl/bot.key" ]]; then
        warning "SSL certificates not found. Generating self-signed certificates..."
        warning "For production, please replace with real SSL certificates!"
        
        # Generate self-signed certificates
        openssl req -x509 -newkey rsa:4096 -keyout ssl/bot.key -out ssl/bot.crt -days 365 -nodes \
            -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
        
        chmod 600 ssl/bot.key
        chmod 644 ssl/bot.crt
        
        warning "Self-signed SSL certificates generated"
        warning "Remember to replace with real certificates for production!"
    else
        success "SSL certificates found"
    fi
}

# Create necessary directories
create_directories() {
    log "Creating necessary directories..."
    
    directories=("logs" "data" "backups" "monitoring/grafana")
    
    for dir in "${directories[@]}"; do
        if [[ ! -d "$dir" ]]; then
            mkdir -p "$dir"
            log "Created directory: $dir"
        fi
    done
    
    # Set proper permissions
    chmod 755 logs data backups
    chmod 777 monitoring/grafana  # Grafana needs write access
    
    success "Directories created and permissions set"
}

# Validate environment configuration
validate_environment() {
    log "Validating environment configuration..."
    
    # Check if .env.prod exists, if not, copy from template
    if [[ ! -f ".env.prod" ]]; then
        warning ".env.prod not found, copying from template..."
        cp "$ENV_FILE" .env.prod
        
        warning "⚠️  IMPORTANT: Please edit .env.prod with your production values!"
        warning "Required changes:"
        warning "  - TELEGRAM_TOKEN: Your real bot token"
        warning "  - FB_REDIRECT_URI: Your production domain"
        warning "  - PRODUCTION_DOMAIN: Your real domain"
        warning "  - Database credentials"
        warning "  - SSL settings"
        
        read -p "Press Enter after you've updated .env.prod..." -n1 -s
        echo
    fi
    
    # Basic validation of key variables
    source .env.prod 2>/dev/null || {
        error "Failed to source .env.prod. Please check file format."
        exit 1
    }
    
    # Check critical variables
    if [[ -z "$TELEGRAM_TOKEN" ]] || [[ "$TELEGRAM_TOKEN" == "YOUR_REAL_TOKEN_FROM_BOTFATHER" ]]; then
        error "TELEGRAM_TOKEN is not set in .env.prod"
        exit 1
    fi
    
    if [[ -z "$FB_APP_ID" ]] || [[ -z "$FB_APP_SECRET" ]]; then
        error "Facebook app credentials are not set in .env.prod"
        exit 1
    fi
    
    success "Environment configuration validated"
}

# Initialize database
init_database() {
    log "Initializing database..."
    
    # Start only PostgreSQL first
    docker-compose -f "$COMPOSE_FILE" up -d postgres
    
    # Wait for PostgreSQL to be ready
    log "Waiting for PostgreSQL to be ready..."
    sleep 10
    
    # Check if database is ready
    for i in {1..30}; do
        if docker-compose -f "$COMPOSE_FILE" exec -T postgres pg_isready -U fb_ads_user -d fb_ads_bot_prod >/dev/null 2>&1; then
            success "PostgreSQL is ready"
            break
        fi
        if [[ $i -eq 30 ]]; then
            error "PostgreSQL failed to start within 5 minutes"
            exit 1
        fi
        sleep 10
    done
    
    # Run database initialization
    log "Running database initialization..."
    docker-compose -f "$COMPOSE_FILE" run --rm bot python initialize_db.py
    
    success "Database initialized"
}

# Deploy application
deploy() {
    log "Deploying Facebook Ads Telegram Bot..."
    
    # Build and start all services
    docker-compose -f "$COMPOSE_FILE" up -d --build
    
    # Wait for services to be ready
    log "Waiting for all services to be ready..."
    sleep 30
    
    # Check health of critical services
    services=("postgres" "redis" "bot" "nginx")
    
    for service in "${services[@]}"; do
        if docker-compose -f "$COMPOSE_FILE" ps "$service" | grep -q "Up"; then
            success "Service $service is running"
        else
            error "Service $service failed to start"
            docker-compose -f "$COMPOSE_FILE" logs "$service"
            exit 1
        fi
    done
    
    success "All services are running"
}

# Show deployment status
show_status() {
    log "Deployment Status:"
    echo
    
    # Show running containers
    docker-compose -f "$COMPOSE_FILE" ps
    echo
    
    # Show endpoints
    echo -e "${BLUE}Available endpoints:${NC}"
    echo "🤖 Bot: Running in background (Telegram)"
    echo "🔍 Health Check: http://localhost:8080/health"
    echo "📊 Detailed Health: http://localhost:8080/health/detailed"
    echo "📈 Metrics: http://localhost:8080/metrics"
    echo "🌐 Nginx: http://localhost (redirects to HTTPS)"
    echo "🔒 HTTPS: https://localhost"
    echo "📊 Prometheus: http://localhost:9090"
    echo "📈 Grafana: http://localhost:3000 (admin/admin123)"
    echo
    
    # Show logs command
    echo -e "${BLUE}Useful commands:${NC}"
    echo "📋 View logs: docker-compose -f $COMPOSE_FILE logs -f"
    echo "📋 View bot logs: docker-compose -f $COMPOSE_FILE logs -f bot"
    echo "🔄 Restart bot: docker-compose -f $COMPOSE_FILE restart bot"
    echo "🛑 Stop all: docker-compose -f $COMPOSE_FILE down"
    echo "🗂️  Update: ./scripts/deploy.sh"
    echo
}

# Main deployment function
main() {
    echo -e "${BLUE}"
    echo "========================================"
    echo "Facebook Ads Telegram Bot - Production"
    echo "========================================"
    echo -e "${NC}"
    
    check_prerequisites
    setup_ssl
    create_directories
    validate_environment
    init_database
    deploy
    show_status
    
    success "🎉 Deployment completed successfully!"
    warning "Don't forget to:"
    warning "  1. Replace self-signed SSL certificates with real ones"
    warning "  2. Update your domain in .env.prod and nginx.conf"
    warning "  3. Configure Facebook webhook URL"
    warning "  4. Set up monitoring alerts"
}

# Handle script arguments
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "status")
        docker-compose -f "$COMPOSE_FILE" ps
        ;;
    "logs")
        docker-compose -f "$COMPOSE_FILE" logs -f "${2:-}"
        ;;
    "stop")
        docker-compose -f "$COMPOSE_FILE" down
        ;;
    "restart")
        docker-compose -f "$COMPOSE_FILE" restart "${2:-}"
        ;;
    "update")
        log "Updating application..."
        docker-compose -f "$COMPOSE_FILE" down
        docker-compose -f "$COMPOSE_FILE" up -d --build
        success "Application updated"
        ;;
    *)
        echo "Usage: $0 {deploy|status|logs|stop|restart|update}"
        echo "  deploy  - Full deployment (default)"
        echo "  status  - Show container status"
        echo "  logs    - Show logs (optionally specify service name)"
        echo "  stop    - Stop all services"
        echo "  restart - Restart services (optionally specify service name)"
        echo "  update  - Update and restart application"
        exit 1
        ;;
esac 