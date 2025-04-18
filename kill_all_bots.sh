#!/bin/bash
# Скрипт для принудительного завершения всех процессов, связанных с ботом

echo "Поиск и остановка всех процессов Python..."
pkill -9 -f "python"
pkill -9 -f "python3"

echo "Поиск и остановка всех процессов, связанных с main.py..."
pkill -9 -f "main.py"

echo "Удаление PID файла, если он существует..."
if [ -f "bot.pid" ]; then
    rm bot.pid
    echo "Файл bot.pid удален"
fi

echo "Проверка, остались ли процессы Python..."
ps_output=$(ps aux | grep python | grep -v grep)
if [ -n "$ps_output" ]; then
    echo "Обнаружены процессы Python:"
    echo "$ps_output"
    echo "Попытка завершить их более жестко..."
    kill -9 $(ps aux | grep python | grep -v grep | awk '{print $2}') 2>/dev/null || echo "Не удалось найти процессы для завершения"
else
    echo "Процессы Python не обнаружены."
fi

echo "Все процессы, связанные с ботом, должны быть остановлены."
echo "Если бот все еще работает, значит, он запущен на другом устройстве с тем же токеном."
echo "В этом случае рекомендуется обновить токен бота в файле .env.dev" 