# services/user_service.py
import aiosqlite
from config.settings import DB_PATH
from storage.journal import ensure_user_header

async def create_or_get_user(telegram_id: int, name: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT id, name, monthly_budget, telegram_id FROM users WHERE telegram_id = ?", (telegram_id,))
        row = await cursor.fetchone()
        if row:
            if name and row[1] != name:
                await db.execute("UPDATE users SET name = ? WHERE telegram_id = ?", (name, telegram_id))
                await db.commit()
                await ensure_user_header(name)
                return {"id": row[0], "name": name, "monthly_budget": row[2], "telegram_id": row[3]}
            return {"id": row[0], "name": row[1], "monthly_budget": row[2], "telegram_id": row[3]}
        else:
            if not name:
                return {"id": None, "name": None, "monthly_budget": 0.0, "telegram_id": telegram_id}
            cursor = await db.execute(
                "INSERT INTO users (telegram_id, name) VALUES (?, ?)",
                (telegram_id, name)
            )
            await db.commit()
            await ensure_user_header(name)
            return {"id": cursor.lastrowid, "name": name, "monthly_budget": 0.0, "telegram_id": telegram_id}

async def set_budget(user_id: int, budget: float) -> bool:
    """Устанавливает месячный бюджет для пользователя."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE users SET monthly_budget = ? WHERE id = ?",
                (budget, user_id)
            )
            await db.commit()
        return True
    except Exception:
        return False

async def get_budget(user_id: int) -> float:
    """Получает месячный бюджет пользователя."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "SELECT monthly_budget FROM users WHERE id = ?",
                (user_id,)
            )
            row = await cursor.fetchone()
            return row[0] if row else 0.0
    except Exception:
        return 0.0