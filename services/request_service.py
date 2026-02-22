"""
Сервис для работы с заявками.
Реализует основную бизнес-логику обработки IT-заявок.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging

from models.request import Request
from models.request_history import RequestHistory
from models.user import User
from models.category import Category
from models.status import Status
from repositories.request_repository import RequestRepository
from repositories.user_repository import UserRepository
from repositories.category_repository import CategoryRepository
from repositories.status_repository import StatusRepository
from repositories.request_history_repository import RequestHistoryRepository
from services.sla_service import SLAService
from services.validation_service import ValidationService
from services.notification_service import NotificationService


class RequestService:
    """
    Сервис для управления заявками.

    Предоставляет методы для создания, обновления, поиска и анализа заявок.
    Реализует бизнес-правила и валидацию.
    """

    def __init__(self):
        """Инициализация сервиса с репозиториями"""
        self.request_repo = RequestRepository()
        self.user_repo = UserRepository()
        self.category_repo = CategoryRepository()
        self.status_repo = StatusRepository()
        self.history_repo = RequestHistoryRepository()

        self.sla_service = SLAService()
        self.validation_service = ValidationService()
        self.notification_service = NotificationService()

        # Настройка логирования
        self.logger = logging.getLogger(__name__)

    # ==================== ОСНОВНЫЕ ОПЕРАЦИИ ====================

    def create_request(self, request_data: Dict[str, Any], created_by: int) -> Optional[int]:
        """
        Создание новой заявки.

        Args:
            request_data: Данные заявки
            created_by: ID создателя

        Returns:
            ID созданной заявки или None в случае ошибки

        Raises:
            ValueError: При некорректных данных
        """
        try:
            # Валидация данных
            self.validation_service.validate_request_data(request_data)

            # Проверка существования пользователя
            requester = self.user_repo.find_by_id(request_data.get('requester_id', created_by))
            if not requester:
                raise ValueError(f"Пользователь с ID {request_data.get('requester_id')} не найден")

            # Проверка категории
            category = self.category_repo.find_by_id(request_data.get('category_id'))
            if not category:
                raise ValueError(f"Категория с ID {request_data.get('category_id')} не найдена")

            # Установка начального статуса
            initial_status = self.status_repo.get_initial_status()
            if not initial_status:
                raise ValueError("Не настроен начальный статус в системе")

            # Создание объекта заявки
            request = Request(
                title=request_data['title'],
                description=request_data.get('description'),
                requester_id=requester.id,
                category_id=category.id,
                priority=request_data.get('priority', 'medium'),
                status_id=initial_status.id,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )

            # Расчет SLA due date
            sla_hours = category.sla_hours
            request.sla_due_date = self.sla_service.calculate_due_date(
                request.created_at,
                sla_hours,
                request.is_critical()
            )

            # Сохранение в БД
            request_id = self.request_repo.create(request)

            # Запись в историю
            history = RequestHistory.create_creation_record(
                request_id=request_id,
                user_id=created_by,
                request_data=request_data
            )
            self.history_repo.create(history)

            # Отправка уведомлений
            self.notification_service.notify_new_request(request_id, request)

            self.logger.info(f"Создана новая заявка #{request_id} пользователем {created_by}")

            return request_id

        except Exception as e:
            self.logger.error(f"Ошибка при создании заявки: {e}")
            raise

    def get_request(self, request_id: int) -> Optional[Request]:
        """
        Получение заявки по ID.

        Args:
            request_id: ID заявки

        Returns:
            Объект заявки или None
        """
        return self.request_repo.find_by_id(request_id)

    def update_request(self, request_id: int, update_data: Dict[str, Any],
                       updated_by: int) -> bool:
        """
        Обновление заявки.

        Args:
            request_id: ID заявки
            update_data: Данные для обновления
            updated_by: ID пользователя, выполняющего обновление

        Returns:
            True если обновление успешно

        Raises:
            ValueError: При некорректных данных
        """
        try:
            request = self.request_repo.find_by_id(request_id)
            if not request:
                raise ValueError(f"Заявка #{request_id} не найдена")

            # Сохраняем старые значения для истории
            old_values = {}

            # Обновление полей
            for field, value in update_data.items():
                if hasattr(request, field) and value is not None:
                    old_values[field] = getattr(request, field)
                    setattr(request, field, value)

            # Обновление времени
            request.updated_at = datetime.now()

            # Если статус изменился, обрабатываем особо
            if 'status_id' in update_data:
                self._handle_status_change(request, update_data['status_id'], updated_by)

            # Сохранение
            success = self.request_repo.update(request)

            # Запись в историю для каждого измененного поля
            if success:
                for field, old_value in old_values.items():
                    if field != 'status_id':  # Статус уже записан отдельно
                        history = RequestHistory.create_field_change(
                            request_id=request_id,
                            user_id=updated_by,
                            field_name=field,
                            old_value=old_value,
                            new_value=update_data[field]
                        )
                        self.history_repo.create(history)

            self.logger.info(f"Заявка #{request_id} обновлена пользователем {updated_by}")

            return success

        except Exception as e:
            self.logger.error(f"Ошибка при обновлении заявки #{request_id}: {e}")
            raise

    def delete_request(self, request_id: int, deleted_by: int,
                       soft_delete: bool = True) -> bool:
        """
        Удаление заявки.

        Args:
            request_id: ID заявки
            deleted_by: ID пользователя
            soft_delete: Мягкое удаление (пометить как удаленную)

        Returns:
            True если удаление успешно
        """
        try:
            if soft_delete:
                # Мягкое удаление - помечаем как удаленную
                request = self.request_repo.find_by_id(request_id)
                if request:
                    request.is_deleted = True
                    request.updated_at = datetime.now()
                    success = self.request_repo.update(request)

                    # Запись в историю
                    history = RequestHistory(
                        request_id=request_id,
                        action='delete',
                        comment='Мягкое удаление',
                        changed_by=deleted_by,
                        changed_at=datetime.now()
                    )
                    self.history_repo.create(history)
            else:
                # Жесткое удаление
                success = self.request_repo.delete(request_id)

            if success:
                self.logger.info(f"Заявка #{request_id} удалена пользователем {deleted_by}")

            return success

        except Exception as e:
            self.logger.error(f"Ошибка при удалении заявки #{request_id}: {e}")
            return False

    # ==================== ОПЕРАЦИИ СО СТАТУСАМИ ====================

    def change_status(self, request_id: int, new_status_id: int,
                      comment: Optional[str], changed_by: int) -> bool:
        """
        Изменение статуса заявки.

        Args:
            request_id: ID заявки
            new_status_id: ID нового статуса
            comment: Комментарий к изменению
            changed_by: ID пользователя

        Returns:
            True если изменение успешно
        """
        try:
            request = self.request_repo.find_by_id(request_id)
            if not request:
                raise ValueError(f"Заявка #{request_id} не найдена")

            old_status_id = request.status_id

            # Проверка возможности перехода
            old_status = self.status_repo.find_by_id(old_status_id)
            if old_status and not old_status.can_transition_to(new_status_id):
                raise ValueError(f"Невозможно перейти из статуса '{old_status.name}'")

            # Проверка прав пользователя
            user = self.user_repo.find_by_id(changed_by)
            new_status = self.status_repo.find_by_id(new_status_id)
            if new_status and not new_status.is_allowed_for_role(user.role):
                raise ValueError(f"Статус '{new_status.name}' недоступен для роли '{user.role}'")

            # Обновление статуса
            request.status_id = new_status_id
            request.updated_at = datetime.now()

            # Специальная обработка для конечных статусов
            if new_status and new_status.is_final:
                if new_status_id == 3:  # Решена
                    request.resolved_at = datetime.now()
                    request.actual_hours = request.calculate_resolution_time()
                elif new_status_id == 4:  # Закрыта
                    request.closed_at = datetime.now()

            # Сохранение
            success = self.request_repo.update(request)

            # Запись в историю
            if success:
                history = RequestHistory.create_status_change(
                    request_id=request_id,
                    user_id=changed_by,
                    old_status=old_status_id,
                    new_status=new_status_id,
                    comment=comment
                )
                self.history_repo.create(history)

                # Уведомления
                self.notification_service.notify_status_change(
                    request_id, old_status_id, new_status_id, comment
                )

                self.logger.info(f"Статус заявки #{request_id} изменен с {old_status_id} на {new_status_id}")

            return success

        except Exception as e:
            self.logger.error(f"Ошибка при изменении статуса заявки #{request_id}: {e}")
            raise

    def _handle_status_change(self, request: Request, new_status_id: int,
                              changed_by: int):
        """
        Обработка изменения статуса (внутренний метод).
        """
        # Аналогично change_status, но без двойной записи в историю
        old_status_id = request.status_id

        # Специальная обработка для конечных статусов
        if new_status_id in [3, 4, 5]:  # Решена, Закрыта, Отклонена
            if new_status_id == 3:  # Решена
                request.resolved_at = datetime.now()
                request.actual_hours = request.calculate_resolution_time()
            elif new_status_id == 4:  # Закрыта
                request.closed_at = datetime.now()

    def assign_request(self, request_id: int, assignee_id: int,
                       comment: Optional[str] = None, assigned_by: Optional[int] = None) -> bool:
        """
        Назначение заявки на исполнителя.

        Args:
            request_id: ID заявки
            assignee_id: ID исполнителя
            comment: Комментарий
            assigned_by: ID назначившего (если None, то сам исполнитель)

        Returns:
            True если назначение успешно
        """
        try:
            request = self.request_repo.find_by_id(request_id)
            if not request:
                raise ValueError(f"Заявка #{request_id} не найдена")

            executor = self.user_repo.find_by_id(assignee_id)
            if not executor:
                raise ValueError(f"Исполнитель с ID {assignee_id} не найден")

            if not executor.is_executor():
                raise ValueError(f"Пользователь {executor.full_name} не является исполнителем")

            old_assignee_id = request.assignee_id

            # Назначение
            request.assignee_id = assignee_id
            request.updated_at = datetime.now()

            # Если заявка была новой, меняем статус на "В работе"
            if request.is_new():
                request.status_id = 2  # В работе

            # Сохранение
            success = self.request_repo.update(request)

            # Запись в историю
            if success:
                history = RequestHistory.create_assign_record(
                    request_id=request_id,
                    user_id=assigned_by or assignee_id,
                    old_assignee=old_assignee_id,
                    new_assignee=assignee_id,
                    comment=comment
                )
                self.history_repo.create(history)

                # Уведомления
                self.notification_service.notify_assignment(request_id, assignee_id)

                self.logger.info(f"Заявка #{request_id} назначена на {executor.full_name}")

            return success

        except Exception as e:
            self.logger.error(f"Ошибка при назначении заявки #{request_id}: {e}")
            raise

    def add_comment(self, request_id: int, user_id: int, comment: str) -> bool:
        """
        Добавление комментария к заявке.

        Args:
            request_id: ID заявки
            user_id: ID автора комментария
            comment: Текст комментария

        Returns:
            True если комментарий добавлен
        """
        try:
            request = self.request_repo.find_by_id(request_id)
            if not request:
                raise ValueError(f"Заявка #{request_id} не найдена")

            # Запись в историю
            history = RequestHistory.create_comment_record(
                request_id=request_id,
                user_id=user_id,
                comment=comment
            )
            history_id = self.history_repo.create(history)

            if history_id:
                # Уведомления
                self.notification_service.notify_new_comment(request_id, user_id, comment)

                self.logger.info(f"Добавлен комментарий к заявке #{request_id}")
                return True

            return False

        except Exception as e:
            self.logger.error(f"Ошибка при добавлении комментария к заявке #{request_id}: {e}")
            return False

    # ==================== МЕТОДЫ ПОИСКА ====================

    def get_user_requests(self, user_id: int, role: Optional[str] = None) -> List[Request]:
        """
        Получение заявок для пользователя в зависимости от роли.

        Args:
            user_id: ID пользователя
            role: Роль пользователя (если None, определяется автоматически)

        Returns:
            Список заявок
        """
        if not role:
            user = self.user_repo.find_by_id(user_id)
            role = user.role if user else 'requester'

        if role == 'requester':
            return self.request_repo.find_by_requester(user_id)
        elif role == 'executor':
            return self.request_repo.find_by_assignee(user_id)
        else:  # admin
            return self.request_repo.find_all(limit=100)

    def get_new_requests(self) -> List[Request]:
        """Получение новых заявок (статус 1)"""
        return self.request_repo.find_by_status(1)

    def get_requests_by_assignee(self, assignee_id: int) -> List[Request]:
        """Получение заявок, назначенных на исполнителя"""
        return self.request_repo.find_by_assignee(assignee_id)

    def get_requests_by_requester(self, requester_id: int) -> List[Request]:
        """Получение заявок, созданных пользователем"""
        return self.request_repo.find_by_requester(requester_id)

    def get_requests_by_status(self, status_id: int) -> List[Request]:
        """Получение заявок по статусу"""
        return self.request_repo.find_by_status(status_id)

    def get_requests_by_category(self, category_id: int) -> List[Request]:
        """Получение заявок по категории"""
        return self.request_repo.find_by_category(category_id)

    def get_overdue_requests(self) -> List[Request]:
        """Получение просроченных заявок"""
        all_requests = self.request_repo.find_active()
        overdue = []

        for request in all_requests:
            if not request.is_finished():
                sla_info = self.sla_service.calculate_sla(request)
                if not sla_info['is_compliant']:
                    overdue.append(request)

        return overdue

    def search_requests(self, criteria: Dict[str, Any]) -> List[Request]:
        """
        Поиск заявок по критериям.

        Args:
            criteria: Словарь с критериями поиска

        Returns:
            Список заявок
        """
        # Базовый поиск
        requests = self.request_repo.find_by_criteria(criteria)

        # Дополнительная фильтрация
        if 'date_from' in criteria:
            date_from = criteria['date_from']
            requests = [r for r in requests if r.created_at and r.created_at >= date_from]

        if 'date_to' in criteria:
            date_to = criteria['date_to']
            requests = [r for r in requests if r.created_at and r.created_at <= date_to]

        if 'overdue_only' in criteria and criteria['overdue_only']:
            requests = [r for r in requests if not self.sla_service.check_sla_compliance(r)]

        return requests

    def get_all_requests(self, limit: int = 100) -> List[Request]:
        """Получение всех заявок"""
        return self.request_repo.find_all(limit=limit)

    # ==================== МЕТОДЫ ДЛЯ ИСТОРИИ ====================

    def get_request_history(self, request_id: int) -> List[Dict[str, Any]]:
        """
        Получение истории изменений заявки.

        Args:
            request_id: ID заявки

        Returns:
            Список записей истории
        """
        history = self.history_repo.find_by_request(request_id)

        # Обогащаем данными о пользователях
        result = []
        for entry in history:
            entry_dict = entry.to_dict()
            user = self.user_repo.find_by_id(entry.changed_by)
            entry_dict['user_name'] = user.full_name if user else 'Неизвестно'
            result.append(entry_dict)

        return result

    def get_request_timeline(self, request_id: int) -> List[Dict[str, Any]]:
        """
        Получение хронологии событий по заявке.

        Args:
            request_id: ID заявки

        Returns:
            Список событий в хронологическом порядке
        """
        history = self.history_repo.find_by_request(request_id)

        timeline = []
        for entry in history:
            user = self.user_repo.find_by_id(entry.changed_by)
            timeline.append({
                'timestamp': entry.changed_at,
                'action': entry.get_action_display(),
                'action_type': entry.action,
                'user': user.full_name if user else 'Неизвестно',
                'details': entry.comment or f"{entry.old_value} → {entry.new_value}",
                'icon': entry.get_action_icon()
            })

        # Сортировка по времени
        timeline.sort(key=lambda x: x['timestamp'])

        return timeline

    # ==================== МЕТОДЫ ДЛЯ СТАТИСТИКИ ====================

    def get_requests_count_by_status(self) -> Dict[str, int]:
        """Получение количества заявок по статусам"""
        all_requests = self.request_repo.find_all()
        result = {}

        for request in all_requests:
            status = self.status_repo.find_by_id(request.status_id)
            if status:
                status_name = status.name
                result[status_name] = result.get(status_name, 0) + 1

        return result

    def get_requests_count_by_priority(self) -> Dict[str, int]:
        """Получение количества заявок по приоритетам"""
        all_requests = self.request_repo.find_all()
        result = {}

        for request in all_requests:
            priority = request.get_priority_display()
            result[priority] = result.get(priority, 0) + 1

        return result

    def get_average_resolution_time(self, days: int = 30) -> Optional[float]:
        """
        Получение среднего времени решения заявок.

        Args:
            days: Период в днях

        Returns:
            Среднее время в часах или None
        """
        since_date = datetime.now() - timedelta(days=days)
        requests = self.request_repo.find_resolved_since(since_date)

        if not requests:
            return None

        total_time = 0
        count = 0

        for request in requests:
            if request.resolved_at and request.created_at:
                delta = request.resolved_at - request.created_at
                total_time += delta.total_seconds() / 3600
                count += 1

        return total_time / count if count > 0 else None

    def get_user_statistics(self, user_id: int) -> Dict[str, Any]:
        """
        Получение статистики по пользователю.

        Args:
            user_id: ID пользователя

        Returns:
            Словарь со статистикой
        """
        user = self.user_repo.find_by_id(user_id)
        if not user:
            return {}

        stats = {}

        if user.is_requester():
            # Статистика заявителя
            created = self.request_repo.find_by_requester(user_id)
            stats['created_total'] = len(created)
            stats['created_by_status'] = self._count_by_status(created)

        elif user.is_executor():
            # Статистика исполнителя
            assigned = self.request_repo.find_by_assignee(user_id)
            resolved = [r for r in assigned if r.is_resolved()]

            stats['assigned_total'] = len(assigned)
            stats['resolved_total'] = len(resolved)
            stats['assigned_by_status'] = self._count_by_status(assigned)

            if resolved:
                total_time = sum(r.actual_hours or 0 for r in resolved)
                stats['avg_resolution_time'] = total_time / len(resolved)

        return stats

    def _count_by_status(self, requests: List[Request]) -> Dict[str, int]:
        """Вспомогательный метод подсчета по статусам"""
        result = {}
        for request in requests:
            status = self.status_repo.find_by_id(request.status_id)
            if status:
                status_name = status.name
                result[status_name] = result.get(status_name, 0) + 1
        return result

    # ==================== МЕТОДЫ ДЛЯ SLA ====================

    def check_sla_compliance(self, request_id: int) -> bool:
        """
        Проверка соблюдения SLA для заявки.

        Args:
            request_id: ID заявки

        Returns:
            True если SLA соблюдается
        """
        request = self.request_repo.find_by_id(request_id)
        if not request:
            return False

        return self.sla_service.check_sla_compliance(request)

    def get_sla_info(self, request_id: int) -> Dict[str, Any]:
        """
        Получение информации о SLA для заявки.

        Args:
            request_id: ID заявки

        Returns:
            Словарь с информацией о SLA
        """
        request = self.request_repo.find_by_id(request_id)
        if not request:
            return {}

        return self.sla_service.calculate_sla(request)

    def get_requests_breaching_sla(self) -> List[Request]:
        """Получение заявок, нарушающих SLA"""
        return self.get_overdue_requests()