# services/report_service.py
import aiosqlite
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo
from config.settings import DB_PATH, DEFAULT_TIMEZONE
from utils.report_formatter import format_report, format_detailed_report


def _get_user_tz(timezone: str) -> ZoneInfo:
    try:
        return ZoneInfo(timezone or DEFAULT_TIMEZONE)
    except Exception:
        return ZoneInfo(DEFAULT_TIMEZONE)


async def _get_timezone(user_id: int) -> str:
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "SELECT timezone FROM users WHERE id = ?", (user_id,)
            )
            row = await cursor.fetchone()
            return row[0] if row and row[0] else DEFAULT_TIMEZONE
    except Exception:
        return DEFAULT_TIMEZONE


def get_day_range_for_tz(target_date: date, timezone: str):
    tz = _get_user_tz(timezone)
    start = datetime(target_date.year, target_date.month, target_date.day, 0, 0, 0, tzinfo=tz)
    end = start + timedelta(days=1)
    # Переводим в naive UTC для сравнения с БД (которая хранит local-naive)
    # Используем naive local time напрямую
    start_naive = datetime(target_date.year, target_date.month, target_date.day, 0, 0, 0)
    end_naive = start_naive + timedelta(days=1)
    return start_naive, end_naive


def get_week_range_for_tz(timezone: str):
    tz = _get_user_tz(timezone)
    today = datetime.now(tz).date()
    monday = today - timedelta(days=today.weekday())
    start = datetime(monday.year, monday.month, monday.day, 0, 0, 0)
    end = start + timedelta(weeks=1)
    return start, end


def get_month_range_for_tz(timezone: str):
    tz = _get_user_tz(timezone)
    now = datetime.now(tz)    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1)
    else:
        end = start.replace(month=start.month + 1)
    return start, end


async def _fetch_detailed_transactions(user_id: int, start, end):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT type, amount, method, category, created_at
            FROM transactions
            WHERE user_id = ? AND created_at >= ? AND created_at < ?
            ORDER BY created_at ASC
        """, (user_id, start.isoformat(), end.isoformat()))
        rows = await cursor.fetchall()

    transactions = []
    for typ, amount, method, category, created_at in rows:
        dt = datetime.fromisoformat(created_at)
        transactions.append({
            "type": typ, "amount": amount, "method": method,
            "category": category, "datetime": dt,
            "date": dt.date(), "time": dt.strftime("%H:%M")
        })
    return transactions


async def _fetch_income_expense_by_method(user_id: int, start, end):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT type, method, SUM(amount)
            FROM transactions
            WHERE user_id = ? AND created_at >= ? AND created_at < ?
            GROUP BY type, method
        """, (user_id, start.isoformat(), end.isoformat()))
        rows = await cursor.fetchall()

    income_cash = income_card = expense_cash = expense_card = 0.0
    for typ, method, total in rows:
        if typ == "income":
            if method == "cash": income_cash = total
            else: income_card = total
        elif typ == "expense":
            if method == "cash": expense_cash = total
            else: expense_card = total
    return income_cash, income_card, expense_cash, expense_card

async def get_daily_report_text(user_id: int, target_date: date) -> str:
    timezone = await _get_timezone(user_id)
    start, end = get_day_range_for_tz(target_date, timezone)
    transactions = await _fetch_detailed_transactions(user_id, start, end)
    if not transactions:
        return "Сегодня ещё нет операций."
    return format_detailed_report(
        f"📊 Отчёт за день {target_date.strftime('%d.%m.%Y')}:", transactions
    )


async def get_weekly_report_text(user_id: int) -> str:
    timezone = await _get_timezone(user_id)
    start, end = get_week_range_for_tz(timezone)
    transactions = await _fetch_detailed_transactions(user_id, start, end)
    if not transactions:
        return "За эту неделю ещё нет операций."
    return format_detailed_report("📆 Отчёт за неделю (Пн–Вс):", transactions)


async def get_monthly_report_text(user_id: int) -> str:
    timezone = await _get_timezone(user_id)
    start, end = get_month_range_for_tz(timezone)
    transactions = await _fetch_detailed_transactions(user_id, start, end)
    if not transactions:
        return "За этот месяц ещё нет операций."
    return format_detailed_report("🗓 Отчёт за месяц:", transactions)


async def get_user_balance(user_id: int) -> tuple:
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "SELECT type, SUM(amount), COUNT(*) FROM transactions WHERE user_id = ? GROUP BY type",
                (user_id,)
            )
            rows = await cursor.fetchall()
        total_income = total_expense = total_count = 0.0
        for typ, amount, count in rows:
            total_count += count
            if typ == "income": total_income = amount
            elif typ == "expense": total_expense = amount
        return total_income - total_expense, total_income, total_expense, int(total_count)
    except Exception:
        return 0, 0, 0, 0


async def get_last_transactions(user_id: int, limit: int = 5) -> list:
    try:
        async with aiosqlite.connect(DB_PATH) as db:            cursor = await db.execute(
                """SELECT amount, type, category, method, created_at FROM transactions
                   WHERE user_id = ? ORDER BY created_at DESC LIMIT ?""",
                (user_id, limit)
            )
            rows = await cursor.fetchall()
        result = []
        for amount, typ, category, method, created_at in rows:
            dt = datetime.fromisoformat(created_at)
            result.append({
                "amount": amount, "type": typ, "category": category,
                "method": method, "time": dt.strftime("%H:%M"),
                "date": dt.strftime("%d.%m.%Y")
            })
        return result
    except Exception:
        return []


async def get_budget_info(user_id: int, monthly_budget: float) -> dict:
    try:
        timezone = await _get_timezone(user_id)
        start, end = get_month_range_for_tz(timezone)
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                """SELECT SUM(amount) FROM transactions
                   WHERE user_id = ? AND type = 'expense' AND created_at >= ? AND created_at < ?""",
                (user_id, start.isoformat(), end.isoformat())
            )
            row = await cursor.fetchone()
        total_expense = row[0] if row and row[0] else 0.0
        remaining = monthly_budget - total_expense if monthly_budget > 0 else 0.0
        percentage = (total_expense / monthly_budget * 100) if monthly_budget > 0 else 0.0
        return {"budget": monthly_budget, "spent": total_expense,
                "remaining": remaining, "percentage": percentage}
    except Exception:
        return {"budget": monthly_budget, "spent": 0.0,
                "remaining": monthly_budget, "percentage": 0.0}


async def get_category_stats(user_id: int, trans_type: str = None) -> dict:
    try:
        timezone = await _get_timezone(user_id)
        start, end = get_month_range_for_tz(timezone)
        async with aiosqlite.connect(DB_PATH) as db:
            if trans_type:
                cursor = await db.execute(
                    """SELECT category, SUM(amount), COUNT(*) FROM transactions
                       WHERE user_id = ? AND type = ? AND created_at >= ? AND created_at < ?
                       GROUP BY category ORDER BY SUM(amount) DESC""",                    (user_id, trans_type, start.isoformat(), end.isoformat())
                )
            else:
                cursor = await db.execute(
                    """SELECT category, SUM(amount), COUNT(*) FROM transactions
                       WHERE user_id = ? AND created_at >= ? AND created_at < ?
                       GROUP BY category ORDER BY SUM(amount) DESC""",
                    (user_id, start.isoformat(), end.isoformat())
                )
            rows = await cursor.fetchall()
        total = sum(r[1] for r in rows) if rows else 0.0
        categories = [
            {"name": r[0], "amount": r[1], "count": r[2],
             "percentage": (r[1] / total * 100) if total > 0 else 0.0}
            for r in rows
        ]
        return {"total": total, "categories": categories, "type": trans_type}
    except Exception:
        return {"total": 0.0, "categories": [], "type": trans_type}


async def search_transactions(user_id: int, query: str = None,
                               min_amount: float = None, max_amount: float = None,
                               trans_type: str = None) -> list:
    try:
        sql = "SELECT amount, type, category, method, created_at FROM transactions WHERE user_id = ?"
        params = [user_id]
        if trans_type:
            sql += " AND type = ?"; params.append(trans_type)
        if min_amount is not None:
            sql += " AND amount >= ?"; params.append(min_amount)
        if max_amount is not None:
            sql += " AND amount <= ?"; params.append(max_amount)
        if query:
            sql += " AND (category LIKE ? OR description LIKE ?)"
            params += [f"%{query}%", f"%{query}%"]
        sql += " ORDER BY created_at DESC LIMIT 50"
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(sql, params)
            rows = await cursor.fetchall()
        result = []
        for amount, typ, category, method, created_at in rows:
            dt = datetime.fromisoformat(created_at)
            result.append({
                "amount": amount, "type": typ, "category": category,
                "method": method, "time": dt.strftime("%H:%M"),
                "date": dt.strftime("%d.%m.%Y")
            })
        return result
    except Exception:        return []


async def get_daily_spending_data(user_id: int, days: int = 30) -> dict:
    try:
        timezone = await _get_timezone(user_id)
        tz = _get_user_tz(timezone)
        end_date = datetime.now(tz).replace(tzinfo=None)
        start_date = end_date - timedelta(days=days)
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                """SELECT DATE(created_at), SUM(amount) FROM transactions
                   WHERE user_id = ? AND type = 'expense'
                   AND created_at >= ? AND created_at < ?
                   GROUP BY DATE(created_at) ORDER BY created_at ASC""",
                (user_id, start_date.isoformat(), end_date.isoformat())
            )
            rows = await cursor.fetchall()
        return {datetime.fromisoformat(d).strftime("%d.%m"): t or 0.0 for d, t in rows}
    except Exception:
        return {}


async def get_category_distribution(user_id: int, trans_type: str = None) -> dict:
    try:
        sql = "SELECT category, SUM(amount) FROM transactions WHERE user_id = ?"
        params = [user_id]
        if trans_type:
            sql += " AND type = ?"; params.append(trans_type)
        sql += " GROUP BY category ORDER BY SUM(amount) DESC"
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(sql, params)
            rows = await cursor.fetchall()
        return {cat: total or 0.0 for cat, total in rows}
    except Exception:
        return {}


async def get_income_vs_expense(user_id: int) -> tuple:
    try:
        timezone = await _get_timezone(user_id)
        start, end = get_month_range_for_tz(timezone)
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                """SELECT SUM(amount) FROM transactions
                   WHERE user_id = ? AND type = 'income'
                   AND created_at >= ? AND created_at < ?""",
                (user_id, start.isoformat(), end.isoformat())
            )
            income = (await cursor.fetchone())[0] or 0.0            cursor = await db.execute(
                """SELECT SUM(amount) FROM transactions
                   WHERE user_id = ? AND type = 'expense'
                   AND created_at >= ? AND created_at < ?""",
                (user_id, start.isoformat(), end.isoformat())
            )
            expense = (await cursor.fetchone())[0] or 0.0
        return income, expense
    except Exception:
        return 0.0, 0.0


async def get_monthly_trend(user_id: int, months: int = 6) -> dict:
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                """SELECT strftime('%m-%Y', created_at), SUM(amount)
                   FROM transactions WHERE user_id = ? AND type = 'expense'
                   GROUP BY strftime('%m-%Y', created_at)
                   ORDER BY strftime('%Y-%m', created_at) DESC LIMIT ?""",
                (user_id, months)
            )
            rows = await cursor.fetchall()
        names = {'01':'Янв','02':'Фев','03':'Мар','04':'Апр','05':'Май','06':'Июн',
                 '07':'Июл','08':'Авг','09':'Сен','10':'Окт','11':'Ноя','12':'Дек'}
        trend = {}
        for month_year, total in reversed(rows):
            if month_year:
                m, y = month_year.split('-')
                trend[f"{names.get(m, m)} {y}"] = total or 0.0
        return trend
    except Exception:
        return {}