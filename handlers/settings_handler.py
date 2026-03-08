# handlers/settings_handler.py
"""Настройки: часовой пояс, напоминания, лимиты, регулярные расходы."""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import aiosqlite
from config.settings import DB_PATH, SUPPORTED_TIMEZONES, EXPENSE_CATEGORIES, INCOME_CATEGORIES
from services.user_service import create_or_get_user
from services.reminder_service import set_reminder, delete_reminder, get_reminder
from services.category_limit_service import set_category_limit, get_category_limits, delete_category_limit
from services.recurring_service import create_recurring, get_recurring_list, delete_recurring
from utils.keyboards import get_main_menu, get_cancel_keyboard
from utils.validators import validate_amount
from utils.report_formatter import format_money

router = Router()
logger = logging.getLogger(__name__)


class TimezoneFlow(StatesGroup):
    choosing = State()


class ReminderFlow(StatesGroup):
    waiting_for_time = State()


class LimitFlow(StatesGroup):
    waiting_for_category = State()
    waiting_for_amount = State()


class RecurringFlow(StatesGroup):
    waiting_for_name = State()
    waiting_for_amount = State()
    waiting_for_type = State()
    waiting_for_category = State()
    waiting_for_method = State()
    waiting_for_day = State()


# ─────────────────────────── ЧАСОВОЙ ПОЯС ───────────────────────────

@router.message(F.text == "/timezone")
async def cmd_timezone(message: Message, state: FSMContext):
    user = await create_or_get_user(message.from_user.id)
    if not user["id"]:        await message.answer("❌ Сначала /start")
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=city, callback_data=f"tz_{tz}")]
        for city, tz in SUPPORTED_TIMEZONES.items()
    ])
    await message.answer(
        "🌍 <b>Выберите ваш часовой пояс:</b>",
        parse_mode="HTML", reply_markup=keyboard
    )
    await state.set_state(TimezoneFlow.choosing)


@router.callback_query(TimezoneFlow.choosing, F.data.startswith("tz_"))
async def timezone_chosen(callback: CallbackQuery, state: FSMContext):
    tz = callback.data[3:]
    user = await create_or_get_user(callback.from_user.id)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET timezone = ? WHERE id = ?", (tz, user["id"]))
        await db.commit()
    await state.clear()
    city = next((c for c, t in SUPPORTED_TIMEZONES.items() if t == tz), tz)
    await callback.message.edit_text(
        f"✅ Часовой пояс установлен: <b>{city}</b> ({tz})\n\n"
        "Теперь время в отчётах будет вашим локальным.",
        parse_mode="HTML"
    )
    await callback.answer()


# ─────────────────────────── НАПОМИНАНИЯ ───────────────────────────

@router.message(F.text == "/reminder")
async def cmd_reminder(message: Message, state: FSMContext):
    user = await create_or_get_user(message.from_user.id)
    if not user["id"]:
        await message.answer("❌ Сначала /start")
        return

    existing = await get_reminder(user["id"])
    text = "🔔 <b>Напоминания</b>\n\n"
    if existing:
        text += f"Текущее напоминание: <b>{existing['time']}</b>\n\n"
    text += (
        "Введите время напоминания в формате <code>ЧЧ:ММ</code>\n"
        "Например: <code>21:00</code>\n\n"
        "Или отправьте <code>выкл</code> чтобы отключить"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=get_cancel_keyboard())    await state.set_state(ReminderFlow.waiting_for_time)


@router.message(ReminderFlow.waiting_for_time)
async def process_reminder_time(message: Message, state: FSMContext):
    if message.text == "↩ Отмена":
        await state.clear()
        await message.answer("❌ Отменено", reply_markup=get_main_menu())
        return

    user = await create_or_get_user(message.from_user.id)
    text = message.text.strip().lower()

    if text in ("выкл", "отключить", "off", "0"):
        await delete_reminder(user["id"])
        await state.clear()
        await message.answer("🔕 Напоминания отключены", reply_markup=get_main_menu())
        return

    import re
    if not re.match(r'^\d{1,2}:\d{2}$', text):
        await message.answer(
            "❌ Неверный формат. Введите время как <code>21:00</code>",
            parse_mode="HTML", reply_markup=get_cancel_keyboard()
        )
        return

    h, m = map(int, text.split(':'))
    if not (0 <= h <= 23 and 0 <= m <= 59):
        await message.answer("❌ Неверное время", reply_markup=get_cancel_keyboard())
        return

    reminder_time = f"{h:02d}:{m:02d}"
    await set_reminder(user["id"], message.from_user.id, reminder_time)
    await state.clear()
    await message.answer(
        f"✅ Напоминание установлено на <b>{reminder_time}</b> ежедневно",
        parse_mode="HTML", reply_markup=get_main_menu()
    )


# ─────────────────────────── ЛИМИТЫ ───────────────────────────

@router.message(F.text == "/limits")
async def cmd_limits(message: Message):
    user = await create_or_get_user(message.from_user.id)
    if not user["id"]:
        await message.answer("❌ Сначала /start")
        return
    limits = await get_category_limits(user["id"])
    if not limits:
        text = (
            "📊 <b>Лимиты по категориям</b>\n\n"
            "У вас пока нет лимитов.\n\n"
            "Используйте /setlimit чтобы установить лимит расходов\n"
            "на конкретную категорию за месяц."
        )
    else:
        text = "📊 <b>Лимиты по категориям</b>\n\n"
        for lim in limits:
            text += f"{lim['category']}: {format_money(lim['limit'])}/мес\n"
        text += "\n/setlimit — установить | /dellimit — удалить"

    await message.answer(text, parse_mode="HTML", reply_markup=get_main_menu())


@router.message(F.text == "/setlimit")
async def cmd_setlimit(message: Message, state: FSMContext):
    user = await create_or_get_user(message.from_user.id)
    if not user["id"]:
        await message.answer("❌ Сначала /start")
        return

    all_cats = EXPENSE_CATEGORIES
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=cat, callback_data=f"lim_cat_{i}")]
        for i, cat in enumerate(all_cats)
    ])
    await message.answer(
        "📂 <b>Выберите категорию для лимита:</b>",
        parse_mode="HTML", reply_markup=keyboard
    )
    await state.set_state(LimitFlow.waiting_for_category)


@router.callback_query(LimitFlow.waiting_for_category, F.data.startswith("lim_cat_"))
async def limit_category_chosen(callback: CallbackQuery, state: FSMContext):
    idx = int(callback.data.split("_")[-1])
    category = EXPENSE_CATEGORIES[idx]
    await state.update_data(category=category)
    await callback.message.edit_text(
        f"💰 Введите месячный лимит для <b>{category}</b> в рублях:",
        parse_mode="HTML"
    )
    await state.set_state(LimitFlow.waiting_for_amount)
    await callback.answer()


@router.message(LimitFlow.waiting_for_amount)async def limit_amount_entered(message: Message, state: FSMContext):
    if message.text == "↩ Отмена":
        await state.clear()
        await message.answer("❌ Отменено", reply_markup=get_main_menu())
        return

    if not validate_amount(message.text):
        await message.answer("❌ Введите корректную сумму", reply_markup=get_cancel_keyboard())
        return

    data = await state.get_data()
    user = await create_or_get_user(message.from_user.id)
    amount = float(message.text.replace(',', '.'))

    await set_category_limit(user["id"], data["category"], amount)
    await state.clear()
    await message.answer(
        f"✅ Лимит установлен!\n"
        f"{data['category']}: {format_money(amount)}/мес",
        reply_markup=get_main_menu()
    )


@router.message(F.text == "/dellimit")
async def cmd_dellimit(message: Message):
    user = await create_or_get_user(message.from_user.id)
    if not user["id"]:
        await message.answer("❌ Сначала /start")
        return

    limits = await get_category_limits(user["id"])
    if not limits:
        await message.answer("У вас нет установленных лимитов.", reply_markup=get_main_menu())
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"🗑 {lim['category']} ({format_money(lim['limit'])})",
            callback_data=f"del_lim_{lim['category']}"
        )]
        for lim in limits
    ])
    await message.answer("Выберите лимит для удаления:", reply_markup=keyboard)


@router.callback_query(F.data.startswith("del_lim_"))
async def delete_limit_callback(callback: CallbackQuery):
    category = callback.data[8:]
    user = await create_or_get_user(callback.from_user.id)
    await delete_category_limit(user["id"], category)    await callback.message.edit_text(f"✅ Лимит для {category} удалён")
    await callback.answer()


# ─────────────────────────── РЕГУЛЯРНЫЕ ───────────────────────────

@router.message(F.text == "/recurring")
async def cmd_recurring(message: Message):
    user = await create_or_get_user(message.from_user.id)
    if not user["id"]:
        await message.answer("❌ Сначала /start")
        return

    items = await get_recurring_list(user["id"])
    if not items:
        text = (
            "🔄 <b>Регулярные транзакции</b>\n\n"
            "У вас пока нет регулярных операций.\n\n"
            "Примеры: аренда каждое 1-е число, зарплата 10-го...\n\n"
            "Используйте /addrecurring чтобы добавить"
        )
    else:
        text = "🔄 <b>Регулярные транзакции</b>\n\n"
        for item in items:
            emoji = "📥" if item["type"] == "income" else "📤"
            status = "✅" if item["is_active"] else "⏸"
            text += (
                f"{status} {emoji} <b>{item['name']}</b>\n"
                f"  {format_money(item['amount'])} • {item['category']}\n"
                f"  Каждое {item['day_of_month']}-е число\n\n"
            )
        text += "/addrecurring — добавить | /delrecurring — удалить"

    await message.answer(text, parse_mode="HTML", reply_markup=get_main_menu())


@router.message(F.text == "/addrecurring")
async def cmd_addrecurring(message: Message, state: FSMContext):
    user = await create_or_get_user(message.from_user.id)
    if not user["id"]:
        await message.answer("❌ Сначала /start")
        return
    await message.answer(
        "🔄 <b>Новая регулярная транзакция</b>\n\n"
        "Введите название (например: <i>Аренда</i>, <i>Зарплата</i>):",
        parse_mode="HTML", reply_markup=get_cancel_keyboard()
    )
    await state.set_state(RecurringFlow.waiting_for_name)

@router.message(RecurringFlow.waiting_for_name)
async def recurring_name(message: Message, state: FSMContext):
    if message.text == "↩ Отмена":
        await state.clear()
        await message.answer("❌ Отменено", reply_markup=get_main_menu())
        return
    await state.update_data(name=message.text.strip()[:50])
    await message.answer(
        "💰 Введите сумму:",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(RecurringFlow.waiting_for_amount)


@router.message(RecurringFlow.waiting_for_amount)
async def recurring_amount(message: Message, state: FSMContext):
    if message.text == "↩ Отмена":
        await state.clear()
        await message.answer("❌ Отменено", reply_markup=get_main_menu())
        return
    if not validate_amount(message.text):
        await message.answer("❌ Некорректная сумма", reply_markup=get_cancel_keyboard())
        return
    await state.update_data(amount=float(message.text.replace(',', '.')))
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="📥 Доход", callback_data="rec_type_income"),
        InlineKeyboardButton(text="📤 Расход", callback_data="rec_type_expense"),
    ]])
    await message.answer("Тип транзакции:", reply_markup=keyboard)
    await state.set_state(RecurringFlow.waiting_for_type)


@router.callback_query(RecurringFlow.waiting_for_type)
async def recurring_type(callback: CallbackQuery, state: FSMContext):
    trans_type = callback.data.split("_")[-1]
    await state.update_data(trans_type=trans_type)
    cats = INCOME_CATEGORIES if trans_type == "income" else EXPENSE_CATEGORIES
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=cat, callback_data=f"rec_cat_{i}")]
        for i, cat in enumerate(cats)
    ])
    await callback.message.edit_text("📂 Выберите категорию:", reply_markup=keyboard)
    await state.set_state(RecurringFlow.waiting_for_category)
    await callback.answer()


@router.callback_query(RecurringFlow.waiting_for_category)
async def recurring_category(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    idx = int(callback.data.split("_")[-1])    cats = INCOME_CATEGORIES if data["trans_type"] == "income" else EXPENSE_CATEGORIES
    category = cats[idx]
    await state.update_data(category=category)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="💵 Наличные", callback_data="rec_method_cash"),
        InlineKeyboardButton(text="💳 Карта", callback_data="rec_method_card"),
    ]])
    await callback.message.edit_text("💳 Способ оплаты:", reply_markup=keyboard)
    await state.set_state(RecurringFlow.waiting_for_method)
    await callback.answer()


@router.callback_query(RecurringFlow.waiting_for_method)
async def recurring_method(callback: CallbackQuery, state: FSMContext):
    method = callback.data.split("_")[-1]
    await state.update_data(method=method)
    await callback.message.edit_text(
        "📅 В какой день месяца? Введите число от 1 до 28:"
    )
    await state.set_state(RecurringFlow.waiting_for_day)
    await callback.answer()


@router.message(RecurringFlow.waiting_for_day)
async def recurring_day(message: Message, state: FSMContext):
    if message.text == "↩ Отмена":
        await state.clear()
        await message.answer("❌ Отменено", reply_markup=get_main_menu())
        return
    try:
        day = int(message.text.strip())
        if not 1 <= day <= 28:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введите число от 1 до 28", reply_markup=get_cancel_keyboard())
        return

    data = await state.get_data()
    user = await create_or_get_user(message.from_user.id)

    success = await create_recurring(
        user["id"], data["name"], data["amount"],
        data["trans_type"], data["method"], data["category"], day
    )
    await state.clear()
    if success:
        type_label = "Доход" if data["trans_type"] == "income" else "Расход"
        await message.answer(
            f"✅ Регулярная транзакция создана!\n\n"
            f"<b>{data['name']}</b>\n"            f"{type_label} • {format_money(data['amount'])}\n"
            f"{data['category']} • каждое {day}-е число",
            parse_mode="HTML", reply_markup=get_main_menu()
        )
    else:
        await message.answer("❌ Ошибка при создании", reply_markup=get_main_menu())


@router.message(F.text == "/delrecurring")
async def cmd_delrecurring(message: Message):
    user = await create_or_get_user(message.from_user.id)
    if not user["id"]:
        await message.answer("❌ Сначала /start")
        return

    items = await get_recurring_list(user["id"])
    if not items:
        await message.answer("Нет регулярных транзакций.", reply_markup=get_main_menu())
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"🗑 {item['name']} ({format_money(item['amount'])})",
            callback_data=f"del_rec_{item['id']}"
        )]
        for item in items
    ])
    await message.answer("Выберите для удаления:", reply_markup=keyboard)


@router.callback_query(F.data.startswith("del_rec_"))
async def delete_recurring_callback(callback: CallbackQuery):
    rec_id = int(callback.data.split("_")[-1])
    user = await create_or_get_user(callback.from_user.id)
    await delete_recurring(user["id"], rec_id)
    await callback.message.edit_text("✅ Регулярная транзакция удалена")
    await callback.answer()