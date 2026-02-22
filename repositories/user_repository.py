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
            ID созданного пользователя или None в случае ошибки
        """
        try:
            # Получаем список колонок таблицы
            columns = self._get_table_columns()

            # Подготавливаем данные для вставки
            data = {
                'username': user.username,
                'email': user.email,
                'full_name': user.full_name,
                'department': user.department,
                'role': user.role,
                'phone': user.phone,
                'telegram_id': user.telegram_id
            }

            # Добавляем опциональные поля, если они есть в таблице
            if 'is_active' in columns:
                data['is_active'] = 1 if user.is_active else 0

            if 'created_at' in columns:
                data['created_at'] = user.created_at or datetime.now()

            if 'updated_at' in columns:
                data['updated_at'] = user.updated_at or datetime.now()

            if 'last_login' in columns and user.last_login:
                data['last_login'] = user.last_login

            # Фильтруем только существующие колонки
            filtered_data = {k: v for k, v in data.items() if k in columns and v is not None}

            if not filtered_data:
                self.logger.error("Нет данных для вставки")
                return None

            # Формируем запрос
            columns_str = ', '.join(filtered_data.keys())
            placeholders = ', '.join(['?' for _ in filtered_data])
            values = list(filtered_data.values())

            query = f"INSERT INTO users ({columns_str}) VALUES ({placeholders})"

            # Выполняем вставку
            user.id = self.db.execute_insert(query, values)

            if user.id:
                self.logger.info(f"Создан новый пользователь: {user.username} (ID: {user.id})")
                return user.id
            else:
                self.logger.error("Не удалось получить ID созданного пользователя")
                return None

        except Exception as e:
            self.logger.error(f"Ошибка при создании пользователя: {e}")
            return None

    def _get_table_columns(self) -> List[str]:
        """Получение списка колонок таблицы users"""
        try:
            query = "PRAGMA table_info(users)"
            results = self.db.execute_query(query)
            return [row['name'] for row in results]
        except Exception as e:
            self.logger.error(f"Ошибка при получении списка колонок: {e}")
            return []

    def update(self, user: User) -> bool:
        """
        Обновление данных пользователя.

        Args:
            user: Объект пользователя

        Returns:
            True при успешном обновлении
        """
        try:
            if not user.id:
                self.logger.error("ID пользователя не указан")
                return False

            # Получаем список колонок
            columns = self._get_table_columns()

            # Подготавливаем данные для обновления
            data = {
                'username': user.username,
                'email': user.email,
                'full_name': user.full_name,
                'department': user.department,
                'role': user.role,
                'phone': user.phone,
                'telegram_id': user.telegram_id
            }

            if 'is_active' in columns:
                data['is_active'] = 1 if user.is_active else 0

            if 'updated_at' in columns:
                data['updated_at'] = datetime.now()

            if 'last_login' in columns and user.last_login:
                data['last_login'] = user.last_login

            # Фильтруем только существующие колонки
            filtered_data = {k: v for k, v in data.items() if k in columns and v is not None}

            if not filtered_data:
                self.logger.warning("Нет данных для обновления")
                return False

            # Формируем запрос
            set_clause = ', '.join([f"{k} = ?" for k in filtered_data.keys()])
            values = list(filtered_data.values())
            values.append(user.id)

            query = f"UPDATE users SET {set_clause} WHERE id = ?"

            affected = self.db.execute_update(query, values)

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
            # Проверяем наличие колонки is_active
            columns = self._get_table_columns()

            if 'is_active' in columns:
                query = "SELECT * FROM users WHERE role = ? AND is_active = 1"
            else:
                query = "SELECT * FROM users WHERE role = ?"

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
            # Проверяем наличие колонки is_active
            columns = self._get_table_columns()

            if 'is_active' in columns:
                query = "SELECT * FROM users WHERE role IN ('executor', 'admin') AND is_active = 1"
            else:
                query = "SELECT * FROM users WHERE role IN ('executor', 'admin')"

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
            # Проверяем наличие колонки is_active
            columns = self._get_table_columns()

            if 'is_active' in columns:
                query = "SELECT * FROM users WHERE role = 'admin' AND is_active = 1"
            else:
                query = "SELECT * FROM users WHERE role = 'admin'"

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
            # Проверяем наличие колонки is_active
            columns = self._get_table_columns()

            if 'is_active' in columns:
                query = "SELECT * FROM users WHERE is_active = 1"
                results = self.db.execute_query(query)
            else:
                # Если нет колонки is_active, возвращаем всех
                results = self.db.execute_query("SELECT * FROM users")

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
            # Проверяем наличие колонки is_active
            columns = self._get_table_columns()

            if 'is_active' in columns:
                query = "SELECT * FROM users WHERE department = ? AND is_active = 1"
            else:
                query = "SELECT * FROM users WHERE department = ?"

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
            search_term = f"%{term}%"

            # Проверяем наличие колонки is_active
            columns = self._get_table_columns()

            if 'is_active' in columns:
                query = """
                SELECT * FROM users 
                WHERE (username LIKE ? OR full_name LIKE ? OR email LIKE ?)
                AND is_active = 1
                LIMIT 20
                """
            else:
                query = """
                SELECT * FROM users 
                WHERE (username LIKE ? OR full_name LIKE ? OR email LIKE ?)
                LIMIT 20
                """

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
                count = len(self.find_by_role(role))
                if count > 0:
                    roles[role] = count

            # Проверяем наличие колонки is_active
            columns = self._get_table_columns()

            if 'is_active' in columns:
                active = self.count({'is_active': 1})
                inactive = total - active
            else:
                active = total
                inactive = 0

            return {
                'total': total,
                'active': active,
                'inactive': inactive,
                'by_role': roles
            }

        except Exception as e:
            self.logger.error(f"Ошибка при получении статистики пользователей: {e}")
            return {}
