from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Профиль", callback_data="profile")],
        [InlineKeyboardButton(text="🔐 Авторизация", callback_data="auth")],
        [InlineKeyboardButton(text="👥 Получатели", callback_data="usernames"),
         InlineKeyboardButton(text="📝 Текст", callback_data="text")],
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings")],
        [InlineKeyboardButton(text="📊 Проверить", callback_data="check"),
         InlineKeyboardButton(text="🚀 Запустить", callback_data="go")],
        [InlineKeyboardButton(text="🛑 Остановить", callback_data="stop"),
         InlineKeyboardButton(text="🗑️ Очистить", callback_data="clear_menu")]
    ])


def get_start_keyboard():
    """Клавиатура при старте (без помощи)"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Профиль", callback_data="profile")]
    ])


def get_no_subscription_keyboard():
    """Клавиатура для пользователей без подписки"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Профиль", callback_data="profile")]
    ])


def get_clear_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑️ ВСЁ", callback_data="clear_all"),
         InlineKeyboardButton(text="🔐 Сессию", callback_data="clear_session")],
        [InlineKeyboardButton(text="👥 Юзернеймы", callback_data="clear_usernames"),
         InlineKeyboardButton(text="📝 Текст", callback_data="clear_message")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")]
    ])


def get_cancel_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]
    ])


def get_back_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")]
    ])


def get_back_to_settings_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад к настройкам", callback_data="settings")]
    ])


def get_mailing_control_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛑 Остановить рассылку", callback_data="stop_mailing")],
        [InlineKeyboardButton(text="◀️ В главное меню", callback_data="back_main")]
    ])


def get_confirmation_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да, удалить", callback_data="confirm_clear"),
            InlineKeyboardButton(text="❌ Нет, отмена", callback_data="cancel_clear")
        ]
    ])


def get_yes_no_keyboard(yes_data="yes", no_data="no"):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да", callback_data=yes_data),
            InlineKeyboardButton(text="❌ Нет", callback_data=no_data)
        ]
    ])


def get_auth_options_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Использовать текущую", callback_data="use_current"),
            InlineKeyboardButton(text="🔄 Авторизовать новый", callback_data="auth_new")
        ],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]
    ])


def get_ready_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Запустить рассылку", callback_data="go")],
        [InlineKeyboardButton(text="◀️ В главное меню", callback_data="back_main")]
    ])


def get_not_ready_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔐 Авторизация", callback_data="auth")],
        [InlineKeyboardButton(text="👥 Получатели", callback_data="usernames")],
        [InlineKeyboardButton(text="📝 Текст", callback_data="text")],
        [InlineKeyboardButton(text="◀️ В главное меню", callback_data="back_main")]
    ])


def get_settings_keyboard():
    """Клавиатура настроек"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⏱ Время рассылки", callback_data="set_mailing_time"),
            InlineKeyboardButton(text="⏳ Задержка", callback_data="set_delay")
        ],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")]
    ])


def get_mailing_time_keyboard():
    """Клавиатура для выбора времени рассылки"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="1 час", callback_data="time_1"),
            InlineKeyboardButton(text="3 часа", callback_data="time_3"),
            InlineKeyboardButton(text="5 часов", callback_data="time_5")
        ],
        [
            InlineKeyboardButton(text="8 часов", callback_data="time_8"),
            InlineKeyboardButton(text="12 часов", callback_data="time_12"),
            InlineKeyboardButton(text="24 часа", callback_data="time_24")
        ],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="settings")]
    ])


def get_cancel_only_keyboard():
    """Клавиатура только с кнопкой отмена"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]
    ])

def get_admin_input_keyboard():
    """Клавиатура для ввода данных в админке"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]
    ])

def get_settings_input_keyboard():
    """Клавиатура для ввода настроек"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]
    ])

def get_delay_keyboard():
    """Клавиатура для выбора задержки"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="1 мин", callback_data="delay_1"),
            InlineKeyboardButton(text="3 мин", callback_data="delay_3"),
            InlineKeyboardButton(text="5 мин", callback_data="delay_5")
        ],
        [
            InlineKeyboardButton(text="10 мин", callback_data="delay_10"),
            InlineKeyboardButton(text="15 мин", callback_data="delay_15"),
            InlineKeyboardButton(text="30 мин", callback_data="delay_30")
        ],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="settings")]
    ])


def get_admin_keyboard():
    """Клавиатура администратора"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users")],
        [InlineKeyboardButton(text="🎫 Выдать подписку", callback_data="admin_give_sub")],
        [InlineKeyboardButton(text="◀️ В главное меню", callback_data="back_main")]
    ])


def get_ga_keyboard():
    """Клавиатура главного админа"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users")],
        [InlineKeyboardButton(text="🎫 Выдать подписку", callback_data="admin_give_sub")],
        [InlineKeyboardButton(text="👑 Управление админами", callback_data="admin_manage_admins")],
        [InlineKeyboardButton(text="◀️ В главное меню", callback_data="back_main")]
    ])


def get_subscription_types_keyboard():
    """Клавиатура для выбора типа подписки"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="1 день", callback_data="sub_1"),
            InlineKeyboardButton(text="5 дней", callback_data="sub_5"),
            InlineKeyboardButton(text="7 дней", callback_data="sub_7")
        ],
        [
            InlineKeyboardButton(text="30 дней", callback_data="sub_30"),
            InlineKeyboardButton(text="Навсегда", callback_data="sub_forever")
        ],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]
    ])


def get_error_keyboard(reason: str = "нет подписки"):
    """Клавиатура с сообщением об ошибке"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ В главное меню", callback_data="back_main")]
    ])


def get_profile_keyboard():
    """Клавиатура для профиля"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ В главное меню", callback_data="back_main")]
    ])


def get_back_admin_ponel():
    """Клавиатура для бэка"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_admin_ponel")]
    ])
