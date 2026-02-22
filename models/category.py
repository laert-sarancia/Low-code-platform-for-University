"""
Модель категории заявок.
Определяет типы проблем и услуг, доступных в системе.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any, List


@dataclass
class Category:
    """
    Класс категории заявок.

    Attributes:
        id: Уникальный идентификатор категории
        name: Название категории
        description: Описание категории
        sla_hours: Стандартное время решения в часах
        is_active: Активна ли категория
        parent_id: ID родительской категории (для иерархии)
        order: Порядок сортировки
        created_at: Дата создания
        updated_at: Дата обновления
        icon: Иконка для отображения
        color: Цвет для отображения
        required_fields: Обязательные поля (JSON)
        auto_assign_to: ID исполнителя для автоназначения
    """

    id: Optional[int] = None
    name: str = ""
    description: Optional[str] = None
    sla_hours: int = 24
    is_active: bool = True
    parent_id: Optional[int] = None
    order: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    icon: Optional[str] = None
    color: Optional[str] = '#3498db'
    required_fields: Optional[Dict[str, Any]] = None
    auto_assign_to: Optional[int] = None

    def __post_init__(self):
        """Валидация после инициализации"""
        self.validate()

    def validate(self) -> bool:
        """
        Валидация данных категории.

        Returns:
            True если данные корректны

        Raises:
            ValueError: При некорректных данных
        """
        if self.name and len(self.name) < 3:
            raise ValueError("Название категории должно содержать минимум 3 символа")

        if self.sla_hours and self.sla_hours <= 0:
            raise ValueError("SLA лимит должен быть положительным числом")

        if self.parent_id == self.id:
            raise ValueError("Категория не может быть родителем самой себя")

        return True

    @classmethod
    def from_db_row(cls, row: Dict[str, Any]) -> 'Category':
        """
        Создание объекта категории из строки БД.

        Args:
            row: Словарь с данными из БД

        Returns:
            Объект Category
        """
        if not row:
            return cls()

        # Парсинг JSON полей
        required_fields = row.get('required_fields')
        if required_fields and isinstance(required_fields, str):
            import json
            try:
                required_fields = json.loads(required_fields)
            except:
                required_fields = {}

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
            description=row.get('description'),
            sla_hours=row.get('sla_hours', 24),
            is_active=bool(row.get('is_active', True)),
            parent_id=row.get('parent_id'),
            order=row.get('order', 0),
            created_at=created_at,
            updated_at=updated_at,
            icon=row.get('icon'),
            color=row.get('color', '#3498db'),
            required_fields=required_fields,
            auto_assign_to=row.get('auto_assign_to')
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Преобразование объекта в словарь для БД.

        Returns:
            Словарь с данными категории
        """
        import json

        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'sla_hours': self.sla_hours,
            'is_active': 1 if self.is_active else 0,
            'parent_id': self.parent_id,
            'order': self.order,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'icon': self.icon,
            'color': self.color,
            'required_fields': json.dumps(self.required_fields) if self.required_fields else None,
            'auto_assign_to': self.auto_assign_to
        }

    # ==================== МЕТОДЫ ДЛЯ РАБОТЫ С ИЕРАРХИЕЙ ====================

    def has_parent(self) -> bool:
        """Проверка наличия родительской категории"""
        return self.parent_id is not None

    def is_root(self) -> bool:
        """Проверка, является ли категория корневой"""
        return self.parent_id is None

    def get_full_path(self, categories_dict: Dict[int, 'Category']) -> str:
        """
        Получение полного пути категории.

        Args:
            categories_dict: Словарь всех категорий {id: category}

        Returns:
            Полный путь вида "Родитель / Дочерняя"
        """
        if not self.has_parent():
            return self.name

        path = [self.name]
        current = self

        while current.has_parent():
            parent = categories_dict.get(current.parent_id)
            if not parent:
                break
            path.insert(0, parent.name)
            current = parent

        return " / ".join(path)

    def get_level(self, categories_dict: Dict[int, 'Category']) -> int:
        """
        Получение уровня вложенности.

        Args:
            categories_dict: Словарь всех категорий

        Returns:
            Уровень вложенности (0 для корневых)
        """
        level = 0
        current = self

        while current.has_parent():
            parent = categories_dict.get(current.parent_id)
            if not parent:
                break
            level += 1
            current = parent

        return level

    # ==================== МЕТОДЫ ДЛЯ РАБОТЫ С ПОЛЯМИ ====================

    def get_required_fields(self) -> List[str]:
        """
        Получение списка обязательных полей.

        Returns:
            Список названий обязательных полей
        """
        if not self.required_fields:
            return ['title', 'description']  # Базовые поля

        return self.required_fields.get('required', [])

    def get_field_validation(self, field_name: str) -> Optional[Dict]:
        """
        Получение правил валидации для поля.

        Args:
            field_name: Название поля

        Returns:
            Словарь с правилами валидации или None
        """
        if not self.required_fields:
            return None

        return self.required_fields.get('validation', {}).get(field_name)

    def has_field(self, field_name: str) -> bool:
        """Проверка наличия поля в категории"""
        if not self.required_fields:
            return field_name in ['title', 'description']

        return field_name in self.required_fields.get('fields', [])

    # ==================== МЕТОДЫ ДЛЯ ОТОБРАЖЕНИЯ ====================

    def get_display_name(self, level: int = 0) -> str:
        """
        Получение имени с отступом для иерархического отображения.

        Args:
            level: Уровень вложенности для отступа

        Returns:
            Отформатированное имя
        """
        indent = "  " * level
        return f"{indent}{self.name}"

    def get_status_badge(self) -> str:
        """Получение индикатора активности"""
        return "🟢" if self.is_active else "🔴"

    def __str__(self) -> str:
        """Строковое представление категории"""
        status = "✓" if self.is_active else "✗"
        return f"[{status}] {self.name} (SLA: {self.sla_hours}ч)"

    def __repr__(self) -> str:
        """Представление для отладки"""
        return f"Category(id={self.id}, name='{self.name}', sla={self.sla_hours})"