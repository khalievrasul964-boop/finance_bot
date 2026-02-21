def format_detailed_report(title: str, transactions: list) -> str:
    """Улучшенный минималистичный отчёт без красных/зелёных иконок."""

    from collections import defaultdict

    by_date = defaultdict(list)
    total_income = 0.0
    total_expense = 0.0

    for trans in transactions:
        by_date[trans["date"]].append(trans)
        if trans["type"] == "income":
            total_income += trans["amount"]
        else:
            total_expense += trans["amount"]

    sorted_dates = sorted(by_date.keys())

    lines = []
    lines.append(title)
    lines.append("")

    for curr_date in sorted_dates:
        date_str = curr_date.strftime("%d.%m.%Y")
        weekday = _get_weekday(curr_date)

        # Заголовок дня
        lines.append(f"📅 {date_str} · {weekday}")
        lines.append("")

        daily_income = 0.0
        daily_expense = 0.0

        for trans in by_date[curr_date]:
            method_emoji = "💵" if trans["method"] == "cash" else "💳"
            time_str = trans["time"]
            amount = format_money(trans["amount"])
            category = trans["category"]

            sign = "+" if trans["type"] == "income" else "−"
            lines.append(f"{time_str:<6} {sign}{amount:<18} {category} {method_emoji}")

            if trans["type"] == "income":
                daily_income += trans["amount"]
            else:
                daily_expense += trans["amount"]

        daily_balance = daily_income - daily_expense

        lines.append("")
        if daily_income > 0:
            lines.append(f"Доход:   {format_money(daily_income)}")
        if daily_expense > 0:
            lines.append(f"Расход:  {format_money(daily_expense)}")

        lines.append("──────────────")
        lines.append(f"💰 Баланс: {format_money(daily_balance)}")
        lines.append("")
        lines.append("")

    # Итог
    total_balance = total_income - total_expense

    lines.append("📊 Итог")
    lines.append("")
    lines.append(f"Доход:   {format_money(total_income)}")
    lines.append(f"Расход:  {format_money(total_expense)}")
    lines.append("──────────────")
    lines.append(f"💰 Баланс: {format_money(total_balance)}")
    lines.append("")
    lines.append(f"📈 Дней в отчёте: {len(sorted_dates)}")
    lines.append(f"💵 Всего операций: {len(transactions)}")

    return "\n".join(lines)
