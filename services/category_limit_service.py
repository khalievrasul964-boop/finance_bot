# services/category_limit_service.py
"""Лимиты расходов по категориям."""
import aiosqlite
import logging
from config.settings import DB_PATH

logger = logging.getLogger(__name__)


async def set_category_limit(user_id: int, category: str, limit: float) -> bool:
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                """INSERT INTO category_limits (user_id, category, monthly_limit)
                   VALUES (?, ?, ?)
                   ON CONFLICT(user_id, category) DO UPDATE SET monthly_limit = excluded.monthly_limit""",
                (user_id, category, limit)
            )
            await db.commit()
        return True
    except Exception as e:
        logger.error(f"❌ set_category_limit: {e}", exc_info=True)
        return False


async def get_category_limits(user_id: int) -> list:
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "SELECT category, monthly_limit FROM category_limits WHERE user_id = ? ORDER BY category",
                (user_id,)
            )
            rows = await cursor.fetchall()
        return [{"category": r[0], "limit": r[1]} for r in rows]
    except Exception:
        return []


async def delete_category_limit(user_id: int, category: str) -> bool:
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "DELETE FROM category_limits WHERE user_id = ? AND category = ?",
                (user_id, category)
            )
            await db.commit()
        return True
    except Exception:
        return False


async def check_category_limit(user_id: int, category: str, start_iso: str, end_iso: str) -> dict | None:
    """
    Проверяет, не превышен ли лимит по категории за текущий месяц.
    Возвращает dict с инфо если лимит установлен, иначе None.
    """
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "SELECT monthly_limit FROM category_limits WHERE user_id = ? AND category = ?",
                (user_id, category)
            )
            row = await cursor.fetchone()
            if not row:
                return None
            limit = row[0]

            cursor = await db.execute(
                """SELECT SUM(amount) FROM transactions
                   WHERE user_id = ? AND category = ? AND type = 'expense'
                   AND created_at >= ? AND created_at < ?""",
                (user_id, category, start_iso, end_iso)
            )
            spent_row = await cursor.fetchone()
            spent = spent_row[0] if spent_row and spent_row[0] else 0.0

        percentage = (spent / limit * 100) if limit > 0 else 0.0
        return {
            "category": category,
            "limit": limit,
            "spent": spent,
            "remaining": max(0, limit - spent),
            "percentage": percentage,
            "exceeded": spent > limit,
            "warning": percentage >= 80,
        }
    except Exception as e:
        logger.error(f"❌ check_category_limit: {e}", exc_info=True)
        return None