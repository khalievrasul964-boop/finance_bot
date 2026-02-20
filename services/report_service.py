# services/report_service.py
import aiosqlite
from datetime import datetime, timedelta, date
from config.settings import DB_PATH
from utils.report_formatter import format_report, format_detailed_report

def get_day_range(target_date: date):
    start = datetime.combine(target_date, datetime.min.time())
    end = start + timedelta(days=1)
    return start, end

def get_week_range():
    today = datetime.utcnow().date()
    monday = today - timedelta(days=today.weekday())
    start = datetime.combine(monday, datetime.min.time())
    end = start + timedelta(weeks=1)
    return start, end

def get_month_range():
    now = datetime.utcnow()
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1)
    else:
        end = start.replace(month=start.month + 1)
    return start, end

async def _fetch_income_expense_by_method(user_id: int, start, end):
    """Получает агрегированные данные по дохода и расходам."""
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
            if method == "cash":
                income_cash = total
            elif method == "card":
                income_card = total
        elif typ == "expense":
            if method == "cash":
                expense_cash = total
            elif method == "card":
                expense_card = total
    return income_cash, income_card, expense_cash, expense_card

async def _fetch_detailed_transactions(user_id: int, start, end):
    """Получает详细 список всех операций с временем."""
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
            "type": typ,
            "amount": amount,
            "method": method,
            "category": category,
            "datetime": dt,
            "date": dt.date(),
            "time": dt.strftime("%H:%M")
        })
    return transactions

async def get_daily_report_text(user_id: int, target_date: date) -> str:
    start, end = get_day_range(target_date)
    
    # Получаем детальные операции
    transactions = await _fetch_detailed_transactions(user_id, start, end)
    
    if not transactions:
        return "Сегодня ещё нет операций."
    
    return format_detailed_report(
        f"📊 Отчёт за день {target_date.strftime('%d.%m.%Y')}:",
        transactions
    )

async def get_weekly_report_text(user_id: int) -> str:
    start, end = get_week_range()
    
    # Получаем детальные операции
    transactions = await _fetch_detailed_transactions(user_id, start, end)
    
    if not transactions:
        return "За эту неделю ещё нет операций."
    
    return format_detailed_report(
        "📆 Отчёт за неделю (Пн–Вс):",
        transactions
    )

async def get_monthly_report_text(user_id: int) -> str:
    start, end = get_month_range()
    
    # Получаем детальные операции
    transactions = await _fetch_detailed_transactions(user_id, start, end)
    
    if not transactions:
        return "За этот месяц ещё нет операций."
    
    return format_detailed_report(
        "🗓 Отчёт за месяц:",
        transactions
    )

async def get_user_balance(user_id: int) -> tuple:
    """Получает текущий баланс и общую статистику пользователя.
    
    Returns:
        (balance, total_income, total_expense, transaction_count)
    """
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("""
                SELECT type, SUM(amount), COUNT(*) FROM transactions
                WHERE user_id = ?
                GROUP BY type
            """, (user_id,))
            rows = await cursor.fetchall()
        
        total_income = total_expense = 0.0
        total_count = 0
        
        for typ, amount, count in rows:
            total_count += count
            if typ == "income":
                total_income = amount
            elif typ == "expense":
                total_expense = amount
        
        balance = total_income - total_expense
        return balance, total_income, total_expense, total_count
    except Exception as e:
        return 0, 0, 0, 0

async def get_last_transactions(user_id: int, limit: int = 5) -> list:
    """Получает последние N транзакций пользователя."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("""
                SELECT amount, type, category, method, created_at FROM transactions
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (user_id, limit))
            rows = await cursor.fetchall()
        
        transactions = []
        for amount, typ, category, method, created_at in rows:
            dt = datetime.fromisoformat(created_at)
            transactions.append({
                "amount": amount,
                "type": typ,
                "category": category,
                "method": method,
                "time": dt.strftime("%H:%M"),
                "date": dt.strftime("%d.%m.%Y")
            })
        
        return transactions
    except Exception as e:
        return []

async def get_budget_info(user_id: int, monthly_budget: float) -> dict:
    """Получает информацию о бюджете и расходах в текущем месяце."""
    try:
        start, end = get_month_range()
        
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("""
                SELECT SUM(amount) FROM transactions
                WHERE user_id = ? AND type = 'expense' AND created_at >= ? AND created_at < ?
            """, (user_id, start.isoformat(), end.isoformat()))
            row = await cursor.fetchone()
        
        total_expense = row[0] if row and row[0] else 0.0
        remaining = monthly_budget - total_expense if monthly_budget > 0 else 0.0
        percentage = (total_expense / monthly_budget * 100) if monthly_budget > 0 else 0.0
        
        return {
            "budget": monthly_budget,
            "spent": total_expense,
            "remaining": remaining,
            "percentage": percentage
        }
    except Exception as e:
        return {
            "budget": monthly_budget,
            "spent": 0.0,
            "remaining": monthly_budget,
            "percentage": 0.0
        }

async def get_category_stats(user_id: int, trans_type: str = None) -> dict:
    """Получает статистику по категориям за текущий месяц.
    
    Args:
        user_id: ID пользователя
        trans_type: 'income' или 'expense' для фильтра, или None для всех
    
    Returns:
        dict с категориями, суммами и процентами
    """
    try:
        start, end = get_month_range()
        
        async with aiosqlite.connect(DB_PATH) as db:
            if trans_type:
                cursor = await db.execute("""
                    SELECT category, SUM(amount), COUNT(*) FROM transactions
                    WHERE user_id = ? AND type = ? AND created_at >= ? AND created_at < ?
                    GROUP BY category
                    ORDER BY SUM(amount) DESC
                """, (user_id, trans_type, start.isoformat(), end.isoformat()))
            else:
                cursor = await db.execute("""
                    SELECT category, SUM(amount), COUNT(*) FROM transactions
                    WHERE user_id = ? AND created_at >= ? AND created_at < ?
                    GROUP BY category
                    ORDER BY SUM(amount) DESC
                """, (user_id, start.isoformat(), end.isoformat()))
            
            rows = await cursor.fetchall()
        
        # Подсчитываем общую сумму
        total = sum(row[1] for row in rows) if rows else 0.0
        
        # Формируем результат
        categories = []
        for category, amount, count in rows:
            percentage = (amount / total * 100) if total > 0 else 0.0
            categories.append({
                "name": category,
                "amount": amount,
                "count": count,
                "percentage": percentage
            })
        
        return {
            "total": total,
            "categories": categories,
            "type": trans_type
        }
    except Exception as e:
        return {
            "total": 0.0,
            "categories": [],
            "type": trans_type
        }

async def search_transactions(user_id: int, query: str = None, min_amount: float = None, max_amount: float = None, trans_type: str = None) -> list:
    """Поиск транзакций по различным критериям.
    
    Args:
        user_id: ID пользователя
        query: Поисковый запрос (категория, описание)
        min_amount: Минимальная сумма
        max_amount: Максимальная сумма
        trans_type: 'income' или 'expense'
    
    Returns:
        Список найденных транзакций
    """
    try:
        sql = "SELECT amount, type, category, method, created_at FROM transactions WHERE user_id = ?"
        params = [user_id]
        
        # Добавляем фильтр по типу
        if trans_type:
            sql += " AND type = ?"
            params.append(trans_type)
        
        # Добавляем фильтр по диапазону сумм
        if min_amount is not None:
            sql += " AND amount >= ?"
            params.append(min_amount)
        
        if max_amount is not None:
            sql += " AND amount <= ?"
            params.append(max_amount)
        
        # Добавляем поиск по категории
        if query:
            sql += " AND (category LIKE ? OR description LIKE ?)"
            search_pattern = f"%{query}%"
            params.append(search_pattern)
            params.append(search_pattern)
        
        # Сортируем по дате (свежие сверху)
        sql += " ORDER BY created_at DESC LIMIT 50"
        
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(sql, params)
            rows = await cursor.fetchall()
        
        transactions = []
        for amount, typ, category, method, created_at in rows:
            dt = datetime.fromisoformat(created_at)
            transactions.append({
                "amount": amount,
                "type": typ,
                "category": category,
                "method": method,
                "time": dt.strftime("%H:%M"),
                "date": dt.strftime("%d.%m.%Y")
            })
        
        return transactions
    except Exception as e:
        return []

async def get_daily_spending_data(user_id: int, days: int = 30) -> dict:
    """Получает данные расходов по дням за последние N дней.
    
    Args:
        user_id: ID пользователя
        days: Количество дней для анализа
    
    Returns:
        Словарь {дата (DD.MM): сумма_расходов}
    """
    try:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("""
                SELECT DATE(created_at), SUM(amount)
                FROM transactions
                WHERE user_id = ? AND type = 'expense' 
                  AND created_at >= ? AND created_at < ?
                GROUP BY DATE(created_at)
                ORDER BY created_at ASC
            """, (user_id, start_date.isoformat(), end_date.isoformat()))
            rows = await cursor.fetchall()
        
        daily_data = {}
        for date_str, total in rows:
            # Преобразуем ISO дату в DD.MM формат
            date_obj = datetime.fromisoformat(date_str)
            formatted_date = date_obj.strftime("%d.%m")
            daily_data[formatted_date] = total or 0.0
        
        return daily_data
    except Exception as e:
        return {}

async def get_category_distribution(user_id: int, trans_type: str = None) -> dict:
    """Получает распределение транзакций по категориям.
    
    Args:
        user_id: ID пользователя
        trans_type: Тип транзакции ('income' или 'expense') или None для обоих
    
    Returns:
        Словарь {категория: сумма}
    """
    try:
        sql = "SELECT category, SUM(amount) FROM transactions WHERE user_id = ?"
        params = [user_id]
        
        if trans_type:
            sql += " AND type = ?"
            params.append(trans_type)
        
        sql += " GROUP BY category ORDER BY SUM(amount) DESC"
        
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(sql, params)
            rows = await cursor.fetchall()
        
        distribution = {}
        for category, total in rows:
            distribution[category] = total or 0.0
        
        return distribution
    except Exception as e:
        return {}

async def get_income_vs_expense(user_id: int) -> tuple:
    """Получает сравнение дохода и расходов за текущий месяц.
    
    Returns:
        Кортеж (total_income, total_expense)
    """
    try:
        start, end = get_month_range()
        
        async with aiosqlite.connect(DB_PATH) as db:
            # Получаем доход
            cursor = await db.execute("""
                SELECT SUM(amount) FROM transactions
                WHERE user_id = ? AND type = 'income'
                  AND created_at >= ? AND created_at < ?
            """, (user_id, start.isoformat(), end.isoformat()))
            income_result = await cursor.fetchone()
            total_income = income_result[0] if income_result[0] else 0.0
            
            # Получаем расходы
            cursor = await db.execute("""
                SELECT SUM(amount) FROM transactions
                WHERE user_id = ? AND type = 'expense'
                  AND created_at >= ? AND created_at < ?
            """, (user_id, start.isoformat(), end.isoformat()))
            expense_result = await cursor.fetchone()
            total_expense = expense_result[0] if expense_result[0] else 0.0
        
        return (total_income, total_expense)
    except Exception as e:
        return (0.0, 0.0)

async def get_monthly_trend(user_id: int, months: int = 6) -> dict:
    """Получает тренд расходов по месяцам.
    
    Args:
        user_id: ID пользователя
        months: Количество месяцев для анализа
    
    Returns:
        Словарь {месяц (MMM): сумма_расходов}
    """
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("""
                SELECT strftime('%m-%Y', created_at), SUM(amount)
                FROM transactions
                WHERE user_id = ? AND type = 'expense'
                GROUP BY strftime('%m-%Y', created_at)
                ORDER BY strftime('%m-%Y', created_at) DESC
                LIMIT ?
            """, (user_id, months))
            rows = await cursor.fetchall()
        
        trend = {}
        month_names = {
            '01': 'Янв', '02': 'Фев', '03': 'Мар', '04': 'Апр',
            '05': 'Май', '06': 'Июн', '07': 'Июл', '08': 'Авг',
            '09': 'Сен', '10': 'Окт', '11': 'Ноя', '12': 'Дек'
        }
        
        for month_year, total in reversed(rows):
            if month_year:
                month, year = month_year.split('-')
                month_name = month_names.get(month, month)
                key = f"{month_name} {year}"
                trend[key] = total or 0.0
        
        return trend
    except Exception as e:
        return {}