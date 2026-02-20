# handlers/goals.py
"""Обработчики для финансовых целей и копилок."""
import logging
from datetime import date, datetime
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from services.user_service import create_or_get_user
from services.goal_service import (
    create_goal,
    get_goals,
    add_to_goal,
    delete_goal,
    get_monthly_saving_suggestion,
)
from utils.keyboards import get_main_menu, get_cancel_keyboard, get_goals_list_keyboard
from utils.validators import validate_amount, format_amount_error_message
from utils.report_formatter import format_money

router = Router()
logger = logging.getLogger(__name__)


class GoalCreateFlow(StatesGroup):
    waiting_for_name = State()
    waiting_for_amount = State()
    waiting_for_deadline = State()


class GoalAddFlow(StatesGroup):
    waiting_for_amount = State()


@router.message(F.text == "🎯 Цели")
@router.message(F.text == "/goals")
async def cmd_goals(message: Message, state: FSMContext):
    """Список целей и главное меню целей."""
    await state.clear()
    try:
        user = await create_or_get_user(message.from_user.id)
        if not user["id"] or not user["name"]:
            await message.answer("❌ Сначала пройдите регистрацию /start")
            return

        goals = await get_goals(user["id"])

        if not goals:
            await message.answer(
                "╔════════════════════════════════════╗\n"
                "║ 🎯 <b>ФИНАНСОВЫЕ ЦЕЛИ</b>          ║\n"
                "╚════════════════════════════════════╝\n\n"
                "У вас пока нет целей.\n\n"
                "💡 <b>Создайте цель</b> — например, накопить на отпуск или новый телефон.\n"
                "Я помогу отслеживать прогресс и подскажу, сколько откладывать в месяц.\n\n"
                "Используйте /addgoal чтобы создать цель",
                parse_mode="HTML",
                reply_markup=get_main_menu()
            )
            return

        text = "╔════════════════════════════════════╗\n"
        text += "║ 🎯 <b>ВАШИ ЦЕЛИ</b>                ║\n"
        text += "╚════════════════════════════════════╝\n\n"

        for g in goals:
            bar_len = int(g["percentage"] / 5)
            bar = "█" * bar_len + "░" * (20 - bar_len)
            text += f"<b>{g['name']}</b>\n"
            text += f"  {bar} {g['percentage']:.0f}%\n"
            text += f"  💰 {format_money(g['current_amount'])} / {format_money(g['target_amount'])}\n"
            text += f"  📌 Осталось: {format_money(g['remaining'])}\n"
            if g["deadline"]:
                try:
                    d = datetime.fromisoformat(g["deadline"]).date()
                    suggestion = get_monthly_saving_suggestion(
                        g["target_amount"], g["current_amount"], d
                    )
                    if suggestion:
                        text += f"  📅 До {d.strftime('%d.%m.%Y')} — откладывайте {format_money(suggestion)}/мес\n"
                    else:
                        text += f"  📅 До {d.strftime('%d.%m.%Y')}\n"
                except (ValueError, TypeError):
                    pass
            text += "\n"

        text += "💡 /addgoal — новая цель | Кнопки ниже — пополнить или удалить"
        await message.answer(
            text,
            parse_mode="HTML",
            reply_markup=get_goals_list_keyboard(goals)
        )
    except Exception as e:
        logger.error(f"❌ Ошибка в cmd_goals: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")


@router.message(F.text == "/addgoal")
async def cmd_addgoal_start(message: Message, state: FSMContext):
    """Начало создания цели."""
    try:
        user = await create_or_get_user(message.from_user.id)
        if not user["id"] or not user["name"]:
            await message.answer("❌ Сначала пройдите регистрацию /start")
            return

        await state.clear()
        await message.answer(
            "🎯 <b>Новая цель</b>\n\n"
            "Введите название цели:\n"
            "Например: <i>Отпуск</i>, <i>Ноутбук</i>, <i>Ремонт</i>",
            parse_mode="HTML",
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(GoalCreateFlow.waiting_for_name)
    except Exception as e:
        logger.error(f"❌ Ошибка в cmd_addgoal_start: {e}", exc_info=True)


@router.message(GoalCreateFlow.waiting_for_name)
async def goal_process_name(message: Message, state: FSMContext):
    if message.text == "↩ Отмена":
        await state.clear()
        await message.answer("❌ Создание цели отменено", reply_markup=get_main_menu())
        return

    name = message.text.strip()[:100]
    if not name:
        await message.answer("❌ Введите название цели")
        return

    await state.update_data(name=name)
    await message.answer(
        "💰 Введите целевую сумму (например: <code>100000</code> или <code>50000.50</code>):",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(GoalCreateFlow.waiting_for_amount)


@router.message(GoalCreateFlow.waiting_for_amount)
async def goal_process_amount(message: Message, state: FSMContext):
    if message.text == "↩ Отмена":
        await state.clear()
        await message.answer("❌ Создание цели отменено", reply_markup=get_main_menu())
        return

    if not validate_amount(message.text):
        await message.answer(format_amount_error_message(), parse_mode="HTML", reply_markup=get_cancel_keyboard())
        return

    amount = float(message.text.replace(",", "."))
    await state.update_data(target_amount=amount)
    await message.answer(
        "📅 <b>Дедлайн (опционально)</b>\n\n"
        "Введите дату в формате ДД.ММ.ГГГГ (например: 01.09.2025)\n"
        "Или отправьте <code>—</code> или <code>пропустить</code> чтобы без дедлайна",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(GoalCreateFlow.waiting_for_deadline)


@router.message(GoalCreateFlow.waiting_for_deadline)
async def goal_process_deadline(message: Message, state: FSMContext):
    if message.text == "↩ Отмена":
        await state.clear()
        await message.answer("❌ Создание цели отменено", reply_markup=get_main_menu())
        return

    deadline = None
    text = message.text.strip().lower()
    if text and text not in ("—", "пропустить", "-", "нет"):
        try:
            parts = message.text.strip().split(".")
            if len(parts) == 3:
                d, m, y = int(parts[0]), int(parts[1]), int(parts[2])
                deadline = date(y, m, d)
                if deadline <= date.today():
                    await message.answer("❌ Дедлайн должен быть в будущем. Введите дату или «пропустить»")
                    return
        except (ValueError, IndexError):
            await message.answer("❌ Неверный формат. Введите ДД.ММ.ГГГГ или «пропустить»")
            return

    data = await state.get_data()
    user = await create_or_get_user(message.from_user.id)
    goal_id = await create_goal(
        user["id"],
        data["name"],
        data["target_amount"],
        deadline
    )

    await state.clear()
    if goal_id:
        await message.answer(
            f"✅ <b>Цель создана!</b>\n\n"
            f"🎯 {data['name']}\n"
            f"💰 Цель: {format_money(data['target_amount'])}\n"
            f"📅 Дедлайн: {deadline.strftime('%d.%m.%Y') if deadline else 'не задан'}\n\n"
            f"Используйте кнопки в /goals чтобы пополнить цель",
            parse_mode="HTML",
            reply_markup=get_main_menu()
        )
    else:
        await message.answer("❌ Не удалось создать цель. Попробуйте позже.", reply_markup=get_main_menu())


@router.callback_query(F.data.startswith("goal_add_"))
async def goal_add_callback(callback: CallbackQuery, state: FSMContext):
    """Пополнение цели — запрашиваем сумму."""
    goal_id = int(callback.data.replace("goal_add_", ""))
    await state.update_data(goal_add_id=goal_id)
    await state.set_state(GoalAddFlow.waiting_for_amount)
    await callback.message.answer(
        "💰 Введите сумму для пополнения цели:",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )
    await callback.answer()


@router.message(GoalAddFlow.waiting_for_amount)
async def goal_add_amount(message: Message, state: FSMContext):
    if message.text == "↩ Отмена":
        await state.clear()
        await message.answer("❌ Пополнение отменено", reply_markup=get_main_menu())
        return

    if not validate_amount(message.text):
        await message.answer(format_amount_error_message(), parse_mode="HTML", reply_markup=get_cancel_keyboard())
        return

    amount = float(message.text.replace(",", "."))
    data = await state.get_data()
    goal_id = data.get("goal_add_id")

    user = await create_or_get_user(message.from_user.id)
    success = await add_to_goal(user["id"], goal_id, amount)

    await state.clear()
    if success:
        await message.answer(
            f"✅ В цель добавлено {format_money(amount)}",
            reply_markup=get_main_menu()
        )
    else:
        await message.answer("❌ Ошибка. Цель не найдена.", reply_markup=get_main_menu())


@router.callback_query(F.data.startswith("goal_del_"))
async def goal_delete_callback(callback: CallbackQuery):
    """Удаление цели."""
    goal_id = int(callback.data.replace("goal_del_", ""))
    user = await create_or_get_user(callback.from_user.id)
    success = await delete_goal(user["id"], goal_id)

    if success:
        await callback.message.answer("✅ Цель удалена", reply_markup=get_main_menu())
        await callback.answer()
    else:
        await callback.answer("❌ Не удалось удалить цель", show_alert=True)
