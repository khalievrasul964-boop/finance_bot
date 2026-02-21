# utils/report_formatter.py
from datetime import date
from collections import defaultdict

def format_money(amount: float) -> str:
    """Форматирует деньги с красивыми разделителями.
    Пример: 1234567.50 -> 1 234 567,50 ₽
    """
    # Преобразуем в строку с 2 знаками после запятой
    parts = f"{amount:.2f}".split('.')
    integer_part = parts[0]
    decimal_part = parts[1]
    
    # Добавляем пробелы каждые 3 цифры справа налево
    formatted = ""
    for i, digit in enumerate(reversed(integer_part)):
        if i > 0 and i % 3 == 0:
            formatted = " " + formatted
        formatted = digit + formatted
    
    # Объединяем целую и дробную части с запятой
    return f"{formatted},{decimal_part} ₽"

def format_report(
    title: str,
    income_cash: float,
    income_card: float,
    expense_cash: float,
    expense_card: float
) -> str:
    total_income = income_cash + income_card
    total_expense = expense_cash + expense_card
    balance = total_income - total_expense

    lines = [
        f"┌{'─' * 48}┐",
        f"│ {title:<46} │"
    ]

    if total_income > 0:
        lines.append(f"├{'─' * 48}┤")
        lines.append(f"│ 📥 <b>ДОХОДЫ:</b> {total_income:>34.2f} ₽ │")
        if income_cash > 0:
            lines.append(f"│    💵 Наличные.........{income_cash:>20.2f} ₽ │")
        if income_card > 0:
            lines.append(f"│    💳 Карта............{income_card:>20.2f} ₽ │")

    if total_expense > 0:
        lines.append(f"├{'─' * 48}┤")
        lines.append(f"│ 📤 <b>РАСХОДЫ:</b> {total_expense:>34.2f} ₽ │")
        if expense_cash > 0:
            lines.append(f"│    💵 Наличные.........{expense_cash:>20.2f} ₽ │")
        if expense_card > 0:
            lines.append(f"│    💳 Карта............{expense_card:>20.2f} ₽ │")

    lines.append(f"├{'─' * 48}┤")
    
    if balance > 0:
        balance_emoji = "🟢"
        balance_label = "ПРИБЫЛЬ"
    else:
        balance_emoji = "🔴"
        balance_label = "ДЕФИЦИТ"
    
    lines.append(f"│ {balance_emoji} <b>{balance_label}:</b> {abs(balance):>38.2f} ₽ │")
    lines.append(f"└{'─' * 48}┘")
    
    return "\n".join(lines)

def format_detailed_report(title: str, transactions: list) -> str:
    """Форматирует красивый отчет без рамок - минималистичный дизайн."""
    
    # Группируем операции по дате
    by_date = defaultdict(list)
    total_income = 0.0
    total_expense = 0.0
    
    for trans in transactions:
        by_date[trans["date"]].append(trans)
        if trans["type"] == "income":
            total_income += trans["amount"]
        else:
            total_expense += trans["amount"]
    
    # Сортируем даты
    sorted_dates = sorted(by_date.keys())
    
    # Красивый заголовок отчета
    lines = [
        f"",
        f"{title}",
        f"",
    ]
    
    # По каждой дате
    for curr_date in sorted_dates:
        date_str = curr_date.strftime("%d.%m.%Y")
        weekday = _get_weekday(curr_date)
        
        lines.append(f"📅 {date_str} ({weekday})")
        
        daily_income = 0.0
        daily_expense = 0.0
        daily_trans = by_date[curr_date]
        
        # Вывод каждой операции
        for trans in daily_trans:
            emoji = "🟢" if trans["type"] == "income" else "🔴"
            method_emoji = "💵" if trans["method"] == "cash" else "💳"
            time_str = trans["time"]
            
            # Красиво форматируем сумму
            amount_formatted = format_money(trans['amount'])
            category = trans["category"]
            
            # Простая строка без рамок
            line = f"  {emoji} {time_str}  •  {amount_formatted:<18}  •  {category}  ({method_emoji})"
            lines.append(line)
            
            if trans["type"] == "income":
                daily_income += trans["amount"]
            else:
                daily_expense += trans["amount"]
        
        # Итого по дню
        daily_balance = daily_income - daily_expense
        lines.append(f"")
        
        # Формируем итоговую строку дня
        if daily_income > 0:
            income_label = f"🟢 Доход:  {format_money(daily_income)}"
            lines.append(f"  {income_label}")
        if daily_expense > 0:
            expense_label = f"🔴 Расход:  {format_money(daily_expense)}"
            lines.append(f"  {expense_label}")
        
        balance_emoji = "🟢" if daily_balance >= 0 else "🔴"
        balance_label = "Баланс:" if daily_balance >= 0 else "Дефицит:"
        balance_line = f"{balance_emoji} {balance_label}  {format_money(abs(daily_balance))}"
        lines.append(f"  {balance_line}")
        
        lines.append(f"")
    
    # Общий итог по всему отчету
    lines.append(f"")
    lines.append(f"📊 Итоговая статистика")
    lines.append(f"")
    
    if total_income > 0:
        lines.append(f"  🟢 Всего доходов:     {format_money(total_income)}")
    if total_expense > 0:
        lines.append(f"  🔴 Всего расходов:    {format_money(total_expense)}")
    
    total_balance = total_income - total_expense
    balance_emoji = "🟢" if total_balance >= 0 else "🔴"
    balance_label = "Прибыль:" if total_balance >= 0 else "Дефицит:"
    lines.append(f"  {balance_emoji} {balance_label} {format_money(abs(total_balance))}")
    
    lines.append(f"")
    lines.append(f"  📈 Дней в отчете: {len(sorted_dates)}")
    lines.append(f"  💵 Всего операций: {len(transactions)}")
    lines.append(f"")
    
    return "\n".join(lines)

def _get_weekday(d: date) -> str:
    """Возвращает день недели на русском."""
    days = {
        0: "Пн", 1: "Вт", 2: "Ср", 3: "Чт",
        4: "Пт", 5: "Сб", 6: "Вс"
    }
    return days.get(d.weekday(), "")

def create_bar_chart(title: str, data: dict, max_width: int = 30) -> str:
    """Создает горизонтальную столбчатую диаграмму.
    
    Args:
        title: Заголовок диаграммы
        data: Словарь {название: значение}
        max_width: Максимальная ширина столбца
    """
    lines = [f"\n📊 {title}\n"]
    
    if not data:
        lines.append("Нет данных для отображения.")
        return "\n".join(lines)
    
    max_value = max(data.values()) if data.values() else 1
    
    for name, value in sorted(data.items(), key=lambda x: x[1], reverse=True):
        # Рассчитываем ширину столба
        bar_width = int((value / max_value) * max_width) if max_value > 0 else 1
        bar = "█" * bar_width + "░" * (max_width - bar_width)
        
        lines.append(f"{name:<20} {bar} {format_money(value)}")
    
    return "\n".join(lines)

def create_pie_chart(title: str, data: dict) -> str:
    """Создает ASCII круговую диаграмму.
    
    Args:
        title: Заголовок диаграммы
        data: Словарь {название: значение}
    """
    lines = [f"\n📈 {title}\n"]
    
    if not data:
        lines.append("Нет данных для отображения.")
        return "\n".join(lines)
    
    total = sum(data.values())
    if total == 0:
        return "\n".join(lines + ["Нет данных для отображения."])
    
    # Создаем круговую диаграмму с помощью символов
    pie_chars = ["🟤", "🟡", "🟢", "🔵", "🟣", "🟠", "🔴", "⚫"]
    
    for idx, (name, value) in enumerate(sorted(data.items(), key=lambda x: x[1], reverse=True)):
        percentage = (value / total) * 100
        emoji = pie_chars[idx % len(pie_chars)]
        
        lines.append(f"{emoji} {name:<20} {percentage:>5.1f}% ({format_money(value)})")
    
    return "\n".join(lines)

def create_daily_bar_chart(title: str, daily_data: dict) -> str:
    """Создает график расходов/доходов по дням.
    
    Args:
        title: Заголовок графика
        daily_data: Словарь {дата: сумма}
    """
    lines = [f"\n📅 {title}\n"]
    
    if not daily_data:
        lines.append("Нет данных для отображения.")
        return "\n".join(lines)
    
    # Сортируем по датам
    sorted_data = sorted(daily_data.items())
    max_value = max(daily_data.values()) if daily_data.values() else 1
    max_width = 25
    
    for date_str, value in sorted_data:
        bar_width = int((value / max_value) * max_width) if max_value > 0 else 1
        bar = "█" * bar_width + "░" * (max_width - bar_width)
        
        lines.append(f"{date_str} {bar} {format_money(value)}")
    
    lines.append("")
    return "\n".join(lines)

def create_comparison_chart(title: str, categories: list, values_list: list, labels: list) -> str:
    """Создает сравнительную диаграмму (например, доход vs расход).
    
    Args:
        title: Заголовок
        categories: Список категорий
        values_list: Список списков значений
        labels: Подписи для каждого набора значений
    """
    lines = [f"\n🔄 {title}\n"]
    
    if not categories:
        lines.append("Нет данных для отображения.")
        return "\n".join(lines)
    
    max_width = 20
    
    # Находим максимальное значение для масштабирования
    all_values = [val for values in values_list for val in values]
    max_value = max(all_values) if all_values else 1
    
    # Создаем таблицу со сравнением
    lines.append("".join(f"{label:>15}" for label in labels))
    lines.append("─" * (15 * len(labels)))
    
    for idx, category in enumerate(categories):
        line = f"{category:<15}"
        for values in values_list:
            if idx < len(values):
                value = values[idx]
                bar_width = int((value / max_value) * max_width) if max_value > 0 else 1
                bar = "█" * bar_width
                line += f" {bar:<20}"
        lines.append(line)
    
    lines.append("")
    return "\n".join(lines)

def create_trend_chart(title: str, data_points: list, width: int = 50) -> str:
    """Создает график тренда с использованием графических символов.
    
    Args:
        title: Заголовок графика
        data_points: Список значений
        width: Ширина графика
    """
    lines = [f"\n📈 {title}\n"]
    
    if not data_points or len(data_points) < 2:
        lines.append("Недостаточно данных для отображения тренда.")
        return "\n".join(lines)
    
    min_val = min(data_points)
    max_val = max(data_points)
    range_val = max_val - min_val if max_val > min_val else 1
    
    chart = []
    height = 10
    
    # Создаем сетку для графика
    for h in range(height, 0, -1):
        line = ""
        for idx, value in enumerate(data_points):
            # Рассчитываем высоту точки
            normalized = (value - min_val) / range_val
            if normalized >= (h - 0.5) / height:
                line += "█"
            else:
                line += " "
        chart.insert(0, line)
    
    # Добавляем оси
    lines.append("\n".join(chart))
    lines.append("─" * len(data_points))
    
    lines.append(f"Min: {format_money(min_val)} | Max: {format_money(max_val)}")
    lines.append("")
    
    return "\n".join(lines)
