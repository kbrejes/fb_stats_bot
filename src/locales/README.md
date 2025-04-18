# Система локализации Facebook Ads Telegram Bot

## Обзор

Система локализации позволяет легко добавлять и изменять переводы в боте. Переводы хранятся в JSON-файлах, организованных по функциональным группам и языкам.

## Структура

```
src/
└── locales/
    ├── ru/
    │   ├── menu.json     # Переводы меню и навигации
    │   ├── errors.json   # Сообщения об ошибках
    │   ├── stats.json    # Переводы для статистики
    │   ├── auth.json     # Сообщения авторизации
    │   ├── common.json   # Общие переводы
    │   └── help.json     # Сообщения справки
    ├── en/
    │   ├── menu.json
    │   ├── errors.json
    │   ├── ...
    └── index.json        # Метаинформация о доступных языках
```

## Использование в коде

### Базовое использование

```python
from src.utils.localization import get_text, _

# Использование через функцию get_text
message = get_text("welcome", user_id=user_id, category="common")

# Или через короткий алиас _
message = _("welcome", user_id=user_id, category="common")
```

### С форматированием

```python
# С параметрами форматирования
error_message = get_text("api_error", user_id=user_id, category="errors", message="Server timeout")
# Результат: "Ошибка API: Server timeout"
```

### Указание категории и языка

```python
# Явное указание языка и категории
button_text = get_text("back_to_main_menu", lang="ru", category="menu")
```

### Работа с языковыми настройками

```python
from src.utils.localization import get_language, set_language, get_language_name

# Получение текущего языка пользователя
current_lang = get_language(user_id)

# Установка языка пользователя
set_language(user_id, "en")

# Получение названия языка
lang_name = get_language_name("ru")  # Результат: "Русский"
```

## Добавление новых переводов

1. Определите, к какой категории относится новый перевод
2. Добавьте ключ и перевод в соответствующий JSON-файл для каждого языка
3. Если нужно создать новую категорию:
   - Создайте новый JSON-файл в папках каждого языка
   - Добавьте название категории в массив `categories` в файле `index.json`

### Пример добавления нового перевода

Например, для добавления перевода "Синхронизация данных..." добавьте в файл `common.json` для каждого языка:

**ru/common.json:**
```json
{
  "syncing_data": "Синхронизация данных..."
}
```

**en/common.json:**
```json
{
  "syncing_data": "Syncing data..."
}
```

## Добавление нового языка

1. Создайте новую директорию с кодом языка в папке `locales`
2. Скопируйте все JSON-файлы из существующего языка
3. Переведите все строки
4. Добавьте код языка в массив `available_languages` в файле `index.json`
5. Добавьте имя языка в объект `language_names` в файле `index.json`

## Миграция со старой системы

Старая система локализации (в `src.utils.languages`) помечена как устаревшая и будет удалена в будущих версиях. Для миграции на новую систему:

1. Замените импорты:
   ```python
   # Старый способ
   from src.utils.languages import get_text, get_language, set_language
   
   # Новый способ
   from src.utils.localization import get_text, get_language, set_language, _
   ```

2. Обновите вызовы функций:
   ```python
   # Старый способ
   text = get_text("key", language)
   
   # Новый способ
   text = get_text("key", lang=language)  # или
   text = get_text("key", user_id=user_id, category="category_name")
   ``` 