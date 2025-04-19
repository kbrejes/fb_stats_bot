-- Скрипт отката изменений в случае ошибок

-- Удаление триггеров
DROP TRIGGER IF EXISTS trg_user_role_changed;
DROP TRIGGER IF EXISTS trg_user_role_changed_requests;
DROP TRIGGER IF EXISTS trg_access_request_approved;

-- Удаление индексов
DROP INDEX IF EXISTS idx_users_role;
DROP INDEX IF EXISTS idx_users_search;

DROP INDEX IF EXISTS idx_access_control_user_id;
DROP INDEX IF EXISTS idx_access_control_target;
DROP INDEX IF EXISTS idx_access_control_status;
DROP INDEX IF EXISTS idx_access_control_active;
DROP INDEX IF EXISTS idx_access_control_target_active;
DROP INDEX IF EXISTS idx_access_control_expiring;

DROP INDEX IF EXISTS idx_access_request_user_id;
DROP INDEX IF EXISTS idx_access_request_target;
DROP INDEX IF EXISTS idx_access_request_status;
DROP INDEX IF EXISTS idx_access_request_assigned;
DROP INDEX IF EXISTS idx_access_request_by_status;

-- Удаление таблиц
DROP TABLE IF EXISTS access_request;
DROP TABLE IF EXISTS access_control;

-- Удаление поля role из таблицы users (требует пересоздания таблицы в SQLite)
PRAGMA foreign_keys=off;
BEGIN TRANSACTION;

-- Сохраняем текущие данные без поля role
CREATE TABLE users_temp AS
SELECT 
    telegram_id, username, first_name, last_name, 
    fb_access_token, fb_refresh_token, token_expires_at, 
    language, last_command, last_context, 
    created_at, updated_at
FROM users;

-- Удаляем старую таблицу
DROP TABLE users;

-- Создаем новую таблицу без поля role
CREATE TABLE users (
    telegram_id INTEGER PRIMARY KEY,
    username VARCHAR(255),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    fb_access_token TEXT,
    fb_refresh_token TEXT,
    token_expires_at DATETIME,
    language VARCHAR(10) NOT NULL DEFAULT 'ru',
    last_command VARCHAR(255),
    last_context TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Копируем данные в новую таблицу
INSERT INTO users (
    telegram_id, username, first_name, last_name, 
    fb_access_token, fb_refresh_token, token_expires_at, 
    language, last_command, last_context, 
    created_at, updated_at
) 
SELECT 
    telegram_id, username, first_name, last_name, 
    fb_access_token, fb_refresh_token, token_expires_at, 
    language, last_command, last_context, 
    created_at, updated_at
FROM users_temp;

-- Удаляем временную таблицу
DROP TABLE users_temp;

COMMIT;
PRAGMA foreign_keys=on;

-- Проверка отката
SELECT sql FROM sqlite_master WHERE type='table' AND name='users'; 