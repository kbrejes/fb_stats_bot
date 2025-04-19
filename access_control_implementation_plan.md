# План внедрения системы ролевого доступа для Facebook Ads Telegram Bot

## 1. Общее описание системы доступа

Система ролевого доступа будет включать три основные роли пользователей с различными уровнями привилегий:

1. **Администратор**: полный доступ ко всем функциям и данным бота.
2. **Таргетолог**: полный доступ к функциям управления кампаниями без возможности управления платежными данными.
3. **Партнер**: ограниченный доступ только к статистике определенных кампаний, назначенных администратором.

## 2. Изменения в структуре базы данных

### 2.1. Модели данных

#### Таблица User (расширение существующей)
```sql
ALTER TABLE User ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'partner';
```

#### Новая таблица AccessControl
```sql
CREATE TABLE AccessControl (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    partner_id INTEGER NOT NULL,
    admin_id INTEGER NOT NULL,
    campaign_id VARCHAR(255) NOT NULL,
    granted_at DATETIME NOT NULL,
    expires_at DATETIME NULL,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    FOREIGN KEY (partner_id) REFERENCES User(id),
    FOREIGN KEY (admin_id) REFERENCES User(id)
);
```

#### Новая таблица AccessRequest
```sql
CREATE TABLE AccessRequest (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    partner_id INTEGER NOT NULL,
    requested_at DATETIME NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending', -- 'pending', 'approved', 'rejected'
    processed_by INTEGER NULL,
    processed_at DATETIME NULL,
    FOREIGN KEY (partner_id) REFERENCES User(id),
    FOREIGN KEY (processed_by) REFERENCES User(id)
);
```

## 3. Изменения в программном коде

### 3.1. Модели и репозитории

#### Обновление моделей пользователей
```python
# src/storage/models/user.py
from enum import Enum

class UserRole(Enum):
    ADMIN = "admin"
    TARGETOLOGIST = "targetologist" 
    PARTNER = "partner"

class User:
    # Добавить поле role к существующей модели
    role: UserRole = UserRole.PARTNER
```

#### Создание моделей для контроля доступа
```python
# src/storage/models/access_control.py
from datetime import datetime

class AccessControl:
    id: int
    partner_id: int
    admin_id: int
    campaign_id: str
    granted_at: datetime
    expires_at: datetime = None
    is_active: bool = True
    
class AccessRequest:
    id: int
    partner_id: int
    requested_at: datetime
    status: str  # 'pending', 'approved', 'rejected'
    processed_by: int = None
    processed_at: datetime = None
```

#### Репозитории для управления доступом
```python
# src/storage/repositories/access_control.py
# Методы для работы с запросами на доступ и управлением доступом
```

### 3.2. Система проверки прав доступа

#### Middleware для проверки прав доступа
```python
# src/bot/middlewares/access_control.py
from aiogram import BaseMiddleware
from typing import Dict, Any, Callable, Awaitable
from aiogram.types import Message

class RoleMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        # Проверка роли пользователя и разрешений
        # ...
```

#### Декораторы для проверки прав
```python
# src/utils/access_control.py
from functools import wraps
from src.storage.models.user import UserRole

def admin_required(func):
    @wraps(func)
    async def wrapper(message, *args, **kwargs):
        # Проверка на администратора
        # ...
    return wrapper

def targetologist_required(func):
    @wraps(func)
    async def wrapper(message, *args, **kwargs):
        # Проверка на таргетолога или администратора
        # ...
    return wrapper

def partner_access_check(campaign_id=None):
    def decorator(func):
        @wraps(func)
        async def wrapper(message, *args, **kwargs):
            # Проверка доступа партнера к конкретной кампании
            # ...
        return wrapper
    return decorator
```

### 3.3. Интерфейс пользователя

#### Новые команды и обработчики
```python
# src/bot/handlers/admin_handlers.py
# Обработчики для управления пользователями и их ролями
```

```python
# src/bot/handlers/partner_handlers.py
# Обработчики для запросов доступа от партнеров
```

#### Клавиатуры в зависимости от роли
```python
# src/bot/keyboards/role_keyboards.py
# Различные клавиатуры для разных ролей
```

## 4. Логика работы с партнерами

### 4.1. Процесс запроса доступа партнером
1. Партнер запрашивает статистику через команду или кнопку
2. Система создает запрос доступа в базе данных
3. Администраторы получают уведомление о новом запросе
4. После одобрения партнер получает доступ к статистике указанных кампаний

### 4.2. Панель управления доступом для администраторов
1. Просмотр всех запросов доступа
2. Одобрение/отклонение запросов
3. Назначение конкретных кампаний для просмотра партнером
4. Настройка срока действия доступа
5. Отзыв доступа

## 5. Фильтрация данных для партнеров

### 5.1. Ограничение видимости данных
```python
# src/api/facebook/insights.py
# Добавление проверки разрешений перед возвратом данных
```

### 5.2. Форматирование ограниченных данных
```python
# src/utils/formatter.py
# Модификация форматирования данных в зависимости от роли пользователя
```

## 6. Этапы разработки и внедрения

### Этап 1: Подготовка базы данных (2 дня)
- Создание новых таблиц
- Миграция существующих пользователей
- Настройка ролей по умолчанию

### Этап 2: Разработка базового функционала ролей (3 дня)
- Реализация моделей и репозиториев
- Создание middleware для проверки прав
- Разработка декораторов для защиты обработчиков

### Этап 3: Реализация интерфейса администратора (4 дня)
- Создание обработчиков для управления пользователями
- Разработка интерфейса для просмотра запросов доступа
- Реализация функционала одобрения/отклонения запросов

### Этап 4: Реализация интерфейса партнера (3 дня)
- Создание ограниченного меню для партнеров
- Разработка системы запросов на доступ к статистике
- Реализация отображения разрешенной статистики

### Этап 5: Интеграция и тестирование (3 дня)
- Интеграция всех компонентов
- Тестирование различных сценариев доступа
- Проверка безопасности и устранение уязвимостей

### Этап 6: Документация и обучение (2 дня)
- Написание документации по использованию
- Создание руководства для администраторов
- Подготовка инструкций для партнеров

## 7. Риски и их митигация

### 7.1. Технические риски
- **Проблема:** Разрешения не применяются корректно
  **Решение:** Внедрение тщательного логирования и мониторинга доступа

- **Проблема:** Производительность при множестве проверок доступа
  **Решение:** Оптимизация запросов и кеширование прав доступа

### 7.2. Пользовательские риски
- **Проблема:** Партнеры не понимают ограничения доступа
  **Решение:** Разработать понятные сообщения об ошибках и руководство

- **Проблема:** Администраторы могут неправильно настроить разрешения
  **Решение:** Создание простого и понятного интерфейса управления доступом с подтверждениями

## 8. Дальнейшее развитие

**ВАЖНО: Данный раздел содержит ТОЛЬКО ИДЕИ для будущего рассмотрения. Реализация описанного ниже функционала НЕ ТРЕБУЕТСЯ в рамках текущего проекта.**

- Расширение системы ролей для более тонкой настройки прав
- Временный доступ с автоматическим отзывом по истечении срока
- Система аудита действий пользователей
- Групповые политики доступа для управления несколькими партнерами
- Автоматическое уведомление партнеров о новых данных статистики 