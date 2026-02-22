"""
Модель истории изменений заявки.
Фиксирует все действия с заявкой для аудита и отслеживания.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any


@dataclass
class RequestHistory:
    """
    Класс записи истории изменений заявки.

    Attributes:
        id: Уникальный идентификатор записи
        request_id: ID заявки
        action: Тип действия (create, assign, status_change, comment, etc.)
        old_value: Старое значение
        new_value: Новое значение
        comment: Комментарий к действию
        changed_by: ID пользователя, совершившего действие
        changed_at: Дата и время изменения
        field_name: Название измененного поля
        metadata: Дополнительные данные (JSON)
    """

    id: Optional[int] = None
    request_id: Optional[int] = None
    action: str = ""  # create, assign, status_change, comment, attachment, etc.
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    comment: Optional[str] = None
    changed_by: Optional[int] = None
    changed_at: Optional[datetime] = None
    field_name: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    # Типы действий
    ACTIONS = [
        'create',  # Создание заявки
        'status_change',  # Изменение статуса
        'assign',  # Назначение исполнителя
        'comment',  # Добавление комментария
        'attachment_add',  # Добавление вложения
        'attachment_remove',  # Удаление вложения
        'field_change',  # Изменение поля
        'priority_change',  # Изменение приоритета
        'category_change',  # Изменение категории
        'satisfaction',  # Оценка удовлетворенности
        'reopen',  # Переоткрытие
        'close'  # Закрытие
    ]

    def __post_init__(self):
        """Валидация после инициализации"""
        self.validate()

    def validate(self) -> bool:
        """
        Валидация данных истории.

        Returns:
            True если данные корректны

        Raises:
            ValueError: При некорректных данных
        """
        if self.action and self.action not in self.ACTIONS:
            raise ValueError(f"Действие должно быть одним из: {self.ACTIONS}")

        return True

    @classmethod
    def from_db_row(cls, row: Dict[str, Any]) -> 'RequestHistory':
        """
        Создание объекта истории из строки БД.

        Args:
            row: Словарь с данными из БД

        Returns:
            Объект RequestHistory
        """
        if not row:
            return cls()

        # Парсинг JSON метаданных
        metadata = row.get('metadata')
        if metadata and isinstance(metadata, str):
            import json
            try:
                metadata = json.loads(metadata)
            except:
                metadata = {}

        # Преобразование даты
        changed_at = None
        if row.get('changed_at'):
            if isinstance(row['changed_at'], str):
                changed_at = datetime.fromisoformat(row['changed_at'].replace('Z', '+00:00'))
            else:
                changed_at = row['changed_at']

        return cls(
            id=row.get('id'),
            request_id=row.get('request_id'),
            action=row.get('action', ''),
            old_value=row.get('old_value'),
            new_value=row.get('new_value'),
            comment=row.get('comment'),
            changed_by=row.get('changed_by'),
            changed_at=changed_at,
            field_name=row.get('field_name'),
            metadata=metadata
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Преобразование объекта в словарь для БД.

        Returns:
            Словарь с данными истории
        """
        import json

        return {
            'id': self.id,
            'request_id': self.request_id,
            'action': self.action,
            'old_value': self.old_value,
            'new_value': self.new_value,
            'comment': self.comment,
            'changed_by': self.changed_by,
            'changed_at': self.changed_at.isoformat() if self.changed_at else None,
            'field_name': self.field_name,
            'metadata': json.dumps(self.metadata) if self.metadata else None
        }

    # ==================== ФАБРИЧНЫЕ МЕТОДЫ ====================

    @classmethod
    def create_creation_record(cls, request_id: int, user_id: int,
                               request_data: Dict) -> 'RequestHistory':
        """
        Создание записи о создании заявки.

        Args:
            request_id: ID заявки
            user_id: ID создателя
            request_data: Данные заявки

        Returns:
            Объект RequestHistory
        """
        return cls(
            request_id=request_id,
            action='create',
            new_value=str(request_data),
            changed_by=user_id,
            changed_at=datetime.now(),
            metadata={'initial_data': request_data}
        )

    @classmethod
    def create_status_change(cls, request_id: int, user_id: int,
                             old_status: int, new_status: int,
                             comment: Optional[str] = None) -> 'RequestHistory':
        """
        Создание записи об изменении статуса.

        Args:
            request_id: ID заявки
            user_id: ID пользователя
            old_status: Старый статус
            new_status: Новый статус
            comment: Комментарий

        Returns:
            Объект RequestHistory
        """
        return cls(
            request_id=request_id,
            action='status_change',
            old_value=str(old_status),
            new_value=str(new_status),
            comment=comment,
            changed_by=user_id,
            changed_at=datetime.now(),
            field_name='status_id'
        )

    @classmethod
    def create_assign_record(cls, request_id: int, user_id: int,
                             old_assignee: Optional[int],
                             new_assignee: int,
                             comment: Optional[str] = None) -> 'RequestHistory':
        """
        Создание записи о назначении исполнителя.

        Args:
            request_id: ID заявки
            user_id: ID пользователя, назначившего
            old_assignee: Старый исполнитель
            new_assignee: Новый исполнитель
            comment: Комментарий

        Returns:
            Объект RequestHistory
        """
        return cls(
            request_id=request_id,
            action='assign',
            old_value=str(old_assignee) if old_assignee else None,
            new_value=str(new_assignee),
            comment=comment,
            changed_by=user_id,
            changed_at=datetime.now(),
            field_name='assignee_id'
        )

    @classmethod
    def create_comment_record(cls, request_id: int, user_id: int,
                              comment: str) -> 'RequestHistory':
        """
        Создание записи о добавлении комментария.

        Args:
            request_id: ID заявки
            user_id: ID автора комментария
            comment: Текст комментария

        Returns:
            Объект RequestHistory
        """
        return cls(
            request_id=request_id,
            action='comment',
            new_value=comment,
            changed_by=user_id,
            changed_at=datetime.now(),
            comment=comment
        )

    @classmethod
    def create_field_change(cls, request_id: int, user_id: int,
                            field_name: str, old_value: Any,
                            new_value: Any) -> 'RequestHistory':
        """
        Создание записи об изменении поля.

        Args:
            request_id: ID заявки
            user_id: ID пользователя
            field_name: Название поля
            old_value: Старое значение
            new_value: Новое значение

        Returns:
            Объект RequestHistory
        """
        return cls(
            request_id=request_id,
            action='field_change',
            old_value=str(old_value) if old_value else None,
            new_value=str(new_value) if new_value else None,
            changed_by=user_id,
            changed_at=datetime.now(),
            field_name=field_name
        )

    # ==================== МЕТОДЫ ДЛЯ ОТОБРАЖЕНИЯ ====================

    def get_action_display(self) -> str:
        """Получение названия действия для отображения"""
        action_names = {
            'create': 'Создание',
            'status_change': 'Изменение статуса',
            'assign': 'Назначение',
            'comment': 'Комментарий',
            'attachment_add': 'Добавление файла',
            'attachment_remove': 'Удаление файла',
            'field_change': 'Изменение поля',
            'priority_change': 'Изменение приоритета',
            'category_change': 'Изменение категории',
            'satisfaction': 'Оценка',
            'reopen': 'Переоткрытие',
            'close': 'Закрытие'
        }
        return action_names.get(self.action, self.action)

    def get_action_icon(self) -> str:
        """Получение иконки действия"""
        icons = {
            'create': '➕',
            'status_change': '🔄',
            'assign': '👤',
            'comment': '💬',
            'attachment_add': '📎',
            'attachment_remove': '🗑️',
            'field_change': '✏️',
            'priority_change': '⚡',
            'category_change': '📂',
            'satisfaction': '⭐',
            'reopen': '↩️',
            'close': '🔒'
        }
        return icons.get(self.action, '📝')

    def __str__(self) -> str:
        """Строковое представление записи истории"""
        time_str = self.changed_at.strftime('%d.%m.%Y %H:%M') if self.changed_at else '--'
        icon = self.get_action_icon()

        if self.action == 'comment':
            return f"{time_str} {icon} Комментарий: {self.comment[:50]}..."
        elif self.action == 'status_change':
            return f"{time_str} {icon} Статус: {self.old_value} → {self.new_value}"
        elif self.action == 'assign':
            return f"{time_str} {icon} Исполнитель: {self.new_value}"
        else:
            return f"{time_str} {icon} {self.get_action_display()}"

    def __repr__(self) -> str:
        """Представление для отладки"""
        return f"RequestHistory(id={self.id}, request={self.request_id}, action='{self.action}')"