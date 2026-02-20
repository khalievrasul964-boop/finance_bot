import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is required")

# Часовой пояс пользователя по умолчанию (UTC)
# Пользователи могут установить свой пояс через /timezone
DEFAULT_TIMEZONE = os.getenv("DEFAULT_TIMEZONE", "UTC")

DB_PATH = BASE_DIR / "data" / "finance.db"
JOURNAL_DIR = BASE_DIR / "journals"

DB_PATH.parent.mkdir(parents=True, exist_ok=True)
JOURNAL_DIR.mkdir(exist_ok=True)

# Категории расходов
EXPENSE_CATEGORIES = [
    "🍔 Еда",
    "🚗 Транспорт", 
    "🏠 Жилье",
    "💻 Техника",
    "👗 Одежда",
    "📚 Образование",
    "🏋️ Спорт",
    "🎬 Развлечения",
    "💊 Здоровье",
    "🛒 Покупки"
]

# Категории доходов
INCOME_CATEGORIES = [
    "💼 Зарплата",
    "🎁 Подарок",
    "📈 Инвестиции",
    "💰 Бонус",
    "🏪 Фриланс",
    "📦 Продажа",
    "🏷 Другое"
]

# Лимит максимальной суммы транзакции (10 млн руб)
MAX_TRANSACTION_AMOUNT = 10_000_000.0
MIN_TRANSACTION_AMOUNT = 0.01