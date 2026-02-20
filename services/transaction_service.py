# services/transaction_service.py
import aiosqlite
import logging
from datetime import datetime
from config.settings import DB_PATH
from storage.journal import log_to_user_file

logger = logging.getLogger(__name__)

async def add_transaction(
    user_id: int, 
    amount: float, 
    trans_type: str, 
    method: str, 
    user_name: str,
    category: str = "Другое",
    description: str = None
) -> bool:
    """
    Добавляет транзакцию в БД и логирует в файл пользователя.
    
    Args:
        user_id: ID пользователя
        amount: Сумма
        trans_type: Тип (income/expense)
        method: Способ (cash/card)
        user_name: Имя пользователя
        category: Категория
        description: Описание (опционально)
    
    Returns:
        bool: True если успешно, False если ошибка
    """
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                """
                INSERT INTO transactions (user_id, amount, type, method, category, description, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, amount, trans_type, method, category, description, datetime.utcnow().isoformat())
            )
            await db.commit()
            transaction_id = cursor.lastrowid
        
        # Запись в персональный файл
        emoji = "🟢" if trans_type == "income" else "🔴"
        method_str = "наличные" if method == "cash" else "карта"
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        cat_str = category if category else "без категории"
        line = f"{emoji} {now} | {amount:.2f} ₽ | {method_str} | {cat_str}"
        await log_to_user_file(user_name, line)
        
        logger.info(f"✅ Транзакция {transaction_id} добавлена для пользователя {user_name}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка при добавлении транзакции: {e}", exc_info=True)
        return False

async def delete_last_transaction(user_id: int, user_name: str) -> bool:
    """
    Удаляет последнюю транзакцию пользователя.
    
    Returns:
        bool: True если успешно, False если ошибка или нет транзакций
    """
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Находим последнюю транзакцию
            cursor = await db.execute(
                """
                SELECT id, amount, type, category FROM transactions 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT 1
                """,
                (user_id,)
            )
            row = await cursor.fetchone()
            
            if not row:
                return False
            
            trans_id, amount, trans_type, category = row
            
            # Удаляем транзакцию
            await db.execute("DELETE FROM transactions WHERE id = ?", (trans_id,))
            await db.commit()
        
        emoji = "🟢" if trans_type == "income" else "🔴"
        logger.info(f"❌ Удалена транзакция {trans_id} пользователя {user_name}: {amount} ₽ ({category})")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка при удалении транзакции: {e}", exc_info=True)
        return False

async def get_last_transaction(user_id: int) -> dict:
    """Получает информацию о последней транзакции."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                """
                SELECT id, amount, type, category, method, created_at FROM transactions 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT 1
                """,
                (user_id,)
            )
            row = await cursor.fetchone()
            
            if not row:
                return None
            
            return {
                "id": row[0],
                "amount": row[1],
                "type": row[2],
                "category": row[3],
                "method": row[4],
                "created_at": row[5]
            }
    except Exception as e:
        logger.error(f"❌ Ошибка при получении последней транзакции: {e}", exc_info=True)
        return None