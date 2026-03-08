# utils/quick_input.py
"""Парсер быстрого ввода транзакции одной строкой.

Форматы:
  500 еда нал        → расход 500, категория Еда, наличные
  500 еда карта      → расход 500, категория Еда, карта
  +3000 зп карта     → доход 3000, категория Зарплата, карта
  -500 такси нал     → расход 500, категория Транспорт, наличные
"""
import re
from config.settings import QUICK_INPUT_ALIASES, INCOME_CATEGORY_NAMES


def parse_quick_input(text: str) -> dict | None:
    """
    Парсит строку быстрого ввода.
    
    Returns:
        dict с ключами: amount, type, method, category
        или None если не удалось распознать
    """
    text = text.strip().lower()
    tokens = text.split()
    if len(tokens) < 2:
        return None

    # --- Сумма ---
    amount_str = tokens[0].lstrip('+').lstrip('-')
    # Знак + = доход, - = расход (явный)
    explicit_income = tokens[0].startswith('+')
    explicit_expense = tokens[0].startswith('-')

    try:
        amount = float(amount_str.replace(',', '.'))
    except ValueError:
        return None

    if amount <= 0:
        return None

    # --- Способ оплаты ---
    method = "cash"  # по умолчанию
    remaining_tokens = tokens[1:]
    filtered_tokens = []
    for token in remaining_tokens:
        if token in ("нал", "наличные", "наличка", "cash"):
            method = "cash"
        elif token in ("карта", "картой", "card", "кар"):
            method = "card"
        else:
            filtered_tokens.append(token)

    # --- Категория ---
    category = None
    for token in filtered_tokens:
        if token in QUICK_INPUT_ALIASES:
            category = QUICK_INPUT_ALIASES[token]
            break

    if not category:
        # Попробуем объединить токены
        combined = " ".join(filtered_tokens)
        if combined in QUICK_INPUT_ALIASES:
            category = QUICK_INPUT_ALIASES[combined]

    if not category:
        return None

    # --- Тип транзакции ---
    if explicit_income:
        trans_type = "income"
    elif explicit_expense:
        trans_type = "expense"
    else:
        # Определяем по категории
        trans_type = "income" if category in INCOME_CATEGORY_NAMES else "expense"

    return {
        "amount": amount,
        "type": trans_type,
        "method": method,
        "category": category,
    }


def format_quick_help() -> str:
    return (
        "⚡ <b>Быстрый ввод</b>\n\n"
        "Просто напишите в чат:\n\n"
        "<code>500 еда нал</code> — расход 500 ₽, Еда, наличные\n"
        "<code>200 такси карта</code> — расход 200 ₽, Транспорт, карта\n"
        "<code>+50000 зп карта</code> — доход 50 000 ₽, Зарплата, карта\n"
        "<code>1500 аптека</code> — расход 1 500 ₽, Здоровье (метод по умолч.)\n\n"
        "<b>Доступные категории:</b>\n"
        "еда, такси, метро, транспорт, жилье, аренда,\n"
        "техника, одежда, курсы, спорт, кино, аптека,\n"
        "магазин, зп, бонус, фриланс, подарок и другие"
    )