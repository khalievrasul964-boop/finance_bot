# handlers/export_handler.py
"""Экспорт транзакций в CSV."""
import logging
from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile, CallbackQuery

from services.user_service import create_or_get_user
from services.export_service import export_to_csv
from utils.keyboards import get_main_menu

router = Router()
logger = logging.getLogger(__name__)


@router.message(F.text == "/export")
async def cmd_export(message: Message):
    user = await create_or_get_user(message.from_user.id)
    if not user["id"]:
        await message.answer("❌ Сначала /start")
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 За месяц", callback_data="export_1")],
        [InlineKeyboardButton(text="📅 За 3 месяца", callback_data="export_3")],
        [InlineKeyboardButton(text="📅 За полгода", callback_data="export_6")],
        [InlineKeyboardButton(text="📋 Всё время", callback_data="export_0")],
    ])
    await message.answer(
        "📊 <b>Экспорт в CSV</b>\n\nВыберите период:",
        parse_mode="HTML", reply_markup=keyboard
    )


@router.callback_query(F.data.startswith("export_"))
async def export_callback(callback: CallbackQuery):
    months = int(callback.data.split("_")[1])
    user = await create_or_get_user(callback.from_user.id)

    await callback.message.edit_text("⏳ Формирую файл...")

    csv_bytes = await export_to_csv(user["id"], months=months)
    if not csv_bytes:
        await callback.message.edit_text(
            "❌ Нет данных для экспорта или произошла ошибка."
        )
        await callback.answer()
        return

    from datetime import datetime
    filename = f"finance_{user['name']}_{datetime.now().strftime('%Y%m%d')}.csv"
    file = BufferedInputFile(csv_bytes, filename=filename)

    period_label = {0: "всё время", 1: "1 месяц", 3: "3 месяца", 6: "6 месяцев"}.get(months, f"{months} мес.")
    await callback.message.answer_document(
        file,
        caption=(
            f"📊 Экспорт транзакций за {period_label}\n"
            "Откройте в Excel или Google Sheets"
        ),
        reply_markup=get_main_menu()
    )
    await callback.answer()