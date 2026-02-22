"""
Репозиторий для работы с пользователями.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime

from repositories.base_repository import BaseRepository
from models.user import User


class UserRepository(BaseRepository[User]):
    """
    Репозиторий для работы с пользователями.

    Предоставляет специфические методы для пользователей:
    - find_by_username - поиск по логину
    - find_by_email - поиск по email
    - find_by_role - поиск по роли
    - find_executors - получение всех исполнителей
    - find_admins - получение всех администраторов
    - find_active - получение активных пользователей
    """

    def __init__(self):
        """Инициализация репозитория пользователей"""
        super().__init__('users', User)

    def create(self, user: User) -> Optional[int]:
        """
        Создание нового пользователя.

        Args:
            user: Объект пользователя

        Returns:
            ID созданного пользователя
        """
        try:
            query = """
            INSERT INTO users 
            (username, email, full_name, department, role, is_active, 
             created_at, updated_at, last_login, phone, telegram_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """

            params = (
                user.username,
                user.email,
                user.full_name,
                user.department,
                user.role,
                1 if user.is_active else 0,
                user.created_at or datetime.now(),
                user.updated_at or datetime.now(),
                user.last_login,
                user.phone,
                user.telegram_id
            )

            user.id = self.db.execute_insert(query, params)
            self.logger.info(f"Создан новый пользователь: {user.username} (ID: {user.id})")

            return user.id

        except Exception as e:
            self.logger.error(f"Ошибка при создании пользователя: {e}")
            return None

    def update(self, user: User) -> bool:
        """
        Обновление данных пользователя.

        Args:
            user: Объект пользователя

        Returns:
            True при успешном обновлении
        """
        try:
            query = """
            UPDATE users 
            SET username = ?, email = ?, full_name = ?, department = ?, 
                role = ?, is_active = ?, updated_at = ?, last_login = ?,
                phone = ?, telegram_id = ?
            WHERE id = ?
            """

            params = (
                user.username,
                user.email,
                user.full_name,
                user.department,
                user.role,
                1 if user.is_active else 0,
                datetime.now(),
                user.last_login,
                user.phone,
                user.telegram_id,
                user.id
            )

            affected = self.db.execute_update(query, params)

            if affected > 0:
                self.logger.info(f"Пользователь {user.username} (ID: {user.id}) обновлен")
                return True

            return False

        except Exception as e:
            self.logger.error(f"Ошибка при обновлении пользователя {user.id}: {e}")
            return False

    def find_by_username(self, username: str) -> Optional[User]:
        """
        Поиск пользователя по логину.

        Args:
            username: Логин пользователя

        Returns:
            Объект пользователя или None
        """
        try:
            query = "SELECT * FROM users WHERE username = ?"
            results = self.db.execute_query(query, (username,))

            if results:
                return User.from_db_row(results[0])
            return None

        except Exception as e:
            self.logger.error(f"Ошибка при поиске пользователя по логину {username}: {e}")
            return None

    def find_by_email(self, email: str) -> Optional[User]:
        """
        Поиск пользователя по email.

        Args:
            email: Email пользователя

        Returns:
            Объект пользователя или None
        """
        try:
            query = "SELECT * FROM users WHERE email = ?"
            results = self.db.execute_query(query, (email,))

            if results:
                return User.from_db_row(results[0])
            return None

        except Exception as e:
            self.logger.error(f"Ошибка при поиске пользователя по email {email}: {e}")
            return None

    def find_by_role(self, role: str) -> List[User]:
        """
        Поиск пользователей по роли.

        Args:
            role: Роль пользователя

        Returns:
            Список пользователей
        """
        try:
            query = "SELECT * FROM users WHERE role = ? AND is_active = 1"
            results = self.db.execute_query(query, (role,))

            return [User.from_db_row(row) for row in results]

        except Exception as e:
            self.logger.error(f"Ошибка при поиске пользователей по роли {role}: {e}")
            return []

    def find_executors(self) -> List[User]:
        """
        Получение всех исполнителей (executor + admin).

        Returns:
            Список исполнителей
        """
        try:
            query = "SELECT * FROM users WHERE role IN ('executor', 'admin') AND is_active = 1"
            results = self.db.execute_query(query)

            return [User.from_db_row(row) for row in results]

        except Exception as e:
            self.logger.error(f"Ошибка при получении исполнителей: {e}")
            return []

    def find_admins(self) -> List[User]:
        """
        Получение всех администраторов.

        Returns:
            Список администраторов
        """
        try:
            query = "SELECT * FROM users WHERE role = 'admin' AND is_active = 1"
            results = self.db.execute_query(query)

            return [User.from_db_row(row) for row in results]

        except Exception as e:
            self.logger.error(f"Ошибка при получении администраторов: {e}")
            return []

    def find_active(self) -> List[User]:
        """
        Получение всех активных пользователей.

        Returns:
            Список активных пользователей
        """
        try:
            query = "SELECT * FROM users WHERE is_active = 1"
            results = self.db.execute_query(query)

            return [User.from_db_row(row) for row in results]

        except Exception as e:
            self.logger.error(f"Ошибка при получении активных пользователей: {e}")
            return []

    def find_by_department(self, department: str) -> List[User]:
        """
        Поиск пользователей по отделу.

        Args:
            department: Название отдела

        Returns:
            Список пользователей
        """
        try:
            query = "SELECT * FROM users WHERE department = ? AND is_active = 1"
            results = self.db.execute_query(query, (department,))

            return [User.from_db_row(row) for row in results]

        except Exception as e:
            self.logger.error(f"Ошибка при поиске пользователей по отделу {department}: {e}")
            return []

    def search(self, term: str) -> List[User]:
        """
        Поиск пользователей по имени или логину.

        Args:
            term: Поисковый запрос

        Returns:
            Список найденных пользователей
        """
        try:
            query = """
            SELECT * FROM users 
            WHERE (username LIKE ? OR full_name LIKE ? OR email LIKE ?)
            AND is_active = 1
            LIMIT 20
            """
            search_term = f"%{term}%"
            results = self.db.execute_query(query, (search_term, search_term, search_term))

            return [User.from_db_row(row) for row in results]

        except Exception as e:
            self.logger.error(f"Ошибка при поиске пользователей по запросу '{term}': {e}")
            return []

    def get_statistics(self) -> Dict[str, Any]:
        """
        Получение статистики по пользователям.

        Returns:
            Словарь со статистикой
        """
        try:
            # Общее количество
            total = self.count()

            # По ролям
            roles = {}
            for role in ['requester', 'executor', 'admin']:
                count = self.count({'role': role})
                if count > 0:
                    roles[role] = count

            # Активные/неактивные
            active = self.count({'is_active': 1})
            inactive = total - active

            return {
                'total': total,
                'active': active,
                'inactive': inactive,
                'by_role': roles
            }

        except Exception as e:
            self.logger.error(f"Ошибка при получении статистики пользователей: {e}")
            return {}
