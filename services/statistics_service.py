"""
Сервис статистики и отчетов.
Собирает и агрегирует данные для формирования отчетов.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import logging

from models.request import Request
from models.user import User
from repositories.request_repository import RequestRepository
from repositories.user_repository import UserRepository
from repositories.category_repository import CategoryRepository
from repositories.status_repository import StatusRepository
from services.sla_service import SLAService


class StatisticsService:
    """
    Сервис для сбора и анализа статистики.
    """

    def __init__(self):
        """Инициализация сервиса статистики"""
        self.request_repo = RequestRepository()
        self.user_repo = UserRepository()
        self.category_repo = CategoryRepository()
        self.status_repo = StatusRepository()
        self.sla_service = SLAService()
        self.logger = logging.getLogger(__name__)

    # ==================== ОСНОВНЫЕ ОТЧЕТЫ ====================

    def get_dashboard_stats(self, days: int = 30) -> Dict[str, Any]:
        """
        Получение статистики для дашборда.

        Args:
            days: Период в днях

        Returns:
            Словарь со статистикой
        """
        since_date = datetime.now() - timedelta(days=days)
        requests = self.request_repo.find_since(since_date)

        stats = {
            'period': f"последние {days} дней",
            'total_requests': len(requests),
            'by_status': self._group_by_status(requests),
            'by_priority': self._group_by_priority(requests),
            'by_category': self._group_by_category(requests),
            'daily_stats': self._get_daily_stats(requests, days),
            'sla_stats': self.sla_service.get_sla_summary(requests),
            'performance': self._get_performance_stats(requests),
            'trends': self._get_trends(requests)
        }

        return stats

    def get_performance_report(self, period_days: int = 30) -> Dict[str, Any]:
        """
        Отчет по эффективности работы.

        Args:
            period_days: Период в днях

        Returns:
            Словарь с показателями эффективности
        """
        since_date = datetime.now() - timedelta(days=period_days)
        requests = self.request_repo.find_resolved_since(since_date)

        report = {
            'period_days': period_days,
            'resolved_count': len(requests),
            'avg_resolution_time': self._calculate_avg_resolution_time(requests),
            'resolution_by_priority': self._resolution_time_by_priority(requests),
            'executor_performance': self._get_executor_performance(period_days),
            'sla_compliance': self.sla_service.get_sla_summary(requests),
            'customer_satisfaction': self._get_satisfaction_stats(requests)
        }

        return report

    def get_user_activity_report(self, user_id: Optional[int] = None,
                                 days: int = 30) -> Dict[str, Any]:
        """
        Отчет по активности пользователей.

        Args:
            user_id: ID пользователя (если None - по всем)
            days: Период в днях

        Returns:
            Словарь с активностью пользователей
        """
        since_date = datetime.now() - timedelta(days=days)

        if user_id:
            # Статистика конкретного пользователя
            user = self.user_repo.find_by_id(user_id)
            if not user:
                return {}

            if user.is_requester():
                requests = self.request_repo.find_by_requester_since(user_id, since_date)
                stats = {
                    'user': user.full_name,
                    'role': user.get_role_display(),
                    'requests_created': len(requests),
                    'by_status': self._group_by_status(requests),
                    'avg_creation_rate': self._calculate_creation_rate(requests, days)
                }
            elif user.is_executor():
                assigned = self.request_repo.find_by_assignee_since(user_id, since_date)
                resolved = self.request_repo.find_resolved_by_assignee_since(user_id, since_date)

                stats = {
                    'user': user.full_name,
                    'role': user.get_role_display(),
                    'assigned': len(assigned),
                    'resolved': len(resolved),
                    'resolution_rate': (len(resolved) / len(assigned) * 100) if assigned else 0,
                    'avg_resolution_time': self._calculate_avg_resolution_time(resolved),
                    'by_status': self._group_by_status(assigned)
                }
            else:
                stats = {'user': user.full_name, 'role': 'Администратор'}

            return stats
        else:
            # Статистика по всем пользователям
            users = self.user_repo.find_all()

            return {
                'total_users': len(users),
                'by_role': self._count_users_by_role(users),
                'active_users': self._get_active_users_count(days),
                'top_creators': self._get_top_creators(days, limit=5),
                'top_executors': self._get_top_executors(days, limit=5)
            }

    # ==================== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ====================

    def _group_by_status(self, requests: List[Request]) -> Dict[str, int]:
        """Группировка заявок по статусам"""
        result = {}
        for request in requests:
            status = self.status_repo.find_by_id(request.status_id)
            if status:
                status_name = status.name
                result[status_name] = result.get(status_name, 0) + 1
        return result

    def _group_by_priority(self, requests: List[Request]) -> Dict[str, int]:
        """Группировка заявок по приоритетам"""
        result = {}
        for request in requests:
            priority = request.get_priority_display()
            result[priority] = result.get(priority, 0) + 1
        return result

    def _group_by_category(self, requests: List[Request]) -> Dict[str, int]:
        """Группировка заявок по категориям"""
        result = {}
        for request in requests:
            category = self.category_repo.find_by_id(request.category_id)
            if category:
                category_name = category.name
                result[category_name] = result.get(category_name, 0) + 1
        return result

    def _get_daily_stats(self, requests: List[Request], days: int) -> List[Dict]:
        """Получение ежедневной статистики"""
        daily = defaultdict(lambda: {'created': 0, 'resolved': 0})

        for request in requests:
            if request.created_at:
                day = request.created_at.date().isoformat()
                daily[day]['created'] += 1

            if request.resolved_at:
                day = request.resolved_at.date().isoformat()
                daily[day]['resolved'] += 1

        # Преобразование в список
        result = []
        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).date().isoformat()
            result.append({
                'date': date,
                'created': daily[date]['created'],
                'resolved': daily[date]['resolved']
            })

        return sorted(result, key=lambda x: x['date'])

    def _get_performance_stats(self, requests: List[Request]) -> Dict[str, Any]:
        """Получение статистики производительности"""
        resolved = [r for r in requests if r.resolved_at]

        if not resolved:
            return {
                'avg_resolution_hours': 0,
                'fastest_resolution': 0,
                'slowest_resolution': 0
            }

        resolution_times = []
        for r in resolved:
            if r.created_at and r.resolved_at:
                hours = (r.resolved_at - r.created_at).total_seconds() / 3600
                resolution_times.append(hours)

        return {
            'avg_resolution_hours': sum(resolution_times) / len(resolution_times) if resolution_times else 0,
            'fastest_resolution': min(resolution_times) if resolution_times else 0,
            'slowest_resolution': max(resolution_times) if resolution_times else 0
        }

    def _get_trends(self, requests: List[Request]) -> Dict[str, Any]:
        """Анализ тенденций"""
        if len(requests) < 10:
            return {'message': 'Недостаточно данных для анализа тенденций'}

        # Разделяем на две половины по времени
        sorted_reqs = sorted(requests, key=lambda x: x.created_at or datetime.min)
        mid = len(sorted_reqs) // 2

        first_half = sorted_reqs[:mid]
        second_half = sorted_reqs[mid:]

        trends = {
            'volume_trend': 'increasing' if len(second_half) > len(first_half) else 'decreasing',
            'resolution_time_trend': self._compare_resolution_times(first_half, second_half),
            'sla_trend': self._compare_sla_compliance(first_half, second_half)
        }

        return trends

    def _compare_resolution_times(self, first: List[Request],
                                  second: List[Request]) -> str:
        """Сравнение времени решения"""
        first_avg = self._calculate_avg_resolution_time(first)
        second_avg = self._calculate_avg_resolution_time(second)

        if second_avg < first_avg * 0.9:
            return 'improving'
        elif second_avg > first_avg * 1.1:
            return 'worsening'
        else:
            return 'stable'

    def _compare_sla_compliance(self, first: List[Request],
                                second: List[Request]) -> str:
        """Сравнение соблюдения SLA"""
        first_compliance = self.sla_service.get_sla_summary(first)['compliance_rate']
        second_compliance = self.sla_service.get_sla_summary(second)['compliance_rate']

        if second_compliance > first_compliance + 5:
            return 'improving'
        elif second_compliance < first_compliance - 5:
            return 'worsening'
        else:
            return 'stable'

    def _calculate_avg_resolution_time(self, requests: List[Request]) -> float:
        """Расчет среднего времени решения"""
        resolved = [r for r in requests if r.resolved_at and r.created_at]

        if not resolved:
            return 0

        total = 0
        for r in resolved:
            hours = (r.resolved_at - r.created_at).total_seconds() / 3600
            total += hours

        return total / len(resolved)

    def _resolution_time_by_priority(self, requests: List[Request]) -> Dict[str, float]:
        """Время решения по приоритетам"""
        by_priority = defaultdict(list)

        for r in requests:
            if r.resolved_at and r.created_at:
                hours = (r.resolved_at - r.created_at).total_seconds() / 3600
                by_priority[r.priority].append(hours)

        result = {}
        for priority, times in by_priority.items():
            if times:
                result[priority] = sum(times) / len(times)

        return result

    def _get_executor_performance(self, days: int) -> List[Dict]:
        """Производительность исполнителей"""
        executors = self.user_repo.find_executors()
        result = []

        for executor in executors:
            assigned = len(self.request_repo.find_by_assignee(executor.id))
            resolved = len([r for r in self.request_repo.find_by_assignee(executor.id)
                            if r.is_resolved()])

            result.append({
                'id': executor.id,
                'name': executor.full_name,
                'assigned': assigned,
                'resolved': resolved,
                'resolution_rate': (resolved / assigned * 100) if assigned else 0
            })

        return sorted(result, key=lambda x: x['resolution_rate'], reverse=True)

    def _get_satisfaction_stats(self, requests: List[Request]) -> Dict[str, Any]:
        """Статистика удовлетворенности"""
        rated = [r for r in requests if r.satisfaction_rating]

        if not rated:
            return {
                'total_ratings': 0,
                'avg_rating': 0,
                'distribution': {}
            }

        distribution = defaultdict(int)
        total = 0

        for r in rated:
            distribution[r.satisfaction_rating] += 1
            total += r.satisfaction_rating

        return {
            'total_ratings': len(rated),
            'avg_rating': total / len(rated),
            'distribution': dict(distribution)
        }

    def _count_users_by_role(self, users: List[User]) -> Dict[str, int]:
        """Подсчет пользователей по ролям"""
        result = {}
        for user in users:
            role = user.get_role_display()
            result[role] = result.get(role, 0) + 1
        return result

    def _get_active_users_count(self, days: int) -> int:
        """Количество активных пользователей"""
        since_date = datetime.now() - timedelta(days=days)
        # В реальном приложении здесь запрос к истории действий
        return 0

    def _get_top_creators(self, days: int, limit: int = 5) -> List[Dict]:
        """Топ создателей заявок"""
        since_date = datetime.now() - timedelta(days=days)
        requests = self.request_repo.find_since(since_date)

        creators = defaultdict(int)
        for r in requests:
            creators[r.requester_id] += 1

        result = []
        for user_id, count in sorted(creators.items(), key=lambda x: x[1], reverse=True)[:limit]:
            user = self.user_repo.find_by_id(user_id)
            if user:
                result.append({
                    'id': user_id,
                    'name': user.full_name,
                    'count': count
                })

        return result

    def _get_top_executors(self, days: int, limit: int = 5) -> List[Dict]:
        """Топ исполнителей"""
        since_date = datetime.now() - timedelta(days=days)
        requests = self.request_repo.find_resolved_since(since_date)

        executors = defaultdict(int)
        for r in requests:
            if r.assignee_id:
                executors[r.assignee_id] += 1

        result = []
        for user_id, count in sorted(executors.items(), key=lambda x: x[1], reverse=True)[:limit]:
            user = self.user_repo.find_by_id(user_id)
            if user:
                result.append({
                    'id': user_id,
                    'name': user.full_name,
                    'resolved': count
                })

        return result

    def _calculate_creation_rate(self, requests: List[Request], days: int) -> float:
        """Расчет скорости создания заявок (в день)"""
        return len(requests) / days if days > 0 else 0