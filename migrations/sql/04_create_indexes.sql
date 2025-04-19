-- Дополнительные индексы для оптимизации запросов к таблицам контроля доступа

-- Индекс для поиска разрешений доступа по пользователю
CREATE INDEX idx_access_control_user_id ON access_control (user_id);

-- Индекс для поиска по целевому объекту
CREATE INDEX idx_access_control_target ON access_control (target_type, target_id);

-- Индекс для поиска по статусу (активные/отозванные)
CREATE INDEX idx_access_control_status ON access_control (revoked_at);

-- Индекс для поиска по сроку действия
CREATE INDEX idx_access_control_expiration ON access_control (expires_at);

-- Индекс для запросов по пользователю
CREATE INDEX idx_access_request_user_id ON access_request (user_id);

-- Индекс для запросов по целевому объекту
CREATE INDEX idx_access_request_target ON access_request (target_type, target_id);

-- Индекс для запросов по статусу
CREATE INDEX idx_access_request_status ON access_request (status);

-- Общий индекс для таблицы пользователей для поиска по имени/юзернейму
CREATE INDEX idx_users_search ON users (username, first_name, last_name); 