# Модуль управления состоянием пользователя

Модуль `src/state` предоставляет централизованный механизм для управления состоянием пользователя в телеграм боте. 

## Основные компоненты

### UserSession

Класс `UserSession` - это основной интерфейс для работы с состоянием пользователя. Он обеспечивает:

- Управление контекстом пользователя
- Централизованный доступ к настройкам
- Сохранение и загрузку данных пользовательской сессии
- Оптимизацию запросов к базе данных

## Использование

### Инициализация сессии

```python
from src.state import UserSession

# Создание сессии с автоматическим исправлением ID пользователя
user_session = await UserSession.get_session(message.from_user.id)

# Или напрямую, без исправления ID
user_session = UserSession(user_id)
```

### Работа с контекстом

```python
# Получение всего контекста
context = user_session.get_context()

# Установка новых значений (объединение с существующими)
user_session.set_context({
    "current_view": "campaigns",
    "selected_date_range": "last_7d"
})

# Замена всего контекста
user_session.set_context(new_context, merge=False)

# Очистка контекста
user_session.clear_context()
```

### Работа с отдельными значениями

```python
# Получение значения с возможностью указать значение по умолчанию
account_id = user_session.get_value("current_account_id", default=None)

# Установка значения
user_session.set_value("current_account_id", "act_123456789")

# Удаление значения
user_session.remove_value("temporary_data")
```

### Специализированные геттеры и сеттеры

```python
# Работа с текущим аккаунтом
account_id = user_session.get_current_account()
user_session.set_current_account(account_id)

# Работа с текущей кампанией
campaign_id = user_session.get_current_campaign()
user_session.set_current_campaign(campaign_id)

# Работа с текущим набором объявлений
ad_set_id = user_session.get_current_ad_set()
user_session.set_current_ad_set(ad_set_id)
```

### Проверка состояния пользователя

```python
# Проверка валидности токена
if not user_session.is_token_valid():
    await message.answer("Ваш токен истек. Используйте /auth для авторизации.")
    return

# Работа с последней выполненной командой
last_command = user_session.get_last_command()
user_session.set_last_command("current_command")

# Работа с языковыми настройками
language = user_session.get_language()
user_session.set_language("en")
```

### Управление кэшем

```python
# Очистка внутреннего кэша для обновления данных из базы
user_session.clear_cache()
```

## Примеры использования

### В обработчиках команд

```python
@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    # Создаем сессию пользователя
    user_session = await UserSession.get_session(message.from_user.id)
    
    # Сохраняем информацию о выполненной команде
    user_session.set_last_command("start")
    
    # Очищаем предыдущий контекст
    user_session.clear_context()
    
    # Приветствуем пользователя на его языке
    language = user_session.get_language()
    # ...остальной код
```

### В обработчиках колбэков

```python
@router.callback_query(F.data.startswith("account:"))
async def account_callback(callback: CallbackQuery) -> None:
    # Создаем сессию пользователя
    user_session = await UserSession.get_session(callback.from_user.id)
    
    # Получаем ID аккаунта из колбэка
    account_id = callback.data.split(":")[1]
    
    # Сохраняем выбранный аккаунт в сессии
    user_session.set_current_account(account_id)
    # ...остальной код
```

### В сервисных функциях

```python
async def check_user_authorization(user_id: int) -> bool:
    # Создаем сессию пользователя
    user_session = await UserSession.get_session(user_id)
    
    # Проверяем валидность токена
    return user_session.is_token_valid()
```

## Преимущества использования

1. **Централизация логики** - все операции с состоянием пользователя сосредоточены в одном месте
2. **Унификация интерфейса** - одинаковые методы доступа к данным во всем приложении
3. **Оптимизация работы с БД** - встроенное кэширование и оптимизация запросов
4. **Удобство разработки** - меньше дублирования кода и понятные именованные методы
5. **Поддержка аутентификации** - встроенные проверки валидности токенов
6. **Языковые настройки** - поддержка мультиязычности 