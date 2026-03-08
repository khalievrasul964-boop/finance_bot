# database/db.py
import aiosqlite
from config.settings import DB_PATH

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                telegram_id INTEGER UNIQUE NOT NULL,
                name TEXT NOT NULL,
                timezone TEXT DEFAULT 'Europe/Moscow',
                monthly_budget REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                type TEXT CHECK(type IN ('income', 'expense')) NOT NULL,
                method TEXT CHECK(method IN ('cash', 'card')) NOT NULL,
                category TEXT DEFAULT 'Другое',
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS goals (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                target_amount REAL NOT NULL,
                current_amount REAL DEFAULT 0.0,
                deadline DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS category_limits (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                category TEXT NOT NULL,
                monthly_limit REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, category),
                FOREIGN KEY(user_id) REFERENCES users(id)            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS recurring_transactions (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                amount REAL NOT NULL,
                type TEXT CHECK(type IN ('income', 'expense')) NOT NULL,
                method TEXT CHECK(method IN ('cash', 'card')) NOT NULL,
                category TEXT NOT NULL,
                day_of_month INTEGER NOT NULL,
                is_active INTEGER DEFAULT 1,
                last_applied DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                telegram_id INTEGER NOT NULL,
                reminder_time TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)
        await db.commit()


async def migrate_db():
    """Добавляет новые колонки и таблицы если их нет."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in await cursor.fetchall()]
        if 'timezone' not in columns:
            await db.execute("ALTER TABLE users ADD COLUMN timezone TEXT DEFAULT 'Europe/Moscow'")
        if 'monthly_budget' not in columns:
            await db.execute("ALTER TABLE users ADD COLUMN monthly_budget REAL DEFAULT 0.0")

        cursor = await db.execute("PRAGMA table_info(transactions)")
        columns = [row[1] for row in await cursor.fetchall()]
        if 'category' not in columns:
            await db.execute("ALTER TABLE transactions ADD COLUMN category TEXT DEFAULT 'Другое'")
        if 'description' not in columns:
            await db.execute("ALTER TABLE transactions ADD COLUMN description TEXT")
        await db.commit()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS goals (
                id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL,
                name TEXT NOT NULL, target_amount REAL NOT NULL,
                current_amount REAL DEFAULT 0.0, deadline DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id));
            CREATE TABLE IF NOT EXISTS category_limits (
                id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL,
                category TEXT NOT NULL, monthly_limit REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, category),
                FOREIGN KEY(user_id) REFERENCES users(id));
            CREATE TABLE IF NOT EXISTS recurring_transactions (
                id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL,
                name TEXT NOT NULL, amount REAL NOT NULL,
                type TEXT CHECK(type IN ('income','expense')) NOT NULL,
                method TEXT CHECK(method IN ('cash','card')) NOT NULL,
                category TEXT NOT NULL, day_of_month INTEGER NOT NULL,
                is_active INTEGER DEFAULT 1, last_applied DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id));
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL,
                telegram_id INTEGER NOT NULL, reminder_time TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id));
        """)
        await db.commit()