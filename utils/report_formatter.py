from datetime import date
from collections import defaultdict

def format_money(amount: float) -> str:
    parts = f"{amount:.2f}".split('.')
    integer_part = parts[0]
    decimal_part = parts[1]
    formatted = ""
    for i, digit in enumerate(reversed(integer_part)):
        if i > 0 and i % 3 == 0:
            formatted = " " + formatted
        formatted = digit + formatted
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

    lines = [f"📊 {title}", ""]

    if total_income > 0:
        lines.append("Доход:")
        if income_cash > 0:
            lines.append(f"💵 {format_money(income_cash)}")
        if income_card > 0:
            lines.append(f"💳 {format_money(income_card)}")
        lines.append(f"Итого: {format_money(total_income)}")
        lines.append("")

    if total_expense > 0:
        lines.append("Расход:")
        if expense_cash > 0:
            lines.append(f"💵 {format_money(expense_cash)}")
        if expense_card > 0:
            lines.append(f"💳 {format_money(expense_card)}")
        lines.append(f"Итого: {format_money(total_expense)}")
        lines.append("")

    balance_label = "Остаток" if balance >= 0 else "Дефицит"
    lines.append(f"💰 {balance_label}: {format_money(abs(balance))}")

    return "\n".join(lines)


def format_detailed_report(title: str, transactions: list) -> str:
    """Форматирует минималистичный отчёт по дням."""

    by_date = defaultdict(list)
    total_income_cash = 0.0
    total_income_card = 0.0
    total_expense_cash = 0.0
    total_expense_card = 0.0

    for trans in transactions:
        by_date[trans["date"]].append(trans)

    sorted_dates = sorted(by_date.keys())

    lines = [f"📊 {title}", ""]

    for curr_date in sorted_dates:
        date_str = curr_date.strftime("%d.%m.%Y")
        weekday = _get_weekday(curr_date)
        lines.append(f"📅 {date_str} ({weekday})")
        lines.append("")

        day_income_cash = 0.0
        day_income_card = 0.0
        day_expense_cash = 0.0
        day_expense_card = 0.0

        # Доходы
        incomes = [t for t in by_date[curr_date] if t["type"] == "income"]
        if incomes:
            lines.append("Доход:")
            for trans in incomes:
                method_emoji = "💵" if trans["method"] == "cash" else "💳"
                category = trans["category"]
                amount = format_money(trans["amount"])
                lines.append(f"{method_emoji} {category}: {amount}")
                if trans["method"] == "cash":
                    day_income_cash += trans["amount"]
                    total_income_cash += trans["amount"]
                else:
                    day_income_card += trans["amount"]
                    total_income_card += trans["amount"]
            total_day_income = day_income_cash + day_income_card
            lines.append(f"Итого: {format_money(total_day_income)}")
            lines.append("")

        # Расходы
        expenses = [t for t in by_date[curr_date] if t["type"] == "expense"]
        if expenses:
            lines.append("Расход:")
            for trans in expenses:
                method_emoji = "💵" if trans["method"] == "cash" else "💳"
                category = trans["category"]
                amount = format_money(trans["amount"])
                lines.append(f"{method_emoji} {category}: {amount}")
                if trans["method"] == "cash":
                    day_expense_cash += trans["amount"]
                    total_expense_cash += trans["amount"]
                else:
                    day_expense_card += trans["amount"]
                    total_expense_card += trans["amount"]
            total_day_expense = day_expense_cash + day_expense_card
            lines.append(f"Итого: {format_money(total_day_expense)}")
            lines.append("")

        # Остаток за день
        day_balance = (day_income_cash + day_income_card) - (day_expense_cash + day_expense_card)
        balance_label = "Остаток" if day_balance >= 0 else "Дефицит"
        lines.append(f"💰 {balance_label}: {format_money(abs(day_balance))}")
        lines.append("")
        lines.append("─" * 28)
        lines.append("")

    # Итоговая статистика
    total_income = total_income_cash + total_income_card
    total_expense = total_expense_cash + total_expense_card
    total_balance = total_income - total_expense

    lines.append("📊 Итоговая статистика")
    lines.append("")

    if total_income > 0:
        lines.append("Доход:")
        if total_income_cash > 0:
            lines.append(f"💵 {format_money(total_income_cash)}")
        if total_income_card > 0:
            lines.append(f"💳 {format_money(total_income_card)}")
        lines.append(f"Итого: {format_money(total_income)}")
        lines.append("")

    if total_expense > 0:
        lines.append("Расход:")
        if total_expense_cash > 0:
            lines.append(f"💵 {format_money(total_expense_cash)}")
        if total_expense_card > 0:
            lines.append(f"💳 {format_money(total_expense_card)}")
        lines.append(f"Итого: {format_money(total_expense)}")
        lines.append("")

    balance_label = "Остаток" if total_balance >= 0 else "Дефицит"
    lines.append(f"💰 {balance_label}: {format_money(abs(total_balance))}")
    lines.append("")
    lines.append(f"📈 Дней в отчёте: {len(sorted_dates)}")
    lines.append(f"💵 Всего операций: {sum(len(v) for v in by_date.values())}")

    return "\n".join(lines)


def _get_weekday(d: date) -> str:
    days = {0: "Пн", 1: "Вт", 2: "Ср", 3: "Чт", 4: "Пт", 5: "Сб", 6: "Вс"}
    return days.get(d.weekday(), "")


def create_bar_chart(title: str, data: dict, max_width: int = 30) -> str:
    lines = [f"\n📊 {title}\n"]
    if not data:
        lines.append("Нет данных для отображения.")
        return "\n".join(lines)
    max_value = max(data.values()) if data.values() else 1
    for name, value in sorted(data.items(), key=lambda x: x[1], reverse=True):
        bar_width = int((value / max_value) * max_width) if max_value > 0 else 1
        bar = "█" * bar_width + "░" * (max_width - bar_width)
        lines.append(f"{name:<20} {bar} {format_money(value)}")
    return "\n".join(lines)


def create_pie_chart(title: str, data: dict) -> str:
    lines = [f"\n📈 {title}\n"]
    if not data:
        lines.append("Нет данных для отображения.")
        return "\n".join(lines)
    total = sum(data.values())
    if total == 0:
        return "\n".join(lines + ["Нет данных для отображения."])
    pie_chars = ["🟤", "🟡", "🟢", "🔵", "🟣", "🟠", "🔴", "⚫"]
    for idx, (name, value) in enumerate(sorted(data.items(), key=lambda x: x[1], reverse=True)):
        percentage = (value / total) * 100
        emoji = pie_chars[idx % len(pie_chars)]
        lines.append(f"{emoji} {name:<20} {percentage:>5.1f}% ({format_money(value)})")
    return "\n".join(lines)


def create_daily_bar_chart(title: str, daily_data: dict) -> str:
    lines = [f"\n📅 {title}\n"]
    if not daily_data:
        lines.append("Нет данных для отображения.")
        return "\n".join(lines)
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
    lines = [f"\n🔄 {title}\n"]
    if not categories:
        lines.append("Нет данных для отображения.")
        return "\n".join(lines)
    max_width = 20
    all_values = [val for values in values_list for val in values]
    max_value = max(all_values) if all_values else 1
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
    lines = [f"\n📈 {title}\n"]
    if not data_points or len(data_points) < 2:
        lines.append("Недостаточно данных для отображения тренда.")
        return "\n".join(lines)
    min_val = min(data_points)
    max_val = max(data_points)
    range_val = max_val - min_val if max_val > min_val else 1
    chart = []
    height = 10
    for h in range(height, 0, -1):
        line = ""
        for idx, value in enumerate(data_points):
            normalized = (value - min_val) / range_val
            if normalized >= (h - 0.5) / height:
                line += "█"
            else:
                line += " "
        chart.insert(0, line)
    lines.append("\n".join(chart))
    lines.append("─" * len(data_points))
    lines.append(f"Min: {format_money(min_val)} | Max: {format_money(max_val)}")
    lines.append("")
    return "\n".join(lines)
