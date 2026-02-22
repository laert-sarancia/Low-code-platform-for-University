"""
Модель вложения к заявке.
Представляет файлы, прикрепленные пользователями к заявкам.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
import os
import mimetypes


@dataclass
class Attachment:
    """
    Класс вложения к заявке.

    Attributes:
        id: Уникальный идентификатор вложения
        request_id: ID заявки
        filename: Оригинальное имя файла
        file_path: Путь к файлу на диске
        file_size: Размер файла в байтах
        mime_type: MIME-тип файла
        uploaded_by: ID пользователя, загрузившего файл
        uploaded_at: Дата и время загрузки
        description: Описание файла
        is_image: Является ли изображением
        metadata: Дополнительные данные (JSON)
    """

    id: Optional[int] = None
    request_id: Optional[int] = None
    filename: str = ""
    file_path: str = ""
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    uploaded_by: Optional[int] = None
    uploaded_at: Optional[datetime] = None
    description: Optional[str] = None
    is_image: bool = False
    metadata: Optional[Dict[str, Any]] = None

    # Разрешенные типы файлов
    ALLOWED_EXTENSIONS = {
        'images': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg'],
        'documents': ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.txt', '.rtf'],
        'archives': ['.zip', '.rar', '.7z', '.tar', '.gz']
    }

    # Максимальный размер файла (10 MB)
    MAX_FILE_SIZE = 10 * 1024 * 1024

    def __post_init__(self):
        """Валидация после инициализации"""
        self.validate()

    def validate(self) -> bool:
        """
        Валидация данных вложения.

        Returns:
            True если данные корректны

        Raises:
            ValueError: При некорректных данных
        """
        if self.filename and not self.filename.strip():
            raise ValueError("Имя файла не может быть пустым")

        if self.file_size and self.file_size > self.MAX_FILE_SIZE:
            raise ValueError(f"Размер файла превышает {self.MAX_FILE_SIZE / 1024 / 1024} MB")

        return True

    @classmethod
    def from_db_row(cls, row: Dict[str, Any]) -> 'Attachment':
        """
        Создание объекта вложения из строки БД.

        Args:
            row: Словарь с данными из БД

        Returns:
            Объект Attachment
        """
        if not row:
            return cls()

        # Парсинг JSON метаданных
        metadata = row.get('metadata')
        if metadata and isinstance(metadata, str):
            import json
            try:
                metadata = json.loads(metadata)
            except:
                metadata = {}

        # Преобразование даты
        uploaded_at = None
        if row.get('uploaded_at'):
            if isinstance(row['uploaded_at'], str):
                uploaded_at = datetime.fromisoformat(row['uploaded_at'].replace('Z', '+00:00'))
            else:
                uploaded_at = row['uploaded_at']

        return cls(
            id=row.get('id'),
            request_id=row.get('request_id'),
            filename=row.get('filename', ''),
            file_path=row.get('file_path', ''),
            file_size=row.get('file_size'),
            mime_type=row.get('mime_type'),
            uploaded_by=row.get('uploaded_by'),
            uploaded_at=uploaded_at,
            description=row.get('description'),
            is_image=bool(row.get('is_image', False)),
            metadata=metadata
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Преобразование объекта в словарь для БД.

        Returns:
            Словарь с данными вложения
        """
        import json

        return {
            'id': self.id,
            'request_id': self.request_id,
            'filename': self.filename,
            'file_path': self.file_path,
            'file_size': self.file_size,
            'mime_type': self.mime_type,
            'uploaded_by': self.uploaded_by,
            'uploaded_at': self.uploaded_at.isoformat() if self.uploaded_at else None,
            'description': self.description,
            'is_image': 1 if self.is_image else 0,
            'metadata': json.dumps(self.metadata) if self.metadata else None
        }

    # ==================== МЕТОДЫ ДЛЯ РАБОТЫ С ФАЙЛАМИ ====================

    @classmethod
    def from_file(cls, file_path: str, request_id: int, uploaded_by: int,
                  description: Optional[str] = None) -> 'Attachment':
        """
        Создание объекта вложения из файла.

        Args:
            file_path: Путь к файлу
            request_id: ID заявки
            uploaded_by: ID загрузившего пользователя
            description: Описание файла

        Returns:
            Объект Attachment
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Файл не найден: {file_path}")

        filename = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)

        # Определение MIME-типа
        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type:
            mime_type = 'application/octet-stream'

        # Проверка, является ли файл изображением
        ext = os.path.splitext(filename)[1].lower()
        is_image = ext in cls.ALLOWED_EXTENSIONS['images']

        return cls(
            request_id=request_id,
            filename=filename,
            file_path=file_path,
            file_size=file_size,
            mime_type=mime_type,
            uploaded_by=uploaded_by,
            uploaded_at=datetime.now(),
            description=description,
            is_image=is_image
        )

    def get_extension(self) -> str:
        """Получение расширения файла"""
        return os.path.splitext(self.filename)[1].lower()

    def get_file_type_category(self) -> str:
        """Получение категории типа файла"""
        ext = self.get_extension()

        for category, extensions in self.ALLOWED_EXTENSIONS.items():
            if ext in extensions:
                return category

        return 'other'

    def get_size_display(self) -> str:
        """Получение размера файла в человекочитаемом формате"""
        if not self.file_size:
            return "0 B"

        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024

        return f"{size:.1f} TB"

    def is_valid_extension(self) -> bool:
        """Проверка допустимости расширения файла"""
        ext = self.get_extension()
        for extensions in self.ALLOWED_EXTENSIONS.values():
            if ext in extensions:
                return True
        return False

    def get_icon(self) -> str:
        """Получение иконки для типа файла"""
        ext = self.get_extension()

        # Изображения
        if ext in self.ALLOWED_EXTENSIONS['images']:
            return '🖼️'

        # Документы
        if ext in ['.pdf']:
            return '📕'
        if ext in ['.doc', '.docx']:
            return '📘'
        if ext in ['.xls', '.xlsx']:
            return '📗'
        if ext in ['.txt']:
            return '📄'

        # Архивы
        if ext in self.ALLOWED_EXTENSIONS['archives']:
            return '📦'

        return '📎'

    # ==================== МЕТОДЫ ДЛЯ РАБОТЫ С ДИСКОМ ====================

    def exists(self) -> bool:
        """Проверка существования файла на диске"""
        return os.path.exists(self.file_path)

    def delete_file(self) -> bool:
        """
        Удаление файла с диска.

        Returns:
            True если файл удален
        """
        if self.exists():
            os.remove(self.file_path)
            return True
        return False

    def get_file_content(self) -> Optional[bytes]:
        """
        Получение содержимого файла.

        Returns:
            Байтовое содержимое файла или None
        """
        if not self.exists():
            return None

        with open(self.file_path, 'rb') as f:
            return f.read()

    # ==================== МЕТОДЫ ДЛЯ ОТОБРАЖЕНИЯ ====================

    def __str__(self) -> str:
        """Строковое представление вложения"""
        icon = self.get_icon()
        size = self.get_size_display()
        return f"{icon} {self.filename} ({size})"

    def __repr__(self) -> str:
        """Представление для отладки"""
        return f"Attachment(id={self.id}, filename='{self.filename}', size={self.file_size})"