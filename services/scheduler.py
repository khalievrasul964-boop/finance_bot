# services/scheduler.py
"""
Фоновый планировщик: напоминания и регулярные транзакции.
Запускается один раз при старте бота.
"""
import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import Bot
from services.reminder_service import get_all_active_reminders
from services.user_service import create_or_get_user
from services.recurring_service import apply_due_recurring
from config.settings import DEFAULT_TIMEZONE

logger = logging.getLogger(__name__)


async def _check_reminders(bot: Bot):
    """Проверяет напоминания каждую минуту."""
    reminders = await get_all_active_reminders()
    for rem in reminders:
        try:
            tz = ZoneInfo(rem["timezone"] or DEFAULT_TIMEZONE)
            now = datetime.now(tz)
            current_time = now.strftime("%H:%M")
            if current_time == rem["reminder_time"]:
                await bot.send_message(
                    rem["telegram_id"],
                    "🔔 <b>Напоминание!</b>\n\n"
                    "Не забудьте записать сегодняшние расходы 💰\n\n"
                    "Нажмите 📤 Расход или 📥 Доход",
                    parse_mode="HTML"
                )
        except Exception as e:
            logger.error(f"❌ Ошибка отправки напоминания {rem['telegram_id']}: {e}")


async def _apply_recurring_for_all(bot: Bot):
    """Применяет регулярные транзакции для всех пользователей."""
    try:
        import aiosqlite
        from config.settings import DB_PATH
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("SELECT id, telegram_id, name FROM users")
            users = await cursor.fetchall()

        for user_id, telegram_id, user_name in users:
            applied = await apply_due_recurring(user_id, user_name)
            if applied:
                lines = []
                for t in applied:
                    emoji = "📥" if t["type"] == "income" else "📤"
                    from utils.report_formatter import format_money
                    lines.append(f"{emoji} {t['name']}: {format_money(t['amount'])}")
                text = "🔄 <b>Регулярные транзакции применены:</b>\n\n" + "\n".join(lines)
                try:
                    await bot.send_message(telegram_id, text, parse_mode="HTML")
                except Exception:
                    pass
    except Exception as e:
        logger.error(f"❌ Ошибка apply_recurring: {e}", exc_info=True)


async def run_scheduler(bot: Bot):
    """Основной цикл планировщика. Запускать как asyncio task."""
    logger.info("🕐 Планировщик запущен")
    last_recurring_check = None

    while True:
        try:
            now = datetime.now()

            # Напоминания — каждую минуту
            await _check_reminders(bot)

            # Регулярные транзакции — раз в день в 00:01
            today = now.date()
            if now.hour == 0 and now.minute == 1 and last_recurring_check != today:
                last_recurring_check = today
                await _apply_recurring_for_all(bot)

        except Exception as e:
            logger.error(f"❌ Ошибка планировщика: {e}", exc_info=True)

        await asyncio.sleep(60)  # Проверяем каждую минуту