require('dotenv').config();
const TelegramBot = require('node-telegram-bot-api');

// Проверяем наличие токена
if (!process.env.BOT_TOKEN) {
    console.error('❌ BOT_TOKEN не найден в переменных окружения!');
    console.log('📝 Создайте файл .env и добавьте: BOT_TOKEN=ваш_токен_бота');
    process.exit(1);
}

const bot = new TelegramBot(process.env.BOT_TOKEN, { polling: true });

console.log('🚀 Бот запущен!');

// Команда /start
bot.onText(/\/start/, (msg) => {
    const chatId = msg.chat.id;
    const welcomeMessage = `
🤖 Привет! Я тестовый бот для CI/CD!

Версия: 1.0.0
Сервер: ${process.env.NODE_ENV || 'development'}
Время запуска: ${new Date().toLocaleString('ru-RU')}

Нажми на кнопки ниже, чтобы проверить мою работу:
    `;

    const options = {
        reply_markup: {
            inline_keyboard: [
                [
                    { text: '🔧 Тест 1', callback_data: 'test_1' },
                    { text: '⚡ Тест 2', callback_data: 'test_2' }
                ],
                [
                    { text: '📊 Статус сервера', callback_data: 'server_status' }
                ],
                [
                    { text: '🔄 Обновить', callback_data: 'refresh' }
                ]
            ]
        }
    };

    bot.sendMessage(chatId, welcomeMessage, options);
});

// Обработка нажатий на кнопки
bot.on('callback_query', (callbackQuery) => {
    const message = callbackQuery.message;
    const data = callbackQuery.data;
    const chatId = message.chat.id;

    let responseText = '';

    switch (data) {
        case 'test_1':
            responseText = '✅ Кнопка "Тест 1" работает!\nТекущее время: ' + new Date().toLocaleString('ru-RU');
            break;
        
        case 'test_2':
            responseText = '✅ Кнопка "Тест 2" работает!\nБот работает стабильно!';
            break;
        
        case 'server_status':
            responseText = `
📊 Статус сервера:
• Версия: 1.0.0
• Среда: ${process.env.NODE_ENV || 'development'}
• Время: ${new Date().toLocaleString('ru-RU')}
• Память: ${Math.round(process.memoryUsage().heapUsed / 1024 / 1024)} MB
• Аптайм: ${Math.round(process.uptime())} секунд
            `;
            break;
        
        case 'refresh':
            responseText = '🔄 Обновлено!\nВремя: ' + new Date().toLocaleString('ru-RU');
            break;
        
        default:
            responseText = '❓ Неизвестная команда';
    }

    // Отправляем ответ
    bot.answerCallbackQuery(callbackQuery.id);
    bot.sendMessage(chatId, responseText);
});

// Обработка команды /help
bot.onText(/\/help/, (msg) => {
    const chatId = msg.chat.id;
    const helpMessage = `
📖 Доступные команды:

/start - Запуск бота и главное меню
/help - Показать эту справку
/status - Статус бота

Этот бот создан для тестирования CI/CD пайплайна.
    `;
    bot.sendMessage(chatId, helpMessage);
});

// Команда /status
bot.onText(/\/status/, (msg) => {
    const chatId = msg.chat.id;
    const statusMessage = `
🤖 Статус бота:
• Работает: ✅
• Версия: 1.0.0
• Время запуска: ${new Date().toLocaleString('ru-RU')}
• Среда: ${process.env.NODE_ENV || 'development'}
    `;
    bot.sendMessage(chatId, statusMessage);
});

// Обработка ошибок
bot.on('error', (error) => {
    console.error('❌ Ошибка бота:', error);
});

// Graceful shutdown
process.on('SIGINT', () => {
    console.log('🛑 Остановка бота...');
    bot.stopPolling();
    process.exit(0);
});

console.log('✅ Бот готов к работе!'); 