"""
Репозиторий для работы с вложениями к заявкам.
"""

from typing import List, Optional
from datetime import datetime

from repositories.base_repository import BaseRepository
from models.attachment import Attachment


class AttachmentRepository(BaseRepository[Attachment]):
    """
    Репозиторий для работы с вложениями.

    Предоставляет специфические методы для вложений:
    - find_by_request - получение вложений заявки
    - find_by_user - получение вложений пользователя
    - find_by_type - поиск по типу файла
    """

    def __init__(self):
        """Инициализация репозитория вложений"""
        super().__init__('attachments', Attachment)

    def create(self, attachment: Attachment) -> Optional[int]:
        """
        Создание записи о вложении.

        Args:
            attachment: Объект вложения

        Returns:
            ID созданной записи
        """
        try:
            query = """
            INSERT INTO attachments 
            (request_id, filename, file_path, file_size, mime_type,
             uploaded_by, uploaded_at, description, is_image, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """

            import json
            params = (
                attachment.request_id,
                attachment.filename,
                attachment.file_path,
                attachment.file_size,
                attachment.mime_type,
                attachment.uploaded_by,
                attachment.uploaded_at or datetime.now(),
                attachment.description,
                1 if attachment.is_image else 0,
                json.dumps(attachment.metadata) if attachment.metadata else None
            )

            attachment.id = self.db.execute_insert(query, params)
            self.logger.info(f"Создана запись о вложении {attachment.filename} для заявки #{attachment.request_id}")

            return attachment.id

        except Exception as e:
            self.logger.error(f"Ошибка при создании записи о вложении: {e}")
            return None

    def update(self, attachment: Attachment) -> bool:
        """
        Обновление информации о вложении.

        Args:
            attachment: Объект вложения

        Returns:
            True при успешном обновлении
        """
        try:
            query = """
            UPDATE attachments 
            SET filename = ?, file_path = ?, file_size = ?, mime_type = ?,
                description = ?, is_image = ?, metadata = ?
            WHERE id = ?
            """

            import json
            params = (
                attachment.filename,
                attachment.file_path,
                attachment.file_size,
                attachment.mime_type,
                attachment.description,
                1 if attachment.is_image else 0,
                json.dumps(attachment.metadata) if attachment.metadata else None,
                attachment.id
            )

            affected = self.db.execute_update(query, params)

            if affected > 0:
                self.logger.info(f"Вложение {attachment.filename} (ID: {attachment.id}) обновлено")
                return True

            return False

        except Exception as e:
            self.logger.error(f"Ошибка при обновлении вложения {attachment.id}: {e}")
            return False

    def find_by_request(self, request_id: int) -> List[Attachment]:
        """
        Получение всех вложений заявки.

        Args:
            request_id: ID заявки

        Returns:
            Список вложений
        """
        try:
            query = """
            SELECT * FROM attachments 
            WHERE request_id = ? 
            ORDER BY uploaded_at DESC
            """
            results = self.db.execute_query(query, (request_id,))

            return [Attachment.from_db_row(row) for row in results]

        except Exception as e:
            self.logger.error(f"Ошибка при получении вложений заявки {request_id}: {e}")
            return []

    def find_by_user(self, user_id: int) -> List[Attachment]:
        """
        Получение вложений, загруженных пользователем.

        Args:
            user_id: ID пользователя

        Returns:
            Список вложений
        """
        try:
            query = """
            SELECT * FROM attachments 
            WHERE uploaded_by = ? 
            ORDER BY uploaded_at DESC
            """
            results = self.db.execute_query(query, (user_id,))

            return [Attachment.from_db_row(row) for row in results]

        except Exception as e:
            self.logger.error(f"Ошибка при получении вложений пользователя {user_id}: {e}")
            return []

    def find_by_type(self, mime_type: str) -> List[Attachment]:
        """
        Поиск вложений по MIME-типу.

        Args:
            mime_type: MIME-тип

        Returns:
            Список вложений
        """
        try:
            query = "SELECT * FROM attachments WHERE mime_type LIKE ?"
            results = self.db.execute_query(query, (f"{mime_type}%",))

            return [Attachment.from_db_row(row) for row in results]

        except Exception as e:
            self.logger.error(f"Ошибка при поиске вложений по типу {mime_type}: {e}")
            return []

    def find_images(self, request_id: Optional[int] = None) -> List[Attachment]:
        """
        Получение изображений.

        Args:
            request_id: Опциональный ID заявки для фильтрации

        Returns:
            Список изображений
        """
        try:
            if request_id:
                query = """
                SELECT * FROM attachments 
                WHERE request_id = ? AND is_image = 1
                ORDER BY uploaded_at DESC
                """
                results = self.db.execute_query(query, (request_id,))
            else:
                query = "SELECT * FROM attachments WHERE is_image = 1 ORDER BY uploaded_at DESC"
                results = self.db.execute_query(query)

            return [Attachment.from_db_row(row) for row in results]

        except Exception as e:
            self.logger.error(f"Ошибка при получении изображений: {e}")
            return []

    def delete_by_request(self, request_id: int) -> int:
        """
        Удаление всех вложений заявки.

        Args:
            request_id: ID заявки

        Returns:
            Количество удаленных записей
        """
        try:
            query = "DELETE FROM attachments WHERE request_id = ?"
            affected = self.db.execute_update(query, (request_id,))

            if affected > 0:
                self.logger.info(f"Удалено {affected} вложений заявки #{request_id}")

            return affected

        except Exception as e:
            self.logger.error(f"Ошибка при удалении вложений заявки {request_id}: {e}")
            return 0

    def get_storage_stats(self, request_id: Optional[int] = None) -> dict:
        """
        Получение статистики по хранилищу.

        Args:
            request_id: Опциональный ID заявки

        Returns:
            Словарь со статистикой
        """
        try:
            if request_id:
                attachments = self.find_by_request(request_id)
            else:
                attachments = self.find_all()

            total_size = sum(a.file_size or 0 for a in attachments)
            total_count = len(attachments)
            image_count = len([a for a in attachments if a.is_image])

            return {
                'total_files': total_count,
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'images_count': image_count,
                'documents_count': total_count - image_count
            }

        except Exception as e:
            self.logger.error(f"Ошибка при получении статистики хранилища: {e}")
            return {}
