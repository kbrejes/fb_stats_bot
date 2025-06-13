#!/bin/bash

# Database backup script for Facebook Ads Telegram Bot
set -e

# Configuration
DB_NAME="fb_ads_bot_prod"
DB_USER="fb_ads_user"
DB_HOST="postgres"
BACKUP_DIR="/backups"
RETENTION_DAYS=30

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Generate backup filename with timestamp
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/fb_ads_bot_backup_$TIMESTAMP.sql"

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

# Create database backup
create_backup() {
    log "Starting database backup..."
    
    # Create SQL dump
    if pg_dump -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" > "$BACKUP_FILE"; then
        success "Database backup created: $BACKUP_FILE"
        
        # Compress backup
        gzip "$BACKUP_FILE"
        BACKUP_FILE="${BACKUP_FILE}.gz"
        success "Backup compressed: $BACKUP_FILE"
        
        # Show backup size
        BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
        log "Backup size: $BACKUP_SIZE"
        
    else
        error "Failed to create database backup"
        exit 1
    fi
}

# Clean old backups
cleanup_old_backups() {
    log "Cleaning up old backups (keeping last $RETENTION_DAYS days)..."
    
    # Find and delete old backups
    DELETED_COUNT=$(find "$BACKUP_DIR" -name "fb_ads_bot_backup_*.sql.gz" -mtime +$RETENTION_DAYS -delete -print | wc -l)
    
    if [[ $DELETED_COUNT -gt 0 ]]; then
        success "Deleted $DELETED_COUNT old backup(s)"
    else
        log "No old backups to delete"
    fi
}

# List available backups
list_backups() {
    log "Available backups:"
    find "$BACKUP_DIR" -name "fb_ads_bot_backup_*.sql.gz" -printf "%T@ %Tc %p\n" | sort -n | cut -d' ' -f2- | while read -r line; do
        echo "  $line"
    done
}

# Verify backup integrity
verify_backup() {
    log "Verifying backup integrity..."
    
    if gzip -t "$BACKUP_FILE"; then
        success "Backup file integrity verified"
    else
        error "Backup file is corrupted!"
        exit 1
    fi
}

# Main backup function
main() {
    log "Starting database backup process..."
    
    create_backup
    verify_backup
    cleanup_old_backups
    list_backups
    
    success "Backup process completed successfully!"
}

# Handle script arguments
case "${1:-backup}" in
    "backup")
        main
        ;;
    "list")
        list_backups
        ;;
    "cleanup")
        cleanup_old_backups
        ;;
    "restore")
        if [[ -z "$2" ]]; then
            error "Please specify backup file to restore"
            echo "Usage: $0 restore <backup_file>"
            exit 1
        fi
        
        RESTORE_FILE="$2"
        
        if [[ ! -f "$RESTORE_FILE" ]]; then
            error "Backup file not found: $RESTORE_FILE"
            exit 1
        fi
        
        log "Restoring database from: $RESTORE_FILE"
        warning "This will overwrite the current database!"
        
        read -p "Are you sure? (yes/no): " -r
        if [[ $REPLY == "yes" ]]; then
            # Decompress and restore
            if [[ "$RESTORE_FILE" == *.gz ]]; then
                gunzip -c "$RESTORE_FILE" | psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME"
            else
                psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" < "$RESTORE_FILE"
            fi
            
            success "Database restored successfully"
        else
            log "Restore cancelled"
        fi
        ;;
    *)
        echo "Usage: $0 {backup|list|cleanup|restore}"
        echo "  backup          - Create database backup (default)"
        echo "  list            - List available backups"
        echo "  cleanup         - Clean old backups"
        echo "  restore <file>  - Restore from backup file"
        exit 1
        ;;
esac 