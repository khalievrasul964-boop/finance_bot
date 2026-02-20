# main.py
import asyncio
import logging
import os
from dotenv import load_dotenv

# Загружаем переменные окружения из .env
load_dotenv()

# Проверяем наличие токена сразу (для быстрой диагностики)
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не найден! Убедитесь, что файл .env существует и содержит строку: BOT_TOKEN=ваш_токен")

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from database.db import init_db, migrate_db
from handlers import start, income, expense, reports, goals

# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

async def set_bot_commands(bot: Bot):
    """Устанавливает список команд бота."""
    commands = [
        BotCommand(command="start", description="🚀 Начать работу"),
        BotCommand(command="help", description="📖 Справка и инструкции"),
        BotCommand(command="undo", description="↩ Отменить последнюю транзакцию"),
        BotCommand(command="goals", description="🎯 Финансовые цели"),
        BotCommand(command="addgoal", description="🎯 Создать цель"),
    ]
    await bot.set_my_commands(commands)
    logger.info("✅ Команды бота установлены")

async def main():
    try:
        # Инициализируем базу данных
        await init_db()
        await migrate_db()
        logger.info("✅ База данных инициализирована")

        # Создаём экземпляры бота и диспетчера
        bot = Bot(token=BOT_TOKEN)
        dp = Dispatcher()

        # Устанавливаем команды
        await set_bot_commands(bot)

        # Подключаем роутеры
        dp.include_routers(
            start.router,
            income.router,
            expense.router,
            reports.router,
            goals.router
        )

        # Удаляем webhook и запускаем polling
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("🚀 Бот запущен и ожидает сообщения...")
        await dp.start_polling(bot)
        
    except Exception as e:
        logger.error(f"❌ Ошибка при запуске бота: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}", exc_info=True)
    except Exception as e:
        logging.error(f"💥 Критическая ошибка: {e}")
        raise