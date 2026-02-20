from config.settings import MAX_TRANSACTION_AMOUNT, MIN_TRANSACTION_AMOUNT
import re

def validate_amount(text: str) -> bool:
    """Проверяет сумму: должна быть положительным числом в допустимом диапазоне."""
    try:
        value = float(text.strip().replace(',', '.'))
        return MIN_TRANSACTION_AMOUNT <= value <= MAX_TRANSACTION_AMOUNT
    except (ValueError, AttributeError):
        return False

def validate_name(text: str) -> bool:
    """Проверяет имя пользователя: не пусто, 1-50 символов, без URL."""
    if not text or len(text.strip()) == 0:
        return False
    if len(text.strip()) > 50:
        return False
    # Проверяем на URL
    if 'http://' in text or 'https://' in text:
        return False
    return True

def format_amount_error_message() -> str:
    """Возвращает сообщение об ошибке для неверной суммы."""
    return (
        f"❌ Некорректная сумма!\n"
        f"Введите число от 0.01 до {MAX_TRANSACTION_AMOUNT:,.0f} ₽\n"
        f"Примеры: <code>500</code>, <code>1500.50</code>"
    )