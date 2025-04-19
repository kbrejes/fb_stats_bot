-- Создание таблицы запросов доступа
CREATE TABLE access_request (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,  -- ID пользователя, запрашивающего доступ (партнер)
    target_id TEXT NOT NULL,   -- ID объекта, к которому запрашивается доступ (например, ID кампании)
    target_type VARCHAR(50) NOT NULL, -- Тип объекта (campaign, account, adset, etc.)
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at DATETIME, -- Время разрешения запроса (NULL - ожидает ответа)
    resolved_by INTEGER,  -- ID пользователя, разрешившего запрос
    status VARCHAR(20) DEFAULT 'pending', -- статус: pending, approved, rejected, canceled
    reason TEXT,         -- Причина запроса от пользователя
    resolution_notes TEXT, -- Примечания при разрешении запроса
    
    FOREIGN KEY (user_id) REFERENCES users(telegram_id) ON DELETE CASCADE,
    FOREIGN KEY (resolved_by) REFERENCES users(telegram_id) ON DELETE SET NULL
);

-- Создание индексов для оптимизации запросов
CREATE INDEX idx_access_request_user_id ON access_request (user_id);
CREATE INDEX idx_access_request_target ON access_request (target_id, target_type);
CREATE INDEX idx_access_request_status ON access_request (status);

-- Тригер для отклонения всех ожидающих запросов при изменении роли пользователя на админа
CREATE TRIGGER trg_user_role_changed_requests
AFTER UPDATE OF role ON users
WHEN NEW.role != OLD.role AND NEW.role = 'admin'
BEGIN
    -- Если пользователь стал администратором, отклонить все его ожидающие запросы
    UPDATE access_request
    SET resolved_at = CURRENT_TIMESTAMP, 
        resolved_by = NEW.telegram_id,
        status = 'canceled',
        resolution_notes = 'Автоматическая отмена запроса при изменении роли на администратора'
    WHERE user_id = NEW.telegram_id AND status = 'pending';
END;

-- Тригер для автоматического создания записи в access_control при одобрении запроса
CREATE TRIGGER trg_access_request_approved
AFTER UPDATE OF status ON access_request
WHEN NEW.status = 'approved' AND OLD.status = 'pending'
BEGIN
    -- Создаем запись в таблице контроля доступа
    INSERT INTO access_control (
        user_id, target_id, target_type, granted_by, 
        granted_at, expires_at, notes
    )
    VALUES (
        NEW.user_id, NEW.target_id, NEW.target_type, NEW.resolved_by,
        CURRENT_TIMESTAMP, 
        datetime('now', '+30 days'), -- Стандартный срок доступа - 30 дней
        'Предоставлен доступ по запросу #' || NEW.id
    );
END; 