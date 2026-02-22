"""
Базовый репозиторий с общими методами CRUD.
Все конкретные репозитории наследуются от этого класса.
"""

from typing import TypeVar, Generic, List, Optional, Dict, Any, Type
import logging

from database.db_manager import DatabaseManager

T = TypeVar('T')


class BaseRepository(Generic[T]):
    """
    Базовый класс для всех репозиториев.

    Предоставляет общие методы для работы с БД:
    - find_by_id - поиск по ID
    - find_all - получение всех записей
    - find_by_criteria - поиск по критериям
    - create - создание записи
    - update - обновление записи
    - delete - удаление записи
    """

    def __init__(self, table_name: str, model_class: Type[T]):
        """
        Инициализация базового репозитория.

        Args:
            table_name: Название таблицы в БД
            model_class: Класс модели
        """
        self.table_name = table_name
        self.model_class = model_class
        self.db = DatabaseManager()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def find_by_id(self, id: int) -> Optional[T]:
        """
        Поиск записи по ID.

        Args:
            id: ID записи

        Returns:
            Объект модели или None
        """
        try:
            query = f"SELECT * FROM {self.table_name} WHERE id = ?"
            results = self.db.execute_query(query, (id,))

            if results:
                return self.model_class.from_db_row(results[0])
            return None

        except Exception as e:
            self.logger.error(f"Ошибка при поиске по ID {id}: {e}")
            return None

    def find_all(self, limit: int = 100, offset: int = 0) -> List[T]:
        """
        Получение всех записей.

        Args:
            limit: Максимальное количество записей
            offset: Смещение для пагинации

        Returns:
            Список объектов модели
        """
        try:
            query = f"SELECT * FROM {self.table_name} LIMIT ? OFFSET ?"
            results = self.db.execute_query(query, (limit, offset))

            return [self.model_class.from_db_row(row) for row in results]

        except Exception as e:
            self.logger.error(f"Ошибка при получении всех записей: {e}")
            return []

    def find_by_criteria(self, criteria: Dict[str, Any]) -> List[T]:
        """
        Поиск записей по критериям.

        Args:
            criteria: Словарь с критериями {поле: значение}

        Returns:
            Список объектов модели
        """
        try:
            if not criteria:
                return self.find_all()

            conditions = []
            params = []

            for key, value in criteria.items():
                if value is not None:
                    conditions.append(f"{key} = ?")
                    params.append(value)

            if not conditions:
                return self.find_all()

            where_clause = " AND ".join(conditions)
            query = f"SELECT * FROM {self.table_name} WHERE {where_clause}"

            results = self.db.execute_query(query, tuple(params))
            return [self.model_class.from_db_row(row) for row in results]

        except Exception as e:
            self.logger.error(f"Ошибка при поиске по критериям {criteria}: {e}")
            return []

    def create(self, entity: T) -> Optional[int]:
        """
        Создание новой записи.
        Должен быть переопределен в дочерних классах.

        Args:
            entity: Объект модели

        Returns:
            ID созданной записи или None
        """
        raise NotImplementedError("Метод create должен быть реализован в дочернем классе")

    def update(self, entity: T) -> bool:
        """
        Обновление записи.
        Должен быть переопределен в дочерних классах.

        Args:
            entity: Объект модели

        Returns:
            True при успешном обновлении
        """
        raise NotImplementedError("Метод update должен быть реализован в дочернем классе")

    def delete(self, id: int) -> bool:
        """
        Удаление записи.

        Args:
            id: ID записи

        Returns:
            True при успешном удалении
        """
        try:
            query = f"DELETE FROM {self.table_name} WHERE id = ?"
            affected = self.db.execute_update(query, (id,))

            if affected > 0:
                self.logger.info(f"Запись с ID {id} удалена из {self.table_name}")
                return True

            self.logger.warning(f"Запись с ID {id} не найдена в {self.table_name}")
            return False

        except Exception as e:
            self.logger.error(f"Ошибка при удалении записи {id}: {e}")
            return False

    def count(self, criteria: Optional[Dict[str, Any]] = None) -> int:
        """
        Подсчет количества записей.

        Args:
            criteria: Критерии для подсчета

        Returns:
            Количество записей
        """
        try:
            if not criteria:
                query = f"SELECT COUNT(*) as count FROM {self.table_name}"
                result = self.db.execute_query(query)
            else:
                conditions = []
                params = []

                for key, value in criteria.items():
                    if value is not None:
                        conditions.append(f"{key} = ?")
                        params.append(value)

                where_clause = " AND ".join(conditions)
                query = f"SELECT COUNT(*) as count FROM {self.table_name} WHERE {where_clause}"
                result = self.db.execute_query(query, tuple(params))

            return result[0]['count'] if result else 0

        except Exception as e:
            self.logger.error(f"Ошибка при подсчете записей: {e}")
            return 0

    def exists(self, id: int) -> bool:
        """
        Проверка существования записи.

        Args:
            id: ID записи

        Returns:
            True если запись существует
        """
        try:
            query = f"SELECT 1 FROM {self.table_name} WHERE id = ?"
            result = self.db.execute_query(query, (id,))
            return len(result) > 0

        except Exception as e:
            self.logger.error(f"Ошибка при проверке существования записи {id}: {e}")
            return False
