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

    # ==================== ОСНОВНЫЕ МЕТОДЫ СТАТИСТИКИ ====================

    def get_statistics(self, days: int = 30) -> Dict[str, Any]:
        """
        Получение общей статистики за период.

        Args:
            days: Период в днях

        Returns:
            Словарь со статистикой
        """
        try:
            since_date = datetime.now() - timedelta(days=days)
            requests = self.request_repo.find_since(since_date)

            # Базовая статистика
            total = len(requests)
            resolved = len([r for r in requests if r.resolved_at])
            open_requests = total - resolved

            # Статистика по статусам
            by_status = self._group_by_status(requests)

            # Статистика по приоритетам
            by_priority = self._group_by_priority(requests)

            # Статистика по категориям
            by_category = self._group_by_category(requests)

            # Статистика SLA
            sla_stats = self.sla_service.get_sla_summary(requests)

            # Среднее время решения
            avg_resolution = self._calculate_avg_resolution_time(requests)

            # Ежедневная статистика
            daily_stats = self._get_daily_stats(requests, days)

            # Тренды
            trends = self._get_trends(requests)

            return {
                'period_days': days,
                'total_requests': total,
                'resolved_requests': resolved,
                'open_requests': open_requests,
                'resolution_rate': round((resolved / total * 100) if total > 0 else 0, 2),
                'by_status': by_status,
                'by_priority': by_priority,
                'by_category': by_category,
                'sla_stats': sla_stats,
                'avg_resolution_hours': round(avg_resolution, 2),
                'daily_stats': daily_stats,
                'trends': trends
            }

        except Exception as e:
            self.logger.error(f"Ошибка при получении статистики: {e}")
            return {}

    def get_detailed_statistics(self, days: int = 30) -> Dict[str, Any]:
        """
        Получение детальной статистики за период.

        Args:
            days: Период в днях

        Returns:
            Детальная статистика
        """
        try:
            since_date = datetime.now() - timedelta(days=days)
            requests = self.request_repo.find_since(since_date)

            return {
                'period_days': days,
                'total_requests': len(requests),
                'by_status_detail': self._get_status_detail(requests),
                'by_priority_detail': self._get_priority_detail(requests),
                'by_category_detail': self._get_category_detail(requests),
                'by_user_detail': self._get_user_detail(requests),
                'resolution_time_distribution': self._get_resolution_distribution(requests),
                'sla_compliance_detail': self._get_sla_detail(requests),
                'hourly_distribution': self._get_hourly_distribution(requests),
                'weekly_distribution': self._get_weekly_distribution(requests)
            }

        except Exception as e:
            self.logger.error(f"Ошибка при получении детальной статистики: {e}")
            return {}

    def get_comparative_statistics(self, days1: int = 30, days2: int = 7) -> Dict[str, Any]:
        """
        Сравнительная статистика за два периода.

        Args:
            days1: Первый период (например, 30 дней)
            days2: Второй период (например, 7 дней)

        Returns:
            Сравнительная статистика
        """
        try:
            stats1 = self.get_statistics(days1)
            stats2 = self.get_statistics(days2)

            # Вычисляем изменения
            changes = {}

            if stats1 and stats2:
                changes = {
                    'total_requests_change': self._calculate_change(
                        stats1.get('total_requests', 0),
                        stats2.get('total_requests', 0)
                    ),
                    'resolution_rate_change': self._calculate_change(
                        stats1.get('resolution_rate', 0),
                        stats2.get('resolution_rate', 0)
                    ),
                    'avg_resolution_change': self._calculate_change(
                        stats1.get('avg_resolution_hours', 0),
                        stats2.get('avg_resolution_hours', 0)
                    )
                }

            return {
                'period1': {'days': days1, 'stats': stats1},
                'period2': {'days': days2, 'stats': stats2},
                'changes': changes
            }

        except Exception as e:
            self.logger.error(f"Ошибка при получении сравнительной статистики: {e}")
            return {}

    # ==================== МЕТОДЫ ДЛЯ ПОЛЬЗОВАТЕЛЕЙ ====================

    def get_user_statistics(self, user_id: int, days: int = 30) -> Dict[str, Any]:
        """
        Получение статистики по конкретному пользователю.

        Args:
            user_id: ID пользователя
            days: Период в днях

        Returns:
            Статистика пользователя
        """
        try:
            user = self.user_repo.find_by_id(user_id)
            if not user:
                return {}

            since_date = datetime.now() - timedelta(days=days)

            if user.is_requester():
                # Статистика заявителя
                requests = self.request_repo.find_by_requester_since(user_id, since_date)

                return {
                    'user_id': user_id,
                    'user_name': user.full_name,
                    'role': 'requester',
                    'period_days': days,
                    'requests_created': len(requests),
                    'by_status': self._group_by_status(requests),
                    'by_priority': self._group_by_priority(requests),
                    'resolved_count': len([r for r in requests if r.resolved_at]),
                    'avg_resolution_hours': self._calculate_avg_resolution_time(requests),
                    'sla_stats': self.sla_service.get_sla_summary(requests)
                }

            elif user.is_executor():
                # Статистика исполнителя
                assigned = self.request_repo.find_by_assignee_since(user_id, since_date)
                resolved = [r for r in assigned if r.resolved_at]

                resolution_times = []
                for r in resolved:
                    if r.resolved_at and r.created_at:
                        hours = (r.resolved_at - r.created_at).total_seconds() / 3600
                        resolution_times.append(hours)

                return {
                    'user_id': user_id,
                    'user_name': user.full_name,
                    'role': 'executor',
                    'period_days': days,
                    'assigned_count': len(assigned),
                    'resolved_count': len(resolved),
                    'resolution_rate': round((len(resolved) / len(assigned) * 100) if assigned else 0, 2),
                    'by_status': self._group_by_status(assigned),
                    'by_priority': self._group_by_priority(assigned),
                    'avg_resolution_hours': round(sum(resolution_times) / len(resolution_times) if resolution_times else 0, 2),
                    'sla_stats': self.sla_service.get_sla_summary(assigned)
                }

            return {}

        except Exception as e:
            self.logger.error(f"Ошибка при получении статистики пользователя {user_id}: {e}")
            return {}

    def get_top_performers(self, limit: int = 5, days: int = 30) -> Dict[str, List]:
        """
        Получение топ исполнителей.

        Args:
            limit: Количество в топе
            days: Период

        Returns:
            Словарь с топами
        """
        try:
            executors = self.user_repo.find_executors()
            since_date = datetime.now() - timedelta(days=days)

            performer_stats = []

            for executor in executors:
                assigned = self.request_repo.find_by_assignee_since(executor.id, since_date)
                resolved = [r for r in assigned if r.resolved_at]

                if assigned:
                    resolution_rate = (len(resolved) / len(assigned)) * 100

                    # Среднее время решения
                    resolution_times = []
                    for r in resolved:
                        if r.resolved_at and r.created_at:
                            hours = (r.resolved_at - r.created_at).total_seconds() / 3600
                            resolution_times.append(hours)

                    avg_time = sum(resolution_times) / len(resolution_times) if resolution_times else 0

                    # SLA compliance
                    sla_compliant = 0
                    for r in resolved:
                        if self.sla_service.check_sla_compliance(r):
                            sla_compliant += 1

                    sla_rate = (sla_compliant / len(resolved) * 100) if resolved else 0

                    performer_stats.append({
                        'id': executor.id,
                        'name': executor.full_name,
                        'assigned': len(assigned),
                        'resolved': len(resolved),
                        'resolution_rate': round(resolution_rate, 2),
                        'avg_resolution_hours': round(avg_time, 2),
                        'sla_compliance_rate': round(sla_rate, 2)
                    })

            # Сортируем по количеству решенных заявок
            top_by_resolved = sorted(performer_stats,
                                    key=lambda x: x['resolved'],
                                    reverse=True)[:limit]

            # Сортируем по скорости решения
            top_by_speed = sorted([p for p in performer_stats if p['resolved'] > 0],
                                 key=lambda x: x['avg_resolution_hours'])[:limit]

            # Сортируем по SLA compliance
            top_by_sla = sorted([p for p in performer_stats if p['resolved'] > 0],
                               key=lambda x: x['sla_compliance_rate'],
                               reverse=True)[:limit]

            return {
                'by_resolved': top_by_resolved,
                'by_speed': top_by_speed,
                'by_sla': top_by_sla
            }

        except Exception as e:
            self.logger.error(f"Ошибка при получении топ исполнителей: {e}")
            return {}

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

    def _get_trends(self, requests: List[Request]) -> Dict[str, Any]:
        """Анализ тенденций"""
        if len(requests) < 10:
            return {'message': 'Недостаточно данных для анализа тенденций'}

        # Сортируем по дате создания
        sorted_reqs = sorted([r for r in requests if r.created_at],
                            key=lambda x: x.created_at)

        if len(sorted_reqs) < 2:
            return {'message': 'Недостаточно данных для анализа'}

        mid = len(sorted_reqs) // 2
        first_half = sorted_reqs[:mid]
        second_half = sorted_reqs[mid:]

        # Тренд количества
        volume_trend = self._get_volume_trend(first_half, second_half)

        # Тренд времени решения
        time_trend = self._get_time_trend(first_half, second_half)

        # Тренд SLA
        sla_trend = self._get_sla_trend(first_half, second_half)

        return {
            'volume_trend': volume_trend,
            'resolution_time_trend': time_trend,
            'sla_trend': sla_trend
        }

    def _get_volume_trend(self, first: List[Request], second: List[Request]) -> str:
        """Тренд количества заявок"""
        if len(second) > len(first) * 1.2:
            return 'increasing'
        elif len(second) < len(first) * 0.8:
            return 'decreasing'
        else:
            return 'stable'

    def _get_time_trend(self, first: List[Request], second: List[Request]) -> str:
        """Тренд времени решения"""
        first_avg = self._calculate_avg_resolution_time(first)
        second_avg = self._calculate_avg_resolution_time(second)

        if first_avg == 0 or second_avg == 0:
            return 'unknown'

        if second_avg < first_avg * 0.9:
            return 'improving'
        elif second_avg > first_avg * 1.1:
            return 'worsening'
        else:
            return 'stable'

    def _get_sla_trend(self, first: List[Request], second: List[Request]) -> str:
        """Тренд соблюдения SLA"""
        first_compliance = self.sla_service.get_sla_summary(first).get('compliance_rate', 0)
        second_compliance = self.sla_service.get_sla_summary(second).get('compliance_rate', 0)

        if second_compliance > first_compliance + 5:
            return 'improving'
        elif second_compliance < first_compliance - 5:
            return 'worsening'
        else:
            return 'stable'

    def _get_status_detail(self, requests: List[Request]) -> List[Dict]:
        """Детальная статистика по статусам"""
        result = []
        for request in requests:
            status = self.status_repo.find_by_id(request.status_id)
            if status:
                result.append({
                    'status_id': status.id,
                    'status_name': status.name,
                    'status_code': status.code,
                    'count': 1
                })

        # Группируем
        from collections import Counter
        counter = Counter()
        for item in result:
            counter[(item['status_id'], item['status_name'], item['status_code'])] += 1

        return [
            {
                'status_id': sid,
                'status_name': name,
                'status_code': code,
                'count': count
            }
            for (sid, name, code), count in counter.items()
        ]

    def _get_priority_detail(self, requests: List[Request]) -> List[Dict]:
        """Детальная статистика по приоритетам"""
        from collections import Counter
        counter = Counter(r.priority for r in requests)

        return [
            {
                'priority': priority,
                'priority_display': Request.PRIORITY_DISPLAY.get(priority, priority),
                'count': count
            }
            for priority, count in counter.items()
        ]

    def _get_category_detail(self, requests: List[Request]) -> List[Dict]:
        """Детальная статистика по категориям"""
        result = []
        for request in requests:
            category = self.category_repo.find_by_id(request.category_id)
            if category:
                result.append({
                    'category_id': category.id,
                    'category_name': category.name,
                    'count': 1
                })

        from collections import Counter
        counter = Counter()
        for item in result:
            counter[(item['category_id'], item['category_name'])] += 1

        return [
            {
                'category_id': cid,
                'category_name': name,
                'count': count
            }
            for (cid, name), count in counter.items()
        ]

    def _get_user_detail(self, requests: List[Request]) -> Dict[str, Any]:
        """Детальная статистика по пользователям"""
        creators = defaultdict(int)
        assignees = defaultdict(int)

        for request in requests:
            if request.requester_id:
                creators[request.requester_id] += 1
            if request.assignee_id:
                assignees[request.assignee_id] += 1

        # Получаем имена пользователей
        creator_details = []
        for user_id, count in sorted(creators.items(), key=lambda x: x[1], reverse=True)[:10]:
            user = self.user_repo.find_by_id(user_id)
            if user:
                creator_details.append({
                    'user_id': user_id,
                    'user_name': user.full_name,
                    'requests_created': count
                })

        assignee_details = []
        for user_id, count in sorted(assignees.items(), key=lambda x: x[1], reverse=True)[:10]:
            user = self.user_repo.find_by_id(user_id)
            if user:
                assignee_details.append({
                    'user_id': user_id,
                    'user_name': user.full_name,
                    'requests_assigned': count
                })

        return {
            'top_creators': creator_details,
            'top_assignees': assignee_details
        }

    def _get_resolution_distribution(self, requests: List[Request]) -> Dict[str, int]:
        """Распределение времени решения"""
        resolved = [r for r in requests if r.resolved_at and r.created_at]

        distribution = {
            'under_1h': 0,
            '1h_to_4h': 0,
            '4h_to_8h': 0,
            '8h_to_24h': 0,
            '1d_to_3d': 0,
            'over_3d': 0
        }

        for r in resolved:
            hours = (r.resolved_at - r.created_at).total_seconds() / 3600

            if hours < 1:
                distribution['under_1h'] += 1
            elif hours < 4:
                distribution['1h_to_4h'] += 1
            elif hours < 8:
                distribution['4h_to_8h'] += 1
            elif hours < 24:
                distribution['8h_to_24h'] += 1
            elif hours < 72:
                distribution['1d_to_3d'] += 1
            else:
                distribution['over_3d'] += 1

        return distribution

    def _get_sla_detail(self, requests: List[Request]) -> Dict[str, Any]:
        """Детальная статистика по SLA"""
        total = 0
        compliant = 0

        for request in requests:
            if request.resolved_at:
                total += 1
                if self.sla_service.check_sla_compliance(request):
                    compliant += 1

        return {
            'total_resolved': total,
            'compliant': compliant,
            'breached': total - compliant,
            'compliance_rate': round((compliant / total * 100) if total else 0, 2)
        }

    def _get_hourly_distribution(self, requests: List[Request]) -> Dict[int, int]:
        """Распределение по часам создания"""
        distribution = defaultdict(int)

        for request in requests:
            if request.created_at:
                hour = request.created_at.hour
                distribution[hour] += 1

        return dict(sorted(distribution.items()))

    def _get_weekly_distribution(self, requests: List[Request]) -> Dict[str, int]:
        """Распределение по дням недели"""
        days = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
        distribution = {day: 0 for day in days}

        for request in requests:
            if request.created_at:
                day_index = request.created_at.weekday()
                distribution[days[day_index]] += 1

        return distribution

    def _calculate_change(self, old_value: float, new_value: float) -> float:
        """Расчет процентного изменения"""
        if old_value == 0:
            return 0
        return round(((new_value - old_value) / old_value) * 100, 2)