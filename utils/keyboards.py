# utils/keyboards.py
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from config.settings import EXPENSE_CATEGORIES, INCOME_CATEGORIES

def get_main_menu() -> ReplyKeyboardMarkup:
    """Главное меню: доход, расход, отчеты, профиль, история, бюджет, статистика, поиск, графики."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📥 Доход"),
                KeyboardButton(text="📤 Расход")
            ],
            [
                KeyboardButton(text="📊 Сегодня"),
                KeyboardButton(text="📆 Неделя"),
                KeyboardButton(text="🗓 Месяц")
            ],
            [
                KeyboardButton(text="👤 Профиль"),
                KeyboardButton(text="📋 История"),
                KeyboardButton(text="💰 Бюджет")
            ],
            [
                KeyboardButton(text="📊 Статистика"),
                KeyboardButton(text="🔍 Поиск"),
                KeyboardButton(text="📈 Графики")
            ],
            [
                KeyboardButton(text="🎯 Цели")
            ],
            [
                KeyboardButton(text="↩ Отмена")
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )

def get_payment_method_keyboard() -> ReplyKeyboardMarkup:
    """Выбор способа платежа."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="💵 Наличные"),
                KeyboardButton(text="💳 Карта")
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def get_expense_categories_keyboard() -> InlineKeyboardMarkup:
    """Выбор категории расхода."""
    keyboard = []
    for i in range(0, len(EXPENSE_CATEGORIES), 2):
        row = []
        for j in range(2):
            if i + j < len(EXPENSE_CATEGORIES):
                cat = EXPENSE_CATEGORIES[i + j]
                row.append(InlineKeyboardButton(text=cat, callback_data=f"exp_cat_{i+j}"))
        keyboard.append(row)
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_income_categories_keyboard() -> InlineKeyboardMarkup:
    """Выбор категории дохода."""
    keyboard = []
    for i in range(0, len(INCOME_CATEGORIES), 2):
        row = []
        for j in range(2):
            if i + j < len(INCOME_CATEGORIES):
                cat = INCOME_CATEGORIES[i + j]
                row.append(InlineKeyboardButton(text=cat, callback_data=f"inc_cat_{i+j}"))
        keyboard.append(row)
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_payment_method_inline_keyboard() -> InlineKeyboardMarkup:
    """Выбор способа платежа через Inline кнопки (для edit_text)."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💵 Наличные", callback_data="method_cash"),
            InlineKeyboardButton(text="💳 Карта", callback_data="method_card")
        ]
    ])

def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Кнопка отмены."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="↩ Отмена")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )


def get_goals_list_keyboard(goals: list) -> InlineKeyboardMarkup:
    """Кнопки для списка целей: пополнить / удалить."""
    keyboard = []
    for g in goals[:5]:
        keyboard.append([
            InlineKeyboardButton(text=f"➕ {g['name'][:15]}", callback_data=f"goal_add_{g['id']}"),
            InlineKeyboardButton(text="🗑", callback_data=f"goal_del_{g['id']}"),
        ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_goal_actions_keyboard(goal_id: int) -> InlineKeyboardMarkup:
    """Кнопки действий с целью."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Пополнить", callback_data=f"goal_add_{goal_id}"),
            InlineKeyboardButton(text="🗑 Удалить", callback_data=f"goal_del_{goal_id}"),
        ]
    ])