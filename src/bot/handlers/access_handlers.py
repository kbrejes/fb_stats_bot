"""
Обработчики для запросов доступа к боту.
"""
from aiogram import Router, F, types
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from src.services.access_service import AccessService
from src.bot.keyboards import cancel_button
from src.bot.utils.access_utils import admin_required
from src.utils.logger import get_logger

router = Router()
logger = get_logger(__name__)

# Состояния процесса запроса доступа
class AccessRequestForm(StatesGroup):
    waiting_for_email = State()
    waiting_for_reason = State()
    confirm = State()


# Обработчик команды запроса доступа
@router.message(Command("request_access"))
async def cmd_request_access(message: types.Message, state: FSMContext):
    """Начинает процесс запроса доступа к боту."""
    # Проверяем, есть ли уже активная сессия запроса
    if await state.get_state() is not None:
        await message.answer("У вас уже есть активный процесс. Пожалуйста, завершите его или отмените с помощью /cancel.")
        return
    
    # Получаем последний запрос пользователя, если есть
    request = await AccessService.get_user_latest_request(message.from_user.id)
    
    if request:
        status = request["status"]
        if status == "PENDING":
            await message.answer("У вас уже есть активный запрос на доступ. Пожалуйста, дождитесь его рассмотрения.")
            return
        elif status == "APPROVED":
            await message.answer("Ваш запрос на доступ уже одобрен. Вы можете использовать бота.")
            return
    
    # Проверяем, имеет ли пользователь уже доступ
    user_has_access = AccessService.check_access(
        telegram_id=message.from_user.id,
        resource_type="system",
        resource_id="base_access"
    )
    
    if user_has_access:
        await message.answer("У вас уже есть доступ к боту.")
        return
    
    # Начинаем процесс запроса доступа
    await state.set_state(AccessRequestForm.waiting_for_email)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [cancel_button("Отмена")]
    ])
    
    await message.answer(
        "Для запроса доступа к боту, пожалуйста, укажите ваш email:",
        reply_markup=keyboard
    )


# Обработчик получения email
@router.message(StateFilter(AccessRequestForm.waiting_for_email))
async def process_email(message: types.Message, state: FSMContext):
    """Обрабатывает email для запроса доступа."""
    email = message.text.strip()
    # Простая валидация email - можно заменить на более сложную
    if "@" not in email or "." not in email:
        await message.answer("Пожалуйста, введите корректный email.")
        return
    
    # Сохраняем email в состоянии
    await state.update_data(email=email)
    await state.set_state(AccessRequestForm.waiting_for_reason)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [cancel_button("Отмена")]
    ])
    
    await message.answer(
        "Спасибо! Теперь, пожалуйста, укажите причину, по которой вам нужен доступ к боту:",
        reply_markup=keyboard
    )


# Обработчик получения причины запроса
@router.message(StateFilter(AccessRequestForm.waiting_for_reason))
async def process_reason(message: types.Message, state: FSMContext):
    """Обрабатывает причину запроса доступа."""
    reason = message.text.strip()
    if len(reason) < 10:
        await message.answer("Пожалуйста, укажите более подробную причину (минимум 10 символов).")
        return
    
    # Сохраняем причину в состоянии
    user_data = await state.update_data(reason=reason)
    await state.set_state(AccessRequestForm.confirm)
    
    # Создаем клавиатуру для подтверждения
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Подтвердить", callback_data="access_confirm"),
            InlineKeyboardButton(text="Отмена", callback_data="access_cancel")
        ]
    ])
    
    # Показываем данные для подтверждения
    await message.answer(
        f"Пожалуйста, проверьте данные запроса:\n\n"
        f"Email: {user_data['email']}\n"
        f"Причина: {user_data['reason']}\n\n"
        f"Все верно?",
        reply_markup=keyboard
    )


# Обработчик подтверждения запроса
@router.callback_query(F.data == "access_confirm", StateFilter(AccessRequestForm.confirm))
async def confirm_request(callback: CallbackQuery, state: FSMContext):
    """Подтверждает и отправляет запрос на доступ."""
    # Получаем данные из состояния
    user_data = await state.get_data()
    
    # Создаем запрос на доступ
    success, request_id, error_message = await AccessService.create_access_request(
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
        last_name=callback.from_user.last_name,
        email=user_data["email"],
        reason=user_data["reason"]
    )
    
    # Очищаем состояние
    await state.clear()
    
    if success:
        # Уведомляем пользователя о успешном создании запроса
        await callback.message.edit_text(
            f"Ваш запрос на доступ успешно отправлен!\n\n"
            f"ID запроса: {request_id}\n\n"
            f"Администратор рассмотрит ваш запрос в ближайшее время."
        )
        
        # Уведомляем администраторов о новом запросе
        admin_ids = await AccessService.get_admin_ids()
        
        for admin_id in admin_ids:
            # Клавиатура для администратора
            admin_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Рассмотреть", 
                        callback_data=f"access_review_{request_id}"
                    )
                ]
            ])
            
            try:
                await callback.bot.send_message(
                    admin_id,
                    f"Новый запрос на доступ!\n\n"
                    f"ID: {request_id}\n"
                    f"Пользователь: {callback.from_user.first_name} {callback.from_user.last_name or ''} (@{callback.from_user.username or 'нет'})\n"
                    f"Telegram ID: {callback.from_user.id}\n"
                    f"Email: {user_data['email']}\n"
                    f"Причина: {user_data['reason']}",
                    reply_markup=admin_keyboard
                )
            except Exception as e:
                # Игнорируем ошибки при отправке сообщений администраторам
                logger.error(f"Ошибка отправки уведомления администратору {admin_id}: {str(e)}")
    else:
        # Уведомляем пользователя об ошибке
        await callback.message.edit_text(
            f"Произошла ошибка при создании запроса на доступ: {error_message or 'Неизвестная ошибка'}"
        )


# Обработчик отмены запроса
@router.callback_query(F.data == "access_cancel", StateFilter(AccessRequestForm.confirm))
async def cancel_request(callback: CallbackQuery, state: FSMContext):
    """Отменяет процесс создания запроса на доступ."""
    await state.clear()
    await callback.message.edit_text("Запрос на доступ отменен.")


# Обработчик просмотра запроса администратором
@router.callback_query(F.data.startswith("access_review_"))
@admin_required
async def review_request(callback: CallbackQuery, **kwargs):
    """Обрабатывает просмотр запроса администратором."""
    request_id = int(callback.data.split("_")[-1])
    
    # Получаем данные запроса
    request = await AccessService.get_access_request(request_id)
    
    if not request:
        await callback.answer("Запрос не найден", show_alert=True)
        return
    
    # Клавиатура для действий администратора
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="Одобрить", 
                callback_data=f"access_approve_{request_id}"
            ),
            InlineKeyboardButton(
                text="Отклонить", 
                callback_data=f"access_deny_{request_id}"
            )
        ]
    ])
    
    # Статус запроса
    status_text = {
        "PENDING": "Ожидает рассмотрения",
        "APPROVED": "Одобрен",
        "DENIED": "Отклонен"
    }.get(request["status"], "Неизвестный статус")
    
    # Формируем сообщение с данными запроса
    message_text = (
        f"Запрос на доступ #{request_id}\n\n"
        f"Статус: {status_text}\n"
        f"Пользователь: {request['first_name']} {request['last_name'] or ''} (@{request['username'] or 'нет'})\n"
        f"Telegram ID: {request['telegram_id']}\n"
        f"Email: {request['email']}\n"
        f"Причина: {request['reason']}\n\n"
        f"Создан: {request['created_at'].strftime('%d.%m.%Y %H:%M')}"
    )
    
    # Если запрос уже обработан, добавляем информацию об этом
    if request["status"] != "PENDING":
        admin_info = f"Обработан администратором: {request['admin_id']}\n"
        if request["admin_notes"]:
            admin_info += f"Заметки: {request['admin_notes']}\n"
        admin_info += f"Дата обработки: {request['updated_at'].strftime('%d.%m.%Y %H:%M')}"
        
        message_text += f"\n\n{admin_info}"
        
        # Убираем кнопки, если запрос уже обработан
        keyboard = None
    
    await callback.message.edit_text(
        message_text,
        reply_markup=keyboard
    )


# Состояния для заметок администратора
class AdminNotes(StatesGroup):
    waiting_for_notes = State()


# Обработчик одобрения запроса администратором
@router.callback_query(F.data.startswith("access_approve_"))
@admin_required
async def approve_request(callback: CallbackQuery, state: FSMContext, **kwargs):
    """Обрабатывает одобрение запроса администратором."""
    request_id = int(callback.data.split("_")[-1])
    
    # Запрашиваем заметки администратора
    await state.update_data(action="approve", request_id=request_id)
    await state.set_state(AdminNotes.waiting_for_notes)
    
    # Клавиатура для заметок
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="Продолжить без заметок", 
                callback_data="admin_notes_skip"
            ),
            InlineKeyboardButton(
                text="Отмена", 
                callback_data="admin_notes_cancel"
            )
        ]
    ])
    
    await callback.message.reply(
        "Добавьте заметки к этому запросу (опционально):",
        reply_markup=keyboard
    )


# Обработчик отклонения запроса администратором
@router.callback_query(F.data.startswith("access_deny_"))
@admin_required
async def deny_request(callback: CallbackQuery, state: FSMContext, **kwargs):
    """Обрабатывает отклонение запроса администратором."""
    request_id = int(callback.data.split("_")[-1])
    
    # Запрашиваем заметки администратора
    await state.update_data(action="deny", request_id=request_id)
    await state.set_state(AdminNotes.waiting_for_notes)
    
    # Клавиатура для заметок
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="Продолжить без заметок", 
                callback_data="admin_notes_skip"
            ),
            InlineKeyboardButton(
                text="Отмена", 
                callback_data="admin_notes_cancel"
            )
        ]
    ])
    
    await callback.message.reply(
        "Добавьте заметки к этому запросу (опционально):",
        reply_markup=keyboard
    )


# Обработчик заметок администратора
@router.message(StateFilter(AdminNotes.waiting_for_notes))
@admin_required
async def process_admin_notes(message: types.Message, state: FSMContext, **kwargs):
    """Обрабатывает заметки администратора и завершает обработку запроса."""
    # Получаем данные из состояния
    state_data = await state.get_data()
    action = state_data.get("action")
    request_id = state_data.get("request_id")
    admin_notes = message.text.strip()
    
    await state.clear()
    
    if not request_id or not action:
        await message.answer("Произошла ошибка. Пожалуйста, попробуйте снова.")
        return
    
    # Обрабатываем запрос в зависимости от действия
    if action == "approve":
        success, result, error = await AccessService.approve_request(
            request_id=request_id,
            admin_id=message.from_user.id,
            admin_notes=admin_notes
        )
        
        if success:
            # Отправляем уведомление пользователю
            try:
                telegram_id = result["request"]["telegram_id"]
                await message.bot.send_message(
                    telegram_id,
                    f"Ваш запрос на доступ №{request_id} был одобрен!\n\n"
                    f"Теперь вы можете использовать бота."
                )
            except Exception as e:
                logger.error(f"Ошибка отправки уведомления пользователю {telegram_id}: {str(e)}")
            
            await message.answer(
                f"Запрос №{request_id} успешно одобрен.\n\n"
                f"Пользователь получил уведомление и доступ к боту."
            )
        else:
            await message.answer(
                f"Ошибка при одобрении запроса: {error or 'Неизвестная ошибка'}"
            )
    
    elif action == "deny":
        success, result, error = await AccessService.deny_request(
            request_id=request_id,
            admin_id=message.from_user.id,
            admin_notes=admin_notes
        )
        
        if success:
            # Отправляем уведомление пользователю
            try:
                telegram_id = result["telegram_id"]
                # Формируем сообщение с отказом
                deny_message = f"Ваш запрос на доступ №{request_id} был отклонен."
                if admin_notes:
                    deny_message += f"\n\nПричина: {admin_notes}"
                
                await message.bot.send_message(
                    telegram_id,
                    deny_message
                )
            except Exception as e:
                logger.error(f"Ошибка отправки уведомления пользователю {telegram_id}: {str(e)}")
            
            await message.answer(
                f"Запрос №{request_id} отклонен.\n\n"
                f"Пользователь получил уведомление об отказе."
            )
        else:
            await message.answer(
                f"Ошибка при отклонении запроса: {error or 'Неизвестная ошибка'}"
            )
    
    else:
        await message.answer("Неизвестное действие. Пожалуйста, попробуйте снова.")


# Обработчик пропуска заметок администратора
@router.callback_query(F.data == "admin_notes_skip", StateFilter(AdminNotes.waiting_for_notes))
@admin_required
async def skip_admin_notes(callback: CallbackQuery, state: FSMContext, **kwargs):
    """Обрабатывает пропуск заметок администратора."""
    # Получаем данные из состояния
    state_data = await state.get_data()
    action = state_data.get("action")
    request_id = state_data.get("request_id")
    
    await state.clear()
    
    if not request_id or not action:
        await callback.answer("Произошла ошибка. Пожалуйста, попробуйте снова.", show_alert=True)
        return
    
    # Обрабатываем запрос в зависимости от действия
    if action == "approve":
        success, result, error = await AccessService.approve_request(
            request_id=request_id,
            admin_id=callback.from_user.id
        )
        
        if success:
            # Отправляем уведомление пользователю
            try:
                telegram_id = result["request"]["telegram_id"]
                await callback.bot.send_message(
                    telegram_id,
                    f"Ваш запрос на доступ №{request_id} был одобрен!\n\n"
                    f"Теперь вы можете использовать бота."
                )
            except Exception as e:
                logger.error(f"Ошибка отправки уведомления пользователю {telegram_id}: {str(e)}")
            
            await callback.message.edit_text(
                f"Запрос №{request_id} успешно одобрен.\n\n"
                f"Пользователь получил уведомление и доступ к боту."
            )
        else:
            await callback.message.edit_text(
                f"Ошибка при одобрении запроса: {error or 'Неизвестная ошибка'}"
            )
    
    elif action == "deny":
        success, result, error = await AccessService.deny_request(
            request_id=request_id,
            admin_id=callback.from_user.id
        )
        
        if success:
            # Отправляем уведомление пользователю
            try:
                telegram_id = result["telegram_id"]
                await callback.bot.send_message(
                    telegram_id,
                    f"Ваш запрос на доступ №{request_id} был отклонен."
                )
            except Exception as e:
                logger.error(f"Ошибка отправки уведомления пользователю {telegram_id}: {str(e)}")
            
            await callback.message.edit_text(
                f"Запрос №{request_id} отклонен.\n\n"
                f"Пользователь получил уведомление об отказе."
            )
        else:
            await callback.message.edit_text(
                f"Ошибка при отклонении запроса: {error or 'Неизвестная ошибка'}"
            )
    
    else:
        await callback.answer("Неизвестное действие. Пожалуйста, попробуйте снова.", show_alert=True)


# Обработчик отмены добавления заметок
@router.callback_query(F.data == "admin_notes_cancel", StateFilter(AdminNotes.waiting_for_notes))
@admin_required
async def cancel_admin_notes(callback: CallbackQuery, state: FSMContext, **kwargs):
    """Отменяет процесс добавления заметок и обработки запроса."""
    await state.clear()
    await callback.message.edit_text("Обработка запроса отменена.")


# Обработчик команды просмотра ожидающих запросов
@router.message(Command("pending_requests"))
@admin_required
async def cmd_pending_requests(message: types.Message, **kwargs):
    """Показывает список ожидающих запросов на доступ."""
    # Получаем ожидающие запросы
    pending_requests = await AccessService.get_pending_requests(limit=10)
    
    if not pending_requests:
        await message.answer("Нет ожидающих запросов на доступ.")
        return
    
    # Формируем сообщение со списком запросов
    result = "Ожидающие запросы на доступ:\n\n"
    
    for i, request in enumerate(pending_requests, 1):
        # Добавляем кнопку для просмотра запроса
        result += (
            f"{i}. Запрос #{request['id']}\n"
            f"От: {request['first_name']} {request['last_name'] or ''} (@{request['username'] or 'нет'})\n"
            f"Email: {request['email']}\n"
            f"Создан: {request['created_at'].strftime('%d.%m.%Y %H:%M')}\n\n"
        )
    
    # Добавляем инструкцию
    result += "Для просмотра деталей запроса и его обработки используйте команду:\n/review_request <ID запроса>"
    
    await message.answer(result)


# Обработчик команды просмотра деталей запроса
@router.message(Command("review_request"))
@admin_required
async def cmd_review_request(message: types.Message, **kwargs):
    """Показывает детали запроса на доступ по ID."""
    # Получаем ID запроса из аргументов команды
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Пожалуйста, укажите ID запроса. Пример: /review_request 123")
        return
    
    try:
        request_id = int(args[1])
    except ValueError:
        await message.answer("Некорректный ID запроса. Пожалуйста, укажите числовой ID.")
        return
    
    # Получаем данные запроса
    request = await AccessService.get_access_request(request_id)
    
    if not request:
        await message.answer(f"Запрос с ID {request_id} не найден.")
        return
    
    # Статус запроса
    status_text = {
        "PENDING": "Ожидает рассмотрения",
        "APPROVED": "Одобрен",
        "DENIED": "Отклонен"
    }.get(request["status"], "Неизвестный статус")
    
    # Формируем сообщение с данными запроса
    message_text = (
        f"Запрос на доступ #{request_id}\n\n"
        f"Статус: {status_text}\n"
        f"Пользователь: {request['first_name']} {request['last_name'] or ''} (@{request['username'] or 'нет'})\n"
        f"Telegram ID: {request['telegram_id']}\n"
        f"Email: {request['email']}\n"
        f"Причина: {request['reason']}\n\n"
        f"Создан: {request['created_at'].strftime('%d.%m.%Y %H:%M')}"
    )
    
    # Если запрос уже обработан, добавляем информацию об этом
    if request["status"] != "PENDING":
        admin_info = f"Обработан администратором: {request['admin_id']}\n"
        if request["admin_notes"]:
            admin_info += f"Заметки: {request['admin_notes']}\n"
        admin_info += f"Дата обработки: {request['updated_at'].strftime('%d.%m.%Y %H:%M')}"
        
        message_text += f"\n\n{admin_info}"
        
        # Для обработанных запросов не добавляем кнопки
        await message.answer(message_text)
        return
    
    # Клавиатура для действий администратора
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="Одобрить", 
                callback_data=f"access_approve_{request_id}"
            ),
            InlineKeyboardButton(
                text="Отклонить", 
                callback_data=f"access_deny_{request_id}"
            )
        ]
    ])
    
    await message.answer(message_text, reply_markup=keyboard) 