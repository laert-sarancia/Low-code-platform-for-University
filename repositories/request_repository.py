"""
Репозиторий для работы с заявками.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from repositories.base_repository import BaseRepository
from models.request import Request


class RequestRepository(BaseRepository[Request]):
    """
    Репозиторий для работы с заявками.

    Предоставляет специфические методы для заявок:
    - find_by_requester - по заявителю
    - find_by_assignee - по исполнителю
    - find_by_status - по статусу
    - find_by_category - по категории
    - find_by_priority - по приоритету
    - find_active - активные заявки
    - find_resolved - решенные заявки
    - find_overdue - просроченные
    """

    def __init__(self):
        """Инициализация репозитория заявок"""
        super().__init__('requests', Request)

    def create(self, request: Request) -> Optional[int]:
        """
        Создание новой заявки.

        Args:
            request: Объект заявки

        Returns:
            ID созданной заявки
        """
        try:
            query = """
            INSERT INTO requests 
            (title, description, requester_id, assignee_id, category_id, 
             status_id, priority, created_at, updated_at, resolved_at, 
             closed_at, sla_due_date, estimated_hours, actual_hours,
             satisfaction_rating, satisfaction_comment, is_deleted)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """

            params = (
                request.title,
                request.description,
                request.requester_id,
                request.assignee_id,
                request.category_id,
                request.status_id,
                request.priority,
                request.created_at or datetime.now(),
                request.updated_at or datetime.now(),
                request.resolved_at,
                request.closed_at,
                request.sla_due_date,
                request.estimated_hours,
                request.actual_hours,
                request.satisfaction_rating,
                request.satisfaction_comment,
                1 if request.is_deleted else 0
            )

            request.id = self.db.execute_insert(query, params)
            self.logger.info(f"Создана новая заявка #{request.id}")

            return request.id

        except Exception as e:
            self.logger.error(f"Ошибка при создании заявки: {e}")
            return None

    def update(self, request: Request) -> bool:
        """
        Обновление заявки.

        Args:
            request: Объект заявки

        Returns:
            True при успешном обновлении
        """
        try:
            query = """
            UPDATE requests 
            SET title = ?, description = ?, requester_id = ?, assignee_id = ?,
                category_id = ?, status_id = ?, priority = ?, updated_at = ?,
                resolved_at = ?, closed_at = ?, sla_due_date = ?,
                estimated_hours = ?, actual_hours = ?,
                satisfaction_rating = ?, satisfaction_comment = ?,
                is_deleted = ?
            WHERE id = ?
            """

            params = (
                request.title,
                request.description,
                request.requester_id,
                request.assignee_id,
                request.category_id,
                request.status_id,
                request.priority,
                datetime.now(),
                request.resolved_at,
                request.closed_at,
                request.sla_due_date,
                request.estimated_hours,
                request.actual_hours,
                request.satisfaction_rating,
                request.satisfaction_comment,
                1 if request.is_deleted else 0,
                request.id
            )

            affected = self.db.execute_update(query, params)

            if affected > 0:
                self.logger.info(f"Заявка #{request.id} обновлена")
                return True

            return False

        except Exception as e:
            self.logger.error(f"Ошибка при обновлении заявки {request.id}: {e}")
            return False

    def find_by_requester(self, requester_id: int) -> List[Request]:
        """
        Поиск заявок по заявителю.

        Args:
            requester_id: ID заявителя

        Returns:
            Список заявок
        """
        try:
            query = """
            SELECT * FROM requests 
            WHERE requester_id = ? AND is_deleted = 0
            ORDER BY created_at DESC
            """
            results = self.db.execute_query(query, (requester_id,))

            return [Request.from_db_row(row) for row in results]

        except Exception as e:
            self.logger.error(f"Ошибка при поиске заявок заявителя {requester_id}: {e}")
            return []

    def find_by_assignee(self, assignee_id: int) -> List[Request]:
        """
        Поиск заявок по исполнителю.

        Args:
            assignee_id: ID исполнителя

        Returns:
            Список заявок
        """
        try:
            query = """
            SELECT * FROM requests 
            WHERE assignee_id = ? AND is_deleted = 0
            ORDER BY created_at DESC
            """
            results = self.db.execute_query(query, (assignee_id,))

            return [Request.from_db_row(row) for row in results]

        except Exception as e:
            self.logger.error(f"Ошибка при поиске заявок исполнителя {assignee_id}: {e}")
            return []

    def find_by_status(self, status_id: int) -> List[Request]:
        """
        Поиск заявок по статусу.

        Args:
            status_id: ID статуса

        Returns:
            Список заявок
        """
        try:
            query = """
            SELECT * FROM requests 
            WHERE status_id = ? AND is_deleted = 0
            ORDER BY created_at DESC
            """
            results = self.db.execute_query(query, (status_id,))

            return [Request.from_db_row(row) for row in results]

        except Exception as e:
            self.logger.error(f"Ошибка при поиске заявок по статусу {status_id}: {e}")
            return []

    def find_by_category(self, category_id: int) -> List[Request]:
        """
        Поиск заявок по категории.

        Args:
            category_id: ID категории

        Returns:
            Список заявок
        """
        try:
            query = """
            SELECT * FROM requests 
            WHERE category_id = ? AND is_deleted = 0
            ORDER BY created_at DESC
            """
            results = self.db.execute_query(query, (category_id,))

            return [Request.from_db_row(row) for row in results]

        except Exception as e:
            self.logger.error(f"Ошибка при поиске заявок по категории {category_id}: {e}")
            return []

    def find_by_priority(self, priority: str) -> List[Request]:
        """
        Поиск заявок по приоритету.

        Args:
            priority: Приоритет

        Returns:
            Список заявок
        """
        try:
            query = """
            SELECT * FROM requests 
            WHERE priority = ? AND is_deleted = 0
            ORDER BY created_at DESC
            """
            results = self.db.execute_query(query, (priority,))

            return [Request.from_db_row(row) for row in results]

        except Exception as e:
            self.logger.error(f"Ошибка при поиске заявок по приоритету {priority}: {e}")
            return []

    def find_active(self) -> List[Request]:
        """
        Получение активных заявок (не завершенных).

        Returns:
            Список активных заявок
        """
        try:
            query = """
            SELECT * FROM requests 
            WHERE status_id NOT IN (3, 4, 5) AND is_deleted = 0
            ORDER BY 
                CASE priority 
                    WHEN 'critical' THEN 1
                    WHEN 'high' THEN 2
                    WHEN 'medium' THEN 3
                    WHEN 'low' THEN 4
                END,
                created_at ASC
            """
            results = self.db.execute_query(query)

            return [Request.from_db_row(row) for row in results]

        except Exception as e:
            self.logger.error(f"Ошибка при получении активных заявок: {e}")
            return []

    def find_resolved(self) -> List[Request]:
        """
        Получение решенных заявок.

        Returns:
            Список решенных заявок
        """
        try:
            query = """
            SELECT * FROM requests 
            WHERE status_id = 3 AND is_deleted = 0
            ORDER BY resolved_at DESC
            """
            results = self.db.execute_query(query)

            return [Request.from_db_row(row) for row in results]

        except Exception as e:
            self.logger.error(f"Ошибка при получении решенных заявок: {e}")
            return []

    def find_by_date_range(self, start_date: datetime, end_date: datetime) -> List[Request]:
        """
        Поиск заявок в диапазоне дат.

        Args:
            start_date: Начальная дата
            end_date: Конечная дата

        Returns:
            Список заявок
        """
        try:
            query = """
            SELECT * FROM requests 
            WHERE created_at BETWEEN ? AND ? AND is_deleted = 0
            ORDER BY created_at DESC
            """
            results = self.db.execute_query(query, (start_date, end_date))

            return [Request.from_db_row(row) for row in results]

        except Exception as e:
            self.logger.error(f"Ошибка при поиске заявок по датам: {e}")
            return []

    def find_since(self, since_date: datetime) -> List[Request]:
        """
        Получение заявок, созданных после указанной даты.

        Args:
            since_date: Дата, с которой искать

        Returns:
            Список заявок
        """
        try:
            query = """
            SELECT * FROM requests 
            WHERE created_at >= ? AND is_deleted = 0
            ORDER BY created_at DESC
            """
            results = self.db.execute_query(query, (since_date,))

            return [Request.from_db_row(row) for row in results]

        except Exception as e:
            self.logger.error(f"Ошибка при получении заявок с {since_date}: {e}")
            return []

    def find_resolved_since(self, since_date: datetime) -> List[Request]:
        """
        Получение заявок, решенных после указанной даты.

        Args:
            since_date: Дата, с которой искать

        Returns:
            Список заявок
        """
        try:
            query = """
            SELECT * FROM requests 
            WHERE resolved_at >= ? AND is_deleted = 0
            ORDER BY resolved_at DESC
            """
            results = self.db.execute_query(query, (since_date,))

            return [Request.from_db_row(row) for row in results]

        except Exception as e:
            self.logger.error(f"Ошибка при получении решенных заявок с {since_date}: {e}")
            return []

    def find_by_assignee_since(self, assignee_id: int, since_date: datetime) -> List[Request]:
        """
        Получение заявок исполнителя, созданных после даты.

        Args:
            assignee_id: ID исполнителя
            since_date: Дата

        Returns:
            Список заявок
        """
        try:
            query = """
            SELECT * FROM requests 
            WHERE assignee_id = ? AND created_at >= ? AND is_deleted = 0
            ORDER BY created_at DESC
            """
            results = self.db.execute_query(query, (assignee_id, since_date))

            return [Request.from_db_row(row) for row in results]

        except Exception as e:
            self.logger.error(f"Ошибка при получении заявок исполнителя {assignee_id}: {e}")
            return []

    def find_resolved_by_assignee_since(self, assignee_id: int, since_date: datetime) -> List[Request]:
        """
        Получение решенных заявок исполнителя после даты.

        Args:
            assignee_id: ID исполнителя
            since_date: Дата

        Returns:
            Список заявок
        """
        try:
            query = """
            SELECT * FROM requests 
            WHERE assignee_id = ? AND resolved_at >= ? AND is_deleted = 0
            ORDER BY resolved_at DESC
            """
            results = self.db.execute_query(query, (assignee_id, since_date))

            return [Request.from_db_row(row) for row in results]

        except Exception as e:
            self.logger.error(f"Ошибка при получении решенных заявок исполнителя {assignee_id}: {e}")
            return []

    def find_by_requester_since(self, requester_id: int, since_date: datetime) -> List[Request]:
        """
        Получение заявок заявителя, созданных после даты.

        Args:
            requester_id: ID заявителя
            since_date: Дата

        Returns:
            Список заявок
        """
        try:
            query = """
            SELECT * FROM requests 
            WHERE requester_id = ? AND created_at >= ? AND is_deleted = 0
            ORDER BY created_at DESC
            """
            results = self.db.execute_query(query, (requester_id, since_date))

            return [Request.from_db_row(row) for row in results]

        except Exception as e:
            self.logger.error(f"Ошибка при получении заявок заявителя {requester_id}: {e}")
            return []

    def get_statistics(self, days: int = 30) -> Dict[str, Any]:
        """
        Получение статистики по заявкам.

        Args:
            days: Период в днях

        Returns:
            Словарь со статистикой
        """
        try:
            since_date = datetime.now() - timedelta(days=days)
            requests = self.find_since(since_date)

            total = len(requests)
            resolved = len([r for r in requests if r.resolved_at])

            # По статусам
            by_status = {}
            for r in requests:
                status_id = r.status_id
                by_status[status_id] = by_status.get(status_id, 0) + 1

            # По приоритетам
            by_priority = {}
            for r in requests:
                priority = r.priority
                by_priority[priority] = by_priority.get(priority, 0) + 1

            # По категориям
            by_category = {}
            for r in requests:
                category_id = r.category_id
                by_category[category_id] = by_category.get(category_id, 0) + 1

            # Среднее время решения
            resolution_times = []
            for r in requests:
                if r.resolved_at and r.created_at:
                    hours = (r.resolved_at - r.created_at).total_seconds() / 3600
                    resolution_times.append(hours)

            avg_resolution = sum(resolution_times) / len(resolution_times) if resolution_times else 0

            return {
                'period_days': days,
                'total': total,
                'resolved': resolved,
                'open': total - resolved,
                'by_status': by_status,
                'by_priority': by_priority,
                'by_category': by_category,
                'avg_resolution_hours': round(avg_resolution, 2)
            }

        except Exception as e:
            self.logger.error(f"Ошибка при получении статистики: {e}")
            return {}