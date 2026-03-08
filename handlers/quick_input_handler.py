# handlers/quick_input_handler.py
"""Обработчик быстрого ввода транзакции одной строкой."""
import logging
from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from services.user_service import create_or_get_user
from services.transaction_service import add_transaction
from services.report_service import get_month_range_for_tz, _get_timezone
from services.category_limit_service import check_category_limit
from utils.quick_input import parse_quick_input
from utils.keyboards import get_main_menu
from utils.report_formatter import format_money

router = Router()
logger = logging.getLogger(__name__)

# Регулярка: начинается с числа (опционально + или -) и содержит пробел
QUICK_INPUT_PATTERN = r'^[+\-]?\d'


@router.message(F.text.regexp(QUICK_INPUT_PATTERN))
async def handle_quick_input(message: Message, state: FSMContext):
    """Перехватывает сообщения вида '500 еда нал' для быстрого ввода."""
    # Не мешаем FSM если пользователь в процессе диалога
    current_state = await state.get_state()
    if current_state is not None:
        return

    parsed = parse_quick_input(message.text)
    if not parsed:
        return  # Не наш формат — пусть другие хендлеры обрабатывают

    user = await create_or_get_user(message.from_user.id)
    if not user["id"] or not user["name"]:
        await message.answer("❌ Сначала пройдите регистрацию /start")
        return

    success = await add_transaction(
        user["id"], parsed["amount"], parsed["type"],
        parsed["method"], user["name"], category=parsed["category"]
    )

    if not success:
        await message.answer("❌ Не удалось сохранить. Попробуйте позже.")
        return

    type_label = "Доход" if parsed["type"] == "income" else "Расход"
    method_label = "наличные" if parsed["method"] == "cash" else "карта"
    emoji = "📥" if parsed["type"] == "income" else "📤"

    response = (
        f"✅ {emoji} <b>{type_label} сохранён</b>\n\n"
        f"💰 {format_money(parsed['amount'])}\n"
        f"📂 {parsed['category']}\n"
        f"💳 {method_label.capitalize()}"
    )

    # Проверяем лимит по категории
    if parsed["type"] == "expense":
        try:
            timezone = await _get_timezone(user["id"])
            start, end = get_month_range_for_tz(timezone)
            limit_info = await check_category_limit(
                user["id"], parsed["category"],
                start.isoformat(), end.isoformat()
            )
            if limit_info:
                if limit_info["exceeded"]:
                    response += (
                        f"\n\n⚠️ <b>Лимит превышен!</b>\n"
                        f"Потрачено {format_money(limit_info['spent'])} "
                        f"из {format_money(limit_info['limit'])}"
                    )
                elif limit_info["warning"]:
                    response += (
                        f"\n\n⚠️ Использовано {limit_info['percentage']:.0f}% лимита "
                        f"({format_money(limit_info['remaining'])} осталось)"
                    )
        except Exception:
            pass

    await message.answer(response, parse_mode="HTML", reply_markup=get_main_menu())