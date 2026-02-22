"""
Сервис для работы с категориями заявок.
Управляет справочником категорий и их иерархией.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from models.category import Category
from repositories.category_repository import CategoryRepository
from services.validation_service import ValidationService


class CategoryService:
    """
    Сервис для управления категориями заявок.
    """

    def __init__(self):
        """Инициализация сервиса категорий"""
        self.category_repo = CategoryRepository()
        self.validation_service = ValidationService()
        self.logger = logging.getLogger(__name__)

    # ==================== ОСНОВНЫЕ ОПЕРАЦИИ ====================

    def create_category(self, category_data: Dict[str, Any]) -> Optional[int]:
        """
        Создание новой категории.

        Args:
            category_data: Данные категории

        Returns:
            ID созданной категории или None
        """
        try:
            # Валидация
            self.validation_service.validate_category_data(category_data)

            # Проверка уникальности имени
            existing = self.category_repo.find_by_name(category_data['name'])
            if existing:
                raise ValueError(f"Категория с именем '{category_data['name']}' уже существует")

            # Создание объекта
            category = Category(
                name=category_data['name'],
                description=category_data.get('description'),
                sla_hours=category_data.get('sla_hours', 24),
                parent_id=category_data.get('parent_id'),
                is_active=category_data.get('is_active', True),
                order=category_data.get('order', 0),
                icon=category_data.get('icon'),
                color=category_data.get('color', '#3498db'),
                required_fields=category_data.get('required_fields'),
                auto_assign_to=category_data.get('auto_assign_to'),
                created_at=datetime.now(),
                updated_at=datetime.now()
            )

            # Проверка parent_id
            if category.parent_id and not self.category_repo.find_by_id(category.parent_id):
                raise ValueError(f"Родительская категория с ID {category.parent_id} не найдена")

            # Сохранение
            category_id = self.category_repo.create(category)

            self.logger.info(f"Создана новая категория: {category.name} (ID: {category_id})")

            return category_id

        except Exception as e:
            self.logger.error(f"Ошибка при создании категории: {e}")
            raise

    def update_category(self, category_id: int, update_data: Dict[str, Any]) -> bool:
        """
        Обновление категории.

        Args:
            category_id: ID категории
            update_data: Данные для обновления

        Returns:
            True при успешном обновлении
        """
        try:
            category = self.category_repo.find_by_id(category_id)
            if not category:
                raise ValueError(f"Категория с ID {category_id} не найдена")

            # Обновление полей
            if 'name' in update_data:
                # Проверка уникальности нового имени
                if update_data['name'] != category.name:
                    existing = self.category_repo.find_by_name(update_data['name'])
                    if existing and existing.id != category_id:
                        raise ValueError(f"Категория с именем '{update_data['name']}' уже существует")
                category.name = update_data['name']

            if 'description' in update_data:
                category.description = update_data['description']

            if 'sla_hours' in update_data:
                category.sla_hours = update_data['sla_hours']

            if 'parent_id' in update_data:
                # Проверка на циклическую зависимость
                if update_data['parent_id'] == category_id:
                    raise ValueError("Категория не может быть родителем самой себя")

                if update_data['parent_id'] and not self.category_repo.find_by_id(update_data['parent_id']):
                    raise ValueError(f"Родительская категория с ID {update_data['parent_id']} не найдена")

                category.parent_id = update_data['parent_id']

            if 'is_active' in update_data:
                category.is_active = update_data['is_active']

            if 'order' in update_data:
                category.order = update_data['order']

            if 'color' in update_data:
                category.color = update_data['color']

            if 'icon' in update_data:
                category.icon = update_data['icon']

            if 'auto_assign_to' in update_data:
                category.auto_assign_to = update_data['auto_assign_to']

            category.updated_at = datetime.now()

            # Сохранение
            success = self.category_repo.update(category)

            if success:
                self.logger.info(f"Категория {category.name} (ID: {category_id}) обновлена")

            return success

        except Exception as e:
            self.logger.error(f"Ошибка при обновлении категории {category_id}: {e}")
            raise

    def delete_category(self, category_id: int, force: bool = False) -> bool:
        """
        Удаление категории.

        Args:
            category_id: ID категории
            force: Принудительное удаление (включая дочерние)

        Returns:
            True при успешном удалении
        """
        try:
            category = self.category_repo.find_by_id(category_id)
            if not category:
                raise ValueError(f"Категория с ID {category_id} не найдена")

            # Проверка наличия дочерних категорий
            children = self.category_repo.find_children(category_id)
            if children and not force:
                raise ValueError(f"Невозможно удалить: категория имеет {len(children)} дочерних категорий")

            # Если force=True, удаляем все дочерние
            if force:
                for child in children:
                    self.category_repo.delete(child.id)

            # Удаление категории
            success = self.category_repo.delete(category_id)

            if success:
                self.logger.info(f"Категория {category.name} (ID: {category_id}) удалена")

            return success

        except Exception as e:
            self.logger.error(f"Ошибка при удалении категории {category_id}: {e}")
            raise

    # ==================== МЕТОДЫ ПОЛУЧЕНИЯ ====================

    def get_category(self, category_id: int) -> Optional[Category]:
        """Получение категории по ID"""
        return self.category_repo.find_by_id(category_id)

    def get_all_categories(self, include_inactive: bool = False) -> List[Category]:
        """Получение всех категорий"""
        if include_inactive:
            return self.category_repo.find_all()
        return self.category_repo.get_active()

    def get_category_tree(self) -> List[Dict[str, Any]]:
        """
        Получение иерархического дерева категорий.

        Returns:
            Список категорий с вложенными дочерними
        """
        all_categories = self.category_repo.find_all()

        # Создаем словарь для быстрого доступа
        category_dict = {c.id: c for c in all_categories}

        # Строим дерево
        tree = []
        for category in all_categories:
            if not category.parent_id:
                # Корневая категория
                tree.append(self._build_category_node(category, category_dict))

        return tree

    def _build_category_node(self, category: Category,
                            category_dict: Dict[int, Category]) -> Dict[str, Any]:
        """
        Построение узла дерева категорий.
        """
        children = []
        for cat in category_dict.values():
            if cat.parent_id == category.id:
                children.append(self._build_category_node(cat, category_dict))

        return {
            'id': category.id,
            'name': category.name,
            'description': category.description,
            'sla_hours': category.sla_hours,
            'is_active': category.is_active,
            'order': category.order,
            'color': category.color,
            'icon': category.icon,
            'children': sorted(children, key=lambda x: x['order'])
        }

    def get_categories_by_level(self, level: int = 0) -> List[Category]:
        """
        Получение категорий определенного уровня.

        Args:
            level: Уровень вложенности (0 - корневые)

        Returns:
            Список категорий
        """
        all_categories = self.category_repo.find_all()
        category_dict = {c.id: c for c in all_categories}

        result = []
        for category in all_categories:
            if category.get_level(category_dict) == level:
                result.append(category)

        return result

    # ==================== МЕТОДЫ ДЛЯ SLA ====================

    def get_sla_hours(self, category_id: int) -> int:
        """Получение SLA часов для категории"""
        category = self.category_repo.find_by_id(category_id)
        return category.sla_hours if category else 24

    def update_sla_hours(self, category_id: int, sla_hours: int) -> bool:
        """Обновление SLA часов для категории"""
        return self.update_category(category_id, {'sla_hours': sla_hours})

    # ==================== МЕТОДЫ СТАТИСТИКИ ====================

    def get_category_stats(self) -> Dict[str, Any]:
        """Получение статистики по категориям"""
        categories = self.category_repo.find_all()

        stats = {
            'total': len(categories),
            'active': len([c for c in categories if c.is_active]),
            'inactive': len([c for c in categories if not c.is_active]),
            'root': len([c for c in categories if not c.parent_id]),
            'avg_sla': sum(c.sla_hours for c in categories) / len(categories) if categories else 0
        }

        return stats