"""
Репозиторий для работы с историей изменений заявок.
"""

from typing import List, Optional
from datetime import datetime

from repositories.base_repository import BaseRepository
from models.request_history import RequestHistory


class RequestHistoryRepository(BaseRepository[RequestHistory]):
    """
    Репозиторий для работы с историей изменений заявок.

    Предоставляет специфические методы для истории:
    - find_by_request - получение истории конкретной заявки
    - find_by_user - получение действий пользователя
    - find_by_action - получение записей по типу действия
    - find_recent - получение недавних действий
    """

    def __init__(self):
        """Инициализация репозитория истории"""
        super().__init__('request_history', RequestHistory)

    def create(self, history: RequestHistory) -> Optional[int]:
        """
        Создание записи в истории.

        Args:
            history: Объект истории

        Returns:
            ID созданной записи
        """
        try:
            query = """
            INSERT INTO request_history 
            (request_id, action, old_value, new_value, comment, 
             changed_by, changed_at, field_name, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """

            import json
            params = (
                history.request_id,
                history.action,
                history.old_value,
                history.new_value,
                history.comment,
                history.changed_by,
                history.changed_at or datetime.now(),
                history.field_name,
                json.dumps(history.metadata) if history.metadata else None
            )

            history.id = self.db.execute_insert(query, params)
            self.logger.debug(f"Создана запись истории для заявки #{history.request_id}")

            return history.id

        except Exception as e:
            self.logger.error(f"Ошибка при создании записи истории: {e}")
            return None

    def update(self, history: RequestHistory) -> bool:
        """
        Обновление записи истории (обычно не требуется).

        Args:
            history: Объект истории

        Returns:
            True при успешном обновлении
        """
        # История обычно не обновляется
        self.logger.warning("Попытка обновления записи истории")
        return False

    def find_by_request(self, request_id: int) -> List[RequestHistory]:
        """
        Получение истории конкретной заявки.

        Args:
            request_id: ID заявки

        Returns:
            Список записей истории
        """
        try:
            query = """
            SELECT * FROM request_history 
            WHERE request_id = ? 
            ORDER BY changed_at DESC
            """
            results = self.db.execute_query(query, (request_id,))

            return [RequestHistory.from_db_row(row) for row in results]

        except Exception as e:
            self.logger.error(f"Ошибка при получении истории заявки {request_id}: {e}")
            return []

    def find_by_user(self, user_id: int, limit: int = 50) -> List[RequestHistory]:
        """
        Получение действий пользователя.

        Args:
            user_id: ID пользователя
            limit: Максимальное количество записей

        Returns:
            Список записей истории
        """
        try:
            query = """
            SELECT * FROM request_history 
            WHERE changed_by = ? 
            ORDER BY changed_at DESC
            LIMIT ?
            """
            results = self.db.execute_query(query, (user_id, limit))

            return [RequestHistory.from_db_row(row) for row in results]

        except Exception as e:
            self.logger.error(f"Ошибка при получении истории пользователя {user_id}: {e}")
            return []

    def find_by_action(self, action: str, limit: int = 50) -> List[RequestHistory]:
        """
        Получение записей по типу действия.

        Args:
            action: Тип действия
            limit: Максимальное количество записей

        Returns:
            Список записей истории
        """
        try:
            query = """
            SELECT * FROM request_history 
            WHERE action = ? 
            ORDER BY changed_at DESC
            LIMIT ?
            """
            results = self.db.execute_query(query, (action, limit))

            return [RequestHistory.from_db_row(row) for row in results]

        except Exception as e:
            self.logger.error(f"Ошибка при поиске действий '{action}': {e}")
            return []

    def find_recent(self, limit: int = 100) -> List[RequestHistory]:
        """
        Получение недавних действий.

        Args:
            limit: Максимальное количество записей

        Returns:
            Список недавних записей
        """
        try:
            query = """
            SELECT * FROM request_history 
            ORDER BY changed_at DESC
            LIMIT ?
            """
            results = self.db.execute_query(query, (limit,))

            return [RequestHistory.from_db_row(row) for row in results]

        except Exception as e:
            self.logger.error(f"Ошибка при получении недавней истории: {e}")
            return []

    def find_by_date_range(self, start_date: datetime, end_date: datetime) -> List[RequestHistory]:
        """
        Получение записей за период.

        Args:
            start_date: Начальная дата
            end_date: Конечная дата

        Returns:
            Список записей
        """
        try:
            query = """
            SELECT * FROM request_history 
            WHERE changed_at BETWEEN ? AND ?
            ORDER BY changed_at DESC
            """
            results = self.db.execute_query(query, (start_date, end_date))

            return [RequestHistory.from_db_row(row) for row in results]

        except Exception as e:
            self.logger.error(f"Ошибка при получении истории за период: {e}")
            return []

    def get_last_action(self, request_id: int) -> Optional[RequestHistory]:
        """
        Получение последнего действия по заявке.

        Args:
            request_id: ID заявки

        Returns:
            Последняя запись истории или None
        """
        try:
            query = """
            SELECT * FROM request_history 
            WHERE request_id = ? 
            ORDER BY changed_at DESC
            LIMIT 1
            """
            results = self.db.execute_query(query, (request_id,))

            if results:
                return RequestHistory.from_db_row(results[0])
            return None

        except Exception as e:
            self.logger.error(f"Ошибка при получении последнего действия для заявки {request_id}: {e}")
            return None

    def count_user_actions(self, user_id: int, days: int = 30) -> int:
        """
        Подсчет действий пользователя за период.

        Args:
            user_id: ID пользователя
            days: Количество дней

        Returns:
            Количество действий
        """
        try:
            since_date = datetime.now() - datetime.timedelta(days=days)
            query = """
            SELECT COUNT(*) as count FROM request_history 
            WHERE changed_by = ? AND changed_at >= ?
            """
            results = self.db.execute_query(query, (user_id, since_date))

            return results[0]['count'] if results else 0

        except Exception as e:
            self.logger.error(f"Ошибка при подсчете действий пользователя {user_id}: {e}")
            return 0
