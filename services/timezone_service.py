# services/timezone_service.py
"""Утилиты для работы с часовыми поясами."""
from datetime import datetime
from zoneinfo import ZoneInfo  # Python 3.9+
from config.settings import DEFAULT_TIMEZONE


def now_user(timezone: str) -> datetime:
    """Возвращает текущее время в часовом поясе пользователя."""
    tz = ZoneInfo(timezone or DEFAULT_TIMEZONE)
    return datetime.now(tz)


def utc_to_user(dt: datetime, timezone: str) -> datetime:
    """Конвертирует UTC datetime в часовой пояс пользователя."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    tz = ZoneInfo(timezone or DEFAULT_TIMEZONE)
    return dt.astimezone(tz)


def user_now_iso(timezone: str) -> str:
    """Возвращает текущее время пользователя в ISO формате для записи в БД."""
    return now_user(timezone).isoformat()