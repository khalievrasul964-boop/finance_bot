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
                   (user_id, amount, type, method, category, description, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (user_id, amount, trans_type, method, category, description, created_at)
            )            await db.commit()
            transaction_id = cursor.lastrowid

        emoji = "🟢" if trans_type == "income" else "🔴"
        method_str = "наличные" if method == "cash" else "карта"
        now_str = datetime.fromisoformat(created_at).strftime("%Y-%m-%d %H:%M")
        line = f"{emoji} {now_str} | {amount:.2f} ₽ | {method_str} | {category}"
        await log_to_user_file(user_name, line)

        logger.info(f"✅ Транзакция {transaction_id} добавлена для {user_name} ({timezone})")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка add_transaction: {e}", exc_info=True)
        return False


async def delete_last_transaction(user_id: int, user_name: str) -> bool:
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                """SELECT id, amount, type, category FROM transactions
                   WHERE user_id = ? ORDER BY created_at DESC LIMIT 1""",
                (user_id,)
            )
            row = await cursor.fetchone()
            if not row:
                return False
            trans_id = row[0]
            await db.execute("DELETE FROM transactions WHERE id = ?", (trans_id,))
            await db.commit()
        logger.info(f"🗑 Удалена транзакция {trans_id} пользователя {user_name}")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка delete_last_transaction: {e}", exc_info=True)
        return False


async def get_last_transaction(user_id: int) -> dict:
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                """SELECT id, amount, type, category, method, created_at
                   FROM transactions WHERE user_id = ?
                   ORDER BY created_at DESC LIMIT 1""",
                (user_id,)
            )
            row = await cursor.fetchone()
            if not row:
                return None
            return {                "id": row[0], "amount": row[1], "type": row[2],
                "category": row[3], "method": row[4], "created_at": row[5]
            }
    except Exception as e:
        logger.error(f"❌ Ошибка get_last_transaction: {e}", exc_info=True)
        return None