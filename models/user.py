"""Модель пользователя"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any
import re


@dataclass
class User:
    """
    Класс пользователя системы.

    Attributes:
        id: Уникальный идентификатор пользователя
        username: Логин для входа в систему
        email: Электронная почта
        full_name: Полное имя (ФИО)
        department: Отдел/подразделение
        role: Роль в системе (requester, executor, admin)
        is_active: Активен ли пользователь
        created_at: Дата создания записи
        updated_at: Дата последнего обновления
        last_login: Дата последнего входа
        phone: Контактный телефон
        telegram_id: ID в Telegram для уведомлений
    """

    id: Optional[int] = None
    username: str = ""
    email: str = ""
    full_name: str = ""
    department: str = ""
    role: str = "requester"  # requester, executor, admin
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    phone: Optional[str] = None
    telegram_id: Optional[str] = None

    # Допустимые роли
    VALID_ROLES = ['requester', 'executor', 'admin']

    def __post_init__(self):
        """Валидация после инициализации"""
        self.validate()

    def validate(self) -> bool:
        """
        Валидация данных пользователя.

        Returns:
            True если данные корректны

        Raises:
            ValueError: При некорректных данных
        """
        if self.username and len(self.username) < 3:
            raise ValueError("Логин должен содержать минимум 3 символа")

        if self.email and not self._is_valid_email(self.email):
            raise ValueError("Некорректный формат email")

        if self.role and self.role not in self.VALID_ROLES:
            raise ValueError(f"Роль должна быть одной из: {self.VALID_ROLES}")

        if self.full_name and len(self.full_name.split()) < 2:
            raise ValueError("Укажите полное имя и фамилию")

        return True

    @staticmethod
    def _is_valid_email(email: str) -> bool:
        """Проверка корректности email"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None

    @classmethod
    def from_db_row(cls, row: dict) -> 'User':
        """
        Создание объекта пользователя из строки БД.

        Args:
            row: Словарь с данными из БД

        Returns:
            Объект User
        """
        if not row:
            return cls()

        # Преобразование строковых дат в объекты datetime
        created_at = None
        if row.get('created_at'):
            if isinstance(row['created_at'], str):
                created_at = datetime.fromisoformat(row['created_at'].replace('Z', '+00:00'))
            else:
                created_at = row['created_at']

        updated_at = None
        if row.get('updated_at'):
            if isinstance(row['updated_at'], str):
                updated_at = datetime.fromisoformat(row['updated_at'].replace('Z', '+00:00'))
            else:
                updated_at = row['updated_at']

        last_login = None
        if row.get('last_login'):
            if isinstance(row['last_login'], str):
                last_login = datetime.fromisoformat(row['last_login'].replace('Z', '+00:00'))
            else:
                last_login = row['last_login']

        return cls(
            id=row.get('id'),
            username=row.get('username', ''),
            email=row.get('email', ''),
            full_name=row.get('full_name', ''),
            department=row.get('department', ''),
            role=row.get('role', 'requester'),
            is_active=bool(row.get('is_active', True)),
            created_at=created_at,
            updated_at=updated_at,
            last_login=last_login,
            phone=row.get('phone'),
            telegram_id=row.get('telegram_id')
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Преобразование объекта в словарь для БД.

        Returns:
            Словарь с данными пользователя
        """
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'full_name': self.full_name,
            'department': self.department,
            'role': self.role,
            'is_active': 1 if self.is_active else 0,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'phone': self.phone,
            'telegram_id': self.telegram_id
        }

    # ==================== МЕТОДЫ ДЛЯ ПРОВЕРКИ РОЛЕЙ ====================

    def is_requester(self) -> bool:
        """Проверка, является ли пользователь заявителем"""
        return self.role == 'requester'

    def is_executor(self) -> bool:
        """Проверка, является ли пользователь исполнителем"""
        return self.role == 'executor' or self.role == 'admin'

    def is_admin(self) -> bool:
        """Проверка, является ли пользователь администратором"""
        return self.role == 'admin'

    def can_manage_requests(self) -> bool:
        """Может ли пользователь управлять заявками (исполнитель/админ)"""
        return self.role in ['executor', 'admin']

    def can_manage_users(self) -> bool:
        """Может ли пользователь управлять пользователями (только админ)"""
        return self.role == 'admin'

    # ==================== МЕТОДЫ ДЛЯ РАБОТЫ С ДАННЫМИ ====================

    def update_last_login(self):
        """Обновление времени последнего входа"""
        self.last_login = datetime.now()
        self.updated_at = datetime.now()

    def deactivate(self):
        """Деактивация пользователя"""
        self.is_active = False
        self.updated_at = datetime.now()

    def activate(self):
        """Активация пользователя"""
        self.is_active = True
        self.updated_at = datetime.now()

    def change_role(self, new_role: str):
        """
        Изменение роли пользователя.

        Args:
            new_role: Новая роль

        Raises:
            ValueError: При некорректной роли
        """
        if new_role not in self.VALID_ROLES:
            raise ValueError(f"Некорректная роль. Допустимы: {self.VALID_ROLES}")

        self.role = new_role
        self.updated_at = datetime.now()

    # ==================== МЕТОДЫ ДЛЯ ОТОБРАЖЕНИЯ ====================

    def get_display_name(self) -> str:
        """Получение имени для отображения"""
        if self.full_name:
            return self.full_name
        return self.username

    def get_short_name(self) -> str:
        """Получение сокращенного имени (Фамилия И.О.)"""
        if not self.full_name:
            return self.username

        parts = self.full_name.split()
        if len(parts) == 1:
            return parts[0]
        elif len(parts) == 2:
            return f"{parts[0]} {parts[1][0]}."
        else:
            return f"{parts[0]} {parts[1][0]}.{parts[2][0]}."

    def get_role_display(self) -> str:
        """Получение названия роли для отображения"""
        roles = {
            'requester': 'Заявитель',
            'executor': 'Исполнитель',
            'admin': 'Администратор'
        }
        return roles.get(self.role, self.role)

    def __str__(self) -> str:
        """Строковое представление пользователя"""
        status = "✓" if self.is_active else "✗"
        return f"[{status}] {self.get_short_name()} ({self.get_role_display()})"

    def __repr__(self) -> str:
        """Представление для отладки"""
        return f"User(id={self.id}, username='{self.username}', role='{self.role}')"