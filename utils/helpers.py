"""Вспомогательные функции"""

from datetime import datetime
import hashlib
import os


def generate_ticket_number(request_id: int) -> str:
    """Генерация номера заявки формата SRQ-2024-001"""
    year = datetime.now().year
    return f"SRQ-{year}-{request_id:04d}"


def format_datetime(dt: datetime) -> str:
    """Форматирование даты для отображения"""
    if not dt:
        return ""
    return dt.strftime("%d.%m.%Y %H:%M")


def hash_filename(filename: str) -> str:
    """Хеширование имени файла для безопасного хранения"""
    name, ext = os.path.splitext(filename)
    hash_obj = hashlib.md5(f"{name}{datetime.now()}".encode())
    return f"{hash_obj.hexdigest()[:10]}{ext}"