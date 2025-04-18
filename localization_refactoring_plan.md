# План рефакторинга системы локализации

## Обзор
Этот план описывает процесс улучшения системы локализации бота, чтобы сделать её более организованной, модульной и простой в поддержке. В настоящее время все переводы хранятся в единых словарях внутри Python-файлов, что затрудняет поддержку, обновление и масштабирование.

## Текущее состояние
- Переводы хранятся в больших словарях в файлах:
  - `src/bot/i18n/__init__.py`
  - `src/utils/languages/language_manager.py`
- Доступ к переводам осуществляется через функции `_()` и `get_text()`
- Поддерживаются языки: русский (ru) и английский (en)
- Нет структурного разделения по функциональным группам

## Цели рефакторинга
1. Разделить переводы по функциональным группам для упрощения обслуживания
2. Перенести переводы из Python-кода в JSON-файлы
3. Создать унифицированный механизм доступа к переводам
4. Обеспечить обратную совместимость
5. Добавить документацию для разработчиков

## Шаги рефакторинга

### 1. Создание структуры директорий

```
src/
└── locales/
    ├── ru/
    │   ├── menu.json
    │   ├── errors.json
    │   ├── stats.json
    │   ├── auth.json
    │   ├── common.json
    │   └── help.json
    ├── en/
    │   ├── menu.json
    │   ├── errors.json
    │   ├── stats.json
    │   ├── auth.json
    │   ├── common.json
    │   └── help.json
    └── index.json  # Метаинформация о доступных языках
```

### 2. Создание JSON файлов с переводами

Каждый JSON-файл будет содержать переводы для своей функциональной группы. Например:

**menu.json (ru)**:
```json
{
  "main_menu": "📋 Главное меню",
  "accounts": "📊 Мои аккаунты",
  "search": "🔎 Поиск",
  "settings": "⚙️ Настройки",
  "help": "ℹ️ Помощь",
  "change_language": "🌐 Изменить язык",
  "notifications_settings": "🔔 Настройки уведомлений",
  "back_to_settings": "⬅️ Назад к настройкам"
}
```

**errors.json (ru)**:
```json
{
  "api_error": "Ошибка API: {message}",
  "network_error": "Ошибка сети. Пожалуйста, проверьте интернет-соединение.",
  "token_expired": "Ваш токен доступа истек. Пожалуйста, используйте команду /auth для повторной авторизации.",
  "permission_error": "Недостаточно прав для выполнения операции.",
  "not_found": "Запрашиваемый {object_type} не найден."
}
```

**stats.json (ru)**:
```json
{
  "loading_stats": "⏳ Загрузка статистики...",
  "no_stats_found": "❌ Статистика не найдена для этого {object_type}.",
  "insights_for": "📊 Статистика для {type}: <b>{name}</b>",
  "period": "Период",
  "summary": "Сводка",
  "impressions": "Показы",
  "clicks": "Клики",
  "reach": "Охват",
  "spend": "Расходы",
  "ctr": "CTR",
  "cpm": "CPM",
  "cpc": "CPC"
}
```

### 3. Создание менеджера локализации

Создать новый класс `LocalizationManager` в файле `src/utils/localization.py`:

```python
class LocalizationManager:
    def __init__(self):
        self.translations = {}
        self.load_translations()
    
    def load_translations(self):
        # Загрузка всех JSON-файлов
        pass
    
    def get_text(self, key, lang="ru", category=None, **kwargs):
        # Получение текста перевода
        pass
    
    def set_language(self, user_id, language):
        # Установка языка для пользователя
        pass
    
    def get_language(self, user_id):
        # Получение языка пользователя
        pass
```

### 4. Обновление существующих модулей

1. Обновить `src/utils/languages/language_manager.py` для работы с новой системой
2. Обеспечить обратную совместимость через алиасы функций
3. Добавить устаревшие предупреждения для старых функций

### 5. Рефакторинг обработчиков для использования новой системы

1. Обновить импорты в файлах обработчиков
2. Заменить прямые обращения к старым функциям на новые
3. Добавить контекст категории при вызове функций

### 6. Тестирование

1. Модульные тесты для нового менеджера локализации
2. Интеграционные тесты с разными языковыми настройками
3. Тестирование обратной совместимости

### 7. Документация

1. Добавить README.md в директорию локализации
2. Обновить документацию в коде
3. Инструкции по добавлению новых переводов

## Технические детали реализации

### Загрузка переводов

```python
def load_translations(self):
    locales_dir = os.path.join("src", "locales")
    for lang in os.listdir(locales_dir):
        if os.path.isdir(os.path.join(locales_dir, lang)):
            self.translations[lang] = {}
            for file in os.listdir(os.path.join(locales_dir, lang)):
                if file.endswith('.json'):
                    category = file.split('.')[0]
                    file_path = os.path.join(locales_dir, lang, file)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        self.translations[lang][category] = json.load(f)
```

### Получение перевода

```python
def get_text(self, key, lang="ru", category=None, **kwargs):
    # Проверка языка
    if lang not in self.translations:
        lang = "ru"
    
    # Если категория не указана, искать во всех категориях
    if category:
        if category in self.translations[lang]:
            text = self.translations[lang][category].get(key)
            if text:
                return text.format(**kwargs) if kwargs else text
    else:
        # Поиск в всех категориях
        for cat, translations in self.translations[lang].items():
            if key in translations:
                text = translations[key]
                return text.format(**kwargs) if kwargs else text
    
    # Возврат ключа, если перевод не найден
    return key
```

## Риски и их снижение

1. **Риск**: Несовместимость с существующим кодом
   - **Снижение**: Обеспечить слой обратной совместимости

2. **Риск**: Проблемы с производительностью при загрузке JSON-файлов
   - **Снижение**: Кэширование загруженных переводов

3. **Риск**: Потеря переводов при миграции
   - **Снижение**: Тщательное сравнение существующих и новых переводов

## Критерии завершения

1. Все переводы разделены по функциональным группам в JSON-файлах
2. Создан и работает новый менеджер локализации
3. Весь существующий код переведен на использование нового менеджера
4. Тесты подтверждают корректность работы локализации
5. Документация обновлена 