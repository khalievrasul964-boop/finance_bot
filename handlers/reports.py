# handlers/reports.py
import logging
from aiogram import Router, F
from aiogram.types import Message
from services.user_service import create_or_get_user
from services.report_service import (
    get_daily_report_text, 
    get_weekly_report_text, 
    get_monthly_report_text
)
from datetime import date
from handlers.start import ensure_daily_report_sync
from utils.keyboards import get_main_menu

router = Router()
logger = logging.getLogger(__name__)

@router.message(F.text == "📊 Сегодня")
async def daily_report(message: Message):
    """Отчет за текущий день."""
    try:
        await ensure_daily_report_sync(message)
        user = await create_or_get_user(message.from_user.id)
        if not user["id"]:
            await message.answer(
                "❌ <b>Ошибка</b>\n\n"
                "Сначала представьтесь! Нажмите /start",
                reply_markup=get_main_menu(),
                parse_mode="HTML"
            )
            return
        
        # Красивый заголовок перед отчетом
        await message.answer(
            "⏳ <b>Формирую отчет на сегодня...</b>",
            parse_mode="HTML"
        )
        
        report = await get_daily_report_text(user["id"], date.today())
        await message.answer(
            f"<code>{report}</code>",
            parse_mode="HTML",
            reply_markup=get_main_menu()
        )
        logger.info(f"📊 Пользователь {user['name']} получил дневной отчет")
    except Exception as e:
        logger.error(f"❌ Ошибка при получении дневного отчета: {e}", exc_info=True)
        await message.answer("❌ Ошибка при формировании отчета. Попробуйте позже.")

@router.message(F.text == "📆 Неделя")
async def weekly_report(message: Message):
    """Отчет за текущую неделю."""
    try:
        await ensure_daily_report_sync(message)
        user = await create_or_get_user(message.from_user.id)
        if not user["id"]:
            await message.answer(
                "❌ <b>Ошибка</b>\n\n"
                "Сначала представьтесь! Нажмите /start",
                reply_markup=get_main_menu(),
                parse_mode="HTML"
            )
            return
        
        # Красивый заголовок перед отчетом
        await message.answer(
            "⏳ <b>Формирую еженедельный отчет...</b>",
            parse_mode="HTML"
        )
        
        report = await get_weekly_report_text(user["id"])
        await message.answer(
            f"<code>{report}</code>",
            parse_mode="HTML",
            reply_markup=get_main_menu()
        )
        logger.info(f"📆 Пользователь {user['name']} получил еженедельный отчет")
    except Exception as e:
        logger.error(f"❌ Ошибка при получении еженедельного отчета: {e}", exc_info=True)
        await message.answer("❌ Ошибка при формировании отчета. Попробуйте позже.")

@router.message(F.text == "🗓 Месяц")
async def monthly_report(message: Message):
    """Отчет за текущий месяц."""
    try:
        await ensure_daily_report_sync(message)
        user = await create_or_get_user(message.from_user.id)
        if not user["id"]:
            await message.answer(
                "❌ <b>Ошибка</b>\n\n"
                "Сначала представьтесь! Нажмите /start",
                reply_markup=get_main_menu(),
                parse_mode="HTML"
            )
            return
        
        # Красивый заголовок перед отчетом
        await message.answer(
            "⏳ <b>Формирую ежемесячный отчет...</b>",
            parse_mode="HTML"
        )
        
        report = await get_monthly_report_text(user["id"])
        await message.answer(
            f"<code>{report}</code>",
            parse_mode="HTML",
            reply_markup=get_main_menu()
        )
        logger.info(f"🗓 Пользователь {user['name']} получил ежемесячный отчет")
    except Exception as e:
        logger.error(f"❌ Ошибка при получении ежемесячного отчета: {e}", exc_info=True)
        await message.answer("❌ Ошибка при формировании отчета. Попробуйте позже.")