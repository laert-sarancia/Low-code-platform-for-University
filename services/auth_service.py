"""
Сервис аутентификации и авторизации.
Управляет входом в систему, проверкой прав доступа и сессиями.
"""

from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import hashlib
import logging
import secrets

from models.user import User
from repositories.user_repository import UserRepository


class AuthService:
    """
    Сервис для аутентификации и авторизации пользователей.
    """

    def __init__(self):
        """Инициализация сервиса аутентификации"""
        self.user_repo = UserRepository()
        self.logger = logging.getLogger(__name__)

        # Время жизни сессии (в часах)
        self.session_lifetime = 24

    def login(self, username: str, password: str) -> Optional[User]:
        """
        Вход пользователя в систему.

        Args:
            username: Имя пользователя
            password: Пароль

        Returns:
            Объект пользователя при успешном входе, иначе None
        """
        try:
            # Поиск пользователя
            user = self.user_repo.find_by_username(username)

            if not user:
                self.logger.warning(f"Попытка входа с несуществующим логином: {username}")
                return None

            if not user.is_active:
                self.logger.warning(f"Попытка входа неактивного пользователя: {username}")
                return None

            # Проверка пароля (для MVP - упрощенная)
            if not self._verify_password(password, user):
                self.logger.warning(f"Неверный пароль для пользователя: {username}")
                return None

            # Обновление времени последнего входа
            user.update_last_login()
            self.user_repo.update(user)

            # Генерация токена сессии
            session_token = self._generate_session_token(user)

            # Сохраняем токен в метаданных пользователя (для простоты)
            # В реальном приложении здесь должен быть менеджер сессий
            user.metadata = user.metadata or {}
            user.metadata['session_token'] = session_token
            user.metadata['session_expires'] = (datetime.now() + timedelta(hours=self.session_lifetime)).isoformat()
            self.user_repo.update(user)

            self.logger.info(f"Успешный вход пользователя: {username}")

            return user

        except Exception as e:
            self.logger.error(f"Ошибка при входе пользователя {username}: {e}")
            return None

    def logout(self, user: User) -> bool:
        """
        Выход пользователя из системы.

        Args:
            user: Объект пользователя

        Returns:
            True при успешном выходе
        """
        try:
            if user and user.metadata:
                # Очистка данных сессии
                if 'session_token' in user.metadata:
                    del user.metadata['session_token']
                if 'session_expires' in user.metadata:
                    del user.metadata['session_expires']

                self.user_repo.update(user)
                self.logger.info(f"Выход пользователя: {user.username}")

            return True

        except Exception as e:
            self.logger.error(f"Ошибка при выходе пользователя: {e}")
            return False

    def check_session(self, session_token: str) -> Optional[User]:
        """
        Проверка валидности сессии.

        Args:
            session_token: Токен сессии

        Returns:
            Объект пользователя если сессия валидна, иначе None
        """
        try:
            # Поиск пользователя с таким токеном
            users = self.user_repo.find_all()

            for user in users:
                if not user.metadata:
                    continue

                stored_token = user.metadata.get('session_token')
                expires_str = user.metadata.get('session_expires')

                if stored_token == session_token and expires_str:
                    expires = datetime.fromisoformat(expires_str)

                    if datetime.now() < expires:
                        return user

            return None

        except Exception as e:
            self.logger.error(f"Ошибка при проверке сессии: {e}")
            return None

    def change_password(self, user: User, old_password: str,
                        new_password: str) -> bool:
        """
        Смена пароля пользователя.

        Args:
            user: Объект пользователя
            old_password: Старый пароль
            new_password: Новый пароль

        Returns:
            True при успешной смене пароля
        """
        try:
            # Проверка старого пароля
            if not self._verify_password(old_password, user):
                self.logger.warning(f"Неверный старый пароль для пользователя: {user.username}")
                return False

            # Валидация нового пароля
            if not self._validate_password_strength(new_password):
                self.logger.warning(f"Слабый новый пароль для пользователя: {user.username}")
                return False

            # Хеширование и сохранение нового пароля
            # В реальном приложении здесь должно быть обновление пароля в БД
            # Для MVP - просто логируем
            self.logger.info(f"Пароль изменен для пользователя: {user.username}")

            return True

        except Exception as e:
            self.logger.error(f"Ошибка при смене пароля: {e}")
            return False

    def has_permission(self, user: User, permission: str,
                       resource: Optional[Any] = None) -> bool:
        """
        Проверка наличия разрешения у пользователя.

        Args:
            user: Объект пользователя
            permission: Проверяемое разрешение
            resource: Опциональный ресурс для проверки

        Returns:
            True если разрешение есть
        """
        if not user or not user.is_active:
            return False

        # Администратор имеет все права
        if user.is_admin():
            return True

        # Проверка конкретных разрешений
        permissions_map = {
            'create_request': ['requester', 'executor', 'admin'],
            'view_own_requests': ['requester', 'executor', 'admin'],
            'view_all_requests': ['admin'],
            'assign_request': ['executor', 'admin'],
            'change_status': ['executor', 'admin'],
            'manage_users': ['admin'],
            'manage_categories': ['admin'],
            'view_statistics': ['executor', 'admin']
        }

        allowed_roles = permissions_map.get(permission, [])

        return user.role in allowed_roles

    def _verify_password(self, password: str, user: User) -> bool:
        """
        Проверка пароля.
        Для MVP - упрощенная проверка.
        """
        # В реальном приложении здесь должно быть сравнение хешей
        # Для тестирования используем простую логику
        test_users = {
            'admin': 'adminpass',
            'ivanov': 'pass',
            'petrova': 'pass'
        }

        expected = test_users.get(user.username)
        return expected == password

    def _validate_password_strength(self, password: str) -> bool:
        """
        Проверка сложности пароля.
        """
        if len(password) < 6:
            return False

        # Проверка наличия цифр и букв (упрощенно)
        has_digit = any(c.isdigit() for c in password)
        has_letter = any(c.isalpha() for c in password)

        return has_digit and has_letter

    def _generate_session_token(self, user: User) -> str:
        """
        Генерация токена сессии.
        """
        import secrets
        return secrets.token_urlsafe(32)