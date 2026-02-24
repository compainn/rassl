from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from telethon import TelegramClient, errors
from telethon.sessions import StringSession
import asyncio
import time
import random
import re
from datetime import datetime, timedelta
import json
import os

# ============================================
# ФЕЙКОВЫЙ ВЕБ-СЕРВЕР (В ТОМ ЖЕ ПОТОКЕ)
# ============================================
try:
    from aiohttp import web
    
    async def run_fake_server():
        """Запускает фейковый сервер в том же цикле событий"""
        app = web.Application()
        
        async def handle(request):
            return web.Response(text="🤖 Bot is running!")
        
        app.router.add_get('/', handle)
        app.router.add_get('/health', handle)
        app.router.add_get('/ping', handle)
        
        port = int(os.environ.get('PORT', 8080))
        
        runner = web.AppRunner(app, handle_signals=False)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', port)
        await site.start()
        
        print(f"🌐 Фейковый сервер запущен на порту {port}")
        return runner
    
    FAKE_SERVER_RUNNER = None
    
except ImportError:
    print("⚠️ aiohttp не установлен")
    FAKE_SERVER_RUNNER = None

from config import TOKEN, SYSTEM_API_ID, SYSTEM_API_HASH, ADMIN_PASSWORD
from models import (
    init_db, get_user, save_user, delete_user, update_user_session, update_user_message,
    update_user_usernames, update_subscription, update_mailing_settings, get_admin, add_admin, get_all_users,
    create_user, get_all_admins, remove_admin, get_config, set_config, is_ga
)
from keyboards import (
    get_main_keyboard, get_no_subscription_keyboard, get_clear_keyboard, get_cancel_keyboard,
    get_back_keyboard, get_back_to_settings_keyboard, get_mailing_control_keyboard, get_confirmation_keyboard,
    get_yes_no_keyboard, get_auth_options_keyboard, get_ready_keyboard,
    get_not_ready_keyboard, get_settings_keyboard, get_mailing_time_keyboard,
    get_delay_keyboard, get_admin_keyboard, get_subscription_types_keyboard,
    get_start_keyboard, get_profile_keyboard, get_back_admin_ponel,
    get_ga_keyboard
)

bot = Bot(token=TOKEN)
dp = Dispatcher()

DEVICES = [
    {"device_model": "iPhone 13 Pro", "system_version": "iOS 17.0"},
    {"device_model": "SM-S918B", "system_version": "Android 14"},
    {"device_model": "iPhone 14 Pro Max", "system_version": "iOS 16.6"}
]


def get_random_device():
    return random.choice(DEVICES)


mailing_active = {}


class AuthStates(StatesGroup):
    waiting_phone = State()
    waiting_code = State()
    waiting_password = State()


class AdminStates(StatesGroup):
    waiting_user_id = State()
    waiting_subscription_type = State()


class SettingsStates(StatesGroup):
    waiting_mailing_time = State()
    waiting_delay = State()


class GAStates(StatesGroup):
    waiting_admin_to_remove = State()


def validate_html(text):
    paired_tags = [
        ('<b>', '</b>'), ('<i>', '</i>'), ('<u>', '</u>'),
        ('<strong>', '</strong>'), ('<em>', '</em>'),
        ('<code>', '</code>'), ('<pre>', '</pre>'),
        ('<blockquote>', '</blockquote>')
    ]
    for open_tag, close_tag in paired_tags:
        open_count = text.count(open_tag)
        close_count = text.count(close_tag)
        if open_count > close_count:
            text += close_tag * (open_count - close_count)
    return text


async def check_subscription(user_id: int) -> bool:
    user = await get_user(user_id)
    if not user:
        user = await create_user(user_id)
        return False
    return user.check_subscription()


async def get_user_keyboard(user_id: int):
    if await check_subscription(user_id):
        return get_main_keyboard()
    else:
        return get_no_subscription_keyboard()


async def get_admin_status_symbol(telegram_id: int) -> str:
    if await is_ga(telegram_id):
        return "👑"
    elif await get_admin(telegram_id):
        return "⭐"
    else:
        return ""


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name or "пользователь"

    user = await get_user(user_id)
    if not user:
        user = await create_user(user_id)

    has_subscription = await check_subscription(user_id)

    if has_subscription:
        welcome_text = f'<b>Добро пожаловать, @{username}</b>\n\n✅ <b>Подписка активна!</b>'
        keyboard = get_start_keyboard()
    else:
        welcome_text = (
            f'<b>Добро пожаловать, @{username}</b>\n\n'
            f'❌ <b>Подписка неактивна</b>\n\n'
        )
        keyboard = get_start_keyboard()

    await message.answer(
        welcome_text,
        parse_mode='HTML',
        reply_markup=keyboard
    )


@dp.message(Command("menu"))
async def cmd_menu(message: types.Message):
    await show_main_menu(message)


async def show_main_menu(message_or_call):
    user_id = message_or_call.from_user.id if isinstance(message_or_call,
                                                         types.Message) else message_or_call.from_user.id
    keyboard = await get_user_keyboard(user_id)

    if isinstance(message_or_call, types.Message):
        await message_or_call.answer("📱 <b>Главное меню</b>", parse_mode='HTML', reply_markup=keyboard)
    else:
        try:
            await message_or_call.message.edit_text("📱 <b>Главное меню</b>", parse_mode='HTML', reply_markup=keyboard)
        except Exception as e:
            if "message is not modified" in str(e):
                await message_or_call.answer("📱 Главное меню")
            else:
                raise


@dp.callback_query(F.data == "back_main")
async def callback_back_main(callback: types.CallbackQuery):
    await show_main_menu(callback)
    await callback.answer()


@dp.callback_query(F.data == "cancel")
async def callback_cancel(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await show_main_menu(callback)
    await callback.answer("❌ Действие отменено")


@dp.callback_query(F.data == "profile")
async def callback_profile(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user = await get_user(user_id)

    if not user:
        user = await create_user(user_id)

    text_lines = []
    text_lines.append("<b>👤 Ваш профиль</b>")
    text_lines.append("")

    if user.check_subscription():
        text_lines.append("<b>🎫 Статус подписки:</b> ✅ АКТИВНА")
        if user.subscription_type == 'forever':
            text_lines.append("<b>├ Тип:</b> Навсегда")
            text_lines.append("<b>└ Истекает:</b> Никогда")
        elif user.subscription_end:
            end_date = user.subscription_end.strftime('%d.%m.%Y %H:%M')
            days_left = (user.subscription_end - datetime.now()).days
            text_lines.append(f"<b>├ Тип:</b> {user.subscription_type}")
            text_lines.append(f"<b>├ Истекает:</b> {end_date}")
            text_lines.append(f"<b>└ Осталось:</b> {days_left} дней")
    else:
        text_lines.append("<b>🎫 Статус подписки:</b> ❌ НЕАКТИВНА")
        text_lines.append("<b>└ Для доступа к функциям нужна подписка</b>")

    text_lines.append("")

    text_lines.append("<b>⚙️ Настройки рассылки:</b>")
    text_lines.append(f"<b>├ Время:</b> {user.mailing_hours} часов")
    text_lines.append(f"<b>└ Задержка:</b> {user.delay_minutes} минут")

    text_lines.append("")

    if user.session_string:
        text_lines.append("<b>🔐 Аккаунт:</b> ✅ Авторизован")
        if user.phone:
            text_lines.append(f"<b>└ Телефон:</b> {user.phone}")
    else:
        text_lines.append("<b>🔐 Аккаунт:</b> ❌ Не авторизован")

    usernames = user.get_usernames()
    text_lines.append(f"<b>👥 Получателей:</b> {len(usernames) if usernames else 0}")

    text_lines.append(f"<b>📝 Текст:</b> {len(user.message) if user.message else 0} символов")

    text = "\n".join(text_lines)

    await callback.message.edit_text(text, parse_mode='HTML', reply_markup=get_profile_keyboard())
    await callback.answer()


# АВТОРИЗАЦИЯ
@dp.callback_query(F.data == "auth")
async def callback_auth(callback: types.CallbackQuery, state: FSMContext):
    if not await check_subscription(callback.from_user.id):
        await callback.message.edit_text(
            "❌ <b>Кнопка недоступна!</b>\n\n"
            "Для использования этой функции нужна активная подписка.\n"
            "Обратитесь к администратору.",
            parse_mode='HTML',
            reply_markup=get_back_keyboard()
        )
        await callback.answer()
        return

    user_id = callback.from_user.id
    user = await get_user(user_id)
    if user and user.session_string:
        await callback.message.edit_text(
            f"🔐 <b>Уже есть активная сессия!</b>\n\n"
            f"📱 Телефон: {user.phone or 'неизвестен'}\n\n"
            f"Выберите действие:",
            parse_mode='HTML',
            reply_markup=get_auth_options_keyboard()
        )
    else:
        await callback.message.edit_text(
            "📱 <b>Введите номер телефона:</b>\n\n"
            "Пример: <code>+79001234567</code>\n"
            "Номер должен начинаться с '+'\n\n"
            "Отправьте номер в чат:",
            parse_mode='HTML',
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(AuthStates.waiting_phone)
    await callback.answer()


@dp.callback_query(F.data == "use_current")
async def callback_use_current(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "✅ <b>Используется текущая сессия</b>\n\n"
        "можно настроить и запустить рассылку",
        parse_mode='HTML',
        reply_markup=await get_user_keyboard(callback.from_user.id)
    )
    await callback.answer()


@dp.callback_query(F.data == "auth_new")
async def callback_auth_new(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "📱 <b>Введите номер телефона:</b>\n\n"
        "Пример: <code>+79001234567</code>\n"
        "Номер должен начинаться с '+'\n\n"
        "Отправьте номер в чат:",
        parse_mode='HTML',
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(AuthStates.waiting_phone)
    await callback.answer()


@dp.message(AuthStates.waiting_phone)
async def process_phone(message: types.Message, state: FSMContext):
    phone = message.text.strip()
    if not phone.startswith('+'):
        await state.clear()
        await message.answer("❌ <b>Авторизация отменена</b>", parse_mode='HTML',
                             reply_markup=await get_user_keyboard(message.from_user.id))
        return

    device = get_random_device()
    client = TelegramClient(
        StringSession(),
        SYSTEM_API_ID,
        SYSTEM_API_HASH,
        device_model=device["device_model"],
        system_version=device["system_version"]
    )
    try:
        await client.connect()
        sent_code = await client.send_code_request(phone)
        await state.update_data(
            phone=phone,
            client=client,
            phone_code_hash=sent_code.phone_code_hash
        )
        await message.answer(
            "✅ <b>Код отправлен в Telegram!</b>\n\n"
            "📱 <b>Введите 5-значный код:</b>\n\n"
            "<i>Форматы:</i>\n"
            "<code>1 2 3 4 5</code>\n"
            '<i>либо</i>\n'
            "<code>12 34 5</code>\n\n"
            "Отправьте код в чат(с пробелами):",
            parse_mode='HTML',
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(AuthStates.waiting_code)
    except errors.PhoneNumberInvalidError:
        await state.clear()
        await message.answer("❌ <b>Неверный номер телефона</b>\n\nАвторизация отменена.", parse_mode='HTML',
                             reply_markup=await get_user_keyboard(message.from_user.id))
        try:
            await client.disconnect()
        except:
            pass
    except errors.PhoneNumberUnoccupiedError:
        await state.clear()
        await message.answer("❌ <b>Номер не зарегистрирован в Telegram</b>\n\nАвторизация отменена.", parse_mode='HTML',
                             reply_markup=await get_user_keyboard(message.from_user.id))
        try:
            await client.disconnect()
        except:
            pass
    except Exception as e:
        await state.clear()
        await message.answer(f"❌ <b>Ошибка:</b> {str(e)[:100]}\n\nАвторизация отменена.", parse_mode='HTML',
                             reply_markup=await get_user_keyboard(message.from_user.id))
        try:
            await client.disconnect()
        except:
            pass


@dp.message(AuthStates.waiting_code)
async def process_code(message: types.Message, state: FSMContext):
    raw_text = message.text.strip()
    code = re.sub(r'[^\d]', '', raw_text)
    if not code.isdigit() or len(code) != 5:
        await state.clear()
        try:
            data = await state.get_data()
            client = data.get("client")
            if client and client.is_connected():
                await client.disconnect()
        except:
            pass
        if raw_text.lower() in ['отмена', 'cancel', 'стоп']:
            await message.answer("❌ <b>Авторизация отменена</b>", parse_mode='HTML',
                                 reply_markup=await get_user_keyboard(message.from_user.id))
        else:
            await message.answer(
                "❌ <b>Неверный формат кода!</b>\n\n"
                "Код должен содержать 5 цифр.\n"
                "Примеры:\n"
                "• <code>1 2 3 4 5</code>\n"
                "• <code>12 34 5</code>\n\n"
                "Попробуйте ещё раз или отмените:",
                parse_mode='HTML',
                reply_markup=get_cancel_keyboard()
            )
        return

    data = await state.get_data()
    client = data.get("client")
    phone = data.get("phone")
    phone_code_hash = data.get("phone_code_hash")
    if not client:
        await message.answer("❌ <b>Ошибка сессии</b>\nИспользуйте авторизацию", parse_mode='HTML',
                             reply_markup=await get_user_keyboard(message.from_user.id))
        await state.clear()
        return

    try:
        await client.sign_in(
            phone=phone,
            code=code,
            phone_code_hash=phone_code_hash
        )
        session_string = client.session.save()
        await save_user(
            telegram_id=message.from_user.id,
            phone=phone,
            session_string=session_string
        )
        await message.answer(
            "✅ <b>Авторизация успешна!</b>\n\n"
            "Теперь можно настроить и запустить рассылку\n",
            parse_mode='HTML',
            reply_markup=await get_user_keyboard(message.from_user.id)
        )
    except errors.SessionPasswordNeededError:
        await message.answer(
            "❌ <b>Аккаунт защищен двухфакторной аутентификацией!</b>\n\n"
            "Уберите, либо используйте другой аккаунт без 2FA.\n",
            parse_mode='HTML',
            reply_markup=await get_user_keyboard(message.from_user.id)
        )
        return
    except errors.PhoneCodeInvalidError:
        attempts = data.get('auth_attempts', 0) + 1
        await state.update_data(auth_attempts=attempts)
        if attempts >= 3:
            await state.clear()
            await message.answer(
                "❌ <b>Слишком много неверных попыток!</b>\n\n"
                "Авторизация отменена. Начните заново: /auth",
                parse_mode='HTML',
                reply_markup=await get_user_keyboard(message.from_user.id)
            )
            return
        await message.answer(
            f"❌ <b>Неверный код!</b> (попытка {attempts}/3)\n\n"
            "Попробуйте ещё раз:\n"
            "<code>1 2 3 4 5</code> или <code>12 34 5</code>\n\n"
            "Или отмените ввод:",
            parse_mode='HTML',
            reply_markup=get_cancel_keyboard()
        )
        return
    except errors.PhoneCodeExpiredError:
        await state.clear()
        await message.answer(
            "❌ <b>Код устарел!</b>\n\n"
            "Запросите новый код через /auth",
            parse_mode='HTML',
            reply_markup=await get_user_keyboard(message.from_user.id)
        )
        return
    except Exception as e:
        await state.clear()
        await message.answer(
            f"❌ <b>Ошибка:</b> {str(e)[:100]}\n\n"
            "Авторизация отменена.",
            parse_mode='HTML',
            reply_markup=await get_user_keyboard(message.from_user.id)
        )
        return
    finally:
        try:
            if client and client.is_connected():
                await client.disconnect()
        except:
            pass
    await state.clear()


# ПОЛУЧАТЕЛИ
@dp.callback_query(F.data == "usernames")
async def callback_usernames(callback: types.CallbackQuery, state: FSMContext):
    if not await check_subscription(callback.from_user.id):
        await callback.message.edit_text(
            "❌ <b>Кнопка недоступна!</b>\n\n"
            "Для использования этой функции нужна активная подписка.\n"
            "Обратитесь к администратору.",
            parse_mode='HTML',
            reply_markup=get_back_keyboard()
        )
        await callback.answer()
        return

    user_id = callback.from_user.id
    user = await get_user(user_id)
    if not user or not user.session_string:
        await callback.message.edit_text(
            "❌ <b>Сначала авторизуйтесь!</b>\n\n"
            "Нажмите кнопку '🔐 Авторизация'",
            parse_mode='HTML',
            reply_markup=get_back_keyboard()
        )
        await callback.answer()
        return

    if user.get_usernames() and len(user.get_usernames()) > 0:
        usernames_list = user.get_usernames()
        await callback.message.edit_text(
            f"📋 <b>Текущие получатели:</b> {len(usernames_list)}\n\n"
            f"<b>Список:</b>\n" + "\n".join([f"• @{username}" for username in usernames_list[:10]]) +
            (f"\n\n... и еще {len(usernames_list) - 10} получателей" if len(usernames_list) > 10 else "") +
            "\n\n<b>Выберите действие:</b>",
            parse_mode='HTML',
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="✏️ Редактировать", callback_data="edit_usernames")],
                [types.InlineKeyboardButton(text="🗑️ Удалить", callback_data="clear_usernames")],
                [types.InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")]
            ])
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        "👥 <b>Отправьте юзернеймы через запятую:</b>\n\n"
        "Пример: <code>@username1, @username2, @username3</code>\n\n"
        "Или: <code>username1, username2, username3</code>\n\n"
        "Отправьте список в чат:",
        parse_mode='HTML',
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state("waiting_usernames")
    await callback.answer()


@dp.callback_query(F.data == "edit_usernames")
async def callback_edit_usernames(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "👥 <b>Отправьте новые юзернеймы через запятую:</b>\n\n"
        "Пример: <code>@username1, @username2, @username3</code>\n\n"
        "Или: <code>username1, username2, username3</code>\n\n"
        "<i>Старый список будет удален</i>\n"
        "Отправьте новый список в чат:",
        parse_mode='HTML',
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state("waiting_usernames")
    await callback.answer()


# ТЕКСТ
@dp.callback_query(F.data == "text")
async def callback_text(callback: types.CallbackQuery, state: FSMContext):
    if not await check_subscription(callback.from_user.id):
        await callback.message.edit_text(
            "❌ <b>Кнопка недоступна!</b>\n\n"
            "Для использования этой функции нужна активная подписка.\n"
            "Обратитесь к администратору.",
            parse_mode='HTML',
            reply_markup=get_back_keyboard()
        )
        await callback.answer()
        return

    user_id = callback.from_user.id
    user = await get_user(user_id)
    if not user or not user.get_usernames():
        await callback.message.edit_text(
            "❌ <b>Сначала укажите юзернеймы!</b>\n\n"
            "Нажмите кнопку '👥 Получатели'",
            parse_mode='HTML',
            reply_markup=get_back_keyboard()
        )
        await callback.answer()
        return

    if user.message:
        await callback.message.edit_text(
            "📝 <b>Текущий текст сохранён!</b>\n\n"
            f"<b>Длина:</b> {len(user.message)} символов\n\n"
            f"<b>Предпросмотр:</b>\n"
            f"<blockquote>{user.message[:150]}{'...' if len(user.message) > 150 else ''}</blockquote>\n\n"
            "<b>Выберите действие:</b>",
            parse_mode='HTML',
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="✏️ Редактировать", callback_data="edit_message")],
                [types.InlineKeyboardButton(text="🗑️ Удалить", callback_data="clear_message")],
                [types.InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")]
            ])
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        "📝 <b>Отправьте текст сообщения:</b>\n\n"
        "Поддерживается HTML разметка\n"
        "Пример: <code>&lt;b&gt;Привет&lt;/b&gt;, это тестовое сообщение!</code>\n\n"
        "Доступные теги: <b>&lt;b&gt;, &lt;i&gt;, &lt;u&gt;, &lt;code&gt;, &lt;pre&gt;</b>\n\n"
        "Отправьте текст в чат:",
        parse_mode='HTML',
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state("waiting_message")
    await callback.answer()


@dp.callback_query(F.data == "edit_message")
async def callback_edit_message(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "📝 <b>Отправьте новый текст сообщения:</b>\n\n"
        "Поддерживается HTML разметка\n"
        "Пример: <code>&lt;b&gt;Привет&lt;/b&gt;, это тестовое сообщение!</code>\n\n"
        "Доступные теги: <b>&lt;b&gt;, &lt;i&gt;, &lt;u&gt;, &lt;code&gt;, &lt;pre&gt;</b>\n\n"
        "<i>Старый текст будет удален</i>\n"
        "Отправьте новый текст в чат:",
        parse_mode='HTML',
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state("waiting_message")
    await callback.answer()


# ПРОВЕРКА
@dp.callback_query(F.data == "check")
async def callback_check(callback: types.CallbackQuery):
    if not await check_subscription(callback.from_user.id):
        await callback.message.edit_text(
            "❌ <b>Кнопка недоступна!</b>\n\n"
            "Для использования этой функции нужна активная подписка.\n"
            "Обратитесь к администратору.",
            parse_mode='HTML',
            reply_markup=get_back_keyboard()
        )
        await callback.answer()
        return

    user_id = callback.from_user.id
    user = await get_user(user_id)
    if not user:
        await callback.message.edit_text(
            "❌ <b>Нет данных</b>\nИспользуйте авторизацию",
            parse_mode='HTML',
            reply_markup=await get_user_keyboard(user_id)
        )
        await callback.answer()
        return

    response_lines = []
    response_lines.append("<b>┌ 👤 Аккаунт</b>")
    is_authorized = False
    if user.session_string:
        try:
            client = TelegramClient(
                StringSession(user.session_string),
                SYSTEM_API_ID,
                SYSTEM_API_HASH
            )
            await client.connect()
            if await client.is_user_authorized():
                me = await client.get_me()
                username = f"@{me.username}" if me.username else "не указан"
                response_lines.append("<b>├ Статус:</b> авторизован ✅")
                if user.phone:
                    phone = user.phone
                    if len(phone) >= 7:
                        formatted = f"{phone[:3]} {phone[3:]}"
                    else:
                        formatted = phone
                    response_lines.append(f"<b>└ Телефон:</b> {formatted}")
                else:
                    response_lines.append("<b>└ Телефон:</b> не указан")
                is_authorized = True
                await client.disconnect()
            else:
                response_lines.append("<b>├ Статус:</b> неавторизован ❌")
                response_lines.append("<b>└ Действие:</b> авторизуйтесь")
                await client.disconnect()
        except Exception as e:
            response_lines.append("<b>├ Статус:</b> ошибка ⚠️")
            response_lines.append("<b>└ Действие:</b> авторизуйтесь")
    else:
        response_lines.append("<b>├ Статус:</b> отсутствует ❌")
        response_lines.append("<b>└ Действие:</b> авторизуйтесь")

    response_lines.append("")
    response_lines.append("<b>┌ 📤 Рассылка</b>")
    usernames = user.get_usernames()
    if usernames:
        response_lines.append(f"<b>├ Получателей:</b> {len(usernames)}")
        if len(usernames) == 1:
            response_lines.append(f"<b>│</b>   1. @{usernames[0]}")
        elif len(usernames) <= 3:
            for i, username in enumerate(usernames, 1):
                response_lines.append(f"<b>│</b>   {i}. @{username}")
        else:
            response_lines.append(f"<b>│</b>   1. @{usernames[0]}")
            response_lines.append(f"<b>│</b>   ... и еще {len(usernames) - 1}")
    else:
        response_lines.append("<b>├ Получателей:</b> 0")

    if user.message:
        text_length = len(user.message)
        response_lines.append(f"<b>└ Сообщение:</b> {text_length} символов")
    else:
        response_lines.append("<b>└ Сообщение:</b> не указано")

    response_lines.append("")
    response_lines.append("<b>┌ Статус</b>")
    ready = all([
        is_authorized,
        usernames and len(usernames) > 0,
        user.message
    ])

    if ready:
        response_lines.append("<b>└ 🟢 ГОТОВО К РАССЫЛКЕ!</b>")
        keyboard = get_ready_keyboard()
    else:
        response_lines.append("<b>└ 🔴 НЕ ГОТОВО</b>")
        missing = []
        if not is_authorized:
            missing.append("авторизация")
        if not usernames or len(usernames) == 0:
            missing.append("юзернеймы")
        if not user.message:
            missing.append("текст")
        if missing:
            response_lines.append(f"   <b>Не хватает:</b> {', '.join(missing)}")
        keyboard = get_not_ready_keyboard()

    response = "\n".join(response_lines)
    await callback.message.edit_text(response, parse_mode='HTML', reply_markup=keyboard)
    await callback.answer()


# РАССЫЛКА
@dp.callback_query(F.data == "go")
async def callback_go(callback: types.CallbackQuery):
    if not await check_subscription(callback.from_user.id):
        await callback.message.edit_text(
            "❌ <b>Кнопка недоступна!</b>\n\n"
            "Для использования этой функции нужна активная подписка.\n"
            "Обратитесь к администратору.",
            parse_mode='HTML',
            reply_markup=get_back_keyboard()
        )
        await callback.answer()
        return

    user_id = callback.from_user.id
    user = await get_user(user_id)
    if not user:
        await callback.message.edit_text(
            "❌ <b>Нет данных</b>\nИспользуйте авторизацию",
            parse_mode='HTML',
            reply_markup=get_back_keyboard()
        )
        await callback.answer()
        return

    if not user.session_string:
        await callback.message.edit_text(
            "❌ <b>Нет сессии</b>\nИспользуйте авторизацию",
            parse_mode='HTML',
            reply_markup=get_back_keyboard()
        )
        await callback.answer()
        return

    usernames = user.get_usernames()
    if not usernames or len(usernames) == 0:
        await callback.message.edit_text(
            "❌ <b>Нет юзернеймов</b>\nИспользуйте 'Получатели'",
            parse_mode='HTML',
            reply_markup=get_back_keyboard()
        )
        await callback.answer()
        return

    if not user.message:
        await callback.message.edit_text(
            "❌ <b>Нет текста</b>\nИспользуйте 'Текст'",
            parse_mode='HTML',
            reply_markup=get_back_keyboard()
        )
        await callback.answer()
        return

    try:
        client = TelegramClient(
            StringSession(user.session_string),
            SYSTEM_API_ID,
            SYSTEM_API_HASH
        )
        await client.connect()
        if not await client.is_user_authorized():
            await client.disconnect()
            await callback.message.edit_text(
                "❌ <b>Сессия недействительна</b>\nИспользуйте авторизацию",
                parse_mode='HTML',
                reply_markup=get_back_keyboard()
            )
            await callback.answer()
            return
        await client.disconnect()
    except Exception as e:
        await callback.message.edit_text(
            f"❌ <b>Ошибка сессии:</b> {str(e)[:100]}",
            parse_mode='HTML',
            reply_markup=get_back_keyboard()
        )
        await callback.answer()
        return

    if user_id in mailing_active and mailing_active[user_id]:
        await callback.message.edit_text(
            "❌ <b>Рассылка уже запущена</b>\nИспользуйте 'Остановить'",
            parse_mode='HTML',
            reply_markup=get_back_keyboard()
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        f"🚀 <b>Подтверждение запуска</b>\n\n"
        f"📱 <b>Аккаунт:</b> {user.phone}\n"
        f"👥 <b>Получателей:</b> {len(usernames)}\n"
        f"⏱ <b>Задержка:</b> {user.delay_minutes} мин\n"
        f"⏳ <b>Длительность:</b> {user.mailing_hours} ч\n\n"
        f"<b>Запустить рассылку?</b>",
        parse_mode='HTML',
        reply_markup=get_yes_no_keyboard(yes_data="confirm_go", no_data="back_main")
    )
    await callback.answer()


@dp.callback_query(F.data == "confirm_go")
async def callback_confirm_go(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user = await get_user(user_id)
    if not user:
        await show_main_menu(callback)
        return

    await callback.message.edit_text(
        f"🚀 <b>РАССЫЛКА ЗАПУЩЕНА!</b>\n\n"
        f"📱 <b>Аккаунт:</b> {user.phone}\n"
        f"👥 <b>Получателей:</b> {len(user.get_usernames())}\n"
        f"⏱ <b>Задержка:</b> {user.delay_minutes} мин\n"
        f"⏳ <b>Длительность:</b> {user.mailing_hours} ч\n\n"
        f"<i>Для остановки нажмите кнопку ниже</i>",
        parse_mode='HTML',
        reply_markup=get_mailing_control_keyboard()
    )
    mailing_active[user_id] = True
    asyncio.create_task(run_mailing(user_id, user))
    await callback.answer()


@dp.callback_query(F.data == "stop")
async def callback_stop(callback: types.CallbackQuery):
    if not await check_subscription(callback.from_user.id):
        await callback.message.edit_text(
            "❌ <b>Кнопка недоступна!</b>\n\n"
            "Для использования этой функции нужна активная подписка.\n"
            "Обратитесь к администратору.",
            parse_mode='HTML',
            reply_markup=get_back_keyboard()
        )
        await callback.answer()
        return

    user_id = callback.from_user.id
    if user_id in mailing_active and mailing_active[user_id]:
        await callback.message.edit_text(
            "🛑 <b>Подтвердите остановку:</b>",
            parse_mode='HTML',
            reply_markup=get_yes_no_keyboard(yes_data="confirm_stop", no_data="back_main")
        )
    else:
        await callback.message.edit_text(
            "ℹ️ <b>Нет активной рассылки</b>",
            parse_mode='HTML',
            reply_markup=get_back_keyboard()
        )
    await callback.answer()


@dp.callback_query(F.data == "stop_mailing")
async def callback_stop_mailing(callback: types.CallbackQuery):
    if not await check_subscription(callback.from_user.id):
        await callback.message.edit_text(
            "❌ <b>Кнопка недоступна!</b>\n\n"
            "Для использования этой функции нужна активная подписка.\n"
            "Обратитесь к администратору.",
            parse_mode='HTML',
            reply_markup=get_back_keyboard()
        )
        await callback.answer()
        return

    user_id = callback.from_user.id
    if user_id in mailing_active and mailing_active[user_id]:
        await callback.message.edit_text(
            "🛑 <b>Подтвердите остановку:</b>",
            parse_mode='HTML',
            reply_markup=get_yes_no_keyboard(yes_data="confirm_stop", no_data="back_main")
        )
    else:
        await callback.message.edit_text(
            "ℹ️ <b>Нет активной рассылки</b>",
            parse_mode='HTML',
            reply_markup=get_back_keyboard()
        )
    await callback.answer()


@dp.callback_query(F.data == "confirm_stop")
async def callback_confirm_stop(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if user_id in mailing_active and mailing_active[user_id]:
        mailing_active[user_id] = False
        await callback.message.edit_text(
            "🛑 <b>Рассылка остановлена!</b>\nПодождите ~4 минуты для полного завершения",
            parse_mode='HTML',
            reply_markup=get_back_keyboard()
        )
    else:
        await callback.message.edit_text(
            "ℹ️ <b>Нет активной рассылки</b>",
            parse_mode='HTML',
            reply_markup=get_back_keyboard()
        )
    await callback.answer()


# ОЧИСТКА
@dp.callback_query(F.data == "clear_menu")
async def callback_clear_menu(callback: types.CallbackQuery):
    if not await check_subscription(callback.from_user.id):
        await callback.message.edit_text(
            "❌ <b>Кнопка недоступна!</b>\n\n"
            "Для использования этой функции нужна активная подписка.\n"
            "Обратитесь к администратору.",
            parse_mode='HTML',
            reply_markup=get_back_keyboard()
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        "🗑️ <b>Очистка данных</b>\n\n"
        "Выберите что удалить:",
        parse_mode='HTML',
        reply_markup=get_clear_keyboard()
    )
    await callback.answer()


@dp.callback_query(F.data == "clear_all")
async def callback_clear_all(callback: types.CallbackQuery):
    if not await check_subscription(callback.from_user.id):
        await callback.message.edit_text(
            "❌ <b>Кнопка недоступна!</b>\n\n"
            "Для использования этой функции нужна активная подписка.\n"
            "Обратитесь к администратору.",
            parse_mode='HTML',
            reply_markup=get_back_keyboard()
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        "⚠️ <b>Внимание!</b>\n\n"
        "Вы уверены что хотите удалить ВСЕ данные?\n"
        "Это действие нельзя отменить.",
        parse_mode='HTML',
        reply_markup=get_confirmation_keyboard()
    )
    await callback.answer()


@dp.callback_query(F.data == "confirm_clear")
async def callback_confirm_clear(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    deleted = await delete_user(user_id)
    if user_id in mailing_active:
        mailing_active[user_id] = False
    if deleted:
        await callback.message.edit_text(
            "🗑️ <b>Все ваши данные удалены!</b>\n\n"
            "Для начала работы используйте авторизацию",
            parse_mode='HTML',
            reply_markup=await get_user_keyboard(user_id)
        )
    else:
        await callback.message.edit_text(
            "ℹ️ <b>Нет данных для удаления</b>",
            parse_mode='HTML',
            reply_markup=await get_user_keyboard(user_id)
        )
    await callback.answer()


@dp.callback_query(F.data == "cancel_clear")
async def callback_cancel_clear(callback: types.CallbackQuery):
    await show_main_menu(callback)
    await callback.answer()


@dp.callback_query(F.data == "clear_session")
async def callback_clear_session(callback: types.CallbackQuery):
    if not await check_subscription(callback.from_user.id):
        await callback.message.edit_text(
            "❌ <b>Кнопка недоступна!</b>\n\n"
            "Для использования этой функции нужна активная подписка.\n"
            "Обратитесь к администратору.",
            parse_mode='HTML',
            reply_markup=get_back_keyboard()
        )
        await callback.answer()
        return

    user_id = callback.from_user.id
    user = await get_user(user_id)
    if user:
        await update_user_session(user_id, None)
        await callback.message.edit_text(
            "✅ <b>Сессия удалена!</b>\nИспользуйте авторизацию для новой",
            parse_mode='HTML',
            reply_markup=await get_user_keyboard(user_id)
        )
    else:
        await callback.message.edit_text(
            "ℹ️ <b>Нет данных для удаления</b>",
            parse_mode='HTML',
            reply_markup=await get_user_keyboard(user_id)
        )
    await callback.answer()


@dp.callback_query(F.data == "clear_usernames")
async def callback_clear_usernames(callback: types.CallbackQuery):
    if not await check_subscription(callback.from_user.id):
        await callback.message.edit_text(
            "❌ <b>Кнопка недоступна!</b>\n\n"
            "Для использования этой функции нужна активная подписка.\n"
            "Обратитесь к администратору.",
            parse_mode='HTML',
            reply_markup=get_back_keyboard()
        )
        await callback.answer()
        return

    user_id = callback.from_user.id
    user = await get_user(user_id)
    if user:
        await update_user_usernames(user_id, [])
        await callback.message.edit_text(
            "✅ <b>Юзернеймы удалены!</b>\nИспользуйте 'Получатели' для нового списка",
            parse_mode='HTML',
            reply_markup=await get_user_keyboard(user_id)
        )
    else:
        await callback.message.edit_text(
            "ℹ️ <b>Нет данных для удаления</b>",
            parse_mode='HTML',
            reply_markup=await get_user_keyboard(user_id)
        )
    await callback.answer()


@dp.callback_query(F.data == "clear_message")
async def callback_clear_message(callback: types.CallbackQuery):
    if not await check_subscription(callback.from_user.id):
        await callback.message.edit_text(
            "❌ <b>Кнопка недоступна!</b>\n\n"
            "Для использования этой функции нужна активная подписка.\n"
            "Обратитесь к администратору.",
            parse_mode='HTML',
            reply_markup=get_back_keyboard()
        )
        await callback.answer()
        return

    user_id = callback.from_user.id
    user = await get_user(user_id)
    if user:
        await update_user_message(user_id, None)
        await callback.message.edit_text(
            "✅ <b>Текст удален!</b>\nИспользуйте 'Текст' для нового сообщения",
            parse_mode='HTML',
            reply_markup=await get_user_keyboard(user_id)
        )
    else:
        await callback.message.edit_text(
            "ℹ️ <b>Нет данных для удаления</b>",
            parse_mode='HTML',
            reply_markup=await get_user_keyboard(user_id)
        )
    await callback.answer()


# НАСТРОЙКИ
@dp.callback_query(F.data == "settings")
async def callback_settings(callback: types.CallbackQuery):
    if not await check_subscription(callback.from_user.id):
        await callback.message.edit_text(
            "❌ <b>Кнопка недоступна!</b>\n\n"
            "Для использования этой функции нужна активная подписка.\n"
            "Обратитесь к администратору.",
            parse_mode='HTML',
            reply_markup=get_back_keyboard()
        )
        await callback.answer()
        return

    user = await get_user(callback.from_user.id)

    text = (
        f"⚙️ <b>Настройки рассылки</b>\n\n"
        f"Текущие значения:\n"
        f"• ⏱ <b>Время рассылки:</b> {user.mailing_hours} часов\n"
        f"• ⏳ <b>Задержка:</b> {user.delay_minutes} минут\n\n"
        f"Выберите что изменить:"
    )

    await callback.message.edit_text(text, parse_mode='HTML', reply_markup=get_settings_keyboard())
    await callback.answer()


@dp.callback_query(F.data == "set_mailing_time")
async def callback_set_mailing_time(callback: types.CallbackQuery, state: FSMContext):
    if not await check_subscription(callback.from_user.id):
        await callback.message.edit_text(
            "❌ <b>Кнопка недоступна!</b>\n\n"
            "Для использования этой функции нужна активная подписка.\n"
            "Обратитесь к администратору.",
            parse_mode='HTML',
            reply_markup=get_back_keyboard()
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        "⏱ <b>Выберите время рассылки:</b>\n\n"
        "Или отправьте свое значение в чат (в часах):",
        parse_mode='HTML',
        reply_markup=get_mailing_time_keyboard()
    )
    await state.set_state(SettingsStates.waiting_mailing_time)
    await callback.answer()


@dp.callback_query(F.data.startswith("time_"))
async def callback_set_time(callback: types.CallbackQuery):
    if not await check_subscription(callback.from_user.id):
        await callback.message.edit_text(
            "❌ <b>Кнопка недоступна!</b>\n\n"
            "Для использования этой функции нужна активная подписка.\n"
            "Обратитесь к администратору.",
            parse_mode='HTML',
            reply_markup=get_back_keyboard()
        )
        await callback.answer()
        return

    time_value = callback.data.replace("time_", "")

    if time_value.isdigit():
        hours = float(time_value)
        await update_mailing_settings(callback.from_user.id, mailing_hours=hours)

        await callback.message.edit_text(
            f"✅ <b>Время рассылки установлено:</b> {hours} часов",
            parse_mode='HTML',
            reply_markup=get_back_to_settings_keyboard()
        )

    await callback.answer()


@dp.callback_query(F.data == "set_delay")
async def callback_set_delay(callback: types.CallbackQuery, state: FSMContext):
    if not await check_subscription(callback.from_user.id):
        await callback.message.edit_text(
            "❌ <b>Кнопка недоступна!</b>\n\n"
            "Для использования этой функции нужна активная подписка.\n"
            "Обратитесь к администратору.",
            parse_mode='HTML',
            reply_markup=get_back_keyboard()
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        "⏳ <b>Выберите задержку между сообщениями:</b>\n\n"
        "Или отправьте свое значение в чат (в минутах):",
        parse_mode='HTML',
        reply_markup=get_delay_keyboard()
    )
    await state.set_state(SettingsStates.waiting_delay)
    await callback.answer()


@dp.callback_query(F.data.startswith("delay_"))
async def callback_set_delay_value(callback: types.CallbackQuery):
    if not await check_subscription(callback.from_user.id):
        await callback.message.edit_text(
            "❌ <b>Кнопка недоступна!</b>\n\n"
            "Для использования этой функции нужна активная подписка.\n"
            "Обратитесь к администратору.",
            parse_mode='HTML',
            reply_markup=get_back_keyboard()
        )
        await callback.answer()
        return

    delay_value = callback.data.replace("delay_", "")

    if delay_value.isdigit():
        minutes = float(delay_value)
        await update_mailing_settings(callback.from_user.id, delay_minutes=minutes)

        await callback.message.edit_text(
            f"✅ <b>Задержка установлена:</b> {minutes} минут",
            parse_mode='HTML',
            reply_markup=get_back_to_settings_keyboard()
        )

    await callback.answer()


# АДМИНКА
@dp.message(Command("set_admin_password"))
async def cmd_set_admin_password(message: types.Message):
    user_id = message.from_user.id

    if not await is_ga(user_id):
        await message.answer("❌ <b>Доступ запрещен!</b> Эта команда только для главного админа.", parse_mode='HTML')
        return

    args = message.text.split()
    if len(args) < 2:
        await message.answer("❌ <b>Использование:</b> /set_admin_password новый_пароль", parse_mode='HTML')
        return

    new_password = args[1]
    await set_config('ADMIN_PASSWORD', new_password)

    await message.answer(f"✅ <b>Пароль для админов обновлен!</b>\n\nНовый пароль: <code>{new_password}</code>",
                         parse_mode='HTML')


@dp.message(Command("set_ga_password"))
async def cmd_set_ga_password(message: types.Message):
    user_id = message.from_user.id

    if not await is_ga(user_id):
        await message.answer("❌ <b>Доступ запрещен!</b> Эта команда только для главного админа.", parse_mode='HTML')
        return

    args = message.text.split()
    if len(args) < 2:
        await message.answer("❌ <b>Использование:</b> /set_ga_password новый_пароль", parse_mode='HTML')
        return

    new_password = args[1]
    await set_config('GA_PASSWORD', new_password)

    await message.answer(f"✅ <b>Пароль для ГА обновлен!</b>\n\nНовый пароль: <code>{new_password}</code>",
                         parse_mode='HTML')


@dp.message(Command("get_admin"))
async def cmd_get_admin(message: types.Message):
    args = message.text.split()
    if len(args) < 2:
        await message.answer("❌ <b>Использование:</b> /get_admin пароль", parse_mode='HTML')
        return

    password = args[1]

    db_password = await get_config('ADMIN_PASSWORD')

    if db_password:
        current_password = db_password
    else:
        current_password = ADMIN_PASSWORD

    if password == current_password:
        user_id = message.from_user.id
        username = message.from_user.username or message.from_user.first_name
        await add_admin(user_id, username, is_ga=False)
        await message.answer(
            "✅ <b>Вы стали администратором!</b>\n\n"
            "/admin - панель администратора\n"
            "/ga - панель главного админа (если получите права ГА)",
            parse_mode='HTML',
            reply_markup=get_admin_keyboard()
        )
    else:
        await message.answer("❌ <b>Неверный пароль!</b>", parse_mode='HTML')


@dp.message(Command("get_ga"))
async def cmd_get_ga(message: types.Message):
    args = message.text.split()
    if len(args) < 2:
        await message.answer("❌ <b>Использование:</b> /get_ga пароль", parse_mode='HTML')
        return

    password = args[1]
    current_password = await get_config('GA_PASSWORD')

    if password == current_password:
        user_id = message.from_user.id
        username = message.from_user.username or message.from_user.first_name
        await add_admin(user_id, username, is_ga=True)
        await message.answer(
            "👑 <b>Вы стали ГЛАВНЫМ АДМИНОМ!</b>\n\n"
            "Доступные команды:\n"
            "/ga - панель главного админа\n"
            "/set_admin_password - изменить пароль админов\n"
            "/set_ga_password - изменить пароль ГА\n"
            "/remove_admin - удалить админа\n"
            "/admin - обычная админка",
            parse_mode='HTML',
            reply_markup=get_ga_keyboard()
        )
    else:
        await message.answer("❌ <b>Неверный пароль!</b>", parse_mode='HTML')


@dp.message(Command("remove_admin"))
async def cmd_remove_admin(message: types.Message, state: FSMContext):
    user_id = message.from_user.id

    if not await is_ga(user_id):
        await message.answer("❌ <b>Доступ запрещен!</b> Эта команда только для главного админа.", parse_mode='HTML')
        return

    args = message.text.split()
    if len(args) >= 2:
        try:
            admin_id = int(args[1])
            await process_remove_admin(admin_id, message)
        except ValueError:
            await message.answer("❌ <b>Неверный ID!</b> Введите числовой ID:", parse_mode='HTML')
    else:
        await message.answer(
            "🗑️ <b>Удаление администратора</b>\n\n"
            "Введите ID админа для удаления:",
            parse_mode='HTML',
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(GAStates.waiting_admin_to_remove)


@dp.message(GAStates.waiting_admin_to_remove)
async def process_admin_to_remove(message: types.Message, state: FSMContext):
    try:
        admin_id = int(message.text.strip())
        await process_remove_admin(admin_id, message)
        await state.clear()
    except ValueError:
        await message.answer("❌ <b>Неверный ID!</b> Введите числовой ID:", parse_mode='HTML')


async def process_remove_admin(admin_id: int, message: types.Message):
    admin = await get_admin(admin_id)

    if not admin:
        await message.answer(f"❌ <b>Админ с ID {admin_id} не найден!</b>", parse_mode='HTML')
        return

    if admin.is_ga:
        await message.answer(f"❌ <b>Нельзя удалить главного админа!</b>", parse_mode='HTML')
        return

    success = await remove_admin(admin_id)
    if success:
        await message.answer(f"✅ <b>Админ с ID {admin_id} удален!</b>", parse_mode='HTML')

        try:
            await bot.send_message(
                admin_id,
                "⚠️ <b>Вы лишены прав администратора!</b>\n\n"
                "Ваши права администратора были отозваны главным админом.",
                parse_mode='HTML'
            )
        except:
            pass
    else:
        await message.answer(f"❌ <b>Ошибка при удалении админа!</b>", parse_mode='HTML')


@dp.message(Command("ga"))
async def cmd_ga(message: types.Message):
    user_id = message.from_user.id

    if not await is_ga(user_id):
        await message.answer("❌ <b>Доступ запрещен!</b>", parse_mode='HTML')
        return

    admin_password = await get_config('ADMIN_PASSWORD')
    ga_password = await get_config('GA_PASSWORD')

    await message.answer(
        f"👑 <b>Панель ГЛАВНОГО АДМИНА</b>\n\n"
        f"🔑 <b>Пароль админов:</b> <code>{admin_password}</code>\n"
        f"👑 <b>Пароль ГА:</b> <code>{ga_password}</code>\n\n"
        f"Выберите действие:",
        parse_mode='HTML',
        reply_markup=get_ga_keyboard()
    )


@dp.message(Command("admin"))
async def cmd_admin(message: types.Message):
    user_id = message.from_user.id
    admin = await get_admin(user_id)

    if admin:
        keyboard = get_ga_keyboard() if admin.is_ga else get_admin_keyboard()
        text = "👑 <b>Панель ГЛАВНОГО АДМИНА</b>\n\n" if admin.is_ga else "⚙️ <b>Панель администратора</b>\n\n"

        await message.answer(
            text + "Выберите действие:",
            parse_mode='HTML',
            reply_markup=keyboard
        )
    else:
        await message.answer("❌ <b>Доступ запрещен!</b>", parse_mode='HTML')


@dp.callback_query(F.data == 'back_admin_ponel')
async def back_admin_ponel(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    admin = await get_admin(user_id)

    if not admin:
        await callback.answer("❌ Доступ запрещен!")
        return

    keyboard = get_ga_keyboard() if admin.is_ga else get_admin_keyboard()
    text = "👑 <b>Панель ГЛАВНОГО АДМИНА</b>\n\n" if admin.is_ga else "<b>Панель администратора</b>\n\n"

    await callback.message.edit_text(
        text + "Выберите действие:",
        parse_mode='HTML',
        reply_markup=keyboard
    )


@dp.callback_query(F.data == "admin_stats")
async def callback_admin_stats(callback: types.CallbackQuery):
    admin = await get_admin(callback.from_user.id)
    if not admin:
        await callback.answer("❌ Доступ запрещен!")
        return

    users = await get_all_users()
    admins_list = await get_all_admins()

    active_users = sum(1 for user in users if user.check_subscription())
    total_users = len(users)
    total_admins = len(admins_list)
    total_ga = sum(1 for admin in admins_list if admin.is_ga)
    total_regular_admins = total_admins - total_ga

    text = (
        f"📊 <b>Статистика бота</b>\n\n"
        f"👥 Всего пользователей: {total_users}\n"
        f"✅ Активных подписок: {active_users}\n"
        f"❌ Без подписки: {total_users - active_users}\n\n"
        f"👑 Главных админов: {total_ga}\n"
        f"⭐ Обычных админов: {total_regular_admins}\n"
        f"📝 Всего админов: {total_admins}\n\n"
        f"<i>Обновлено: {datetime.now().strftime('%d.%m.%Y %H:%M')}</i>"
    )

    await callback.message.edit_text(text, parse_mode='HTML', reply_markup=get_back_admin_ponel())
    await callback.answer()


@dp.callback_query(F.data == "admin_users")
async def callback_admin_users(callback: types.CallbackQuery):
    admin = await get_admin(callback.from_user.id)
    if not admin:
        await callback.answer("❌ Доступ запрещен!")
        return

    users = await get_all_users()

    if not users:
        await callback.message.edit_text("📭 <b>Нет пользователей</b>", parse_mode='HTML',
                                         reply_markup=get_back_admin_ponel())
        await callback.answer()
        return

    text = "👥 <b>Список пользователей:</b>\n\n"
    for i, user in enumerate(users[:50], 1):
        status = "✅" if user.check_subscription() else "❌"
        admin_symbol = await get_admin_status_symbol(user.telegram_id)

        sub_info = ""
        if user.subscription_end:
            days_left = (user.subscription_end - datetime.now()).days
            if days_left > 0:
                sub_info = f" ({days_left}д)"

        text += f"{i}. ID: {user.telegram_id} {status}{sub_info} {admin_symbol}\n"

    if len(users) > 50:
        text += f"\n... и еще {len(users) - 50} пользователей"

    await callback.message.edit_text(text, parse_mode='HTML', reply_markup=get_back_admin_ponel())
    await callback.answer()


@dp.callback_query(F.data == "admin_give_sub")
async def callback_admin_give_sub(callback: types.CallbackQuery, state: FSMContext):
    admin = await get_admin(callback.from_user.id)
    if not admin:
        await callback.answer("❌ Доступ запрещен!")
        return

    await callback.message.edit_text(
        "🎫 <b>Выдача подписки</b>\n\n"
        "Введите ID пользователя:",
        parse_mode='HTML',
        reply_markup=get_back_admin_ponel()
    )
    await state.set_state(AdminStates.waiting_user_id)
    await callback.answer()


@dp.callback_query(F.data == "admin_manage_admins")
async def callback_admin_manage_admins(callback: types.CallbackQuery):
    admin = await get_admin(callback.from_user.id)
    if not admin or not admin.is_ga:
        await callback.answer("❌ Доступ запрещен!")
        return

    admins = await get_all_admins()

    text = "👑 <b>Список администраторов</b>\n\n"

    for i, admin_user in enumerate(admins, 1):
        status = "👑 ГА" if admin_user.is_ga else "⭐ Админ"
        text += f"{i}. ID: {admin_user.telegram_id} - {status}\n"
        if admin_user.username:
            text += f"   👤 @{admin_user.username}\n"

    text += "\n🗑️ <b>Удалить админа:</b> /remove_admin [ID]\n"
    text += "🔑 <b>Изменить пароль админов:</b> /set_admin_password [пароль]\n"
    text += "👑 <b>Изменить пароль ГА:</b> /set_ga_password [пароль]"

    await callback.message.edit_text(text, parse_mode='HTML', reply_markup=get_back_admin_ponel())
    await callback.answer()


@dp.message(AdminStates.waiting_user_id)
async def process_admin_user_id(message: types.Message, state: FSMContext):
    try:
        user_id = int(message.text.strip())
        await state.update_data(user_id=user_id)

        await message.answer(
            f"✅ <b>Пользователь найден:</b> {user_id}\n\n"
            "Выберите тип подписки:",
            parse_mode='HTML',
            reply_markup=get_subscription_types_keyboard()
        )
        await state.set_state(AdminStates.waiting_subscription_type)
    except ValueError:
        await message.answer("❌ <b>Неверный ID!</b>\nВведите числовой ID:\n", parse_mode='HTML',
                             reply_markup=get_cancel_keyboard())


@dp.callback_query(AdminStates.waiting_subscription_type)
async def process_subscription_type(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user_id = data.get('user_id')

    if callback.data.startswith("sub_"):
        sub_type = callback.data.replace("sub_", "")

        days_map = {
            "1": (1, "1 день"),
            "5": (5, "5 дней"),
            "7": (7, "7 дней"),
            "30": (30, "30 дней"),
            "forever": (0, "навсегда")
        }

        if sub_type in days_map:
            days, desc = days_map[sub_type]
            await update_subscription(user_id, days, sub_type if sub_type != "forever" else "forever")

            await callback.message.edit_text(
                f"✅ <b>Подписка выдана!</b>\n\n"
                f"👤 Пользователь: {user_id}\n"
                f"🎫 Тип: {desc}",
                parse_mode='HTML',
                reply_markup=get_admin_keyboard()
            )

            try:
                await bot.send_message(
                    user_id,
                    f"🎉 <b>Вам выдана подписка!</b>\n\n"
                    f"Тип: {desc}\n"
                    f"Теперь у вас есть доступ ко всем функциям бота!",
                    parse_mode='HTML'
                )
            except:
                pass

            await state.clear()

    await callback.answer()


# ОБРАБОТКА ТЕКСТА
@dp.message(F.text & ~F.text.startswith('/'))
async def handle_text(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    text = message.text.strip()

    current_state = await state.get_state()

    if current_state == SettingsStates.waiting_mailing_time.state:
        try:
            hours = float(text)
            if 0.1 <= hours <= 24:
                await update_mailing_settings(user_id, mailing_hours=hours)
                await message.answer(
                    f"✅ <b>Время рассылки установлено:</b> {hours} часов",
                    parse_mode='HTML',
                    reply_markup=get_back_to_settings_keyboard()
                )
                await state.clear()
            else:
                await message.answer("❌ <b>Введите число от 0.1 до 24 часов</b>", parse_mode='HTML',
                                     reply_markup=get_cancel_keyboard())
        except ValueError:
            await message.answer("❌ <b>Введите число!</b>", parse_mode='HTML', reply_markup=get_cancel_keyboard())
        return

    elif current_state == SettingsStates.waiting_delay.state:
        try:
            minutes = float(text)
            if 0.1 <= minutes <= 60:
                await update_mailing_settings(user_id, delay_minutes=minutes)
                await message.answer(
                    f"✅ <b>Задержка установлена:</b> {minutes} минут",
                    parse_mode='HTML',
                    reply_markup=get_back_to_settings_keyboard()
                )
                await state.clear()
            else:
                await message.answer("❌ <b>Введите число от 0.1 до 60 минут</b>", parse_mode='HTML',
                                     reply_markup=get_cancel_keyboard())
        except ValueError:
            await message.answer("❌ <b>Введите число!</b>", parse_mode='HTML', reply_markup=get_cancel_keyboard())
        return

    elif current_state == "waiting_usernames":
        if not await check_subscription(user_id):
            await message.answer(
                "❌ <b>Действие недоступно!</b>\n\n"
                "Для использования этой функции нужна активная подписка.\n"
                "Обратитесь к администратору.",
                parse_mode='HTML',
                reply_markup=get_back_keyboard()
            )
            await state.clear()
            return

        user = await get_user(user_id)
        if not user or not user.session_string:
            await message.answer(
                "❌ <b>Сначала авторизуйтесь!</b>\n\n"
                "Нажмите кнопку '🔐 Авторизация'",
                parse_mode='HTML',
                reply_markup=get_back_keyboard()
            )
            await state.clear()
            return

        usernames = [u.strip().lstrip('@') for u in text.split(',') if u.strip()]
        if len(usernames) > 1000:
            await message.answer("❌ <b>Слишком много юзернеймов!</b>\nМаксимум 1000", parse_mode='HTML',
                                 reply_markup=await get_user_keyboard(user_id))
            return

        if usernames:
            await update_user_usernames(user_id, usernames)
            await message.answer(
                f"✅ <b>{len(usernames)} юзернеймов сохранено</b>\n\n"
                f"Теперь введите текст сообщения:",
                parse_mode='HTML',
                reply_markup=await get_user_keyboard(user_id)
            )
            await state.clear()
        else:
            await message.answer("❌ <b>Не найдено юзернеймов</b>\nПопробуйте еще раз:", parse_mode='HTML',
                                 reply_markup=await get_user_keyboard(user_id))
        return

    elif current_state == "waiting_message":
        if not await check_subscription(user_id):
            await message.answer(
                "❌ <b>Действие недоступно!</b>\n\n"
                "Для использования этой функции нужна активная подписка.\n"
                "Обратитесь к администратору.",
                parse_mode='HTML',
                reply_markup=get_back_keyboard()
            )
            await state.clear()
            return

        user = await get_user(user_id)
        if not user or not user.get_usernames():
            await message.answer(
                "❌ <b>Сначала укажите юзернеймы!</b>\n\n"
                "Нажмите кнопку '👥 Получатели'",
                parse_mode='HTML',
                reply_markup=get_back_keyboard()
            )
            await state.clear()
            return

        if len(text) > 4000:
            await message.answer("❌ <b>Текст слишком длинный!</b>\nМаксимум 4000 символов", parse_mode='HTML',
                                 reply_markup=await get_user_keyboard(user_id))
            return

        await update_user_message(user_id, text)
        await message.answer(
            "✅ <b>Текст сохранен</b>\n\n"
            "Проверьте готовность и запускайте рассылку!",
            parse_mode='HTML',
            reply_markup=await get_user_keyboard(user_id)
        )
        await state.clear()
        return

    elif current_state == AuthStates.waiting_phone.state:
        await process_phone(message, state)
    elif current_state == AuthStates.waiting_code.state:
        await process_code(message, state)

    else:
        user = await get_user(user_id)
        if not user:
            await message.answer("❌ <b>Сначала авторизуйтесь!</b>", parse_mode='HTML',
                                 reply_markup=await get_user_keyboard(user_id))
            return

        if user.session_string and (not user.get_usernames() or len(user.get_usernames()) == 0):
            if not await check_subscription(user_id):
                await message.answer(
                    "❌ <b>Действие недоступно!</b>\n\n"
                    "Для использования этой функции нужна активная подписка.\n"
                    "Обратитесь к администратору.",
                    parse_mode='HTML',
                    reply_markup=get_back_keyboard()
                )
                return

            usernames = [u.strip().lstrip('@') for u in text.split(',') if u.strip()]
            if len(usernames) > 1000:
                await message.answer("❌ <b>Слишком много юзернеймов!</b>\nМаксимум 1000", parse_mode='HTML',
                                     reply_markup=await get_user_keyboard(user_id))
                return
            if usernames:
                await update_user_usernames(user_id, usernames)
                await message.answer(
                    f"✅ <b>{len(usernames)} юзернеймов сохранено</b>\n\n"
                    f"Теперь введите текст сообщения:",
                    parse_mode='HTML',
                    reply_markup=await get_user_keyboard(user_id)
                )
            else:
                await message.answer("❌ <b>Не найдено юзернеймов</b>\nПопробуйте еще раз:", parse_mode='HTML',
                                     reply_markup=await get_user_keyboard(user_id))
        elif user.get_usernames() and len(user.get_usernames()) > 0 and not user.message:
            if not await check_subscription(user_id):
                await message.answer(
                    "❌ <b>Действие недоступно!</b>\n\n"
                    "Для использования этой функции нужна активная подписка.\n"
                    "Обратитесь к администратору.",
                    parse_mode='HTML',
                    reply_markup=get_back_keyboard()
                )
                return

            if len(text) > 4000:
                await message.answer("❌ <b>Текст слишком длинный!</b>\nМаксимум 4000 символов", parse_mode='HTML',
                                     reply_markup=await get_user_keyboard(user_id))
                return
            await update_user_message(user_id, text)
            await message.answer(
                "✅ <b>Текст сохранен</b>\n\n"
                "Проверьте готовность и запускайте рассылку!",
                parse_mode='HTML',
                reply_markup=await get_user_keyboard(user_id)
            )
        else:
            await message.answer(
                "ℹ️ <b>Используйте кнопки меню для навигации</b>",
                parse_mode='HTML',
                reply_markup=await get_user_keyboard(user_id)
            )


async def run_mailing(user_id, user):
    session_string = user.session_string
    usernames = user.get_usernames()
    message_text = validate_html(user.message)

    MAILING_SECONDS = user.get_mailing_seconds()
    DELAY_SECONDS = user.get_delay_seconds()

    try:
        device = get_random_device()
        client = TelegramClient(
            StringSession(session_string),
            SYSTEM_API_ID,
            SYSTEM_API_HASH,
            device_model=device["device_model"],
            system_version=device["system_version"]
        )
        await client.connect()
        if not await client.is_user_authorized():
            await bot.send_message(user_id, "❌ <b>Сессия недействительна</b>", parse_mode='HTML',
                                   reply_markup=await get_user_keyboard(user_id))
            mailing_active[user_id] = False
            return
        me = await client.get_me()
        await bot.send_message(user_id, f"✅ <b>Авторизован как:</b> {me.first_name or me.username}", parse_mode='HTML')
        start_time = time.time()
        total_sent = 0
        error_count = 0
        random.shuffle(usernames)
        while mailing_active.get(user_id, False):
            if time.time() - start_time > MAILING_SECONDS:
                await bot.send_message(user_id, f"⏰ <b>Время вышло!</b> ({user.mailing_hours} ч)", parse_mode='HTML',
                                       reply_markup=await get_user_keyboard(user_id))
                break
            for username in usernames:
                if not mailing_active.get(user_id, False):
                    break
                try:
                    await client.send_message(username, message_text, parse_mode='html')
                    total_sent += 1
                    if total_sent % 10 == 0:
                        elapsed = time.time() - start_time
                        remaining = max(0, MAILING_SECONDS - elapsed)
                        hours = int(remaining // 3600)
                        mins = int((remaining % 3600) // 60)
                        await bot.send_message(
                            user_id,
                            f"📨 <b>Отправлено:</b> {total_sent}\n"
                            f"⏰ <b>Осталось:</b> {hours}ч {mins}м",
                            parse_mode='HTML'
                        )
                    await asyncio.sleep(DELAY_SECONDS)
                except errors.FloodWaitError as e:
                    wait_time = e.seconds
                    await bot.send_message(user_id, f"⏰ <b>Флуд! Ждём {wait_time} сек</b>", parse_mode='HTML')
                    await asyncio.sleep(wait_time)
                    continue
                except Exception as e:
                    error_count += 1
                    error_msg = str(e)
                    if "Could not find" in error_msg:
                        pass
                    elif "Too Many Requests" in error_msg:
                        await bot.send_message(user_id, "⚡ <b>Слишком много запросов!</b> Ждём 30 сек",
                                               parse_mode='HTML')
                        await asyncio.sleep(30)
                    elif "Flood control exceeded" in error_msg:
                        await bot.send_message(user_id, "⏰ <b>Превышен контроль флуда!</b> Ждём 60 сек",
                                               parse_mode='HTML')
                        await asyncio.sleep(60)
                    elif error_count > 5:
                        await bot.send_message(user_id, f"⚠️ <b>Много ошибок ({error_count})</b>", parse_mode='HTML')
                    continue
        await bot.send_message(
            user_id,
            f"🎉 <b>Рассылка завершена!</b>\n\n"
            f"📨 <b>Отправлено:</b> {total_sent}\n"
            f"⚠️ <b>Ошибок:</b> {error_count}",
            parse_mode='HTML',
            reply_markup=await get_user_keyboard(user_id)
        )
    except Exception as e:
        await bot.send_message(user_id, f"<b>Критическая ошибка:</b> {str(e)[:200]}", parse_mode='HTML',
                               reply_markup=await get_user_keyboard(user_id))
    finally:
        try:
            if 'client' in locals() and client.is_connected():
                await client.disconnect()
        except:
            pass
        if user_id in mailing_active:
            mailing_active[user_id] = False


async def main():
    await init_db()
    
    # 1. СНАЧАЛА запускаем фейковый сервер
    fake_server_task = None
    if 'run_fake_server' in dir():
        fake_server_task = asyncio.create_task(run_fake_server())
        print("🌐 Запускаем фейковый сервер...")
        # Даем серверу время запуститься
        await asyncio.sleep(2)
    
    print("✅ Фейковый сервер должен быть запущен")
    
    # 2. Пробуем запустить бота
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await asyncio.sleep(1)
        
        print("✅ Бот запускается...")
        await dp.start_polling(bot)
    except Exception as e:
        print(f"❌ Ошибка бота: {e}")
        print("🌐 Фейковый сервер продолжает работать на порту")
        # Держим процесс живым, даже если бот упал
        while True:
            await asyncio.sleep(60)
            print("🌐 Фейковый сервер все еще работает...")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n❗ Бот отключен")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        # Не даем процессу умереть
        import time
        while True:
            time.sleep(60)
            print("⚠️ Процесс поддерживается для фейкового сервера")
