# services/goal_service.py
"""Сервис для работы с финансовыми целями (копилками)."""
import aiosqlite
import logging
from datetime import date
from config.settings import DB_PATH

logger = logging.getLogger(__name__)


async def create_goal(user_id: int, name: str, target_amount: float, deadline: date = None) -> int | None:
    """Создаёт новую цель. Возвращает id цели или None."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                """
                INSERT INTO goals (user_id, name, target_amount, deadline)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, name.strip(), target_amount, deadline.isoformat() if deadline else None)
            )
            await db.commit()
            return cursor.lastrowid
    except Exception as e:
        logger.error(f"❌ Ошибка при создании цели: {e}", exc_info=True)
        return None


async def get_goals(user_id: int) -> list[dict]:
    """Возвращает список целей пользователя."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT id, name, target_amount, current_amount, deadline
                FROM goals WHERE user_id = ?
                ORDER BY created_at DESC
                """,
                (user_id,)
            )
            rows = await cursor.fetchall()
            return [
                {
                    "id": r["id"],
                    "name": r["name"],
                    "target_amount": r["target_amount"],
                    "current_amount": r["current_amount"],
                    "deadline": r["deadline"],
                    "percentage": min(100.0, (r["current_amount"] / r["target_amount"] * 100) if r["target_amount"] > 0 else 0),
                    "remaining": max(0, r["target_amount"] - r["current_amount"]),
                }
                for r in rows
            ]
    except Exception as e:
        logger.error(f"❌ Ошибка при получении целей: {e}", exc_info=True)
        return []


async def add_to_goal(user_id: int, goal_id: int, amount: float) -> bool:
    """Добавляет сумму к цели. Проверяет, что цель принадлежит пользователю."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Проверяем, что цель принадлежит пользователю
            cursor = await db.execute(
                "SELECT id FROM goals WHERE id = ? AND user_id = ?",
                (goal_id, user_id)
            )
            if not await cursor.fetchone():
                return False

            await db.execute(
                """
                UPDATE goals SET current_amount = current_amount + ?
                WHERE id = ? AND user_id = ?
                """,
                (amount, goal_id, user_id)
            )
            await db.commit()
            return True
    except Exception as e:
        logger.error(f"❌ Ошибка при пополнении цели: {e}", exc_info=True)
        return False


async def delete_goal(user_id: int, goal_id: int) -> bool:
    """Удаляет цель. Проверяет принадлежность пользователю."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "DELETE FROM goals WHERE id = ? AND user_id = ?",
                (goal_id, user_id)
            )
            await db.commit()
            return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"❌ Ошибка при удалении цели: {e}", exc_info=True)
        return False


def get_monthly_saving_suggestion(target: float, current: float, deadline: date) -> float | None:
    """Сколько нужно откладывать в месяц до дедлайна."""
    if not deadline:
        return None
    today = date.today()
    if deadline <= today:
        return None
    months_left = max(1, (deadline - today).days / 30)
    remaining = max(0, target - current)
    return remaining / months_left if remaining > 0 else 0
