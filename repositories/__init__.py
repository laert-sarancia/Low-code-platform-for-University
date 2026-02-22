"""
Инициализационный файл для пакета repositories.
Экспортирует все классы репозиториев для удобного импорта.
"""

from repositories.base_repository import BaseRepository
from repositories.user_repository import UserRepository
from repositories.request_repository import RequestRepository
from repositories.category_repository import CategoryRepository
from repositories.status_repository import StatusRepository
from repositories.request_history_repository import RequestHistoryRepository
from repositories.attachment_repository import AttachmentRepository

__all__ = [
    'BaseRepository',
    'UserRepository',
    'RequestRepository',
    'CategoryRepository',
    'StatusRepository',
    'RequestHistoryRepository',
    'AttachmentRepository'
]