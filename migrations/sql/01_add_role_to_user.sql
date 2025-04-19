-- Добавление поля role в таблицу users
ALTER TABLE users ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'partner';

-- Создание индекса для ускорения запросов по ролям
CREATE INDEX idx_users_role ON users (role);

-- Комментарии к полю role
PRAGMA foreign_keys=off;
BEGIN TRANSACTION;
PRAGMA legacy_alter_table = ON;
ALTER TABLE users RENAME TO users_old;
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
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    role VARCHAR(20) NOT NULL DEFAULT 'partner' -- Роль пользователя: admin, targetologist, partner
);
INSERT INTO users (
    telegram_id, username, first_name, last_name, 
    fb_access_token, fb_refresh_token, token_expires_at, 
    language, last_command, last_context, 
    created_at, updated_at, role
) 
SELECT 
    telegram_id, username, first_name, last_name, 
    fb_access_token, fb_refresh_token, token_expires_at, 
    language, last_command, last_context, 
    created_at, updated_at, 'partner'
FROM users_old;
DROP TABLE users_old;
COMMIT;
PRAGMA foreign_keys=on;

-- Проверка успешности операции
SELECT sql FROM sqlite_master WHERE type='table' AND name='users'; 