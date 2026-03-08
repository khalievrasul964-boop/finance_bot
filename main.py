# main.py
import asyncio
import logging
import os
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не найден!")

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from database.db import init_db, migrate_db
from handlers import start, income, expense, reports, goals
from handlers import settings_handler, export_handler, quick_input_handler
from services.scheduler import run_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def set_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="🚀 Главное меню"),
        BotCommand(command="help", description="📖 Справка"),
        BotCommand(command="undo", description="↩ Отменить последнюю операцию"),
        BotCommand(command="goals", description="🎯 Финансовые цели"),
        BotCommand(command="timezone", description="🌍 Часовой пояс"),
        BotCommand(command="reminder", description="🔔 Напоминание"),
        BotCommand(command="limits", description="📊 Лимиты по категориям"),
        BotCommand(command="setlimit", description="📊 Установить лимит"),
        BotCommand(command="recurring", description="🔄 Регулярные транзакции"),
        BotCommand(command="addrecurring", description="🔄 Добавить регулярную"),
        BotCommand(command="export", description="📤 Экспорт в CSV"),
    ]
    await bot.set_my_commands(commands)


async def main():
    await init_db()
    await migrate_db()
    logger.info("✅ База данных инициализирована")

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    await set_bot_commands(bot)

    # Порядок важен: quick_input должен быть ПОСЛЕДНИМ
    # чтобы не перехватывать команды FSM
    dp.include_routers(
        start.router,
        income.router,
        expense.router,
        reports.router,
        goals.router,
        settings_handler.router,
        export_handler.router,
        quick_input_handler.router,   # ← последним!
    )

    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("🚀 Бот запущен!")

    # Запускаем планировщик параллельно с polling
    await asyncio.gather(
        dp.start_polling(bot),
        run_scheduler(bot),
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Бот остановлен")