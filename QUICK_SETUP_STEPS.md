# 🚀 Быстрая настройка продакшн (для непrogrammers)

## ШАГ 1: Настройка GitHub Secrets (СЕЙЧАС)

1. Откройте в браузере: https://github.com/kbrejes/fb_stats_bot
2. Нажмите **Settings** (вверху справа)
3. В левом меню найдите **Secrets and variables** → нажмите **Actions**
4. Нажмите зеленую кнопку **New repository secret**

Добавьте по очереди эти секреты (каждый отдельно):

### Секрет 1: PROD_SSH_KEY (ВАЖНО!)
- Name: `PROD_SSH_KEY`
- Secret: (скопируйте весь текст ниже, включая BEGIN и END строки)
```
-----BEGIN OPENSSH PRIVATE KEY-----
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
-----END OPENSSH PRIVATE KEY-----
```
- Нажмите **Add secret**

### Секрет 2: PROD_HOST
- Name: `PROD_HOST`
- Secret: `188.166.221.59`
- Нажмите **Add secret**

### Секрет 3: PROD_USER  
- Name: `PROD_USER`
- Secret: `botuser`
- Нажмите **Add secret**

### Секрет 4: PROD_PORT
- Name: `PROD_PORT` 
- Secret: `22`
- Нажмите **Add secret**

### Секрет 5: TELEGRAM_TOKEN
- Name: `TELEGRAM_TOKEN`
- Secret: `7595294156:AAFcKTYzTt0h0xEt-BiVs-otrmYB6dAL7LY`
- Нажмите **Add secret**

### Секрет 6: OPENAI_API_KEY
- Name: `OPENAI_API_KEY`
- Secret: `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`
- Нажмите **Add secret**

### Секрет 7: FB_APP_ID
- Name: `FB_APP_ID`
- Secret: `639419165542707`
- Нажмите **Add secret**

### Секрет 8: FB_APP_SECRET
- Name: `FB_APP_SECRET`
- Secret: `73af4e475afddfbd61fb74628481eb28`
- Нажмите **Add secret**

### Секрет 9: TELEGRAM_CHAT_ID
- Name: `TELEGRAM_CHAT_ID`
- Secret: `400133981`
- Нажмите **Add secret**

### Секрет 10: TELEGRAM_BOT_TOKEN
- Name: `TELEGRAM_BOT_TOKEN`
- Secret: `7595294156:AAFcKTYzTt0h0xEt-BiVs-otrmYB6dAL7LY`
- Нажмите **Add secret**

### Секрет 11: NOTIFICATION_EMAIL
- Name: `NOTIFICATION_EMAIL`
- Secret: `your-email@gmail.com` (замените на свой email)
- Нажмите **Add secret**

## ✅ После добавления всех секретов - напишите мне "секреты добавлены" 

## 🚀 **Настройка сервера (выполняйте команды по очереди)**

Скопируйте и выполните эти команды одну за другой:

### **Шаг 1: Обновление системы**
```bash
apt update && apt upgrade -y
```

### **Шаг 2: Установка необходимых пакетов**
```bash
apt install -y curl wget git ufw fail2ban htop
```

### **Шаг 3: Создание пользователя для бота**
```bash
adduser botuser
```
(Когда спросит пароль - придумайте и запомните его, остальные поля можно пропустить нажимая Enter)

### **Шаг 4: Добавление пользователя в sudo группу**
```bash
usermod -aG sudo botuser
```

### **Шаг 5: Создание SSH директории для botuser**
```bash
mkdir -p /home/botuser/.ssh
```

## ✅ **Выполните эти команды по очереди и напишите мне:**
- **"команды выполнены"** - когда все сделаете
- **"ошибка на шаге X"** - если что-то пойдет не так

Начинайте с первой команды! 🔧 