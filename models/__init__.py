"""
Инициализационный файл для пакета models.
Экспортирует все классы моделей для удобного импорта.
"""

from models.user import User
from models.request import Request
from models.category import Category
from models.status import Status
from models.request_history import RequestHistory
from models.attachment import Attachment

__all__ = [
    'User',
    'Request',
    'Category',
    'Status',
    'RequestHistory',
    'Attachment'
]