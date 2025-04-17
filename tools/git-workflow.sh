#!/bin/bash

# Скрипт для безопасной работы с Git
# Добавьте это в файл tools/git-workflow.sh

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Основные функции работы с Git
create_feature_branch() {
    local branch_name=$1
    git checkout main
    git checkout -b "feature/$branch_name"
    echo -e "${GREEN}✅ Ветка feature/$branch_name создана${NC}"
}

commit_changes() {
    # Создаем бэкап перед коммитом
    mkdir -p backups
    timestamp=$(date +%Y%m%d_%H%M%S)
    tar -czf "backups/backup_$timestamp.tar.gz" --exclude=".git" --exclude="backups" .
    echo -e "${GREEN}✅ Бэкап создан в backups/backup_$timestamp.tar.gz${NC}"
    
    # Спрашиваем сообщение коммита
    echo -e "${YELLOW}Введите сообщение коммита:${NC}"
    read -p "> " commit_message
    
    # Коммитим изменения
    git add .
    git commit -m "$commit_message"
    git tag "save_$timestamp"
    echo -e "${GREEN}✅ Изменения сохранены${NC}"
}

finish_feature() {
    current_branch=$(git rev-parse --abbrev-ref HEAD)
    
    # Создаем бэкап перед слиянием
    mkdir -p backups
    timestamp=$(date +%Y%m%d_%H%M%S)
    tar -czf "backups/pre_merge_$timestamp.tar.gz" --exclude=".git" --exclude="backups" .
    echo -e "${GREEN}✅ Бэкап создан перед слиянием${NC}"
    
    # Проверяем конфликты
    git checkout main
    can_merge=true
    git merge --no-commit --no-ff "$current_branch" > /dev/null 2>&1 || can_merge=false
    git merge --abort > /dev/null 2>&1
    git checkout "$current_branch"
    
    if [ "$can_merge" = false ]; then
        echo -e "${RED}⚠️ Обнаружены конфликты!${NC}"
        echo -e "1) Создать новую ветку из main"
        echo -e "2) Продолжить слияние вручную"
        echo -e "3) Отменить операцию"
        read -p "> " option
        
        case "$option" in
            1)
                git checkout main
                git checkout -b "${current_branch}_new"
                echo -e "${GREEN}✅ Создана новая ветка ${current_branch}_new${NC}"
                return
                ;;
            2)
                echo -e "${YELLOW}Продолжаем со слиянием...${NC}"
                ;;
            *)
                echo -e "${YELLOW}Операция отменена${NC}"
                return
                ;;
        esac
    fi
    
    # Сливаем изменения
    git checkout main
    echo -e "${YELLOW}Сливаем изменения...${NC}"
    if git merge "$current_branch"; then
        git tag -f working-version
        echo -e "${GREEN}✅ Слияние успешно выполнено${NC}"
    else
        echo -e "${RED}❌ Ошибка при слиянии${NC}"
        git merge --abort
        return
    fi
}

restore_backup() {
    echo -e "${YELLOW}Доступные бэкапы:${NC}"
    ls -1 backups/*.tar.gz
    echo -e "${YELLOW}Введите имя бэкапа для восстановления:${NC}"
    read -p "backups/" backup_name
    
    if [ ! -f "backups/$backup_name" ]; then
        echo -e "${RED}❌ Бэкап не найден${NC}"
        return
    fi
    
    echo -e "${YELLOW}Восстанавливаем из бэкапа...${NC}"
    mkdir -p temp_restore
    tar -xzf "backups/$backup_name" -C temp_restore
    cp -r temp_restore/* ./
    rm -rf temp_restore
    echo -e "${GREEN}✅ Восстановление завершено${NC}"
}

show_help() {
    echo -e "${GREEN}Система защиты от потери кода${NC}"
    echo -e "Использование:"
    echo -e "./tools/git-workflow.sh <команда> [параметры]"
    echo -e ""
    echo -e "Команды:"
    echo -e "feature <имя> - Создать новую ветку"
    echo -e "commit - Сохранить изменения"
    echo -e "finish - Завершить и слить изменения"
    echo -e "restore - Восстановить из бэкапа"
    echo -e "help - Показать справку"
}

# Обработка команд
case "$1" in
    feature)
        create_feature_branch "$2"
        ;;
    commit)
        commit_changes
        ;;
    finish)
        finish_feature
        ;;
    restore)
        restore_backup
        ;;
    help)
        show_help
        ;;
    *)
        show_help
        ;;
esac 