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
  stop)
    stop_bot
    ;;
  restart)
    stop_bot
    sleep 2
    start_bot
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
  *)
    echo "Использование: $0 {start|stop|restart|status|logs|test}"
    exit 1
    ;;
esac

exit 0 