"""
Репозиторий для работы со статусами заявок.
"""

from typing import List, Optional, Dict
from datetime import datetime

from repositories.base_repository import BaseRepository
from models.status import Status


class StatusRepository(BaseRepository[Status]):
    """
    Репозиторий для работы со статусами.

    Предоставляет специфические методы для статусов:
    - find_by_code - поиск по коду
    - get_initial_status - получение начального статуса
    - get_final_statuses - получение конечных статусов
    - get_next_statuses - получение доступных следующих статусов
    """

    def __init__(self):
        """Инициализация репозитория статусов"""
        super().__init__('statuses', Status)

    def create(self, status: Status) -> Optional[int]:
        """
        Создание нового статуса.

        Args:
            status: Объект статуса

        Returns:
            ID созданного статуса
        """
        try:
            query = """
            INSERT INTO statuses 
            (name, code, description, color, "order", is_initial, is_final,
             requires_comment, allowed_roles, next_statuses, created_at, updated_at, icon)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """

            import json
            params = (
                status.name,
                status.code,
                status.description,
                status.color,
                status.order,
                1 if status.is_initial else 0,
                1 if status.is_final else 0,
                1 if status.requires_comment else 0,
                json.dumps(status.allowed_roles) if status.allowed_roles else None,
                json.dumps(status.next_statuses) if status.next_statuses else None,
                status.created_at or datetime.now(),
                status.updated_at or datetime.now(),
                status.icon
            )

            status.id = self.db.execute_insert(query, params)
            self.logger.info(f"Создан новый статус: {status.name} (ID: {status.id})")

            return status.id

        except Exception as e:
            self.logger.error(f"Ошибка при создании статуса: {e}")
            return None

    def update(self, status: Status) -> bool:
        """
        Обновление статуса.

        Args:
            status: Объект статуса

        Returns:
            True при успешном обновлении
        """
        try:
            query = """
            UPDATE statuses 
            SET name = ?, code = ?, description = ?, color = ?, "order" = ?,
                is_initial = ?, is_final = ?, requires_comment = ?,
                allowed_roles = ?, next_statuses = ?, updated_at = ?, icon = ?
            WHERE id = ?
            """

            import json
            params = (
                status.name,
                status.code,
                status.description,
                status.color,
                status.order,
                1 if status.is_initial else 0,
                1 if status.is_final else 0,
                1 if status.requires_comment else 0,
                json.dumps(status.allowed_roles) if status.allowed_roles else None,
                json.dumps(status.next_statuses) if status.next_statuses else None,
                datetime.now(),
                status.icon,
                status.id
            )

            affected = self.db.execute_update(query, params)

            if affected > 0:
                self.logger.info(f"Статус {status.name} (ID: {status.id}) обновлен")
                return True

            return False

        except Exception as e:
            self.logger.error(f"Ошибка при обновлении статуса {status.id}: {e}")
            return False

    def find_by_code(self, code: str) -> Optional[Status]:
        """
        Поиск статуса по коду.

        Args:
            code: Код статуса

        Returns:
            Объект статуса или None
        """
        try:
            query = "SELECT * FROM statuses WHERE code = ?"
            results = self.db.execute_query(query, (code,))

            if results:
                return Status.from_db_row(results[0])
            return None

        except Exception as e:
            self.logger.error(f"Ошибка при поиске статуса по коду '{code}': {e}")
            return None

    def get_initial_status(self) -> Optional[Status]:
        """
        Получение начального статуса.

        Returns:
            Объект статуса или None
        """
        try:
            query = "SELECT * FROM statuses WHERE is_initial = 1 LIMIT 1"
            results = self.db.execute_query(query)

            if results:
                return Status.from_db_row(results[0])
            return None

        except Exception as e:
            self.logger.error(f"Ошибка при получении начального статуса: {e}")
            return None

    def get_final_statuses(self) -> List[Status]:
        """
        Получение конечных статусов.

        Returns:
            Список конечных статусов
        """
        try:
            query = "SELECT * FROM statuses WHERE is_final = 1 ORDER BY \"order\""
            results = self.db.execute_query(query)

            return [Status.from_db_row(row) for row in results]

        except Exception as e:
            self.logger.error(f"Ошибка при получении конечных статусов: {e}")
            return []

    def get_next_statuses(self, status_id: int) -> List[Status]:
        """
        Получение доступных следующих статусов.

        Args:
            status_id: ID текущего статуса

        Returns:
            Список доступных статусов
        """
        try:
            status = self.find_by_id(status_id)
            if not status:
                return []

            if not status.next_statuses:
                # Если не указаны следующие статусы, возвращаем все
                all_statuses = self.find_all()
                return [s for s in all_statuses if s.id != status_id]

            # Получаем статусы по IDs
            result = []
            for sid in status.next_statuses:
                next_status = self.find_by_id(sid)
                if next_status:
                    result.append(next_status)

            return result

        except Exception as e:
            self.logger.error(f"Ошибка при получении следующих статусов для {status_id}: {e}")
            return []

    def get_status_flow(self) -> Dict[int, List[int]]:
        """
        Получение карты переходов статусов.

        Returns:
            Словарь {from_status_id: [to_status_ids]}
        """
        try:
            statuses = self.find_all()
            flow = {}

            for status in statuses:
                if status.next_statuses:
                    flow[status.id] = status.next_statuses

            return flow

        except Exception as e:
            self.logger.error(f"Ошибка при получении карты переходов: {e}")
            return {}