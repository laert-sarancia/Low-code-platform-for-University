"""
Сервис валидации данных.
Обеспечивает проверку корректности входных данных.
"""

import re
from typing import Dict, Any, List, Optional
from datetime import datetime


class ValidationService:
    """
    Сервис для валидации данных всех типов.
    """

    # Регулярные выражения для валидации
    EMAIL_PATTERN = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    PHONE_PATTERN = r'^\+?[0-9]{10,15}$'
    USERNAME_PATTERN = r'^[a-zA-Z0-9_]{3,20}$'

    def validate_request_data(self, data: Dict[str, Any]) -> bool:
        """
        Валидация данных заявки.

        Args:
            data: Данные заявки

        Returns:
            True если данные корректны

        Raises:
            ValueError: При некорректных данных
        """
        errors = []

        # Проверка обязательных полей
        required_fields = ['title']
        for field in required_fields:
            if field not in data or not data[field]:
                errors.append(f"Поле '{field}' обязательно")

        if 'title' in data:
            if len(data['title']) < 5:
                errors.append("Тема должна содержать минимум 5 символов")
            if len(data['title']) > 200:
                errors.append("Тема не должна превышать 200 символов")

        if 'description' in data and data['description']:
            if len(data['description']) > 5000:
                errors.append("Описание не должно превышать 5000 символов")

        if 'priority' in data and data['priority']:
            valid_priorities = ['critical', 'high', 'medium', 'low']
            if data['priority'] not in valid_priorities:
                errors.append(f"Приоритет должен быть одним из: {valid_priorities}")

        if 'category_id' in data and data['category_id']:
            if not isinstance(data['category_id'], int) or data['category_id'] <= 0:
                errors.append("Некорректный ID категории")

        if errors:
            raise ValueError("\n".join(errors))

        return True

    def validate_user_data(self, data: Dict[str, Any]) -> bool:
        """
        Валидация данных пользователя.

        Args:
            data: Данные пользователя

        Returns:
            True если данные корректны

        Raises:
            ValueError: При некорректных данных
        """
        errors = []

        # Проверка обязательных полей
        required_fields = ['username', 'email', 'full_name']
        for field in required_fields:
            if field not in data or not data[field]:
                errors.append(f"Поле '{field}' обязательно")

        if 'username' in data and data['username']:
            if not re.match(self.USERNAME_PATTERN, data['username']):
                errors.append("Логин должен содержать 3-20 символов (буквы, цифры, _)")

        if 'email' in data and data['email']:
            if not re.match(self.EMAIL_PATTERN, data['email']):
                errors.append("Некорректный формат email")

        if 'full_name' in data and data['full_name']:
            if len(data['full_name'].split()) < 2:
                errors.append("Укажите полное имя и фамилию")
            if len(data['full_name']) > 100:
                errors.append("ФИО не должно превышать 100 символов")

        if 'phone' in data and data['phone']:
            if not re.match(self.PHONE_PATTERN, data['phone']):
                errors.append("Некорректный формат телефона")

        if 'role' in data and data['role']:
            valid_roles = ['requester', 'executor', 'admin']
            if data['role'] not in valid_roles:
                errors.append(f"Роль должна быть одной из: {valid_roles}")

        if errors:
            raise ValueError("\n".join(errors))

        return True

    def validate_category_data(self, data: Dict[str, Any]) -> bool:
        """
        Валидация данных категории.

        Args:
            data: Данные категории

        Returns:
            True если данные корректны

        Raises:
            ValueError: При некорректных данных
        """
        errors = []

        if 'name' in data and data['name']:
            if len(data['name']) < 3:
                errors.append("Название категории должно содержать минимум 3 символа")
            if len(data['name']) > 50:
                errors.append("Название категории не должно превышать 50 символов")
        else:
            errors.append("Поле 'name' обязательно")

        if 'sla_hours' in data and data['sla_hours'] is not None:
            if not isinstance(data['sla_hours'], (int, float)) or data['sla_hours'] <= 0:
                errors.append("SLA часы должны быть положительным числом")

        if 'color' in data and data['color']:
            # Проверка HEX цвета
            if not re.match(r'^#[0-9A-Fa-f]{6}$', data['color']):
                errors.append("Цвет должен быть в формате HEX (#RRGGBB)")

        if errors:
            raise ValueError("\n".join(errors))

        return True

    def validate_status_data(self, data: Dict[str, Any]) -> bool:
        """
        Валидация данных статуса.

        Args:
            data: Данные статуса

        Returns:
            True если данные корректны

        Raises:
            ValueError: При некорректных данных
        """
        errors = []

        if 'name' in data and data['name']:
            if len(data['name']) < 2:
                errors.append("Название статуса должно содержать минимум 2 символа")
        else:
            errors.append("Поле 'name' обязательно")

        if 'code' in data and data['code']:
            if not data['code'].isidentifier():
                errors.append("Код статуса должен быть допустимым идентификатором")
        else:
            errors.append("Поле 'code' обязательно")

        if 'color' in data and data['color']:
            if not re.match(r'^#[0-9A-Fa-f]{6}$', data['color']):
                errors.append("Цвет должен быть в формате HEX (#RRGGBB)")

        if errors:
            raise ValueError("\n".join(errors))

        return True

    def validate_date_range(self, start_date: Optional[datetime],
                            end_date: Optional[datetime]) -> bool:
        """
        Валидация диапазона дат.

        Args:
            start_date: Начальная дата
            end_date: Конечная дата

        Returns:
            True если диапазон корректен

        Raises:
            ValueError: При некорректном диапазоне
        """
        if start_date and end_date and start_date > end_date:
            raise ValueError("Начальная дата не может быть позже конечной")

        return True

    def sanitize_input(self, text: str) -> str:
        """
        Очистка входных данных от потенциально опасных символов.

        Args:
            text: Входной текст

        Returns:
            Очищенный текст
        """
        if not text or not isinstance(text, str):
            return ""

        # Словарь для экранирования специальных символов
        html_escape_table = {
            "&": "&amp;",
            '"': "&quot;",
            "'": "&apos;",
            ">": "&gt;",
            "<": "&lt;",
        }

        # Экранирование HTML-спецсимволов
        escaped_text = "".join(html_escape_table.get(c, c) for c in text)

        # Удаление управляющих символов (кроме разрешенных)
        allowed_chars = {'\n', '\r', '\t'}
        cleaned_text = ''.join(
            char for char in escaped_text
            if ord(char) >= 32 or char in allowed_chars
        )

        # Удаление лишних пробелов
        cleaned_text = ' '.join(cleaned_text.split())

        return cleaned_text.strip()
