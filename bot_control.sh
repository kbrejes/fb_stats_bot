#!/bin/bash
# Управление Telegram-ботом для Facebook Ads
# Скрипт для запуска, остановки и проверки статуса бота

LOG_FILE="bot_output.log"
PID_FILE="bot.pid"

start_bot() {
  if [ -f "$PID_FILE" ] && ps -p $(cat $PID_FILE) > /dev/null; then
    echo "Бот уже запущен с PID $(cat $PID_FILE)"
    exit 1
  fi
  
  echo "Запуск бота..."
  python3 main.py > $LOG_FILE 2>&1 &
  echo $! > $PID_FILE
  echo "Бот запущен с PID $(cat $PID_FILE)"
  echo "Логи сохраняются в $LOG_FILE"
}

start_bot_test() {
  # Запускает бота в режиме вывода логов в консоль для тестирования
  echo "Запуск бота в тестовом режиме (вывод в консоль)..."
  echo "Для остановки нажмите Ctrl+C"
  python3 main.py
}

stop_bot() {
  if [ -f "$PID_FILE" ]; then
    PID=$(cat $PID_FILE)
    echo "Остановка бота с PID $PID..."
    kill $PID
    rm $PID_FILE
    echo "Бот остановлен"
  else
    echo "PID файл не найден, пробуем остановить все процессы бота..."
    pkill -f "python3 main.py"
    echo "Все процессы бота остановлены"
  fi
}

find_bot_processes() {
  echo "Поиск всех процессов, связанных с ботом..."
  echo "1. Поиск по 'python main.py':"
  ps aux | grep "python main.py" | grep -v grep
  
  echo "2. Поиск по 'python3 main.py':"
  ps aux | grep "python3 main.py" | grep -v grep
  
  echo "3. Поиск всех процессов 'python' с 'main':"
  ps aux | grep "python" | grep "main" | grep -v grep
  
  echo "4. Поиск через pgrep:" 
  pgrep -fl python | grep main
  
  echo "5. PID файл содержит (если существует):"
  if [ -f "$PID_FILE" ]; then
    cat $PID_FILE
    echo "Проверка, существует ли процесс с этим PID:"
    ps -p $(cat $PID_FILE) || echo "Процесс не найден"
  else
    echo "PID файл не найден"
  fi
}

check_status() {
  if [ -f "$PID_FILE" ] && ps -p $(cat $PID_FILE) > /dev/null; then
    echo "Бот запущен с PID $(cat $PID_FILE)"
    echo "Последние 10 строк логов:"
    tail -n 10 $LOG_FILE
  else
    echo "Бот не запущен"
    if [ -f "$PID_FILE" ]; then
      echo "PID файл существует, но процесс не активен. Удаляем PID файл..."
      rm $PID_FILE
    fi
  fi
}

view_logs() {
  if [ -f "$LOG_FILE" ]; then
    echo "Последние 50 строк логов:"
    tail -n 50 $LOG_FILE
  else
    echo "Файл логов не найден"
  fi
}

run_tests() {
  echo "Запуск тестов бота..."
  python3 test_bot_integration.py
}

case "$1" in
  start)
    start_bot
    ;;
  start_test)
    start_bot_test
    ;;
  stop)
    stop_bot
    ;;
  restart)
    stop_bot
    sleep 2
    start_bot
    ;;
  restart_test)
    stop_bot
    sleep 2
    start_bot_test
    ;;
  status)
    check_status
    ;;
  logs)
    view_logs
    ;;
  test)
    run_tests
    ;;
  find)
    find_bot_processes
    ;;
  *)
    echo "Использование: $0 {start|start_test|stop|restart|restart_test|status|logs|test|find}"
    echo "  start       - Запустить бота в фоновом режиме"
    echo "  start_test  - Запустить бота в режиме вывода логов в консоль"
    echo "  stop        - Остановить бота"
    echo "  restart     - Перезапустить бота в фоновом режиме"
    echo "  restart_test - Перезапустить бота с выводом логов в консоль"
    echo "  status      - Проверить статус бота"
    echo "  logs        - Показать последние записи логов"
    echo "  test        - Запустить тесты"
    echo "  find        - Найти все процессы бота"
    exit 1
    ;;
esac

exit 0 