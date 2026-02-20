# handlers/start.py
import logging
from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from services.user_service import create_or_get_user, set_budget, get_budget
from services.report_service import (
    get_daily_report_text, get_user_balance, get_last_transactions, 
    get_budget_info, get_category_stats, search_transactions,
    get_daily_spending_data, get_category_distribution, get_income_vs_expense,
    get_monthly_trend
)
from services.transaction_service import delete_last_transaction, get_last_transaction
from utils.keyboards import get_main_menu, get_cancel_keyboard
from utils.validators import validate_name, format_amount_error_message, validate_amount
from utils.report_formatter import (
    format_money, create_bar_chart, create_pie_chart, 
    create_daily_bar_chart, create_comparison_chart, create_trend_chart
)
from datetime import date, timedelta
from storage.journal import ensure_user_header, append_daily_report_to_user_file

router = Router()
logger = logging.getLogger(__name__)

class Registration(StatesGroup):
    waiting_for_name = State()

class BudgetFlow(StatesGroup):
    waiting_for_budget = State()

class SearchFlow(StatesGroup):
    waiting_for_query = State()

async def ensure_daily_report_sync(message: Message):
    """Синхронизирует дневные отчеты из БД в файлы пользователей."""
    try:
        user = await create_or_get_user(message.from_user.id)
        if not user["id"] or not user["name"]:
            return
        await ensure_user_header(user["name"])
        yesterday = date.today() - timedelta(days=1)
        report = await get_daily_report_text(user["id"], yesterday)
        if "ещё нет операций" not in report:
            await append_daily_report_to_user_file(user["name"], yesterday, report)
    except Exception as e:
        logger.error(f"❌ Ошибка при синхронизации отчета: {e}", exc_info=True)

@router.message(F.text == "/start")
async def cmd_start(message: Message, state: FSMContext):
    """Команда /start - регистрация и главное меню."""
    try:
        await state.clear()
        user = await create_or_get_user(message.from_user.id)
        
        if user["name"] is None:
            await message.answer(
                "╔═══════════════════════════════════╗\n"
                "║ 👋 <b>ДОБРО ПОЖАЛОВАТЬ!</b>         ║\n"
                "╚═══════════════════════════════════╝\n\n"
                "Я — ваш <b>финансовый помощник</b> 💰\n"
                "Я помогу вам:\n\n"
                "✅ <b>Отслеживать</b> доходы и расходы\n"
                "✅ <b>Категоризировать</b> все операции\n"
                "✅ <b>Анализировать</b> расходы\n"
                "✅ <b>Вести дневник</b> финансов\n"
                "✅ <b>Получать отчеты</b> за день/неделю/месяц\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "<i>Как вас зовут?</i>",
                parse_mode="HTML",
                reply_markup=get_cancel_keyboard()
            )
            await state.set_state(Registration.waiting_for_name)
        else:
            await message.answer(
                f"═════════════════════════════════\n"
                f"✨ <b>С возвращением, {user['name']}!</b> ✨\n"
                f"═════════════════════════════════",
                reply_markup=get_main_menu(),
                parse_mode="HTML"
            )
    except Exception as e:
        logger.error(f"❌ Ошибка в /start: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")

@router.message(F.text == "/help")
async def cmd_help(message: Message):
    """Команда /help - справка по боту."""
    try:
        await message.answer(
            "╔════════════════════════════════════╗\n"
            "║ 📖 <b>СПРАВКА И ИНСТРУКЦИИ</b>     ║\n"
            "╚════════════════════════════════════╝\n\n"
            
            "<b>━ 📥 ДОБАВИТЬ ДОХОД ━</b>\n"
            "Нажмите: 📥 Доход\n"
            "1️⃣ Введите сумму (например: 50000 или 50000.50)\n"
            "2️⃣ Выберите категорию (зарплата, подарок, бонус...)\n"
            "3️⃣ Выберите способ получения (наличные или карта)\n"
            "✅ Готово! Доход добавлен в дневник\n\n"
            
            "<b>━ 📤 ДОБАВИТЬ РАСХОД ━</b>\n"
            "Нажмите: 📤 Расход\n"
            "1️⃣ Введите сумму (например: 450 или 299.90)\n"
            "2️⃣ Выберите категорию (еда, транспорт, жилье...)\n"
            "3️⃣ Выберите способ оплаты (наличные или карта)\n"
            "✅ Готово! Расход добавлен в дневник\n\n"
            
            "<b>━ 📊 ПРОСМОТР ОТЧЕТОВ ━</b>\n"
            "📊 Сегодня — Отчет с начала дня\n"
            "📆 Неделя — Отчет за текущую неделю (Пн-Вс)\n"
            "🗓 Месяц — Отчет за текущий месяц\n"
            "💡 Отчеты показывают доходы и расходы\n\n"
            
            "<b>━ ↩️ ОТМЕНА ОПЕРАЦИИ ━</b>\n"
            "Команда: <code>/undo</code>\n"
            "Удаляет последнюю добавленную операцию\n"
            "Идеально при ошибке в вводе\n\n"
            
            "<b>━ 🎯 ФИНАНСОВЫЕ ЦЕЛИ ━</b>\n"
            "/goals — список целей и прогресс\n"
            "/addgoal — создать новую цель\n"
            "Добавляйте цели (отпуск, техника) и отслеживайте накопления.\n"
            "Бот подскажет, сколько откладывать в месяц до дедлайна.\n\n"
            
            "<b>━ 💡 ПОЛЕЗНЫЕ СОВЕТЫ ━</b>\n"
            "• 📝 Ведите записи ежедневно для контроля\n"
            "• 🏷️ Используйте категории для анализа\n"
            "• 💳 Отличайте наличные от карты\n"
            "• 📊 Проверяйте отчеты еженедельно\n"
            "• 📁 Ваш дневник хранится в files\n\n"
            
            "<b>━ 🎨 БЫСТРЫЕ ДЕЙСТВИЯ ━</b>\n"
            "/start — Главное меню\n"
            "/help — Эта справка\n"
            "/undo — Отменить последнюю операцию\n"
            "↩ Отмена — Прервать текущее действие\n\n"
            
            "❓ Другие вопросы? Просто используйте бота!\n"
            "Он простой и интуитивный 😊",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"❌ Ошибка в /help: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")

@router.message(F.text == "/undo")
async def cmd_undo(message: Message):
    """Команда /undo - удалить последнюю транзакцию."""
    try:
        user = await create_or_get_user(message.from_user.id)
        if not user["id"]:
            await message.answer("❌ Сначала пройдите регистрацию /start")
            return
        
        trans = await get_last_transaction(user["id"])
        if not trans:
            await message.answer(
                "❌ <b>Нет операций для отмены</b>\n\n"
                "Вы пока не добавили ни одной операции.",
                parse_mode="HTML"
            )
            return
        
        emoji = "🟢" if trans["type"] == "income" else "🔴"
        success = await delete_last_transaction(user["id"], user["name"])
        
        if success:
            method = "наличные" if trans["method"] == "cash" else "карта"
            type_label = "Доход" if trans["type"] == "income" else "Расход"
            
            await message.answer(
                "╔════════════════════════════════════╗\n"
                f"║ {emoji} <b>ОПЕРАЦИЯ ОТМЕНЕНА</b>          ║\n"
                "╚════════════════════════════════════╝\n\n"
                f"<b>Сумма:</b> {trans['amount']:.2f} ₽\n"
                f"<b>Тип:</b> {type_label}\n"
                f"<b>Категория:</b> {trans['category']}\n"
                f"<b>Способ:</b> {method.capitalize()}\n\n"
                "✅ Операция успешно удалена из дневника",
                parse_mode="HTML"
            )
        else:
            await message.answer("❌ Ошибка при отмене транзакции")
    except Exception as e:
        logger.error(f"❌ Ошибка в /undo: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")

@router.message(Registration.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    """Обработка ввода имени при регистрации."""
    try:
        if message.text == "↩ Отмена":
            await state.clear()
            await message.answer("❌ Регистрация отменена", reply_markup=get_main_menu())
            return
        
        name = message.text.strip()
        if not validate_name(name):
            await message.answer(
                "❌ Пожалуйста, введите корректное имя:\n"
                "• От 1 до 50 символов\n"
                "• Без ссылок и спецсимволов",
                reply_markup=get_cancel_keyboard()
            )
            return
        
        result = await create_or_get_user(message.from_user.id, name=name)
        if not result["id"]:
            await message.answer("❌ Ошибка регистрации. Попробуйте позже.")
            return
        
        await message.answer(
            f"✨ Отлично, <b>{name}</b>!\n\n"
            "Теперь вы можете:\n"
            "• 📥 Добавлять доходы\n"
            "• 📤 Добавлять расходы\n"
            "• 📊 Смотреть отчёты\n"
            "• ↩ Отменять операции\n\n"
            "Напишите /help для подробной справки",
            reply_markup=get_main_menu(),
            parse_mode="HTML"
        )
        await state.clear()
    except Exception as e:
        logger.error(f"❌ Ошибка при обработке имени: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка. Попробуйте еще раз.")

@router.message(F.text == "↩ Отмена")
async def cancel_action(message: Message, state: FSMContext):
    """Общая обработка отмены."""
    try:
        await state.clear()
        await message.answer(
            "❌ Действие отменено",
            reply_markup=get_main_menu()
        )
    except Exception as e:
        logger.error(f"❌ Ошибка при отмене: {e}", exc_info=True)

@router.message(F.text == "/profile")
async def cmd_profile(message: Message):
    """Команда /profile - показать профиль пользователя и баланс."""
    try:
        user = await create_or_get_user(message.from_user.id)
        if not user["id"] or not user["name"]:
            await message.answer("❌ Сначала пройдите регистрацию /start")
            return
        
        balance, total_income, total_expense, total_count = await get_user_balance(user["id"])
        
        # Определяем значок баланса
        if balance > 0:
            balance_emoji = "🟢"
        elif balance < 0:
            balance_emoji = "🔴"
        else:
            balance_emoji = "⚪"
        
        balance_text = format_money(balance)
        income_text = format_money(total_income)
        expense_text = format_money(total_expense)
        
        # Получаем информацию о бюджете
        budget_info = await get_budget_info(user["id"], user["monthly_budget"])
        
        # Формируем строку с информацией о бюджете
        budget_text = ""
        if user["monthly_budget"] > 0:
            budget_text = (
                f"\n<b>━━━ БЮДЖЕТ НА МЕСЯЦ ━━━</b>\n"
                f"💰 <b>Лимит:</b> {format_money(budget_info['budget'])}\n"
                f"📊 <b>Потрачено:</b> {format_money(budget_info['spent'])} ({budget_info['percentage']:.1f}%)\n"
            )
            
            if budget_info['spent'] > budget_info['budget']:
                budget_text += f"🔴 <b>Превышено:</b> {format_money(abs(budget_info['remaining']))}"
            else:
                budget_text += f"🟢 <b>Осталось:</b> {format_money(budget_info['remaining'])}"
        else:
            budget_text = "\n<b>━━━ БЮДЖЕТ ━━━</b>\n💡 Бюджет не установлен. Используйте /setbudget 50000"
        
        await message.answer(
            f"╔════════════════════════════════════╗\n"
            f"║ 🎯 <b>МОЙ ПРОФИЛЬ</b>              ║\n"
            f"╚════════════════════════════════════╝\n\n"
            
            f"<b>👤 Имя:</b> {user['name']}\n"
            f"<b>🆔 ID:</b> {user['telegram_id']}\n\n"
            
            f"<b>━━━ ФИНАНСОВАЯ СТАТИСТИКА ━━━</b>\n"
            f"{balance_emoji} <b>Баланс:</b> {balance_text}\n"
            f"🟢 <b>Всего доходов:</b> {income_text}\n"
            f"🔴 <b>Всего расходов:</b> {expense_text}\n"
            f"📊 <b>Всего операций:</b> {total_count}\n"
            f"{budget_text}\n\n"
            
            f"<b>━━━ БЫСТРЫЕ КОМАНДЫ ━━━</b>\n"
            f"/setbudget 50000 — установить бюджет\n"
            f"/stats — статистика по категориям\n"
            f"/search еда — поиск по категории",
            parse_mode="HTML",
            reply_markup=get_main_menu()
        )
    except Exception as e:
        logger.error(f"❌ Ошибка в /profile: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")

@router.message(F.text == "👤 Профиль")
async def menu_profile(message: Message):
    """Обработка кнопки профиля в меню."""
    await cmd_profile(message)

@router.message(F.text == "/history")
async def cmd_history(message: Message):
    """Команда /history - показать последние 5 транзакций."""
    try:
        user = await create_or_get_user(message.from_user.id)
        if not user["id"] or not user["name"]:
            await message.answer("❌ Сначала пройдите регистрацию /start")
            return
        
        transactions = await get_last_transactions(user["id"], limit=5)
        
        if not transactions:
            await message.answer(
                "❌ <b>Нет операций</b>\n\n"
                "У вас пока не было операций. Начните с добавления дохода или расхода!",
                parse_mode="HTML",
                reply_markup=get_main_menu()
            )
            return
        
        # Формируем красивый список операций
        history_text = "╔════════════════════════════════════╗\n"
        history_text += "║ 📋 <b>ПОСЛЕДНИЕ ОПЕРАЦИИ</b>       ║\n"
        history_text += "╚════════════════════════════════════╝\n\n"
        
        for i, trans in enumerate(transactions, 1):
            emoji = "🟢" if trans["type"] == "income" else "🔴"
            method_emoji = "💵" if trans["method"] == "cash" else "💳"
            amount_text = format_money(trans["amount"])
            
            history_text += (
                f"{i}. {emoji} <b>{trans['date']} {trans['time']}</b>\n"
                f"   💰 {amount_text}\n"
                f"   📁 {trans['category']} {method_emoji}\n\n"
            )
        
        await message.answer(history_text, parse_mode="HTML", reply_markup=get_main_menu())
    except Exception as e:
        logger.error(f"❌ Ошибка в /history: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")

@router.message(F.text == "📋 История")
async def menu_history(message: Message):
    """Обработка кнопки истории в меню."""
    await cmd_history(message)

@router.message(F.text == "/setbudget", F.text.startswith("/setbudget"))
async def cmd_setbudget(message: Message, state: FSMContext):
    """Команда /setbudget - установить месячный бюджет."""
    try:
        user = await create_or_get_user(message.from_user.id)
        if not user["id"] or not user["name"]:
            await message.answer("❌ Сначала пройдите регистрацию /start")
            return
        
        # Пытаемся получить сумму из команды
        text = message.text.strip()
        if text.startswith("/setbudget "):
            amount_str = text.replace("/setbudget ", "").strip()
            if not amount_str:
                await message.answer(
                    "💰 <b>Установка бюджета</b>\n\n"
                    "Напишите сумму месячного лимита расходов:\n\n"
                    "Пример: <code>50000</code> или <code>50000.50</code>",
                    parse_mode="HTML",
                    reply_markup=get_cancel_keyboard()
                )
                await state.set_state(BudgetFlow.waiting_for_budget)
                return
            
            # Валидируем сумму
            if not validate_amount(amount_str):
                await message.answer(
                    format_amount_error_message(),
                    parse_mode="HTML",
                    reply_markup=get_cancel_keyboard()
                )
                return
            
            budget = float(amount_str.replace(",", "."))
            success = await set_budget(user["id"], budget)
            
            if success:
                budget_text = format_money(budget)
                await message.answer(
                    f"✅ <b>Бюджет установлен!</b>\n\n"
                    f"💰 Месячный лимит: {budget_text}\n\n"
                    f"Теперь я буду контролировать ваши расходы и предупреждать,\n"
                    f"когда вы приблизитесь к лимиту.",
                    parse_mode="HTML",
                    reply_markup=get_main_menu()
                )
                logger.info(f"💰 Пользователь {user['name']} установил бюджет: {budget}")
            else:
                await message.answer("❌ Ошибка при установке бюджета. Попробуйте позже.")
            return
        
        # Если просто /setbudget без аргументов
        await message.answer(
            "💰 <b>Установка бюджета</b>\n\n"
            "Напишите сумму месячного лимита расходов:\n\n"
            "Пример: <code>50000</code> или <code>50000.50</code>",
            parse_mode="HTML",
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(BudgetFlow.waiting_for_budget)
    except Exception as e:
        logger.error(f"❌ Ошибка в /setbudget: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")

@router.message(BudgetFlow.waiting_for_budget)
async def process_budget(message: Message, state: FSMContext):
    """Обработка ввода суммы бюджета."""
    try:
        if message.text == "↩ Отмена":
            await state.clear()
            await message.answer("❌ Установка бюджета отменена", reply_markup=get_main_menu())
            return
        
        amount_str = message.text.strip()
        
        if not validate_amount(amount_str):
            await message.answer(
                format_amount_error_message(),
                parse_mode="HTML",
                reply_markup=get_cancel_keyboard()
            )
            return
        
        user = await create_or_get_user(message.from_user.id)
        budget = float(amount_str.replace(",", "."))
        success = await set_budget(user["id"], budget)
        
        if success:
            budget_text = format_money(budget)
            await message.answer(
                f"✅ <b>Бюджет установлен!</b>\n\n"
                f"💰 Месячный лимит: {budget_text}\n\n"
                f"Теперь я буду контролировать ваши расходы и предупреждать,\n"
                f"когда вы приблизитесь к лимиту.",
                parse_mode="HTML",
                reply_markup=get_main_menu()
            )
            logger.info(f"💰 Пользователь {user['name']} установил бюджет: {budget}")
        else:
            await message.answer("❌ Ошибка при установке бюджета. Попробуйте позже.")
        
        await state.clear()
    except Exception as e:
        logger.error(f"❌ Ошибка при обработке бюджета: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка. Попробуйте еще раз.")
        await state.clear()

@router.message(F.text == "💰 Бюджет")
async def menu_budget(message: Message, state: FSMContext):
    """Обработка кнопки бюджета в меню."""
    await cmd_setbudget(message, state)

@router.message(F.text == "/stats")
async def cmd_stats(message: Message):
    """Команда /stats - показать статистику по категориям за месяц."""
    try:
        user = await create_or_get_user(message.from_user.id)
        if not user["id"] or not user["name"]:
            await message.answer("❌ Сначала пройдите регистрацию /start")
            return
        
        # Получаем статистику по расходам
        expense_stats = await get_category_stats(user["id"], "expense")
        expense_categories = expense_stats["categories"]
        
        # Получаем статистику по доходам
        income_stats = await get_category_stats(user["id"], "income")
        income_categories = income_stats["categories"]
        
        # Если нет данных
        if not expense_categories and not income_categories:
            await message.answer(
                "❌ <b>Нет данных для статистики</b>\n\n"
                "У вас пока не было операций в этом месяце.\n"
                "Добавьте доходы или расходы и посмотрите статистику!",
                parse_mode="HTML",
                reply_markup=get_main_menu()
            )
            return
        
        # Формируем красивый вывод статистики
        stats_text = "📊 Статистика за текущий месяц\n\n"
        
        # Статистика по расходам
        if expense_categories:
            stats_text += "🔴 <b>РАСХОДЫ ПО КАТЕГОРИЯМ:</b>\n\n"
            total_expense = expense_stats["total"]
            
            for idx, cat in enumerate(expense_categories[:5], 1):  # Топ-5
                name = cat["name"]
                amount = cat["amount"]
                percentage = cat["percentage"]
                
                # Красивая стрелка для прогресса
                bar_length = int(percentage / 5)  # 20% = 1 блок
                bar = "█" * bar_length + "░" * (20 - bar_length)
                
                stats_text += (
                    f"{idx}. {name}\n"
                    f"   {bar} {percentage:.1f}%\n"
                    f"   💰 {format_money(amount)}\n\n"
                )
            
            stats_text += f"📤 <b>Всего расходов:</b> {format_money(total_expense)}\n\n"
        
        # Статистика по доходам
        if income_categories:
            stats_text += "🟢 <b>ДОХОДЫ ПО КАТЕГОРИЯМ:</b>\n\n"
            total_income = income_stats["total"]
            
            for idx, cat in enumerate(income_categories[:5], 1):  # Топ-5
                name = cat["name"]
                amount = cat["amount"]
                percentage = cat["percentage"]
                
                # Красивая стрелка для прогресса
                bar_length = int(percentage / 5)  # 20% = 1 блок
                bar = "█" * bar_length + "░" * (20 - bar_length)
                
                stats_text += (
                    f"{idx}. {name}\n"
                    f"   {bar} {percentage:.1f}%\n"
                    f"   💰 {format_money(amount)}\n\n"
                )
            
            stats_text += f"📥 <b>Всего доходов:</b> {format_money(total_income)}\n\n"
        
        await message.answer(
            stats_text,
            parse_mode="HTML",
            reply_markup=get_main_menu()
        )
        logger.info(f"📊 Пользователь {user['name']} просмотрел статистику")
    except Exception as e:
        logger.error(f"❌ Ошибка в /stats: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")

@router.message(F.text == "📊 Статистика")
async def menu_stats(message: Message):
    """Обработка кнопки статистики в меню."""
    await cmd_stats(message)

@router.message(F.text == "/search", F.text.startswith("/search"))
async def cmd_search(message: Message, state: FSMContext):
    """Команда /search - поиск операций по различным критериям."""
    try:
        user = await create_or_get_user(message.from_user.id)
        if not user["id"] or not user["name"]:
            await message.answer("❌ Сначала пройдите регистрацию /start")
            return
        
        text = message.text.strip()
        
        # Если есть аргумент сразу
        if text.startswith("/search "):
            query = text.replace("/search ", "").strip()
            if not query:
                await show_search_help(message, state)
                return
            
            # Выполняем поиск
            await execute_search(message, user, query)
            return
        
        # Если просто /search
        await show_search_help(message, state)
    except Exception as e:
        logger.error(f"❌ Ошибка в /search: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")

async def show_search_help(message: Message, state: FSMContext):
    """Показывает справку по поиску и просит ввести запрос."""
    await message.answer(
        "🔍 <b>ПОИСК ОПЕРАЦИЙ</b>\n\n"
        "<b>Примеры поиска:</b>\n\n"
        "1️⃣ <b>По категории:</b>\n"
        "   /search еда\n"
        "   /search транспорт\n\n"
        
        "2️⃣ <b>По сумме:</b>\n"
        "   /search 5000-10000 (от 5000 до 10000)\n"
        "   /search 50000 (ровно 50000)\n\n"
        
        "3️⃣ <b>С фильтром типа:</b>\n"
        "   /search еда:expense (расходы на еду)\n"
        "   /search зарплата:income (только доходы)\n\n"
        
        "Напишите поисковый запрос:",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(SearchFlow.waiting_for_query)

async def execute_search(message: Message, user: dict, query: str):
    """Выполняет поиск по запросу."""
    # Парсим запрос
    trans_type = None
    search_query = query
    min_amount = None
    max_amount = None
    
    # Проверяем на фильтр типа (еда:expense, зарплата:income)
    if ":" in query:
        parts = query.split(":")
        search_query = parts[0].strip()
        trans_type = "expense" if parts[1].strip() in ["expense", "расход"] else "income"
    
    # Проверяем на диапазон сумм (5000-10000)
    elif "-" in query and query[0].isdigit():
        try:
            parts = query.split("-")
            if len(parts) == 2:
                min_amount = float(parts[0].strip())
                max_amount = float(parts[1].strip())
                search_query = None
        except ValueError:
            pass
    
    # Проверяем на конкретную сумму
    elif query.replace(".", "").replace(",", "").isdigit():
        try:
            amount = float(query.replace(",", "."))
            min_amount = amount * 0.99  # ±1% допуска
            max_amount = amount * 1.01
            search_query = None
        except ValueError:
            pass
    
    # Выполняем поиск
    results = await search_transactions(
        user["id"],
        query=search_query,
        min_amount=min_amount,
        max_amount=max_amount,
        trans_type=trans_type
    )
    
    # Выводим результаты
    if not results:
        await message.answer(
            "❌ <b>Ничего не найдено</b>\n\n"
            f"По запросу \"{query}\" нет результатов.\n"
            "Проверьте правильность ввода и попробуйте еще раз.",
            parse_mode="HTML",
            reply_markup=get_main_menu()
        )
        return
    
    # Формируем красивый результат поиска
    search_text = f"🔍 <b>Результаты поиска: \"{query}\"</b>\n\n"
    search_text += f"Найдено: <b>{len(results)}</b> операци(й)\n\n"
    
    total_income = 0.0
    total_expense = 0.0
    
    for idx, trans in enumerate(results, 1):
        emoji = "🟢" if trans["type"] == "income" else "🔴"
        method_emoji = "💵" if trans["method"] == "cash" else "💳"
        
        search_text += (
            f"{idx}. {emoji} <b>{trans['date']} {trans['time']}</b>\n"
            f"   💰 {format_money(trans['amount'])}\n"
            f"   📁 {trans['category']} {method_emoji}\n\n"
        )
        
        if trans["type"] == "income":
            total_income += trans["amount"]
        else:
            total_expense += trans["amount"]
    
    # Добавляем итоги
    search_text += f"━━━━━━━━━━━━━━━━━━━━━━━\n"
    if total_income > 0:
        search_text += f"🟢 Доход: {format_money(total_income)}\n"
    if total_expense > 0:
        search_text += f"🔴 Расход: {format_money(total_expense)}\n"
    
    if total_income > 0 or total_expense > 0:
        balance = total_income - total_expense
        balance_emoji = "🟢" if balance >= 0 else "🔴"
        search_text += f"{balance_emoji} Итог: {format_money(abs(balance))}"
    
    await message.answer(
        search_text,
        parse_mode="HTML",
        reply_markup=get_main_menu()
    )
    logger.info(f"🔍 Пользователь {user['name']} выполнил поиск: {query}")

@router.message(SearchFlow.waiting_for_query)
async def process_search_query(message: Message, state: FSMContext):
    """Обработка ввода поисковой фразы."""
    try:
        if message.text == "↩ Отмена":
            await state.clear()
            await message.answer("❌ Поиск отменен", reply_markup=get_main_menu())
            return
        
        user = await create_or_get_user(message.from_user.id)
        await execute_search(message, user, message.text.strip())
        await state.clear()
    except Exception as e:
        logger.error(f"❌ Ошибка в обработке поиска: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка. Попробуйте еще раз.")
        await state.clear()

@router.message(F.text == "🔍 Поиск")
async def menu_search(message: Message, state: FSMContext):
    """Обработка кнопки поиска в меню."""
    await cmd_search(message, state)

@router.message(F.text == "📈 Графики")
async def menu_charts(message: Message):
    """Обработка кнопки графиков в меню."""
    await cmd_charts(message)

@router.message(F.commands(["chart", "charts", "graphs"]))
async def cmd_charts(message: Message):
    """Показывает красивые графики расходов и доходов."""
    try:
        user = await create_or_get_user(message.from_user.id)
        
        # Получаем все необходимые данные для графиков
        daily_data = await get_daily_spending_data(user['id'], days=30)
        expense_distribution = await get_category_distribution(user['id'], trans_type='expense')
        income_distribution = await get_category_distribution(user['id'], trans_type='income')
        income_total, expense_total = await get_income_vs_expense(user['id'])
        monthly_trend = await get_monthly_trend(user['id'], months=6)
        
        chart_text = "\n🎯 ГРАФИКИ И СТАТИСТИКА\n"
        chart_text += "═" * 40 + "\n"
        
        # График расходов по дням
        if daily_data:
            chart_text += create_daily_bar_chart("📅 Расходы по дням (30 дней)", daily_data)
        else:
            chart_text += "\n📅 Расходы по дням: Нет данных\n"
        
        # График распределения расходов по категориям
        if expense_distribution:
            chart_text += create_pie_chart("📊 Расходы по категориям", expense_distribution)
        else:
            chart_text += "\n📊 Расходы по категориям: Нет данных\n"
        
        # График распределения доходов по категориям
        if income_distribution:
            chart_text += create_pie_chart("💰 Доходы по категориям", income_distribution)
        else:
            chart_text += "\n💰 Доходы по категориям: Нет данных\n"
        
        # Сравнение доход vs расход
        if income_total > 0 or expense_total > 0:
            comparison_data = {
                "💰 Доход": [income_total],
                "🔴 Расход": [expense_total]
            }
            chart_text += "\n🔄 ДОХОД vs РАСХОД (Текущий месяц)\n"
            chart_text += "─" * 40 + "\n"
            
            income_bar_width = int((income_total / max(income_total, expense_total)) * 30)
            expense_bar_width = int((expense_total / max(income_total, expense_total)) * 30)
            
            chart_text += f"💰 Доход:  {'█' * income_bar_width}{'░' * (30 - income_bar_width)} {format_money(income_total)}\n"
            chart_text += f"🔴 Расход: {'█' * expense_bar_width}{'░' * (30 - expense_bar_width)} {format_money(expense_total)}\n"
            
            balance = income_total - expense_total
            balance_emoji = "🟢" if balance >= 0 else "🔴"
            chart_text += f"{balance_emoji} Баланс: {format_money(abs(balance))}\n"
        
        # Тренд расходов по месяцам
        if monthly_trend:
            chart_text += create_bar_chart("📈 Тренд расходов (последние 6 месяцев)", monthly_trend)
        
        chart_text += "═" * 40 + "\n"
        
        await message.answer(
            chart_text,
            parse_mode="HTML",
            reply_markup=get_main_menu()
        )
        logger.info(f"📈 Пользователь {user['name']} просмотрел графики")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при показе графиков: {e}", exc_info=True)
        await message.answer(
            "❌ Произошла ошибка при загрузке графиков. Попробуйте позже.",
            reply_markup=get_main_menu()
        )