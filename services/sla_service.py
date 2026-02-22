"""
Сервис для расчета SLA (Service Level Agreement).
Реализует логику подсчета времени и определения соблюдения сроков.
"""

from datetime import datetime, timedelta
from typing import Dict, List
import logging

from models.request import Request
from config import Config


class SLAService:
    """
    Сервис для работы с SLA.

    Предоставляет методы для расчета времени, проверки соблюдения сроков
    и визуализации статуса SLA.
    """

    def __init__(self):
        """Инициализация сервиса SLA"""
        self.logger = logging.getLogger(__name__)

    # ==================== ОСНОВНЫЕ МЕТОДЫ РАСЧЕТА ====================

    def calculate_sla(self, request: Request) -> Dict[str, any]:
        """
        Расчет SLA для заявки.

        Args:
            request: Объект заявки

        Returns:
            Словарь с информацией о соблюдении SLA
        """
        try:
            # Получаем лимит SLA (из категории или приоритета)
            sla_limit = self._get_sla_limit(request)

            # Текущее время или время решения
            current_time = request.resolved_at or datetime.now()

            # Вычисляем прошедшее время с учетом рабочих часов
            elapsed_hours = self._calculate_elapsed_hours(
                request.created_at,
                current_time,
                request.is_critical()  # Критические считаем 24/7
            )

            # Проверяем соблюдение SLA
            is_compliant = elapsed_hours <= sla_limit

            # Вычисляем процент выполнения
            percentage = min(100, (elapsed_hours / sla_limit) * 100) if sla_limit > 0 else 0

            # Определяем цветовой код
            color = self._get_status_color(percentage, is_compliant, request.priority)

            # Оставшееся время
            remaining = max(0, sla_limit - elapsed_hours)

            # Время превышения (если нарушено)
            overrun = max(0, elapsed_hours - sla_limit) if not is_compliant else 0

            return {
                'is_compliant': is_compliant,
                'elapsed_hours': round(elapsed_hours, 2),
                'sla_limit': sla_limit,
                'percentage': round(percentage, 2),
                'color': color,
                'remaining_hours': round(remaining, 2),
                'overrun_hours': round(overrun, 2),
                'status_text': 'В SLA' if is_compliant else 'Нарушено SLA',
                'due_date': self.calculate_due_date(
                    request.created_at,
                    sla_limit,
                    request.is_critical()
                )
            }

        except Exception as e:
            self.logger.error(f"Ошибка расчета SLA для заявки #{request.id}: {e}")
            return {
                'is_compliant': True,
                'elapsed_hours': 0,
                'sla_limit': 24,
                'percentage': 0,
                'color': '#95a5a6',
                'remaining_hours': 24,
                'overrun_hours': 0,
                'status_text': 'Ошибка расчета',
                'due_date': None
            }

    def check_sla_compliance(self, request: Request) -> bool:
        """
        Проверка соблюдения SLA.

        Args:
            request: Объект заявки

        Returns:
            True если SLA соблюдается
        """
        if request.is_finished():
            # Для завершенных заявок проверяем, уложились ли в срок
            if request.resolved_at and request.created_at:
                elapsed = self._calculate_elapsed_hours(
                    request.created_at,
                    request.resolved_at,
                    request.is_critical()
                )
                sla_limit = self._get_sla_limit(request)
                return elapsed <= sla_limit
            return True
        else:
            # Для активных заявок проверяем текущее состояние
            return self.calculate_sla(request)['is_compliant']

    def calculate_due_date(self, start_date: datetime, sla_hours: int,
                           critical: bool = False) -> datetime:
        """
        Расчет даты истечения SLA.

        Args:
            start_date: Дата начала
            sla_hours: Количество часов SLA
            critical: Критический ли приоритет

        Returns:
            Дата истечения срока
        """
        if critical:
            # Для критических - просто добавляем часы
            return start_date + timedelta(hours=sla_hours)

        # Для остальных - учитываем рабочие часы
        current = start_date
        remaining_hours = sla_hours

        while remaining_hours > 0:
            current += timedelta(hours=1)

            # Проверяем, рабочий ли час
            if self._is_working_hour(current):
                remaining_hours -= 1

        return current

    # ==================== МЕТОДЫ РАСЧЕТА ВРЕМЕНИ ====================

    def _calculate_elapsed_hours(self, start: datetime, end: datetime,
                                 critical: bool = False) -> float:
        """
        Расчет прошедших часов с учетом рабочего времени.

        Args:
            start: Начальное время
            end: Конечное время
            critical: Флаг критичности (24/7)

        Returns:
            Количество прошедших часов
        """
        if start >= end:
            return 0

        if critical:
            # Для критических заявок - 24/7
            delta = end - start
            return delta.total_seconds() / 3600

        # Для остальных - только рабочие часы
        return self._calculate_work_hours(start, end)

    def _calculate_work_hours(self, start: datetime, end: datetime) -> float:
        """
        Расчет рабочих часов между двумя датами.

        Args:
            start: Начальное время
            end: Конечное время

        Returns:
            Количество рабочих часов
        """
        if start >= end:
            return 0

        total_hours = 0.0
        current = start

        while current < end:
            if self._is_working_hour(current):
                # Считаем этот час
                total_hours += 1
                current += timedelta(hours=1)
            else:
                # Переходим к следующему часу
                current += timedelta(hours=1)

        return total_hours

    def _is_working_hour(self, dt: datetime) -> bool:
        """
        Проверка, является ли час рабочим.

        Args:
            dt: Дата и время

        Returns:
            True если час рабочий
        """
        # Проверка дня недели (0 - понедельник в Python)
        if dt.weekday() >= 5:  # Суббота (5) или Воскресенье (6)
            return False

        # Проверка рабочего времени
        if dt.hour < Config.WORK_HOURS_START or dt.hour >= Config.WORK_HOURS_END:
            return False

        return True

    def _get_sla_limit(self, request: Request) -> float:
        """
        Получение лимита SLA в часах.

        Args:
            request: Объект заявки

        Returns:
            Количество часов SLA
        """
        # По умолчанию из приоритета
        return Config.SLA_LIMITS.get(request.priority, 24)

    # ==================== МЕТОДЫ ДЛЯ ВИЗУАЛИЗАЦИИ ====================

    def _get_status_color(self, percentage: float, is_compliant: bool,
                          priority: str) -> str:
        """
        Определение цвета для отображения статуса SLA.

        Args:
            percentage: Процент выполнения
            is_compliant: Соблюдается ли SLA
            priority: Приоритет

        Returns:
            HEX код цвета
        """
        if not is_compliant:
            return '#e74c3c'  # Красный - нарушено

        if priority == 'critical':
            # Для критических более строгая шкала
            if percentage < 30:
                return '#2ecc71'  # Зеленый
            elif percentage < 60:
                return '#f39c12'  # Оранжевый
            else:
                return '#e67e22'  # Темно-оранжевый
        else:
            # Для обычных
            if percentage < 50:
                return '#2ecc71'  # Зеленый
            elif percentage < 80:
                return '#f39c12'  # Оранжевый
            else:
                return '#e67e22'  # Темно-оранжевый

    def get_sla_progress_bar(self, request: Request, width: int = 20) -> str:
        """
        Получение прогресс-бара для отображения SLA.

        Args:
            request: Объект заявки
            width: Ширина прогресс-бара в символах

        Returns:
            Строка с прогресс-баром
        """
        sla_info = self.calculate_sla(request)
        percentage = sla_info['percentage']

        filled = int(width * percentage / 100)
        empty = width - filled

        # Выбор символов в зависимости от статуса
        if sla_info['is_compliant']:
            bar = '█' * filled + '░' * empty
        else:
            bar = '█' * filled + '▒' * empty

        return f"[{bar}] {percentage:.1f}%"

    def get_sla_summary(self, requests: List[Request]) -> Dict[str, any]:
        """
        Получение сводки по SLA для списка заявок.

        Args:
            requests: Список заявок

        Returns:
            Словарь со сводной информацией
        """
        total = len(requests)
        if total == 0:
            return {
                'total': 0,
                'compliant': 0,
                'breached': 0,
                'compliance_rate': 0
            }

        compliant = 0
        breached = 0

        for request in requests:
            if request.is_finished():
                if self.check_sla_compliance(request):
                    compliant += 1
                else:
                    breached += 1

        compliance_rate = (compliant / (compliant + breached)) * 100 if (compliant + breached) > 0 else 0

        return {
            'total': total,
            'compliant': compliant,
            'breached': breached,
            'compliance_rate': round(compliance_rate, 2)
        }
