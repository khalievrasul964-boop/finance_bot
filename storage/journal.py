# storage/journal.py
import re
from pathlib import Path
from datetime import datetime

# Папка для персональных файлов пользователей
USER_DATA_DIR = Path("users_data")
USER_DATA_DIR.mkdir(exist_ok=True)


def sanitize_filename(name: str) -> str:
    """
    Преобразует имя пользователя в безопасное имя файла.
    Удаляет спецсимволы, заменяет пробелы на подчёркивания.
    """
    if not name or not name.strip():
        return "anonymous"
    # Оставляем только буквы, цифры, пробелы, дефисы, подчёркивания
    safe = re.sub(r'[^\w\s\-]', '', name.strip())
    # Заменяем пробелы и множественные подчёркивания
    safe = safe.replace(' ', '_')
    safe = re.sub(r'_+', '_', safe)
    # Обрезаем до 50 символов и убираем крайние подчёркивания
    safe = safe[:50].strip('_')
    return safe if safe else "user"


async def ensure_user_header(user_name: str):
    """
    Создаёт файл с заголовком, если он ещё не существует.
    """
    filename = sanitize_filename(user_name) + ".txt"
    filepath = USER_DATA_DIR / filename
    if not filepath.exists():
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"# 📒 Финансовый дневник — {user_name}\n\n")


async def log_to_user_file(user_name: str, line: str):
    """
    Добавляет строку (транзакцию) в файл пользователя.
    """
    filename = sanitize_filename(user_name) + ".txt"
    filepath = USER_DATA_DIR / filename
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(line + "\n")


async def append_daily_report_to_user_file(user_name: str, report_date: datetime.date, report_text: str):
    """
    Добавляет подробный отчёт за день в файл пользователя, избегая дублирования.
    Форматирует красивую таблицу с временем и категориями.
    """
    if "ещё нет операций" in report_text:
        return

    filename = sanitize_filename(user_name) + ".txt"
    filepath = USER_DATA_DIR / filename

    # Проверяем, не записан ли уже отчёт за эту дату в новом или старом формате
    date_str = report_date.strftime("%d.%m.%Y")
    old_date_str = f"📅 {report_date}"
    
    if filepath.exists():
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
            # Проверяем оба формата даты
            if f"📅 {date_str}" in content or old_date_str in content:
                return  # Уже сохранён

    # Записываем весь отчёт с красивым форматированием
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(f"\n{report_text}\n")
