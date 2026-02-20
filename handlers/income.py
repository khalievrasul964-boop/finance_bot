# handlers/income.py
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from services.user_service import create_or_get_user
from services.transaction_service import add_transaction
from config.settings import INCOME_CATEGORIES
from utils.keyboards import (
    get_main_menu,
    get_income_categories_keyboard, 
    get_payment_method_inline_keyboard,
    get_cancel_keyboard
)
from utils.validators import validate_amount, format_amount_error_message
from utils.report_formatter import format_money
from config.settings import INCOME_CATEGORIES
from handlers.start import ensure_daily_report_sync

router = Router()
logger = logging.getLogger(__name__)

class IncomeFlow(StatesGroup):
    waiting_for_amount = State()
    waiting_for_category = State()
    waiting_for_method = State()

@router.message(F.text == "📥 Доход")
async def income_start(message: Message, state: FSMContext):
    """Начало добавления дохода."""
    try:
        await ensure_daily_report_sync(message)
        await message.answer(
            "╔════════════════════════════════════╗\n"
            "║ 💰 <b>НОВЫЙ ДОХОД</b>               ║\n"
            "╚════════════════════════════════════╝\n\n"
            "Введите сумму дохода:\n"
            "(например: <code>50000</code> или <code>50000.50</code>)",
            parse_mode="HTML",
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(IncomeFlow.waiting_for_amount)
    except Exception as e:
        logger.error(f"❌ Ошибка в income_start: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")

@router.message(IncomeFlow.waiting_for_amount)
async def income_amount(message: Message, state: FSMContext):
    """Обработка суммы дохода."""
    try:
        if message.text == "↩ Отмена":
            await state.clear()
            await message.answer("❌ Отменено", reply_markup=get_main_menu())
            return
        
        if not validate_amount(message.text):
            await message.answer(
                format_amount_error_message(),
                parse_mode="HTML",
                reply_markup=get_cancel_keyboard()
            )
            return
        
        amount = float(message.text.replace(',', '.'))
        await state.update_data(amount=amount)
        
        await message.answer(
            "📂 <b>Выберите категорию дохода:</b>",
            parse_mode="HTML",
            reply_markup=get_income_categories_keyboard()
        )
        await state.set_state(IncomeFlow.waiting_for_category)
    except Exception as e:
        logger.error(f"❌ Ошибка в income_amount: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка. Попробуйте еще раз.")

@router.callback_query(IncomeFlow.waiting_for_category)
async def income_category(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора категории дохода."""
    try:
        category_idx = int(callback.data.split("_")[-1])
        category = INCOME_CATEGORIES[category_idx]
        
        await state.update_data(category=category)
        await callback.message.edit_text(
            f"✅ <b>Категория выбрана!</b>\n"
            f"📂 {category}\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "💳 <b>Выберите способ получения:</b>",
            parse_mode="HTML",
            reply_markup=get_payment_method_inline_keyboard()
        )
        await state.set_state(IncomeFlow.waiting_for_method)
        await callback.answer()
    except Exception as e:
        logger.error(f"❌ Ошибка в income_category: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка", show_alert=True)

@router.callback_query(IncomeFlow.waiting_for_method)
async def income_method(callback: CallbackQuery, state: FSMContext):
    """Обработка способа получения дохода (callback)."""
    try:
        if not callback.data.startswith("method_"):
            await callback.answer()
            return
        
        method = callback.data.split("_")[1]  # "cash" или "card"
        method_label = "наличные" if method == "cash" else "карта"
        
        data = await state.get_data()
        user = await create_or_get_user(callback.from_user.id)
        
        if not user["id"] or not user["name"]:
            await callback.message.answer("❌ Ошибка: имя не установлено. Нажмите /start.")
            await state.clear()
            await callback.answer()
            return
        
        success = await add_transaction(
            user["id"], 
            data["amount"], 
            "income", 
            method, 
            user["name"],
            category=data.get("category", "Другое")
        )
        
        if success:
            formatted_amount = format_money(data['amount'])
            await callback.message.edit_text(
                "╔════════════════════════════════════╗\n"
                "║ ✅ <b>ДОХОД ДОБАВЛЕН!</b>          ║\n"
                "╚════════════════════════════════════╝\n\n"
                f"💰 <b>Сумма:</b> {formatted_amount}\n"
                f"📂 <b>Категория:</b> {data.get('category', 'Другое')}\n"
                f"💳 <b>Способ:</b> {method_label.capitalize()}\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "✅ Записано в ваш финансовый дневник",
                parse_mode="HTML"
            )
            
            # Отправляем главное меню отдельным сообщением
            await callback.message.answer(
                "Выберите действие:",
                reply_markup=get_main_menu()
            )
        else:
            await callback.message.answer(
                "❌ Ошибка при добавлении дохода. Попробуйте позже.",
                reply_markup=get_main_menu()
            )
        
        await state.clear()
        await callback.answer()
    except Exception as e:
        logger.error(f"❌ Ошибка в income_method: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка", show_alert=True)
        await state.clear()