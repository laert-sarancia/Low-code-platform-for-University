"""
Модель заявки на IT-обслуживание.
Представляет запрос пользователя на решение проблемы или получение услуги.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any


@dataclass
class Request:
    """
    Класс заявки на IT-обслуживание.

    Attributes:
        id: Уникальный номер заявки
        title: Краткое описание (тема)
        description: Подробное описание проблемы
        requester_id: ID создателя заявки
        assignee_id: ID исполнителя
        category_id: ID категории
        status_id: ID статуса
        priority: Приоритет (critical, high, medium, low)
        created_at: Дата создания
        updated_at: Дата последнего обновления
        resolved_at: Дата решения
        closed_at: Дата закрытия
        sla_due_date: Крайний срок по SLA
        estimated_hours: Оценка времени решения (часы)
        actual_hours: Фактическое время решения (часы)
        satisfaction_rating: Оценка удовлетворенности (1-5)
        satisfaction_comment: Комментарий к оценке
        is_deleted: Помечена ли на удаление
    """

    id: Optional[int] = None
    title: str = ""
    description: Optional[str] = None
    requester_id: Optional[int] = None
    assignee_id: Optional[int] = None
    category_id: Optional[int] = None
    status_id: Optional[int] = None
    priority: str = "medium"  # critical, high, medium, low
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    sla_due_date: Optional[datetime] = None
    estimated_hours: Optional[float] = None
    actual_hours: Optional[float] = None
    satisfaction_rating: Optional[int] = None
    satisfaction_comment: Optional[str] = None
    is_deleted: bool = False

    # Допустимые приоритеты
    VALID_PRIORITIES = ['critical', 'high', 'medium', 'low']

    # Словарь для перевода приоритетов
    PRIORITY_DISPLAY = {
        'critical': 'Критический',
        'high': 'Высокий',
        'medium': 'Средний',
        'low': 'Низкий'
    }

    def __post_init__(self):
        """Валидация после инициализации"""
        self.validate()

    def validate(self) -> bool:
        """
        Валидация данных заявки.

        Returns:
            True если данные корректны

        Raises:
            ValueError: При некорректных данных
        """
        if self.title and len(self.title) < 5:
            raise ValueError("Тема должна содержать минимум 5 символов")

        if self.priority and self.priority not in self.VALID_PRIORITIES:
            raise ValueError(f"Приоритет должен быть одним из: {self.VALID_PRIORITIES}")

        if self.satisfaction_rating is not None:
            if not 1 <= self.satisfaction_rating <= 5:
                raise ValueError("Оценка удовлетворенности должна быть от 1 до 5")

        return True

    @classmethod
    def from_db_row(cls, row: Dict[str, Any]) -> 'Request':
        """
        Создание объекта заявки из строки БД.

        Args:
            row: Словарь с данными из БД

        Returns:
            Объект Request
        """
        if not row:
            return cls()

        # Функция для преобразования строки в datetime
        def parse_datetime(value):
            if not value:
                return None
            if isinstance(value, str):
                return datetime.fromisoformat(value.replace('Z', '+00:00'))
            return value

        return cls(
            id=row.get('id'),
            title=row.get('title', ''),
            description=row.get('description'),
            requester_id=row.get('requester_id'),
            assignee_id=row.get('assignee_id'),
            category_id=row.get('category_id'),
            status_id=row.get('status_id'),
            priority=row.get('priority', 'medium'),
            created_at=parse_datetime(row.get('created_at')),
            updated_at=parse_datetime(row.get('updated_at')),
            resolved_at=parse_datetime(row.get('resolved_at')),
            closed_at=parse_datetime(row.get('closed_at')),
            sla_due_date=parse_datetime(row.get('sla_due_date')),
            estimated_hours=row.get('estimated_hours'),
            actual_hours=row.get('actual_hours'),
            satisfaction_rating=row.get('satisfaction_rating'),
            satisfaction_comment=row.get('satisfaction_comment'),
            is_deleted=bool(row.get('is_deleted', False))
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Преобразование объекта в словарь для БД.

        Returns:
            Словарь с данными заявки
        """
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'requester_id': self.requester_id,
            'assignee_id': self.assignee_id,
            'category_id': self.category_id,
            'status_id': self.status_id,
            'priority': self.priority,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'closed_at': self.closed_at.isoformat() if self.closed_at else None,
            'sla_due_date': self.sla_due_date.isoformat() if self.sla_due_date else None,
            'estimated_hours': self.estimated_hours,
            'actual_hours': self.actual_hours,
            'satisfaction_rating': self.satisfaction_rating,
            'satisfaction_comment': self.satisfaction_comment,
            'is_deleted': 1 if self.is_deleted else 0
        }

    # ==================== МЕТОДЫ ДЛЯ РАБОТЫ СО СТАТУСАМИ ====================

    def is_new(self) -> bool:
        """Проверка, является ли заявка новой"""
        return self.status_id == 1  # ID статуса "Новая"

    def is_in_progress(self) -> bool:
        """Проверка, в работе ли заявка"""
        return self.status_id == 2  # ID статуса "В работе"

    def is_resolved(self) -> bool:
        """Проверка, решена ли заявка"""
        return self.status_id == 3  # ID статуса "Решена"

    def is_closed(self) -> bool:
        """Проверка, закрыта ли заявка"""
        return self.status_id == 4  # ID статуса "Закрыта"

    def is_rejected(self) -> bool:
        """Проверка, отклонена ли заявка"""
        return self.status_id == 5  # ID статуса "Отклонена"

    def is_finished(self) -> bool:
        """Проверка, завершена ли заявка (решена, закрыта, отклонена)"""
        return self.status_id in [3, 4, 5]

    # ==================== МЕТОДЫ ДЛЯ РАБОТЫ С ПРИОРИТЕТАМИ ====================

    def is_critical(self) -> bool:
        """Проверка критического приоритета"""
        return self.priority == 'critical'

    def is_high(self) -> bool:
        """Проверка высокого приоритета"""
        return self.priority == 'high'

    def is_medium(self) -> bool:
        """Проверка среднего приоритета"""
        return self.priority == 'medium'

    def is_low(self) -> bool:
        """Проверка низкого приоритета"""
        return self.priority == 'low'

    def get_priority_display(self) -> str:
        """Получение названия приоритета для отображения"""
        return self.PRIORITY_DISPLAY.get(self.priority, self.priority)

    def get_priority_level(self) -> int:
        """Получение числового уровня приоритета (1 - highest)"""
        levels = {
            'critical': 1,
            'high': 2,
            'medium': 3,
            'low': 4
        }
        return levels.get(self.priority, 99)

    def get_sla_hours(self) -> int:
        """Получение количества часов SLA по приоритету"""
        from config import Config
        return Config.SLA_LIMITS.get(self.priority, 24)

    # ==================== МЕТОДЫ ДЛЯ РАСЧЕТА ВРЕМЕНИ ====================

    def calculate_age(self) -> float:
        """
        Расчет возраста заявки в часах.

        Returns:
            Количество часов с момента создания
        """
        if not self.created_at:
            return 0

        delta = datetime.now() - self.created_at
        return delta.total_seconds() / 3600

    def calculate_resolution_time(self) -> Optional[float]:
        """
        Расчет времени решения в часах.

        Returns:
            Количество часов между созданием и решением,
            None если заявка еще не решена
        """
        if not self.resolved_at or not self.created_at:
            return None

        delta = self.resolved_at - self.created_at
        return delta.total_seconds() / 3600

    def calculate_working_time(self) -> Optional[float]:
        """
        Расчет рабочего времени с учетом рабочего графика.

        Returns:
            Количество рабочих часов
        """
        from services.sla_service import SLAService

        sla_service = SLAService()
        end_time = self.resolved_at or datetime.now()

        return sla_service._calculate_work_hours(self.created_at, end_time)

    # ==================== МЕТОДЫ ДЛЯ ИЗМЕНЕНИЯ СОСТОЯНИЯ ====================

    def assign_to(self, user_id: int):
        """
        Назначение заявки на исполнителя.

        Args:
            user_id: ID исполнителя
        """
        self.assignee_id = user_id
        self.updated_at = datetime.now()

        # Если заявка была новой, меняем статус на "В работе"
        if self.is_new():
            self.status_id = 2

    def start_work(self):
        """Начало работы над заявкой"""
        if self.is_new():
            self.status_id = 2  # В работе
            self.updated_at = datetime.now()

    def resolve(self):
        """Отметка о решении заявки"""
        if not self.is_finished():
            self.status_id = 3  # Решена
            self.resolved_at = datetime.now()
            self.updated_at = datetime.now()

            # Расчет фактического времени
            if self.created_at:
                self.actual_hours = self.calculate_resolution_time()

    def close(self):
        """Закрытие заявки"""
        if not self.is_closed():
            self.status_id = 4  # Закрыта
            self.closed_at = datetime.now()
            self.updated_at = datetime.now()

    def reject(self, reason: Optional[str] = None):
        """Отклонение заявки"""
        self.status_id = 5  # Отклонена
        if reason:
            self.description = (self.description or "") + f"\n\nОтклонена: {reason}"
        self.updated_at = datetime.now()

    def add_satisfaction(self, rating: int, comment: Optional[str] = None):
        """
        Добавление оценки удовлетворенности.

        Args:
            rating: Оценка от 1 до 5
            comment: Комментарий к оценке
        """
        if not 1 <= rating <= 5:
            raise ValueError("Оценка должна быть от 1 до 5")

        self.satisfaction_rating = rating
        self.satisfaction_comment = comment
        self.updated_at = datetime.now()

    # ==================== МЕТОДЫ ДЛЯ ОТОБРАЖЕНИЯ ====================

    def get_title_preview(self, length: int = 50) -> str:
        """Получение превью темы"""
        if len(self.title) <= length:
            return self.title
        return self.title[:length - 3] + "..."

    def get_description_preview(self, length: int = 100) -> str:
        """Получение превью описания"""
        if not self.description:
            return ""
        if len(self.description) <= length:
            return self.description
        return self.description[:length - 3] + "..."

    def get_status_color(self) -> str:
        """Получение цвета статуса"""
        status_colors = {
            1: '#3498db',  # Новая - синий
            2: '#f39c12',  # В работе - оранжевый
            3: '#2ecc71',  # Решена - зеленый
            4: '#95a5a6',  # Закрыта - серый
            5: '#e74c3c'  # Отклонена - красный
        }
        return status_colors.get(self.status_id, '#000000')

    def __str__(self) -> str:
        """Строковое представление заявки"""
        status_icons = {
            1: '🆕',
            2: '🔄',
            3: '✅',
            4: '🔒',
            5: '❌'
        }
        icon = status_icons.get(self.status_id, '📋')

        return f"{icon} #{self.id}: {self.get_title_preview(40)} [{self.priority}]"

    def __repr__(self) -> str:
        """Представление для отладки"""
        return f"Request(id={self.id}, title='{self.title[:20]}...', status_id={self.status_id})"