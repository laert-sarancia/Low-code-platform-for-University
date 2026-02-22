"""
Модель статуса заявки.
Определяет возможные состояния заявки в жизненном цикле.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any, List


@dataclass
class Status:
    """
    Класс статуса заявки.

    Attributes:
        id: Уникальный идентификатор статуса
        name: Название статуса
        code: Код статуса (для программного использования)
        description: Описание статуса
        color: Цвет для отображения
        order: Порядок сортировки
        is_initial: Является ли начальным статусом
        is_final: Является ли конечным статусом
        requires_comment: Требует ли комментарий при переходе
        allowed_roles: Роли, которым доступен статус
        next_statuses: IDs возможных следующих статусов
        created_at: Дата создания
        updated_at: Дата обновления
        icon: Иконка для отображения
    """

    id: Optional[int] = None
    name: str = ""
    code: str = ""
    description: Optional[str] = None
    color: str = '#3498db'
    order: int = 0
    is_initial: bool = False
    is_final: bool = False
    requires_comment: bool = False
    allowed_roles: Optional[List[str]] = None
    next_statuses: Optional[List[int]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    icon: Optional[str] = None

    # Стандартные статусы системы
    STANDARD_STATUSES = {
        'new': {'id': 1, 'name': 'Новая', 'color': '#3498db', 'is_initial': True},
        'in_progress': {'id': 2, 'name': 'В работе', 'color': '#f39c12'},
        'resolved': {'id': 3, 'name': 'Решена', 'color': '#2ecc71', 'is_final': True},
        'closed': {'id': 4, 'name': 'Закрыта', 'color': '#95a5a6', 'is_final': True},
        'rejected': {'id': 5, 'name': 'Отклонена', 'color': '#e74c3c', 'is_final': True}
    }

    def __post_init__(self):
        """Валидация после инициализации"""
        self.validate()

    def validate(self) -> bool:
        """
        Валидация данных статуса.

        Returns:
            True если данные корректны

        Raises:
            ValueError: При некорректных данных
        """
        if self.name and len(self.name) < 2:
            raise ValueError("Название статуса должно содержать минимум 2 символа")

        if self.code and not self.code.isidentifier():
            raise ValueError("Код статуса должен быть допустимым идентификатором")

        return True

    @classmethod
    def from_db_row(cls, row: Dict[str, Any]) -> 'Status':
        """
        Создание объекта статуса из строки БД.

        Args:
            row: Словарь с данными из БД

        Returns:
            Объект Status
        """
        if not row:
            return cls()

        # Парсинг JSON полей
        allowed_roles = row.get('allowed_roles')
        if allowed_roles and isinstance(allowed_roles, str):
            import json
            try:
                allowed_roles = json.loads(allowed_roles)
            except:
                allowed_roles = []

        next_statuses = row.get('next_statuses')
        if next_statuses and isinstance(next_statuses, str):
            import json
            try:
                next_statuses = json.loads(next_statuses)
            except:
                next_statuses = []

        # Преобразование дат
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

        return cls(
            id=row.get('id'),
            name=row.get('name', ''),
            code=row.get('code', ''),
            description=row.get('description'),
            color=row.get('color', '#3498db'),
            order=row.get('order', 0),
            is_initial=bool(row.get('is_initial', False)),
            is_final=bool(row.get('is_final', False)),
            requires_comment=bool(row.get('requires_comment', False)),
            allowed_roles=allowed_roles,
            next_statuses=next_statuses,
            created_at=created_at,
            updated_at=updated_at,
            icon=row.get('icon')
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Преобразование объекта в словарь для БД.

        Returns:
            Словарь с данными статуса
        """
        import json

        return {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'description': self.description,
            'color': self.color,
            'order': self.order,
            'is_initial': 1 if self.is_initial else 0,
            'is_final': 1 if self.is_final else 0,
            'requires_comment': 1 if self.requires_comment else 0,
            'allowed_roles': json.dumps(self.allowed_roles) if self.allowed_roles else None,
            'next_statuses': json.dumps(self.next_statuses) if self.next_statuses else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'icon': self.icon
        }

    # ==================== МЕТОДЫ ДЛЯ РАБОТЫ СО СТАТУСАМИ ====================

    @classmethod
    def get_initial_status_id(cls) -> int:
        """Получение ID начального статуса"""
        return 1  # Новая

    @classmethod
    def get_final_status_ids(cls) -> List[int]:
        """Получение IDs конечных статусов"""
        return [3, 4, 5]  # Решена, Закрыта, Отклонена

    def can_transition_to(self, status_id: int) -> bool:
        """
        Проверка возможности перехода к указанному статусу.

        Args:
            status_id: ID целевого статуса

        Returns:
            True если переход возможен
        """
        if not self.next_statuses:
            return True  # Если не указаны, разрешаем все
        return status_id in self.next_statuses

    def is_allowed_for_role(self, role: str) -> bool:
        """
        Проверка доступности статуса для роли.

        Args:
            role: Роль пользователя

        Returns:
            True если статус доступен
        """
        if not self.allowed_roles:
            return True  # Если не указаны, доступен всем
        return role in self.allowed_roles

    # ==================== МЕТОДЫ ДЛЯ ОТОБРАЖЕНИЯ ====================

    def get_display_name(self) -> str:
        """Получение имени для отображения"""
        return self.name

    def get_status_badge(self) -> str:
        """Получение эмодзи для статуса"""
        badges = {
            'new': '🆕',
            'in_progress': '🔄',
            'resolved': '✅',
            'closed': '🔒',
            'rejected': '❌'
        }
        return badges.get(self.code, '📌')

    def get_color_code(self) -> str:
        """Получение ANSI color code для терминала"""
        color_map = {
            '#3498db': '\033[94m',  # Синий
            '#f39c12': '\033[93m',  # Желтый
            '#2ecc71': '\033[92m',  # Зеленый
            '#95a5a6': '\033[90m',  # Серый
            '#e74c3c': '\033[91m',  # Красный
        }
        return color_map.get(self.color, '\033[0m')

    def __str__(self) -> str:
        """Строковое представление статуса"""
        badge = self.get_status_badge()
        return f"{badge} {self.name}"

    def __repr__(self) -> str:
        """Представление для отладки"""
        return f"Status(id={self.id}, code='{self.code}', name='{self.name}')"