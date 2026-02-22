"""
Репозиторий для работы с категориями заявок.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime

from repositories.base_repository import BaseRepository
from models.category import Category


class CategoryRepository(BaseRepository[Category]):
    """
    Репозиторий для работы с категориями.

    Предоставляет специфические методы для категорий:
    - find_by_name - поиск по названию
    - get_active - получение активных категорий
    - find_children - получение дочерних категорий
    - find_root - получение корневых категорий
    """

    def __init__(self):
        """Инициализация репозитория категорий"""
        super().__init__('categories', Category)

    def create(self, category: Category) -> Optional[int]:
        """
        Создание новой категории.

        Args:
            category: Объект категории

        Returns:
            ID созданной категории
        """
        try:
            query = """
            INSERT INTO categories 
            (name, description, sla_hours, is_active, parent_id, "order",
             created_at, updated_at, icon, color, required_fields, auto_assign_to)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """

            import json
            params = (
                category.name,
                category.description,
                category.sla_hours,
                1 if category.is_active else 0,
                category.parent_id,
                category.order,
                category.created_at or datetime.now(),
                category.updated_at or datetime.now(),
                category.icon,
                category.color,
                json.dumps(category.required_fields) if category.required_fields else None,
                category.auto_assign_to
            )

            category.id = self.db.execute_insert(query, params)
            self.logger.info(f"Создана новая категория: {category.name} (ID: {category.id})")

            return category.id

        except Exception as e:
            self.logger.error(f"Ошибка при создании категории: {e}")
            return None

    def update(self, category: Category) -> bool:
        """
        Обновление категории.

        Args:
            category: Объект категории

        Returns:
            True при успешном обновлении
        """
        try:
            query = """
            UPDATE categories 
            SET name = ?, description = ?, sla_hours = ?, is_active = ?,
                parent_id = ?, "order" = ?, updated_at = ?, icon = ?,
                color = ?, required_fields = ?, auto_assign_to = ?
            WHERE id = ?
            """

            import json
            params = (
                category.name,
                category.description,
                category.sla_hours,
                1 if category.is_active else 0,
                category.parent_id,
                category.order,
                datetime.now(),
                category.icon,
                category.color,
                json.dumps(category.required_fields) if category.required_fields else None,
                category.auto_assign_to,
                category.id
            )

            affected = self.db.execute_update(query, params)

            if affected > 0:
                self.logger.info(f"Категория {category.name} (ID: {category.id}) обновлена")
                return True

            return False

        except Exception as e:
            self.logger.error(f"Ошибка при обновлении категории {category.id}: {e}")
            return False

    def find_by_name(self, name: str) -> Optional[Category]:
        """
        Поиск категории по названию.

        Args:
            name: Название категории

        Returns:
            Объект категории или None
        """
        try:
            query = "SELECT * FROM categories WHERE name = ?"
            results = self.db.execute_query(query, (name,))

            if results:
                return Category.from_db_row(results[0])
            return None

        except Exception as e:
            self.logger.error(f"Ошибка при поиске категории по названию '{name}': {e}")
            return None

    def get_active(self) -> List[Category]:
        """
        Получение всех активных категорий.

        Returns:
            Список активных категорий
        """
        try:
            query = "SELECT * FROM categories WHERE is_active = 1 ORDER BY \"order\", name"
            results = self.db.execute_query(query)

            return [Category.from_db_row(row) for row in results]

        except Exception as e:
            self.logger.error(f"Ошибка при получении активных категорий: {e}")
            return []

    def find_children(self, parent_id: int) -> List[Category]:
        """
        Получение дочерних категорий.

        Args:
            parent_id: ID родительской категории

        Returns:
            Список дочерних категорий
        """
        try:
            query = """
            SELECT * FROM categories 
            WHERE parent_id = ? AND is_active = 1 
            ORDER BY \"order\", name
            """
            results = self.db.execute_query(query, (parent_id,))

            return [Category.from_db_row(row) for row in results]

        except Exception as e:
            self.logger.error(f"Ошибка при получении дочерних категорий для {parent_id}: {e}")
            return []

    def find_root(self) -> List[Category]:
        """
        Получение корневых категорий (без родителя).

        Returns:
            Список корневых категорий
        """
        try:
            query = """
            SELECT * FROM categories 
            WHERE parent_id IS NULL AND is_active = 1 
            ORDER BY \"order\", name
            """
            results = self.db.execute_query(query)

            return [Category.from_db_row(row) for row in results]

        except Exception as e:
            self.logger.error(f"Ошибка при получении корневых категорий: {e}")
            return []

    def get_tree(self) -> List[Dict[str, Any]]:
        """
        Получение иерархического дерева категорий.

        Returns:
            Дерево категорий
        """
        try:
            all_categories = self.find_all()
            category_dict = {c.id: c for c in all_categories}

            def build_node(cat: Category) -> Dict[str, Any]:
                children = []
                for c in all_categories:
                    if c.parent_id == cat.id:
                        children.append(build_node(c))

                return {
                    'id': cat.id,
                    'name': cat.name,
                    'description': cat.description,
                    'sla_hours': cat.sla_hours,
                    'is_active': cat.is_active,
                    'order': cat.order,
                    'color': cat.color,
                    'children': sorted(children, key=lambda x: x['order'])
                }

            root_categories = [c for c in all_categories if not c.parent_id]
            return [build_node(cat) for cat in sorted(root_categories, key=lambda x: x.order)]

        except Exception as e:
            self.logger.error(f"Ошибка при построении дерева категорий: {e}")
            return []

    def get_statistics(self) -> Dict[str, Any]:
        """
        Получение статистики по категориям.

        Returns:
            Словарь со статистикой
        """
        try:
            categories = self.find_all()

            total = len(categories)
            active = len([c for c in categories if c.is_active])
            root = len([c for c in categories if not c.parent_id])

            if categories:
                avg_sla = sum(c.sla_hours for c in categories) / total
            else:
                avg_sla = 0

            return {
                'total': total,
                'active': active,
                'inactive': total - active,
                'root': root,
                'avg_sla_hours': round(avg_sla, 2)
            }

        except Exception as e:
            self.logger.error(f"Ошибка при получении статистики категорий: {e}")
            return {}