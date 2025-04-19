-- Создание таблицы управления доступом
CREATE TABLE access_control (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,  -- ID пользователя, имеющего доступ (партнер)
    target_id TEXT NOT NULL,   -- ID объекта, к которому предоставлен доступ (например, ID кампании)
    target_type VARCHAR(50) NOT NULL, -- Тип объекта (campaign, account, adset, etc.)
    granted_by INTEGER NOT NULL, -- ID пользователя, выдавшего доступ (админ или таргетолог)
    granted_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME, -- Время истечения доступа (NULL - бессрочный)
    revoked_at DATETIME, -- Время отзыва доступа (NULL - активен)
    revoked_by INTEGER,  -- ID пользователя, отозвавшего доступ
    notes TEXT,          -- Примечания к доступу
    
    FOREIGN KEY (user_id) REFERENCES users(telegram_id) ON DELETE CASCADE,
    FOREIGN KEY (granted_by) REFERENCES users(telegram_id) ON DELETE SET NULL,
    FOREIGN KEY (revoked_by) REFERENCES users(telegram_id) ON DELETE SET NULL
);

-- Создание индексов для оптимизации запросов
CREATE INDEX idx_access_control_user_id ON access_control (user_id);
CREATE INDEX idx_access_control_target ON access_control (target_id, target_type);
CREATE INDEX idx_access_control_status ON access_control (expires_at, revoked_at);

-- Тригер для автоматического обновления доступов при изменении роли пользователя
CREATE TRIGGER trg_user_role_changed
AFTER UPDATE OF role ON users
WHEN NEW.role != OLD.role AND NEW.role = 'admin'
BEGIN
    -- Если пользователь стал администратором, отозвать все его запросы на доступ
    UPDATE access_control 
    SET revoked_at = CURRENT_TIMESTAMP, 
        revoked_by = NEW.telegram_id,
        notes = 'Автоматический отзыв доступа при изменении роли на администратора'
    WHERE user_id = NEW.telegram_id AND revoked_at IS NULL;
END; 