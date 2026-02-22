"""Конфигурационные параметры приложения"""

import os


class Config:
    # База данных
    DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'database', 'requests.db')

    # Настройки SLA (в часах)
    SLA_LIMITS = {
        'critical': 2,  # Критический
        'high': 8,  # Высокий
        'medium': 24,  # Средний
        'low': 72  # Низкий
    }

    # Приоритеты заявок
    PRIORITIES = ['critical', 'high', 'medium', 'low']

    # Рабочее время (для расчета SLA)
    WORK_HOURS_START = 9  # 9:00
    WORK_HOURS_END = 18  # 18:00
    WORK_DAYS = [0, 1, 2, 3, 4]  # Пн-Пт (0 - понедельник в Python)

    # Цветовые коды для статусов
    STATUS_COLORS = {
        'new': '#3498db',  # Синий
        'in_progress': '#f39c12',  # Оранжевый
        'resolved': '#2ecc71',  # Зеленый
        'closed': '#95a5a6',  # Серый
        'rejected': '#e74c3c'  # Красный
    }
