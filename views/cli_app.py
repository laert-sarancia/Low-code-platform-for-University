"""
Консольный интерфейс для системы управления IT-заявками.
Обеспечивает взаимодействие пользователя с системой через командную строку.
"""

import os
import sys
from datetime import datetime
from typing import Optional, List, Dict, Any

# Для цветного вывода в консоль
try:
    from colorama import init, Fore, Back, Style

    init(autoreset=True)
    COLORS_AVAILABLE = True
except ImportError:
    # Заглушки, если colorama не установлена
    class Fore:
        BLACK = RED = GREEN = YELLOW = BLUE = MAGENTA = CYAN = WHITE = RESET = ''
        LIGHTBLACK_EX = LIGHTRED_EX = LIGHTGREEN_EX = LIGHTYELLOW_EX = ''
        LIGHTBLUE_EX = LIGHTMAGENTA_EX = LIGHTCYAN_EX = LIGHTWHITE_EX = ''


    class Back:
        BLACK = RED = GREEN = YELLOW = BLUE = MAGENTA = CYAN = WHITE = RESET = ''


    class Style:
        BRIGHT = DIM = NORMAL = RESET_ALL = ''


    COLORS_AVAILABLE = False

# Для форматирования таблиц
try:
    from tabulate import tabulate

    TABULATE_AVAILABLE = True
except ImportError:
    TABULATE_AVAILABLE = False

# Импорт сервисов и репозиториев
from services.request_service import RequestService
from services.sla_service import SLAService
from services.notification_service import NotificationService
from services.statistics_service import StatisticsService
from repositories.user_repository import UserRepository
from repositories.category_repository import CategoryRepository
from repositories.status_repository import StatusRepository
from models.user import User
from models.request import Request
from config import Config


class CLIApp:
    """
    Главный класс консольного приложения.
    Управляет состоянием сессии пользователя и навигацией по меню.
    """

    def __init__(self):
        """Инициализация приложения и сервисов"""
        # Инициализация сервисов
        self.request_service = RequestService()
        self.sla_service = SLAService()
        self.notification_service = NotificationService()
        self.statistics_service = StatisticsService()  # Добавляем сервис статистики

        # Инициализация репозиториев
        self.user_repo = UserRepository()
        self.category_repo = CategoryRepository()
        self.status_repo = StatusRepository()

        # Состояние сессии
        self.current_user: Optional[User] = None
        self.current_role: Optional[str] = None

        # Настройки отображения
        self.page_size = 10
        self.current_page = 1

        # Кэш для часто используемых данных
        self._categories_cache = None
        self._statuses_cache = None

        # Флаг для выхода
        self.running = True

    def clear_screen(self):
        """Очистка экрана консоли"""
        os.system('cls' if os.name == 'nt' else 'clear')

    def print_header(self, title: str):
        """Вывод заголовка с оформлением"""
        print("\n" + "=" * 70)
        print(f"   {title}")
        print("=" * 70 + "\n")

    def print_success(self, message: str):
        """Вывод сообщения об успехе зеленым цветом"""
        if COLORS_AVAILABLE:
            print(f"{Fore.GREEN}✓ {message}{Style.RESET_ALL}")
        else:
            print(f"[OK] {message}")

    def print_error(self, message: str):
        """Вывод сообщения об ошибке красным цветом"""
        if COLORS_AVAILABLE:
            print(f"{Fore.RED}✗ {message}{Style.RESET_ALL}")
        else:
            print(f"[ERROR] {message}")

    def print_warning(self, message: str):
        """Вывод предупреждения желтым цветом"""
        if COLORS_AVAILABLE:
            print(f"{Fore.YELLOW}⚠ {message}{Style.RESET_ALL}")
        else:
            print(f"[WARN] {message}")

    def print_info(self, message: str):
        """Вывод информационного сообщения синим цветом"""
        if COLORS_AVAILABLE:
            print(f"{Fore.CYAN}ℹ {message}{Style.RESET_ALL}")
        else:
            print(f"[INFO] {message}")

    def print_table(self, data: List[Dict], headers: Dict[str, str]):
        """
        Вывод данных в виде таблицы

        Args:
            data: Список словарей с данными
            headers: Словарь {поле_в_данных: заголовок_колонки}
        """
        if not data:
            self.print_warning("Нет данных для отображения")
            return

        if TABULATE_AVAILABLE:
            # Подготовка данных для tabulate
            table_data = []
            for row in data:
                table_row = []
                for field in headers.keys():
                    value = row.get(field, '')
                    # Форматирование специальных типов
                    if isinstance(value, datetime):
                        value = value.strftime("%d.%m.%Y %H:%M")
                    elif isinstance(value, bool):
                        value = "✓" if value else "✗"
                    elif value is None:
                        value = "-"
                    table_row.append(value)
                table_data.append(table_row)

            print(tabulate(
                table_data,
                headers=list(headers.values()),
                tablefmt="grid",
                stralign="left"
            ))
        else:
            # Простой вывод без tabulate
            for i, row in enumerate(data, 1):
                print(f"\n--- Запись {i} ---")
                for field, header in headers.items():
                    value = row.get(field, '-')
                    if isinstance(value, datetime):
                        value = value.strftime("%d.%m.%Y %H:%M")
                    print(f"{header}: {value}")

    def print_menu(self, title: str, options: List[tuple]) -> str:
        """
        Вывод меню и получение выбора пользователя

        Args:
            title: Заголовок меню
            options: Список кортежей (ключ, описание, [цвет])

        Returns:
            Выбранный ключ
        """
        self.print_header(title)

        for key, description, *color_info in options:
            color = color_info[0] if color_info else Fore.WHITE
            if COLORS_AVAILABLE:
                print(f"  {color}{key}{Style.RESET_ALL}. {description}")
            else:
                print(f"  {key}. {description}")

        print("\n  " + "-" * 40)
        print(f"  {Fore.YELLOW if COLORS_AVAILABLE else ''}0. Выйти{Style.RESET_ALL if COLORS_AVAILABLE else ''}")

        while True:
            choice = input("\n  Ваш выбор: ").strip()
            if choice == '0':
                return '0'
            for key, *_ in options:
                if choice == key:
                    return key
            self.print_error("Неверный выбор. Пожалуйста, попробуйте снова.")

    def input_with_validation(self, prompt: str, validator=None, required=True, default=None) -> str:
        """
        Ввод с валидацией

        Args:
            prompt: Приглашение к вводу
            validator: Функция валидации (принимает значение, возвращает bool/str)
            required: Обязательно ли поле
            default: Значение по умолчанию
        """
        while True:
            if default:
                value = input(f"{prompt} [{default}]: ").strip()
                if not value:
                    return default
            else:
                value = input(f"{prompt}: ").strip()

            if not value and not required:
                return value

            if not value and required:
                self.print_error("Это поле обязательно для заполнения")
                continue

            if validator:
                result = validator(value)
                if result is True:
                    return value
                elif isinstance(result, str):
                    self.print_error(result)
                else:
                    self.print_error("Некорректное значение")
            else:
                return value

    def select_from_list(self, items: List[tuple], prompt: str = "Выберите из списка") -> Optional[Any]:
        """
        Выбор элемента из списка

        Args:
            items: Список кортежей (id, отображаемое_имя, [доп_данные])
            prompt: Приглашение к выбору

        Returns:
            Выбранный id или None
        """
        if not items:
            self.print_warning("Список пуст")
            return None

        print(f"\n{prompt}:")
        for i, item in enumerate(items, 1):
            if len(item) == 2:
                print(f"  {i}. {item[1]}")
            else:
                print(f"  {i}. {item[1]} ({item[2]})")

        while True:
            try:
                choice = input("\n  Номер: ").strip()
                if not choice:
                    return None

                idx = int(choice) - 1
                if 0 <= idx < len(items):
                    return items[idx][0]
                else:
                    self.print_error("Неверный номер")
            except ValueError:
                self.print_error("Введите число")

    # ==================== МЕТОДЫ АУТЕНТИФИКАЦИИ ====================

    def login(self) -> bool:
        """
        Аутентификация пользователя

        Returns:
            True если успешно, False если выход
        """
        self.clear_screen()
        self.print_header("Вход в систему управления IT-заявками")

        print("Добро пожаловать в систему автоматизации IT-заявок")
        print("Университет 'Синергия'\n")

        # Для MVP используем упрощенную аутентификацию
        # В реальной системе здесь была бы интеграция с Azure AD
        print("Доступные тестовые учетные записи:")
        print("  admin / adminpass  - Администратор")
        print("  ivanov / pass      - Исполнитель (IT-специалист)")
        print("  petrova / pass     - Заявитель (сотрудник деканата)")
        print()

        username = self.input_with_validation("Логин", required=True)
        if username == '0':
            return False

        password = self.input_with_validation("Пароль", required=True)

        # Поиск пользователя в БД
        user = self.user_repo.find_by_username(username)

        # Для MVP проверка упрощенная
        if user and password == 'pass' or (username == 'admin' and password == 'adminpass'):
            self.current_user = user
            self.current_role = user.role
            self.print_success(f"Добро пожаловать, {user.full_name}!")

            # Запись в историю входа
            self.notification_service.log_user_action(user.id, 'login')

            return True
        else:
            self.print_error("Неверный логин или пароль")
            input("\nНажмите Enter для продолжения...")
            return self.login()

    def logout(self):
        """Выход из системы"""
        if self.current_user:
            self.notification_service.log_user_action(self.current_user.id, 'logout')
        self.current_user = None
        self.current_role = None
        self.print_info("Вы вышли из системы")

    # ==================== МЕТОДЫ ДЛЯ ВСЕХ ПОЛЬЗОВАТЕЛЕЙ ====================

    def show_main_menu(self):
        """Главное меню в зависимости от роли"""
        if self.current_role == 'admin':
            self.show_admin_menu()
        elif self.current_role == 'executor':
            self.show_executor_menu()
        else:
            self.show_requester_menu()

    def show_my_requests(self):
        """Просмотр своих заявок"""
        self.clear_screen()
        self.print_header("Мои заявки")

        # Получаем заявки пользователя
        requests = self.request_service.get_user_requests(
            self.current_user.id,
            self.current_role
        )

        if not requests:
            self.print_warning("У вас нет заявок")
            input("\nНажмите Enter для продолжения...")
            return

        # Подготовка данных для таблицы
        table_data = []
        for req in requests:
            status = self.status_repo.find_by_id(req.status_id)
            category = self.category_repo.find_by_id(req.category_id)
            sla_info = self.sla_service.calculate_sla(req)

            # Определяем цвет для статуса SLA
            sla_color = ''
            if COLORS_AVAILABLE:
                if not sla_info['is_compliant']:
                    sla_color = Fore.RED
                elif sla_info['percentage'] > 80:
                    sla_color = Fore.YELLOW
                else:
                    sla_color = Fore.GREEN

            table_data.append({
                'id': req.id,
                'title': req.title[:50] + '...' if len(req.title) > 50 else req.title,
                'category': category.name if category else '-',
                'status': status.name if status else '-',
                'priority': req.priority.upper(),
                'created': req.created_at,
                'sla': f"{sla_color}{sla_info['status_text']}{Style.RESET_ALL if COLORS_AVAILABLE else ''}",
                'assignee': self._get_user_name(req.assignee_id)
            })

        headers = {
            'id': '№',
            'title': 'Тема',
            'category': 'Категория',
            'status': 'Статус',
            'priority': 'Приор.',
            'created': 'Создана',
            'sla': 'SLA',
            'assignee': 'Исполнитель'
        }

        self.print_table(table_data, headers)

        # Детальный просмотр
        self.view_request_details()

    def view_request_details(self):
        """Просмотр деталей конкретной заявки"""
        req_id = input("\nВведите номер заявки для просмотра деталей (Enter для возврата): ").strip()
        if not req_id:
            return

        try:
            req_id = int(req_id)
            request = self.request_service.get_request_by_id(req_id)

            if not request:
                self.print_error("Заявка не найдена")
                input("Нажмите Enter для продолжения...")
                return

            # Проверка прав доступа
            if (self.current_role == 'requester' and
                    request.requester_id != self.current_user.id):
                self.print_error("У вас нет прав на просмотр этой заявки")
                input("Нажмите Enter для продолжения...")
                return

            self.show_request_card(request)

        except ValueError:
            self.print_error("Неверный формат номера")

    def show_request_card(self, request: Request):
        """Отображение карточки заявки"""
        self.clear_screen()
        self.print_header(f"Заявка #{request.id}")

        # Получаем связанные данные
        requester = self.user_repo.find_by_id(request.requester_id)
        assignee = self.user_repo.find_by_id(request.assignee_id) if request.assignee_id else None
        category = self.category_repo.find_by_id(request.category_id)
        status = self.status_repo.find_by_id(request.status_id)

        # Расчет SLA
        sla_info = self.sla_service.calculate_sla(request)

        # Определяем цвет для статуса
        status_color = ''
        if COLORS_AVAILABLE and status:
            status_color = status.color or Fore.WHITE

        # Вывод информации
        print(f"{Fore.CYAN if COLORS_AVAILABLE else ''}Тема:{Style.RESET_ALL} {request.title}")
        print(f"{Fore.CYAN if COLORS_AVAILABLE else ''}Описание:{Style.RESET_ALL} {request.description or '-'}")
        print()
        print(
            f"{Fore.CYAN if COLORS_AVAILABLE else ''}Категория:{Style.RESET_ALL} {category.name if category else '-'}")
        print(
            f"{Fore.CYAN if COLORS_AVAILABLE else ''}Приоритет:{Style.RESET_ALL} {self._format_priority(request.priority)}")
        print(
            f"{Fore.CYAN if COLORS_AVAILABLE else ''}Статус:{Style.RESET_ALL} {status_color}{status.name if status else '-'}{Style.RESET_ALL if COLORS_AVAILABLE else ''}")
        print()
        print(
            f"{Fore.CYAN if COLORS_AVAILABLE else ''}Заявитель:{Style.RESET_ALL} {requester.full_name if requester else '-'} ({requester.department if requester else '-'})")
        print(
            f"{Fore.CYAN if COLORS_AVAILABLE else ''}Исполнитель:{Style.RESET_ALL} {assignee.full_name if assignee else 'Не назначен'}")
        print()
        print(
            f"{Fore.CYAN if COLORS_AVAILABLE else ''}Создана:{Style.RESET_ALL} {request.created_at.strftime('%d.%m.%Y %H:%M') if request.created_at else '-'}")
        print(
            f"{Fore.CYAN if COLORS_AVAILABLE else ''}Обновлена:{Style.RESET_ALL} {request.updated_at.strftime('%d.%m.%Y %H:%M') if request.updated_at else '-'}")
        if request.resolved_at:
            print(
                f"{Fore.CYAN if COLORS_AVAILABLE else ''}Решена:{Style.RESET_ALL} {request.resolved_at.strftime('%d.%m.%Y %H:%M')}")

        print("\n" + "-" * 70)

        # Информация о SLA
        sla_color = sla_info['color']
        if COLORS_AVAILABLE:
            print(f"{Fore.CYAN}SLA статус:{Style.RESET_ALL} {sla_color}{sla_info['status_text']}{Style.RESET_ALL}")
        else:
            print(f"SLA статус: {sla_info['status_text']}")
        print(f"Прошло времени: {sla_info['elapsed_hours']} ч.")
        print(f"Лимит SLA: {sla_info['sla_limit']} ч.")
        print(f"Выполнение: {sla_info['percentage']}%")
        if sla_info['remaining_hours'] > 0:
            print(f"Осталось: {sla_info['remaining_hours']} ч.")

        print("\n" + "-" * 70)

        # История изменений
        self.show_request_history(request.id)

        # Действия с заявкой
        self.request_actions(request)

    def show_request_history(self, request_id: int):
        """Отображение истории изменений заявки"""
        history = self.request_service.get_request_history(request_id)

        if not history:
            print("\nИстория изменений отсутствует")
            return

        print(f"\n{Fore.CYAN if COLORS_AVAILABLE else ''}История изменений:{Style.RESET_ALL}")

        for entry in history:
            changed_by = self.user_repo.find_by_id(entry['changed_by'])
            old_status = self.status_repo.find_by_id(entry['old_status_id']) if entry['old_status_id'] else None
            new_status = self.status_repo.find_by_id(entry['new_status_id'])

            status_change = ""
            if old_status and new_status:
                status_change = f"{old_status.name} → {new_status.name}"
            elif new_status:
                status_change = f"→ {new_status.name}"

            date_str = entry['changed_at'].strftime('%d.%m.%Y %H:%M') if entry['changed_at'] else '-'

            print(f"  {date_str} | {changed_by.full_name if changed_by else '-'}: {status_change}")
            if entry.get('comment'):
                print(f"    Комментарий: {entry['comment']}")

    def _format_priority(self, priority: str) -> str:
        """Форматирование приоритета с цветом"""
        priority_colors = {
            'critical': (Fore.RED, 'КРИТИЧЕСКИЙ'),
            'high': (Fore.YELLOW, 'ВЫСОКИЙ'),
            'medium': (Fore.GREEN, 'СРЕДНИЙ'),
            'low': (Fore.BLUE, 'НИЗКИЙ')
        }

        color, text = priority_colors.get(priority, (Fore.WHITE, priority.upper()))

        if COLORS_AVAILABLE:
            return f"{color}{text}{Style.RESET_ALL}"
        return text

    def _get_user_name(self, user_id: Optional[int]) -> str:
        """Получение имени пользователя по ID"""
        if not user_id:
            return '-'
        user = self.user_repo.find_by_id(user_id)
        return user.full_name if user else '-'

    # ==================== МЕТОДЫ ДЛЯ ЗАЯВИТЕЛЯ ====================

    def show_requester_menu(self):
        """Меню для заявителя"""
        menu_options = [
            ('1', 'Создать новую заявку', Fore.GREEN),
            ('2', 'Мои заявки', Fore.BLUE),
            ('3', 'Поиск заявок', Fore.CYAN),
            ('4', 'Мой профиль', Fore.MAGENTA)
        ]

        while True:
            self.clear_screen()
            choice = self.print_menu(
                f"Меню заявителя: {self.current_user.full_name}",
                menu_options
            )

            if choice == '0':
                self.logout()
                break
            elif choice == '1':
                self.create_request()
            elif choice == '2':
                self.show_my_requests()
            elif choice == '3':
                self.search_requests()
            elif choice == '4':
                self.show_profile()

    def create_request(self):
        """Создание новой заявки"""
        self.clear_screen()
        self.print_header("Создание новой заявки")

        # Получаем список категорий
        categories = self.category_repo.get_active()
        if not categories:
            self.print_error("Нет доступных категорий. Обратитесь к администратору.")
            input("\nНажмите Enter для продолжения...")
            return

        # Выбор категории
        category_items = [(c.id, c.name, f"SLA: {c.sla_hours}ч") for c in categories]
        category_id = self.select_from_list(category_items, "Выберите категорию заявки")

        if not category_id:
            return

        # Ввод данных заявки
        title = self.input_with_validation(
            "Краткое описание (тема)",
            validator=lambda x: len(x) >= 5 or "Минимум 5 символов",
            required=True
        )

        description = self.input_with_validation(
            "Подробное описание проблемы",
            required=False,
            default="-"
        )

        # Выбор приоритета
        print("\nВыберите приоритет:")
        priorities = [
            ('critical', 'Критический (система не работает)'),
            ('high', 'Высокий (сильно мешает работе)'),
            ('medium', 'Средний (мешает, но можно работать)'),
            ('low', 'Низкий (не срочно)')
        ]

        for i, (code, desc) in enumerate(priorities, 1):
            print(f"  {i}. {desc}")

        priority_idx = None
        while priority_idx is None:
            try:
                choice = int(input("\n  Номер приоритета (1-4): ").strip())
                if 1 <= choice <= 4:
                    priority = priorities[choice - 1][0]
                    priority_idx = choice
                else:
                    self.print_error("Введите число от 1 до 4")
            except ValueError:
                self.print_error("Введите число")

        # Создание заявки
        request_data = {
            'title': title,
            'description': description,
            'requester_id': self.current_user.id,
            'category_id': category_id,
            'priority': priority,
            'status_id': 1  # Статус "Новая"
        }

        try:
            request_id = self.request_service.create_request(request_data)
            self.print_success(f"Заявка #{request_id} успешно создана!")

            # Отправка уведомлений
            self.notification_service.notify_new_request(request_id)

        except Exception as e:
            self.print_error(f"Ошибка при создании заявки: {e}")

        input("\nНажмите Enter для продолжения...")

    # ==================== МЕТОДЫ ДЛЯ ИСПОЛНИТЕЛЯ ====================

    def show_executor_menu(self):
        """Меню для исполнителя"""
        menu_options = [
            ('1', 'Новые заявки', Fore.RED),
            ('2', 'Мои заявки в работе', Fore.YELLOW),
            ('3', 'Поиск заявок', Fore.CYAN),
            ('4', 'Просроченные заявки', Fore.MAGENTA),
            ('5', 'Статистика', Fore.BLUE),
            ('6', 'Мой профиль', Fore.GREEN)
        ]

        while True:
            self.clear_screen()

            # Показываем счетчики
            self._show_executor_counts()

            choice = self.print_menu(
                f"Меню исполнителя: {self.current_user.full_name}",
                menu_options
            )

            if choice == '0':
                self.logout()
                break
            elif choice == '1':
                self.show_new_requests()
            elif choice == '2':
                self.show_assigned_requests()
            elif choice == '3':
                self.search_requests()
            elif choice == '4':
                self.show_overdue_requests()
            elif choice == '5':
                self.show_statistics()
            elif choice == '6':
                self.show_profile()

    def _show_executor_counts(self):
        """Отображение счетчиков для исполнителя"""
        new_count = len(self.request_service.get_new_requests())
        assigned_count = len(self.request_service.get_requests_by_assignee(self.current_user.id))
        overdue_count = len(self.request_service.get_overdue_requests())

        print("\n" + " " * 10 + "=" * 50)
        print(
            " " * 10 + f"📋 Новых заявок: {Fore.RED if COLORS_AVAILABLE else ''}{new_count}{Style.RESET_ALL if COLORS_AVAILABLE else ''}")
        print(
            " " * 10 + f"🔄 В работе: {Fore.YELLOW if COLORS_AVAILABLE else ''}{assigned_count}{Style.RESET_ALL if COLORS_AVAILABLE else ''}")
        print(
            " " * 10 + f"⚠ Просрочено: {Fore.RED if COLORS_AVAILABLE else ''}{overdue_count}{Style.RESET_ALL if COLORS_AVAILABLE else ''}")
        print(" " * 10 + "=" * 50 + "\n")

    def show_new_requests(self):
        """Отображение новых заявок"""
        self.clear_screen()
        self.print_header("Новые заявки (ожидают назначения)")

        requests = self.request_service.get_new_requests()

        if not requests:
            self.print_warning("Новых заявок нет")
            input("\nНажмите Enter для продолжения...")
            return

        # Подготовка данных
        table_data = []
        for req in requests:
            requester = self.user_repo.find_by_id(req.requester_id)
            sla_info = self.sla_service.calculate_sla(req)

            sla_color = ''
            if COLORS_AVAILABLE:
                if not sla_info['is_compliant']:
                    sla_color = Fore.RED
                elif sla_info['percentage'] > 80:
                    sla_color = Fore.YELLOW

            table_data.append({
                'id': req.id,
                'title': req.title[:40] + '...' if len(req.title) > 40 else req.title,
                'requester': requester.full_name if requester else '-',
                'priority': self._format_priority(req.priority),
                'created': req.created_at,
                'sla': f"{sla_color}{sla_info['status_text']}{Style.RESET_ALL if COLORS_AVAILABLE else ''}"
            })

        headers = {
            'id': '№',
            'title': 'Тема',
            'requester': 'Заявитель',
            'priority': 'Приоритет',
            'created': 'Создана',
            'sla': 'SLA'
        }

        self.print_table(table_data, headers)

        # Возможность назначить заявку
        self.assign_requests_menu(requests)

    def assign_requests_menu(self, requests: List[Request]):
        """Меню назначения заявок"""
        print("\n" + "-" * 70)
        print("Действия:")
        print("  Введите номер заявки для назначения")
        print("  Enter для возврата")

        choice = input("\n  Номер заявки: ").strip()
        if not choice:
            return

        try:
            req_id = int(choice)
            request = next((r for r in requests if r.id == req_id), None)

            if request:
                self.assign_to_self(request)
            else:
                self.print_error("Заявка не найдена в списке новых")
        except ValueError:
            self.print_error("Неверный формат номера")

    def assign_to_self(self, request: Request):
        """Назначение заявки на себя"""
        confirm = input(f"\nНазначить заявку #{request.id} на себя? (д/н): ").strip().lower()

        if confirm in ['д', 'да', 'y', 'yes']:
            try:
                self.request_service.assign_request(request.id, self.current_user.id)
                self.print_success(f"Заявка #{request.id} назначена на вас")

                # Добавить комментарий
                comment = input("Комментарий (необязательно): ").strip()
                if comment:
                    self.request_service.add_comment(request.id, self.current_user.id, comment)

                # Уведомление заявителя
                self.notification_service.notify_assignment(request.id, self.current_user.id)

            except Exception as e:
                self.print_error(f"Ошибка при назначении: {e}")

        input("\nНажмите Enter для продолжения...")

    def show_assigned_requests(self):
        """Отображение заявок, назначенных на текущего исполнителя"""
        self.clear_screen()
        self.print_header("Мои заявки в работе")

        requests = self.request_service.get_requests_by_assignee(self.current_user.id)

        if not requests:
            self.print_warning("У вас нет заявок в работе")
            input("\nНажмите Enter для продолжения...")
            return

        # Подготовка данных
        table_data = []
        for req in requests:
            requester = self.user_repo.find_by_id(req.requester_id)
            status = self.status_repo.find_by_id(req.status_id)
            sla_info = self.sla_service.calculate_sla(req)

            sla_color = ''
            if COLORS_AVAILABLE and not sla_info['is_compliant']:
                sla_color = Fore.RED

            table_data.append({
                'id': req.id,
                'title': req.title[:40] + '...' if len(req.title) > 40 else req.title,
                'requester': requester.full_name if requester else '-',
                'status': status.name if status else '-',
                'priority': self._format_priority(req.priority),
                'created': req.created_at,
                'sla': f"{sla_color}{sla_info['status_text']}{Style.RESET_ALL if COLORS_AVAILABLE else ''}"
            })

        headers = {
            'id': '№',
            'title': 'Тема',
            'requester': 'Заявитель',
            'status': 'Статус',
            'priority': 'Приор.',
            'created': 'Создана',
            'sla': 'SLA'
        }

        self.print_table(table_data, headers)

        # Действия с выбранной заявкой
        self.manage_assigned_request()

    def manage_assigned_request(self):
        """Управление назначенной заявкой"""
        req_id = input("\nВведите номер заявки для работы (Enter для возврата): ").strip()
        if not req_id:
            return

        try:
            req_id = int(req_id)
            request = self.request_service.get_request_by_id(req_id)

            if not request or request.assignee_id != self.current_user.id:
                self.print_error("Заявка не найдена или не назначена на вас")
                input("Нажмите Enter для продолжения...")
                return

            self.show_request_card(request)

        except ValueError:
            self.print_error("Неверный формат номера")

    def request_actions(self, request: Request):
        """Действия с заявкой (для исполнителя)"""
        if self.current_role not in ['executor', 'admin']:
            return

        print("\n" + "-" * 70)
        print("Действия с заявкой:")
        print("  1. Изменить статус")
        print("  2. Добавить комментарий")
        print("  3. Переназначить исполнителя")
        print("  Enter. Вернуться")

        choice = input("\n  Выбор: ").strip()

        if choice == '1':
            self.change_request_status(request)
        elif choice == '2':
            self.add_comment(request)
        elif choice == '3':
            self.reassign_request(request)

    def change_request_status(self, request: Request):
        """Изменение статуса заявки"""
        # Получаем доступные статусы
        current_status = self.status_repo.find_by_id(request.status_id)
        available_statuses = self.status_repo.get_next_statuses(request.status_id)

        if not available_statuses:
            self.print_warning("Нет доступных статусов для изменения")
            return

        print(f"\nТекущий статус: {current_status.name if current_status else '-'}")
        print("Доступные статусы:")

        status_items = [(s.id, s.name, s.color) for s in available_statuses]
        selected_id = self.select_from_list(status_items, "Выберите новый статус")

        if not selected_id:
            return

        comment = self.input_with_validation(
            "Комментарий к изменению",
            required=False
        )

        try:
            self.request_service.update_status(
                request.id,
                selected_id,
                comment,
                self.current_user.id
            )

            self.print_success(f"Статус заявки #{request.id} изменен")

            # Уведомление заявителя
            self.notification_service.notify_status_change(
                request.id,
                request.status_id,
                selected_id
            )

        except Exception as e:
            self.print_error(f"Ошибка при изменении статуса: {e}")

        input("\nНажмите Enter для продолжения...")

    def add_comment(self, request: Request):
        """Добавление комментария к заявке"""
        comment = self.input_with_validation(
            "Введите комментарий",
            required=True,
            validator=lambda x: len(x) >= 3 or "Комментарий слишком короткий"
        )

        try:
            self.request_service.add_comment(
                request.id,
                self.current_user.id,
                comment
            )

            self.print_success("Комментарий добавлен")

            # Уведомление заявителя о новом комментарии
            self.notification_service.notify_new_comment(request.id, comment)

        except Exception as e:
            self.print_error(f"Ошибка при добавлении комментария: {e}")

        input("\nНажмите Enter для продолжения...")

    def reassign_request(self, request: Request):
        """Переназначение заявки другому исполнителю"""
        # Получаем список исполнителей
        executors = self.user_repo.find_executors()

        if not executors:
            self.print_warning("Нет доступных исполнителей")
            return

        # Исключаем текущего исполнителя
        available = [(u.id, u.full_name, u.department) for u in executors if u.id != self.current_user.id]

        if not available:
            self.print_warning("Нет других исполнителей")
            return

        print("\nДоступные исполнители:")
        selected_id = self.select_from_list(available, "Выберите нового исполнителя")

        if not selected_id:
            return

        comment = self.input_with_validation(
            "Причина переназначения",
            required=True
        )

        try:
            self.request_service.assign_request(
                request.id,
                selected_id,
                comment,
                self.current_user.id
            )

            self.print_success(f"Заявка #{request.id} переназначена")

        except Exception as e:
            self.print_error(f"Ошибка при переназначении: {e}")

        input("\nНажмите Enter для продолжения...")

    def show_overdue_requests(self):
        """Отображение просроченных заявок"""
        self.clear_screen()
        self.print_header("Просроченные заявки")

        overdue = self.request_service.get_overdue_requests()

        if not overdue:
            self.print_success("Просроченных заявок нет!")
            input("\nНажмите Enter для продолжения...")
            return

        table_data = []
        for req in overdue:
            requester = self.user_repo.find_by_id(req.requester_id)
            assignee = self.user_repo.find_by_id(req.assignee_id)
            sla_info = self.sla_service.calculate_sla(req)

            table_data.append({
                'id': req.id,
                'title': req.title[:40] + '...' if len(req.title) > 40 else req.title,
                'requester': requester.full_name if requester else '-',
                'assignee': assignee.full_name if assignee else 'Не назначен',
                'priority': req.priority.upper(),
                'overdue': f"{sla_info['elapsed_hours'] - sla_info['sla_limit']:.1f} ч."
            })

        headers = {
            'id': '№',
            'title': 'Тема',
            'requester': 'Заявитель',
            'assignee': 'Исполнитель',
            'priority': 'Приор.',
            'overdue': 'Просрочка'
        }

        self.print_table(table_data, headers)
        input("\nНажмите Enter для продолжения...")

    # ==================== МЕТОДЫ ДЛЯ АДМИНИСТРАТОРА ====================

    def show_admin_menu(self):
        """Меню администратора"""
        menu_options = [
            ('1', 'Управление заявками', Fore.GREEN),
            ('2', 'Управление пользователями', Fore.BLUE),
            ('3', 'Управление справочниками', Fore.CYAN),
            ('4', 'Отчеты и статистика', Fore.MAGENTA),
            ('5', 'Настройки системы', Fore.YELLOW),
            ('6', 'Мой профиль', Fore.WHITE)
        ]

        while True:
            self.clear_screen()
            choice = self.print_menu(
                f"Панель администратора: {self.current_user.full_name}",
                menu_options
            )

            if choice == '0':
                self.logout()
                break
            elif choice == '1':
                self.admin_request_management()
            elif choice == '2':
                self.user_management()
            elif choice == '3':
                self.directory_management()
            elif choice == '4':
                self.show_statistics()
            elif choice == '5':
                self.system_settings()
            elif choice == '6':
                self.show_profile()

    def admin_request_management(self):
        """Управление заявками для администратора"""
        self.clear_screen()
        self.print_header("Управление заявками")

        menu_options = [
            ('1', 'Все заявки', Fore.CYAN),
            ('2', 'Новые заявки', Fore.GREEN),
            ('3', 'В работе', Fore.YELLOW),
            ('4', 'Завершенные', Fore.BLUE),
            ('5', 'Просроченные', Fore.RED),
            ('6', 'Поиск', Fore.MAGENTA)
        ]

        choice = self.print_menu("Выберите раздел", menu_options)

        if choice == '1':
            self.show_all_requests()
        elif choice == '2':
            self.show_requests_by_status(1)  # Новая
        elif choice == '3':
            self.show_requests_by_status(2)  # В работе
        elif choice == '4':
            self.show_requests_by_status([3, 4])  # Решена, Закрыта
        elif choice == '5':
            self.show_overdue_requests()
        elif choice == '6':
            self.search_requests()

    def show_all_requests(self, limit: int = 50):
        """Отображение всех заявок"""
        self.clear_screen()
        self.print_header("Все заявки")

        requests = self.request_service.get_all_requests(limit)
        self._display_requests_table(requests)
        input("\nНажмите Enter для продолжения...")

    def show_requests_by_status(self, status_ids):
        """Отображение заявок по статусу"""
        if isinstance(status_ids, int):
            status_ids = [status_ids]

        requests = []
        for sid in status_ids:
            requests.extend(self.request_service.get_requests_by_status(sid))

        self._display_requests_table(requests)
        input("\nНажмите Enter для продолжения...")

    def _display_requests_table(self, requests: List[Request]):
        """Вспомогательный метод для отображения таблицы заявок"""
        if not requests:
            self.print_warning("Нет заявок для отображения")
            return

        table_data = []
        for req in requests:
            requester = self.user_repo.find_by_id(req.requester_id)
            assignee = self.user_repo.find_by_id(req.assignee_id)
            status = self.status_repo.find_by_id(req.status_id)
            sla_info = self.sla_service.calculate_sla(req)

            sla_status = sla_info['status_text']
            if COLORS_AVAILABLE:
                if not sla_info['is_compliant']:
                    sla_status = f"{Fore.RED}{sla_status}{Style.RESET_ALL}"
                elif sla_info['percentage'] > 80:
                    sla_status = f"{Fore.YELLOW}{sla_status}{Style.RESET_ALL}"

            table_data.append({
                'id': req.id,
                'title': req.title[:30] + '...' if len(req.title) > 30 else req.title,
                'requester': requester.full_name if requester else '-',
                'assignee': assignee.full_name if assignee else '-',
                'status': status.name if status else '-',
                'priority': req.priority.upper(),
                'created': req.created_at,
                'sla': sla_status
            })

        headers = {
            'id': '№',
            'title': 'Тема',
            'requester': 'Заявитель',
            'assignee': 'Исполнитель',
            'status': 'Статус',
            'priority': 'Приор.',
            'created': 'Создана',
            'sla': 'SLA'
        }

        self.print_table(table_data, headers)

    def user_management(self):
        """Управление пользователями"""
        self.clear_screen()
        self.print_header("Управление пользователями")

        menu_options = [
            ('1', 'Список пользователей', Fore.CYAN),
            ('2', 'Добавить пользователя', Fore.GREEN),
            ('3', 'Редактировать пользователя', Fore.YELLOW),
            ('4', 'Заблокировать пользователя', Fore.RED),
            ('5', 'Назначить роль', Fore.BLUE)
        ]

        choice = self.print_menu("Выберите действие", menu_options)

        if choice == '1':
            self.list_users()
        elif choice == '2':
            self.add_user()
        elif choice == '3':
            self.edit_user()
        elif choice == '4':
            self.toggle_user_status()
        elif choice == '5':
            self.change_user_role()

    def list_users(self):
        """Список пользователей"""
        self.clear_screen()
        self.print_header("Список пользователей")

        users = self.user_repo.find_all()

        table_data = []
        for user in users:
            # Получаем статистику по пользователю
            if user.role == 'executor':
                assigned = len(self.request_service.get_requests_by_assignee(user.id))
                resolved = len(self.request_service.get_resolved_requests_by_user(user.id))
                stats = f"В работе: {assigned}, Решено: {resolved}"
            elif user.role == 'requester':
                created = len(self.request_service.get_requests_by_requester(user.id))
                stats = f"Создано: {created}"
            else:
                stats = '-'

            table_data.append({
                'id': user.id,
                'username': user.username,
                'full_name': user.full_name,
                'department': user.department or '-',
                'role': user.role.upper(),
                'stats': stats,
                'created': user.created_at
            })

        headers = {
            'id': 'ID',
            'username': 'Логин',
            'full_name': 'ФИО',
            'department': 'Отдел',
            'role': 'Роль',
            'stats': 'Статистика',
            'created': 'Создан'
        }

        self.print_table(table_data, headers)
        input("\nНажмите Enter для продолжения...")

    def add_user(self):
        """Добавление нового пользователя"""
        self.clear_screen()
        self.print_header("Добавление нового пользователя")

        print("Введите данные нового пользователя:")

        username = self.input_with_validation(
            "Логин",
            validator=lambda x: len(x) >= 3 or "Логин должен быть минимум 3 символа"
        )

        # Проверка уникальности
        if self.user_repo.find_by_username(username):
            self.print_error("Пользователь с таким логином уже существует")
            input("\nНажмите Enter для продолжения...")
            return

        full_name = self.input_with_validation(
            "ФИО",
            validator=lambda x: len(x.split()) >= 2 or "Введите полное имя и фамилию"
        )

        email = self.input_with_validation(
            "Email",
            validator=lambda x: '@' in x and '.' in x or "Введите корректный email"
        )

        department = self.input_with_validation(
            "Отдел",
            required=True
        )

        print("\nВыберите роль:")
        roles = [
            ('requester', 'Заявитель'),
            ('executor', 'Исполнитель'),
            ('admin', 'Администратор')
        ]

        role_id = self.select_from_list([(r[0], r[1]) for r in roles], "Роль")

        if not role_id:
            return

        # Создание пользователя
        user_data = {
            'username': username,
            'email': email,
            'full_name': full_name,
            'department': department,
            'role': role_id
        }

        try:
            user_id = self.user_repo.create(user_data)
            self.print_success(f"Пользователь {full_name} создан (ID: {user_id})")
        except Exception as e:
            self.print_error(f"Ошибка при создании пользователя: {e}")

        input("\nНажмите Enter для продолжения...")

    def directory_management(self):
        """Управление справочниками"""
        self.clear_screen()
        self.print_header("Управление справочниками")

        menu_options = [
            ('1', 'Категории заявок', Fore.CYAN),
            ('2', 'Статусы заявок', Fore.GREEN),
            ('3', 'Приоритеты (SLA)', Fore.YELLOW)
        ]

        choice = self.print_menu("Выберите справочник", menu_options)

        if choice == '1':
            self.manage_categories()
        elif choice == '2':
            self.manage_statuses()
        elif choice == '3':
            self.manage_priorities()

    def manage_statuses(self):
        """Управление статусами заявок"""
        self.clear_screen()
        self.print_header("УПРАВЛЕНИЕ СТАТУСАМИ")

        from repositories.status_repository import StatusRepository
        status_repo = StatusRepository()

        # Получаем все статусы
        statuses = status_repo.find_all()

        if not statuses:
            self.print_warning("Статусы не найдены")
        else:
            # Подготовка данных для таблицы
            table_data = []
            for status in statuses:
                # Получаем количество заявок с этим статусом
                from repositories.request_repository import RequestRepository
                request_repo = RequestRepository()
                requests_count = len(request_repo.find_by_status(status.id))

                # Определяем тип статуса
                status_type = []
                if status.is_initial:
                    status_type.append("Начальный")
                if status.is_final:
                    status_type.append("Конечный")
                if status.requires_comment:
                    status_type.append("Требует комментарий")

                status_type_str = ", ".join(status_type) if status_type else "Промежуточный"

                table_data.append({
                    'id': status.id,
                    'name': status.name,
                    'code': status.code,
                    'color': status.color,
                    'type': status_type_str,
                    'requests': requests_count,
                    'order': status.order
                })

            headers = {
                'id': 'ID',
                'name': 'Название',
                'code': 'Код',
                'color': 'Цвет',
                'type': 'Тип',
                'requests': 'Заявок',
                'order': 'Порядок'
            }

            self.print_table(table_data, headers)

        print("\nДействия:")
        print("  1. Добавить статус")
        print("  2. Редактировать статус")
        print("  3. Удалить статус")
        print("  4. Настроить переходы между статусами")
        print("  0. Назад")

        choice = input("\nВаш выбор: ").strip()

        if choice == '1':
            self.add_status()
        elif choice == '2':
            self.edit_status()
        elif choice == '3':
            self.delete_status()
        elif choice == '4':
            self.configure_status_transitions()

    def add_status(self):
        """Добавление нового статуса"""
        self.clear_screen()
        self.print_header("ДОБАВЛЕНИЕ НОВОГО СТАТУСА")

        from models.status import Status
        from repositories.status_repository import StatusRepository
        status_repo = StatusRepository()

        print("Введите данные нового статуса:")

        # Ввод названия
        while True:
            name = input("Название статуса: ").strip()
            if not name:
                self.print_error("Название обязательно")
                continue
            if len(name) < 2:
                self.print_error("Название должно быть минимум 2 символа")
                continue
            break

        # Ввод кода
        while True:
            code = input("Код статуса (латиницей, например 'in_progress'): ").strip()
            if not code:
                self.print_error("Код обязателен")
                continue
            if not code.replace('_', '').isalnum():
                self.print_error("Код может содержать только буквы, цифры и _")
                continue
            # Проверка уникальности
            existing = status_repo.find_by_code(code)
            if existing:
                self.print_error(f"Статус с кодом '{code}' уже существует")
                continue
            break

        # Ввод описания
        description = input("Описание (Enter для пропуска): ").strip()

        # Ввод цвета
        color = input("Цвет в HEX формате (например #3498db) [Enter для #3498db]: ").strip()
        if not color:
            color = "#3498db"
        elif not color.startswith('#') or len(color) != 7:
            self.print_warning("Неверный формат цвета, используется #3498db")
            color = "#3498db"

        # Настройки статуса
        print("\nНастройки статуса:")

        is_initial = input("Это начальный статус? (д/н) [н]: ").strip().lower()
        is_initial = is_initial in ['д', 'да', 'y', 'yes']

        is_final = input("Это конечный статус? (д/н) [н]: ").strip().lower()
        is_final = is_final in ['д', 'да', 'y', 'yes']

        requires_comment = input("Требовать комментарий при переходе? (д/н) [н]: ").strip().lower()
        requires_comment = requires_comment in ['д', 'да', 'y', 'yes']

        # Порядок сортировки
        try:
            order = input("Порядок сортировки (число) [0]: ").strip()
            order = int(order) if order else 0
        except ValueError:
            order = 0

        # Создание статуса
        status = Status(
            name=name,
            code=code,
            description=description,
            color=color,
            is_initial=is_initial,
            is_final=is_final,
            requires_comment=requires_comment,
            order=order
        )

        try:
            status_id = status_repo.create(status)
            if status_id:
                self.print_success(f"Статус '{name}' успешно создан (ID: {status_id})")
            else:
                self.print_error("Не удалось создать статус")
        except Exception as e:
            self.print_error(f"Ошибка при создании статуса: {e}")

        input("\nНажмите Enter для продолжения...")

    def edit_status(self):
        """Редактирование статуса"""
        self.clear_screen()
        self.print_header("РЕДАКТИРОВАНИЕ СТАТУСА")

        from repositories.status_repository import StatusRepository
        status_repo = StatusRepository()

        # Получаем все статусы для выбора
        statuses = status_repo.find_all()

        if not statuses:
            self.print_warning("Нет статусов для редактирования")
            input("\nНажмите Enter для продолжения...")
            return

        # Показываем список статусов
        print("Доступные статусы:")
        status_items = [(s.id, s.name, f"Код: {s.code}") for s in statuses]
        selected_id = self.select_from_list(status_items, "Выберите статус для редактирования")

        if not selected_id:
            return

        status = status_repo.find_by_id(selected_id)
        if not status:
            self.print_error("Статус не найден")
            return

        print("\nТекущие данные статуса:")
        print(f"  Название: {status.name}")
        print(f"  Код: {status.code}")
        print(f"  Описание: {status.description or '-'}")
        print(f"  Цвет: {status.color}")
        print(f"  Начальный: {'Да' if status.is_initial else 'Нет'}")
        print(f"  Конечный: {'Да' if status.is_final else 'Нет'}")
        print(f"  Требует комментарий: {'Да' if status.requires_comment else 'Нет'}")
        print(f"  Порядок: {status.order}")

        print("\nВведите новые данные (Enter для сохранения текущего):")

        # Редактирование названия
        new_name = input(f"Название [{status.name}]: ").strip()
        if new_name:
            status.name = new_name

        # Редактирование описания
        new_description = input(f"Описание [{status.description or '-'}]: ").strip()
        if new_description:
            status.description = new_description
        elif new_description == '' and status.description:
            # Пустая строка - удаляем описание
            status.description = None

        # Редактирование цвета
        new_color = input(f"Цвет [{status.color}]: ").strip()
        if new_color:
            if new_color.startswith('#') and len(new_color) == 7:
                status.color = new_color
            else:
                self.print_warning("Неверный формат цвета, оставлен текущий")

        # Редактирование настроек
        print("\nНастройки статуса (Enter для сохранения текущего):")

        is_initial = input(f"Начальный статус? (д/н) [{'д' if status.is_initial else 'н'}]: ").strip().lower()
        if is_initial in ['д', 'да', 'y', 'yes']:
            status.is_initial = True
        elif is_initial in ['н', 'нет', 'n', 'no']:
            status.is_initial = False

        is_final = input(f"Конечный статус? (д/н) [{'д' if status.is_final else 'н'}]: ").strip().lower()
        if is_final in ['д', 'да', 'y', 'yes']:
            status.is_final = True
        elif is_final in ['н', 'нет', 'n', 'no']:
            status.is_final = False

        requires_comment = input(f"Требовать комментарий? (д/н) [{'д' if status.requires_comment else 'н'}]: ").strip().lower()
        if requires_comment in ['д', 'да', 'y', 'yes']:
            status.requires_comment = True
        elif requires_comment in ['н', 'нет', 'n', 'no']:
            status.requires_comment = False

        try:
            new_order = input(f"Порядок [{status.order}]: ").strip()
            if new_order:
                status.order = int(new_order)
        except ValueError:
            self.print_warning("Неверный формат числа, оставлен текущий порядок")

        # Сохранение
        try:
            if status_repo.update(status):
                self.print_success(f"Статус '{status.name}' успешно обновлен")
            else:
                self.print_error("Не удалось обновить статус")
        except Exception as e:
            self.print_error(f"Ошибка при обновлении статуса: {e}")

        input("\nНажмите Enter для продолжения...")

    def delete_status(self):
        """Удаление статуса"""
        self.clear_screen()
        self.print_header("УДАЛЕНИЕ СТАТУСА")

        from repositories.status_repository import StatusRepository
        from repositories.request_repository import RequestRepository
        status_repo = StatusRepository()
        request_repo = RequestRepository()

        # Получаем все статусы
        statuses = status_repo.find_all()

        if not statuses:
            self.print_warning("Нет статусов для удаления")
            input("\nНажмите Enter для продолжения...")
            return

        # Показываем список статусов с количеством заявок
        print("Доступные статусы:")
        status_items = []
        for s in statuses:
            requests_count = len(request_repo.find_by_status(s.id))
            status_items.append((s.id, s.name, f"Заявок: {requests_count}"))

        selected_id = self.select_from_list(status_items, "Выберите статус для удаления")

        if not selected_id:
            return

        status = status_repo.find_by_id(selected_id)
        if not status:
            self.print_error("Статус не найден")
            return

        # Проверяем, используется ли статус
        requests_count = len(request_repo.find_by_status(status.id))

        print(f"\nСтатус: {status.name} (ID: {status.id})")
        print(f"Код: {status.code}")
        print(f"Используется в {requests_count} заявках")

        if requests_count > 0:
            self.print_warning(f"Невозможно удалить статус, который используется в заявках!")
            print("Сначала переназначьте статусы заявок или удалите заявки с этим статусом.")
            input("\nНажмите Enter для продолжения...")
            return

        # Подтверждение удаления
        confirm = input(f"\nВы уверены, что хотите удалить статус '{status.name}'? (д/н): ").strip().lower()

        if confirm in ['д', 'да', 'y', 'yes']:
            try:
                if status_repo.delete(status.id):
                    self.print_success(f"Статус '{status.name}' успешно удален")
                else:
                    self.print_error("Не удалось удалить статус")
            except Exception as e:
                self.print_error(f"Ошибка при удалении статуса: {e}")
        else:
            self.print_info("Удаление отменено")

        input("\nНажмите Enter для продолжения...")

    def configure_status_transitions(self):
        """Настройка переходов между статусами"""
        self.clear_screen()
        self.print_header("НАСТРОЙКА ПЕРЕХОДОВ МЕЖДУ СТАТУСАМИ")

        from repositories.status_repository import StatusRepository
        status_repo = StatusRepository()

        # Получаем все статусы
        statuses = status_repo.find_all()

        if len(statuses) < 2:
            self.print_warning("Недостаточно статусов для настройки переходов")
            input("\nНажмите Enter для продолжения...")
            return

        # Показываем текущие переходы
        print("Текущие переходы:")
        print("-" * 60)

        for status in statuses:
            next_statuses = status_repo.get_next_statuses(status.id)
            if next_statuses:
                next_names = [s.name for s in next_statuses]
                print(f"{status.name} → {', '.join(next_names)}")
            else:
                print(f"{status.name} → (нет переходов)")

        print("-" * 60)

        print("\nВыберите действие:")
        print("  1. Настроить переходы для статуса")
        print("  2. Сбросить все переходы")
        print("  0. Назад")

        choice = input("\nВаш выбор: ").strip()

        if choice == '1':
            self._configure_single_status_transitions(statuses, status_repo)
        elif choice == '2':
            self._reset_all_transitions(statuses, status_repo)

    def _configure_single_status_transitions(self, statuses, status_repo):
        """Настройка переходов для конкретного статуса"""

        # Выбор статуса
        print("\nВыберите статус для настройки:")
        status_items = [(s.id, s.name) for s in statuses]
        selected_id = self.select_from_list(status_items, "Статус")

        if not selected_id:
            return

        current_status = status_repo.find_by_id(selected_id)

        # Получаем текущие следующие статусы
        current_next = status_repo.get_next_statuses(current_status.id)
        current_next_ids = [s.id for s in current_next]

        print(f"\nНастройка переходов из статуса '{current_status.name}'")
        print("Выберите статусы, в которые можно перейти (можно выбрать несколько):")

        # Показываем все статусы для выбора
        other_statuses = [s for s in statuses if s.id != current_status.id]

        selected_ids = []
        for status in other_statuses:
            default = " [X]" if status.id in current_next_ids else " [ ]"
            response = input(f"{default} {status.name} (д/н)? ").strip().lower()
            if response in ['д', 'да', 'y', 'yes']:
                selected_ids.append(status.id)

        # Обновляем переходы
        current_status.next_statuses = selected_ids

        try:
            if status_repo.update(current_status):
                self.print_success(f"Переходы для статуса '{current_status.name}' обновлены")
            else:
                self.print_error("Не удалось обновить переходы")
        except Exception as e:
            self.print_error(f"Ошибка при обновлении переходов: {e}")

        input("\nНажмите Enter для продолжения...")

    def _reset_all_transitions(self, statuses, status_repo):
        """Сброс всех переходов"""
        confirm = input("\nВы уверены, что хотите сбросить все переходы? (д/н): ").strip().lower()

        if confirm in ['д', 'да', 'y', 'yes']:
            success = True
            for status in statuses:
                status.next_statuses = None
                if not status_repo.update(status):
                    success = False
                    self.print_error(f"Не удалось сбросить переходы для статуса '{status.name}'")

            if success:
                self.print_success("Все переходы успешно сброшены")

        input("\nНажмите Enter для продолжения...")

    def manage_categories(self):
        """Управление категориями"""
        self.clear_screen()
        self.print_header("Управление категориями")

        categories = self.category_repo.find_all()

        table_data = []
        for cat in categories:
            # Получаем количество заявок в категории
            req_count = len(self.request_service.get_requests_by_category(cat.id))

            table_data.append({
                'id': cat.id,
                'name': cat.name,
                'description': cat.description[:30] + '...' if cat.description and len(
                    cat.description) > 30 else cat.description,
                'sla': f"{cat.sla_hours} ч.",
                'active': '✓' if cat.is_active else '✗',
                'requests': req_count
            })

        headers = {
            'id': 'ID',
            'name': 'Название',
            'description': 'Описание',
            'sla': 'SLA (ч)',
            'active': 'Активна',
            'requests': 'Заявок'
        }

        self.print_table(table_data, headers)

        print("\nДействия:")
        print("  1. Добавить категорию")
        print("  2. Редактировать категорию")
        print("  3. Деактивировать категорию")
        print("  Enter. Назад")

        choice = input("\nВыбор: ").strip()

        if choice == '1':
            self.add_category()
        elif choice == '2':
            self.edit_category()
        elif choice == '3':
            self.toggle_category()

    def edit_category(self):
        """Редактирование категории"""
        self.clear_screen()
        self.print_header("РЕДАКТИРОВАНИЕ КАТЕГОРИИ")

        from repositories.category_repository import CategoryRepository
        category_repo = CategoryRepository()

        # Получаем все категории
        categories = category_repo.find_all()

        if not categories:
            self.print_warning("Нет категорий для редактирования")
            input("\nНажмите Enter для продолжения...")
            return

        # Показываем список категорий
        print("Доступные категории:")
        cat_items = [(c.id, c.name, f"SLA: {c.sla_hours}ч") for c in categories]
        selected_id = self.select_from_list(cat_items, "Выберите категорию для редактирования")

        if not selected_id:
            return

        category = category_repo.find_by_id(selected_id)
        if not category:
            self.print_error("Категория не найдена")
            return

        print("\nТекущие данные категории:")
        print(f"  Название: {category.name}")
        print(f"  Описание: {category.description or '-'}")
        print(f"  SLA лимит: {category.sla_hours} ч.")
        print(f"  Родительская категория: {category.parent_id or '-'}")
        print(f"  Активна: {'Да' if category.is_active else 'Нет'}")
        print(f"  Цвет: {category.color}")

        print("\nВведите новые данные (Enter для сохранения текущего):")

        # Редактирование названия
        new_name = input(f"Название [{category.name}]: ").strip()
        if new_name:
            category.name = new_name

        # Редактирование описания
        new_description = input(f"Описание [{category.description or '-'}]: ").strip()
        if new_description:
            category.description = new_description

        # Редактирование SLA
        try:
            new_sla = input(f"SLA лимит [{category.sla_hours}]: ").strip()
            if new_sla:
                category.sla_hours = int(new_sla)
        except ValueError:
            self.print_warning("Неверный формат, оставлен текущий SLA")

        # Редактирование родителя
        all_categories = category_repo.find_all()
        other_categories = [c for c in all_categories if c.id != category.id]

        if other_categories:
            print("\nВыберите нового родителя (Enter для текущего):")
            cat_items = [(c.id, c.name) for c in other_categories]
            cat_items.insert(0, (None, "Корневая категория"))
            cat_items.insert(0, (category.parent_id, f"Текущий: {category.parent_id or 'Корневая'}"))

            new_parent_id = self.select_from_list(cat_items, "Родитель")
            if new_parent_id is not None:
                category.parent_id = new_parent_id if new_parent_id != 0 else None

        # Активность
        active_input = input(f"Активна? (д/н) [{'д' if category.is_active else 'н'}]: ").strip().lower()
        if active_input in ['д', 'да', 'y', 'yes']:
            category.is_active = True
        elif active_input in ['н', 'нет', 'n', 'no']:
            category.is_active = False

        # Цвет
        new_color = input(f"Цвет [{category.color}]: ").strip()
        if new_color:
            category.color = new_color

        # Сохранение
        try:
            if category_repo.update(category):
                self.print_success(f"Категория '{category.name}' успешно обновлена")
            else:
                self.print_error("Не удалось обновить категорию")
        except Exception as e:
            self.print_error(f"Ошибка при обновлении категории: {e}")

        input("\nНажмите Enter для продолжения...")


    def add_category(self):
        """Добавление новой категории"""
        print("\n--- Добавление категории ---")

        name = self.input_with_validation(
            "Название категории",
            required=True
        )

        description = self.input_with_validation(
            "Описание",
            required=False,
            default="-"
        )

        sla_hours = self.input_with_validation(
            "SLA лимит (часы)",
            validator=lambda x: x.isdigit() and int(x) > 0 or "Введите положительное число",
            required=True
        )

        try:
            category_id = self.category_repo.create({
                'name': name,
                'description': description,
                'sla_hours': int(sla_hours),
                'is_active': 1
            })
            self.print_success(f"Категория '{name}' создана (ID: {category_id})")
        except Exception as e:
            self.print_error(f"Ошибка: {e}")

        input("\nНажмите Enter для продолжения...")

    def show_statistics(self):
        """Отображение статистики и отчетов"""
        self.clear_screen()
        self.print_header("СТАТИСТИКА И ОТЧЕТЫ")

        print("Выберите период:")
        print("  1. За 7 дней")
        print("  2. За 30 дней")
        print("  3. За 90 дней")
        print("  4. Детальная статистика")
        print("  5. Сравнение периодов")
        print("  0. Назад")

        choice = input("\nВаш выбор: ").strip()

        if choice == '0':
            return
        elif choice == '1':
            stats = self.statistics_service.get_statistics(days=7)
            self._display_statistics(stats, "ЗА 7 ДНЕЙ")
        elif choice == '2':
            stats = self.statistics_service.get_statistics(days=30)
            self._display_statistics(stats, "ЗА 30 ДНЕЙ")
        elif choice == '3':
            stats = self.statistics_service.get_statistics(days=90)
            self._display_statistics(stats, "ЗА 90 ДНЕЙ")
        elif choice == '4':
            stats = self.statistics_service.get_detailed_statistics(days=30)
            self._display_detailed_statistics(stats)
        elif choice == '5':
            stats = self.statistics_service.get_comparative_statistics(30, 7)
            self._display_comparative_statistics(stats)

        input("\nНажмите Enter для продолжения...")

    def _display_statistics(self, stats: Dict, period_title: str):
        """Отображение общей статистики"""
        if not stats:
            self.print_warning("Нет данных для отображения")
            return

        print(f"\n{Fore.CYAN}=== СТАТИСТИКА {period_title} ==={Style.RESET_ALL}")
        print(f"Всего заявок: {stats.get('total_requests', 0)}")
        print(f"Решено: {stats.get('resolved_requests', 0)}")
        print(f"Открыто: {stats.get('open_requests', 0)}")
        print(f"Процент решения: {stats.get('resolution_rate', 0)}%")
        print(f"Среднее время решения: {stats.get('avg_resolution_hours', 0)} ч.")

        print(f"\n{Fore.CYAN}По статусам:{Style.RESET_ALL}")
        for status, count in stats.get('by_status', {}).items():
            print(f"  {status}: {count}")

        print(f"\n{Fore.CYAN}По приоритетам:{Style.RESET_ALL}")
        for priority, count in stats.get('by_priority', {}).items():
            print(f"  {priority}: {count}")

        print(f"\n{Fore.CYAN}SLA статистика:{Style.RESET_ALL}")
        sla = stats.get('sla_stats', {})
        print(f"  Соблюдено: {sla.get('compliant', 0)}")
        print(f"  Нарушено: {sla.get('breached', 0)}")
        print(f"  Процент соблюдения: {sla.get('compliance_rate', 0)}%")

    def _display_detailed_statistics(self, stats: Dict):
        """Отображение детальной статистики"""
        if not stats:
            self.print_warning("Нет данных для отображения")
            return

        print(f"\n{Fore.CYAN}=== ДЕТАЛЬНАЯ СТАТИСТИКА ==={Style.RESET_ALL}")
        print(f"Всего заявок за период: {stats.get('total_requests', 0)}")

        # Распределение по часам
        hourly = stats.get('hourly_distribution', {})
        if hourly:
            print(f"\n{Fore.CYAN}Распределение по часам:{Style.RESET_ALL}")
            for hour in range(24):
                count = hourly.get(hour, 0)
                if count > 0:
                    bar = '█' * count
                    print(f"  {hour:02d}:00 {bar} ({count})")

        # Распределение по дням недели
        weekly = stats.get('weekly_distribution', {})
        if weekly:
            print(f"\n{Fore.CYAN}Распределение по дням недели:{Style.RESET_ALL}")
            for day, count in weekly.items():
                print(f"  {day}: {count}")

        # Топ создателей
        users = stats.get('by_user_detail', {})
        top_creators = users.get('top_creators', [])
        if top_creators:
            print(f"\n{Fore.CYAN}Топ создателей заявок:{Style.RESET_ALL}")
            for creator in top_creators:
                print(f"  {creator['user_name']}: {creator['requests_created']}")

        # Топ исполнителей
        top_assignees = users.get('top_assignees', [])
        if top_assignees:
            print(f"\n{Fore.CYAN}Топ исполнителей:{Style.RESET_ALL}")
            for assignee in top_assignees:
                print(f"  {assignee['user_name']}: {assignee['requests_assigned']}")

    def _display_comparative_statistics(self, stats: Dict):
        """Отображение сравнительной статистики"""
        if not stats:
            self.print_warning("Нет данных для отображения")
            return

        period1 = stats.get('period1', {})
        period2 = stats.get('period2', {})
        changes = stats.get('changes', {})

        days1 = period1.get('days', 30)
        days2 = period2.get('days', 7)
        stats1 = period1.get('stats', {})
        stats2 = period2.get('stats', {})

        print(f"\n{Fore.CYAN}=== СРАВНЕНИЕ ПЕРИОДОВ ==={Style.RESET_ALL}")
        print(f"\n{'Показатель':<30} {days1} дней   {days2} дней   Изменение")
        print("-" * 70)

        total1 = stats1.get('total_requests', 0)
        total2 = stats2.get('total_requests', 0)
        change = changes.get('total_requests_change', 0)
        arrow = "↑" if change > 0 else "↓" if change < 0 else "→"
        print(f"{'Всего заявок':<30} {total1:<8} {total2:<8} {arrow} {change}%")

        rate1 = stats1.get('resolution_rate', 0)
        rate2 = stats2.get('resolution_rate', 0)
        change = changes.get('resolution_rate_change', 0)
        arrow = "↑" if change > 0 else "↓" if change < 0 else "→"
        print(f"{'Процент решения':<30} {rate1:<8}% {rate2:<8}% {arrow} {change}%")

        time1 = stats1.get('avg_resolution_hours', 0)
        time2 = stats2.get('avg_resolution_hours', 0)
        change = changes.get('avg_resolution_change', 0)
        arrow = "↓" if change < 0 else "↑" if change > 0 else "→"
        print(f"{'Ср. время решения':<30} {time1:<8}ч {time2:<8}ч {arrow} {abs(change)}%")

    def search_requests(self):
        """Поиск заявок по различным критериям"""
        self.clear_screen()
        self.print_header("Поиск заявок")

        print("Критерии поиска (оставьте пустым для пропуска):")

        # Сбор критериев
        criteria = {}

        title = input("Тема (часть текста): ").strip()
        if title:
            criteria['title'] = title

        # Поиск по датам
        date_from = input("Дата с (ДД.ММ.ГГГГ): ").strip()
        if date_from:
            try:
                criteria['date_from'] = datetime.strptime(date_from, "%d.%m.%Y")
            except ValueError:
                self.print_warning("Неверный формат даты, критерий пропущен")

        date_to = input("Дата по (ДД.ММ.ГГГГ): ").strip()
        if date_to:
            try:
                criteria['date_to'] = datetime.strptime(date_to, "%d.%m.%Y")
            except ValueError:
                self.print_warning("Неверный формат даты, критерий пропущен")

        # Выбор статуса
        statuses = self.status_repo.find_all()
        if statuses:
            status_items = [(s.id, s.name) for s in statuses]
            status_items.insert(0, (None, "Любой статус"))
            status_id = self.select_from_list(status_items, "Статус")
            if status_id:
                criteria['status_id'] = status_id

        # Выбор приоритета
        print("\nПриоритет:")
        priorities = [(p, p.upper()) for p in Config.PRIORITIES]
        priorities.insert(0, (None, "Любой приоритет"))
        priority = self.select_from_list(priorities, "Приоритет")
        if priority:
            criteria['priority'] = priority

        # Выполнение поиска
        results = self.request_service.search_requests(criteria)

        print(
            f"\n{Fore.CYAN if COLORS_AVAILABLE else ''}Найдено заявок: {len(results)}{Style.RESET_ALL if COLORS_AVAILABLE else ''}")

        if results:
            self._display_requests_table(results)

        input("\nНажмите Enter для продолжения...")

    def show_profile(self):
        """Отображение профиля текущего пользователя"""
        self.clear_screen()
        self.print_header("Мой профиль")

        if not self.current_user:
            return

        print(f"{Fore.CYAN if COLORS_AVAILABLE else ''}Логин:{Style.RESET_ALL} {self.current_user.username}")
        print(f"{Fore.CYAN if COLORS_AVAILABLE else ''}ФИО:{Style.RESET_ALL} {self.current_user.full_name}")
        print(f"{Fore.CYAN if COLORS_AVAILABLE else ''}Email:{Style.RESET_ALL} {self.current_user.email}")
        print(f"{Fore.CYAN if COLORS_AVAILABLE else ''}Отдел:{Style.RESET_ALL} {self.current_user.department or '-'}")
        print(f"{Fore.CYAN if COLORS_AVAILABLE else ''}Роль:{Style.RESET_ALL} {self.current_user.role.upper()}")
        print(
            f"{Fore.CYAN if COLORS_AVAILABLE else ''}Дата регистрации:{Style.RESET_ALL} {self.current_user.created_at.strftime('%d.%m.%Y') if self.current_user.created_at else '-'}")

        # Статистика пользователя
        print(
            f"\n{Fore.CYAN if COLORS_AVAILABLE else ''}=== МОЯ СТАТИСТИКА ==={Style.RESET_ALL if COLORS_AVAILABLE else ''}")

        if self.current_user.role == 'requester':
            created = len(self.request_service.get_requests_by_requester(self.current_user.id))
            resolved = len(self.request_service.get_resolved_requests_by_user(self.current_user.id, as_requester=True))
            print(f"Создано заявок: {created}")
            print(f"Решено заявок: {resolved}")
        elif self.current_user.role == 'executor':
            assigned = len(self.request_service.get_requests_by_assignee(self.current_user.id))
            resolved = len(self.request_service.get_resolved_requests_by_user(self.current_user.id, as_executor=True))
            print(f"Назначено заявок: {assigned}")
            print(f"Решено заявок: {resolved}")

        input("\nНажмите Enter для продолжения...")

    def system_settings(self):
        """Настройки системы"""
        self.clear_screen()
        self.print_header("Настройки системы")

        menu_options = [
            ('1', 'Настройки SLA', Fore.CYAN),
            ('2', 'Настройки уведомлений', Fore.GREEN),
            ('3', 'Резервное копирование', Fore.YELLOW),
            ('4', 'Логи системы', Fore.BLUE)
        ]

        choice = self.print_menu("Выберите раздел", menu_options)

        if choice == '1':
            self.configure_sla()
        elif choice == '2':
            self.configure_notifications()
        elif choice == '3':
            self.backup_database()
        elif choice == '4':
            self.view_logs()

    def configure_sla(self):
        """Настройка параметров SLA"""
        self.clear_screen()
        self.print_header("Настройка SLA")

        print("Текущие настройки SLA:")
        for priority, hours in Config.SLA_LIMITS.items():
            print(f"  {priority}: {hours} часов")

        print(f"\nРабочее время: {Config.WORK_HOURS_START}:00 - {Config.WORK_HOURS_END}:00")
        print(f"Рабочие дни: Пн-Пт")

        print("\nИзменение настроек SLA (оставьте пустым для сохранения текущего):")

        for priority in Config.PRIORITIES:
            new_value = input(f"{priority} лимит (часы) [{Config.SLA_LIMITS[priority]}]: ").strip()
            if new_value and new_value.isdigit():
                Config.SLA_LIMITS[priority] = int(new_value)
                self.print_success(f"{priority} обновлен до {new_value} часов")

        # Сохранение в конфиг (в реальном приложении - в БД)
        self.print_success("Настройки SLA обновлены")
        input("\nНажмите Enter для продолжения...")

    def backup_database(self):
        """Резервное копирование базы данных"""
        self.clear_screen()
        self.print_header("Резервное копирование")

        import shutil
        from datetime import datetime

        backup_dir = "backups"
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(backup_dir, f"requests_backup_{timestamp}.db")

        try:
            shutil.copy2(Config.DATABASE_PATH, backup_file)
            self.print_success(f"База данных сохранена в {backup_file}")

            # Показываем список бэкапов
            backups = sorted([f for f in os.listdir(backup_dir) if f.endswith('.db')], reverse=True)
            if backups:
                print(
                    f"\n{Fore.CYAN if COLORS_AVAILABLE else ''}Доступные бэкапы:{Style.RESET_ALL if COLORS_AVAILABLE else ''}")
                for i, backup in enumerate(backups[:5], 1):
                    size = os.path.getsize(os.path.join(backup_dir, backup)) / 1024
                    print(f"  {i}. {backup} ({size:.1f} KB)")

        except Exception as e:
            self.print_error(f"Ошибка при создании бэкапа: {e}")

        input("\nНажмите Enter для продолжения...")

    def view_logs(self):
        """Просмотр логов системы"""
        self.clear_screen()
        self.print_header("Логи системы")

        log_file = "app.log"
        if os.path.exists(log_file):
            with open(log_file, 'r') as f:
                lines = f.readlines()[-50:]  # Последние 50 строк
                for line in lines:
                    print(line.strip())
        else:
            self.print_warning("Лог-файл не найден")

        input("\nНажмите Enter для продолжения...")

    # ==================== ОСНОВНОЙ ЦИКЛ ====================

    def run(self):
        """Запуск основного цикла приложения"""
        while self.running:
            if not self.current_user:
                if not self.login():
                    break

            self.show_main_menu()

        self.print_info("Работа завершена. До свидания!")


# Точка входа для запуска CLI
if __name__ == "__main__":
    app = CLIApp()
    app.run()
