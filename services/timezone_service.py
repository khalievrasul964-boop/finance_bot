# services/transaction_service.py
import aiosqlite
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from config.settings import DB_PATH, DEFAULT_TIMEZONE
from storage.journal import log_to_user_file

logger = logging.getLogger(__name__)


def _now_for_user(timezone: str) -> str:
    """Возвращает текущее время пользователя в ISO формате."""
    tz = ZoneInfo(timezone or DEFAULT_TIMEZONE)
    return datetime.now(tz).replace(tzinfo=None).isoformat()


async def _get_user_timezone(user_id: int) -> str:
    """Получает часовой пояс пользователя из БД."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "SELECT timezone FROM users WHERE id = ?", (user_id,)
            )
            row = await cursor.fetchone()
            return row[0] if row and row[0] else DEFAULT_TIMEZONE
    except Exception:
        return DEFAULT_TIMEZONE


async def add_transaction(
    user_id: int,
    amount: float,
    trans_type: str,
    method: str,
    user_name: str,
    category: str = "Другое",
    description: str = None
) -> bool:
    try:
        timezone = await _get_user_timezone(user_id)
        created_at = _now_for_user(timezone)

        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                """INSERT INTO transactions
                   (user_id, amount, type, method,