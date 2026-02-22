#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Скрипт для управления базой данных системы IT-заявок.
Позволяет:
- Добавлять новых пользователей
- Просматривать содержимое всех таблиц
- Визуализировать структуру БД
"""

import os
import sys
import sqlite3
from datetime import datetime
from typing import List, Dict, Any, Optional
import argparse

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.db_manager import DatabaseManager
from models.user import User
from repositories.user_repository import UserRepository
from config import Config

# Попытка импорта для красивого вывода
try:
    from tabulate import tabulate

    TABULATE_AVAILABLE = True
except ImportError:
    TABULATE_AVAILABLE = False

try:
    from colorama import init, Fore, Back, Style

    init(autoreset=True)
    COLORS_AVAILABLE = True
except ImportError:
    class Fore:
        BLACK = RED = GREEN = YELLOW = BLUE = MAGENTA = CYAN = WHITE = RESET = ''
        LIGHTBLACK_EX = LIGHTRED_EX = LIGHTGREEN_EX = LIGHTYELLOW_EX = ''
        LIGHTBLUE_EX = LIGHTMAGENTA_EX = LIGHTCYAN_EX = LIGHTWHITE_EX = ''


    class Style:
        BRIGHT = DIM = NORMAL = RESET_ALL = ''


    COLORS_AVAILABLE = False


class DatabaseManagerCLI:
    """CLI для управления базой данных"""

    def __init__(self):
        """Инициализация менеджера БД"""
        self.db = DatabaseManager()
        self.user_repo = UserRepository()
        self.conn = None

    def get_connection(self):
        """Получение соединения с БД"""
        if not self.conn:
            self.conn = sqlite3.connect(Config.DATABASE_PATH)
            self.conn.row_factory = sqlite3.Row
        return self.conn

    def close_connection(self):
        """Закрытие соединения с БД"""
        if self.conn:
            self.conn.close()
            self.conn = None

    def print_success(self, message: str):
        """Вывод сообщения об успехе"""
        if COLORS_AVAILABLE:
            print(f"{Fore.GREEN}✓ {message}{Style.RESET_ALL}")
        else:
            print(f"[OK] {message}")

    def print_error(self, message: str):
        """Вывод сообщения об ошибке"""
        if COLORS_AVAILABLE:
            print(f"{Fore.RED}✗ {message}{Style.RESET_ALL}")
        else:
            print(f"[ERROR] {message}")

    def print_warning(self, message: str):
        """Вывод предупреждения"""
        if COLORS_AVAILABLE:
            print(f"{Fore.YELLOW}⚠ {message}{Style.RESET_ALL}")
        else:
            print(f"[WARN] {message}")

    def print_info(self, message: str):
        """Вывод информационного сообщения"""
        if COLORS_AVAILABLE:
            print(f"{Fore.CYAN}ℹ {message}{Style.RESET_ALL}")
        else:
            print(f"[INFO] {message}")

    def print_header(self, title: str):
        """Вывод заголовка"""
        print("\n" + "=" * 80)
        if COLORS_AVAILABLE:
            print(f"{Fore.BLUE}{Style.BRIGHT}{title:^80}{Style.RESET_ALL}")
        else:
            print(f"{title:^80}")
        print("=" * 80)

    def print_table(self, data: List[Dict], title: str = ""):
        """
        Вывод данных в виде таблицы

        Args:
            data: Список словарей с данными
            title: Заголовок таблицы
        """
        if not data:
            self.print_warning(f"Нет данных в таблице {title}")
            return

        if title:
            print(f"\n{Fore.CYAN if COLORS_AVAILABLE else ''}{title}:{Style.RESET_ALL if COLORS_AVAILABLE else ''}")

        if TABULATE_AVAILABLE:
            # Получаем заголовки из первого элемента
            headers = list(data[0].keys())
            # Подготавливаем данные
            table_data = []
            for row in data:
                table_row = []
                for key in headers:
                    value = row[key]
                    # Форматирование специальных типов
                    if isinstance(value, datetime):
                        value = value.strftime("%Y-%m-%d %H:%M:%S")
                    elif isinstance(value, bool):
                        value = "✓" if value else "✗"
                    elif value is None:
                        value = "-"
                    table_row.append(value)
                table_data.append(table_row)

            print(tabulate(table_data, headers=headers, tablefmt="grid"))
        else:
            # Простой вывод без tabulate
            for i, row in enumerate(data, 1):
                print(f"\n  Запись {i}:")
                for key, value in row.items():
                    if isinstance(value, datetime):
                        value = value.strftime("%Y-%m-%d %H:%M:%S")
                    elif value is None:
                        value = "-"
                    print(f"    {key}: {value}")

    def get_tables(self) -> List[str]:
        """Получение списка всех таблиц в БД"""
        try:
            conn = self.get_connection()
            cursor = conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
            """)
            tables = [row['name'] for row in cursor.fetchall()]
            return tables
        except Exception as e:
            self.print_error(f"Ошибка при получении списка таблиц: {e}")
            return []

    def get_table_schema(self, table_name: str) -> List[Dict]:
        """
        Получение схемы таблицы

        Args:
            table_name: Имя таблицы

        Returns:
            Список колонок с информацией
        """
        try:
            conn = self.get_connection()
            cursor = conn.execute(f"PRAGMA table_info({table_name})")
            columns = []
            for row in cursor.fetchall():
                columns.append({
                    'cid': row['cid'],
                    'name': row['name'],
                    'type': row['type'],
                    'notnull': row['notnull'],
                    'dflt_value': row['dflt_value'],
                    'pk': row['pk']
                })
            return columns
        except Exception as e:
            self.print_error(f"Ошибка при получении схемы таблицы {table_name}: {e}")
            return []

    def get_foreign_keys(self, table_name: str) -> List[Dict]:
        """
        Получение внешних ключей таблицы

        Args:
            table_name: Имя таблицы

        Returns:
            Список внешних ключей
        """
        try:
            conn = self.get_connection()
            cursor = conn.execute(f"PRAGMA foreign_key_list({table_name})")
            fks = []
            for row in cursor.fetchall():
                fks.append({
                    'id': row['id'],
                    'seq': row['seq'],
                    'table': row['table'],
                    'from': row['from'],
                    'to': row['to'],
                    'on_update': row['on_update'],
                    'on_delete': row['on_delete']
                })
            return fks
        except Exception as e:
            self.print_error(f"Ошибка при получении внешних ключей: {e}")
            return []

    def get_table_data(self, table_name: str, limit: int = 50) -> List[Dict]:
        """
        Получение данных из таблицы

        Args:
            table_name: Имя таблицы
            limit: Максимальное количество записей

        Returns:
            Список записей
        """
        try:
            conn = self.get_connection()
            cursor = conn.execute(f"SELECT * FROM {table_name} LIMIT ?", (limit,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            self.print_error(f"Ошибка при получении данных из {table_name}: {e}")
            return []

    def get_table_count(self, table_name: str) -> int:
        """
        Получение количества записей в таблице

        Args:
            table_name: Имя таблицы

        Returns:
            Количество записей
        """
        try:
            conn = self.get_connection()
            cursor = conn.execute(f"SELECT COUNT(*) as count FROM {table_name}")
            return cursor.fetchone()['count']
        except Exception as e:
            self.print_error(f"Ошибка при подсчете записей в {table_name}: {e}")
            return 0

    # ==================== МЕТОДЫ ДЛЯ ДОБАВЛЕНИЯ ПОЛЬЗОВАТЕЛЕЙ ====================

    def add_user_interactive(self):
        """Интерактивное добавление пользователя"""
        self.print_header("ДОБАВЛЕНИЕ НОВОГО ПОЛЬЗОВАТЕЛЯ")

        print("\nВведите данные нового пользователя:")

        # Ввод логина
        while True:
            username = input("Логин (3-20 символов, буквы/цифры/_): ").strip()
            if not username:
                self.print_error("Логин обязателен")
                continue
            if len(username) < 3 or len(username) > 20:
                self.print_error("Логин должен быть от 3 до 20 символов")
                continue
            if not username.replace('_', '').isalnum():
                self.print_error("Логин может содержать только буквы, цифры и _")
                continue

            # Проверка уникальности
            existing = self.user_repo.find_by_username(username)
            if existing:
                self.print_error(f"Пользователь с логином '{username}' уже существует")
                continue
            break

        # Ввод email
        while True:
            email = input("Email: ").strip()
            if not email:
                self.print_error("Email обязателен")
                continue
            if '@' not in email or '.' not in email:
                self.print_error("Введите корректный email")
                continue
            break

        # Ввод ФИО
        while True:
            full_name = input("ФИО (полностью): ").strip()
            if not full_name:
                self.print_error("ФИО обязательно")
                continue
            if len(full_name.split()) < 2:
                self.print_error("Введите полное имя и фамилию")
                continue
            break

        # Ввод отдела
        department = input("Отдел/подразделение: ").strip()
        if not department:
            department = "Не указан"

        # Выбор роли
        print("\nВыберите роль:")
        roles = [
            ('1', 'requester', 'Заявитель'),
            ('2', 'executor', 'Исполнитель'),
            ('3', 'admin', 'Администратор')
        ]
        for key, code, name in roles:
            print(f"  {key}. {name}")

        while True:
            role_choice = input("Номер роли (1-3): ").strip()
            if role_choice in ['1', '2', '3']:
                role = roles[int(role_choice) - 1][1]
                break
            self.print_error("Выберите 1, 2 или 3")

        # Ввод телефона (опционально)
        phone = input("Телефон (опционально, Enter для пропуска): ").strip()
        if not phone:
            phone = None

        # Подтверждение
        print("\n" + "-" * 50)
        print("Проверьте введенные данные:")
        print(f"  Логин:     {username}")
        print(f"  Email:     {email}")
        print(f"  ФИО:       {full_name}")
        print(f"  Отдел:     {department}")
        print(f"  Роль:      {role}")
        print(f"  Телефон:   {phone or 'не указан'}")
        print("-" * 50)

        confirm = input("\nСохранить пользователя? (д/н): ").strip().lower()
        if confirm in ['д', 'да', 'y', 'yes']:
            self._save_user(username, email, full_name, department, role, phone)
        else:
            self.print_warning("Добавление отменено")

    def add_user_batch(self, users_data: List[Dict]):
        """
        Пакетное добавление пользователей

        Args:
            users_data: Список словарей с данными пользователей
        """
        self.print_header("ПАКЕТНОЕ ДОБАВЛЕНИЕ ПОЛЬЗОВАТЕЛЕЙ")

        success = 0
        failed = 0

        for i, user_data in enumerate(users_data, 1):
            try:
                print(f"\n{i}. Обработка: {user_data.get('username', 'N/A')}")

                # Проверка обязательных полей
                required = ['username', 'email', 'full_name']
                missing = [f for f in required if f not in user_data]
                if missing:
                    raise ValueError(f"Отсутствуют поля: {missing}")

                # Проверка уникальности
                existing = self.user_repo.find_by_username(user_data['username'])
                if existing:
                    raise ValueError(f"Логин '{user_data['username']}' уже существует")

                # Создание пользователя
                user = User(
                    username=user_data['username'],
                    email=user_data['email'],
                    full_name=user_data['full_name'],
                    department=user_data.get('department', 'Не указан'),
                    role=user_data.get('role', 'requester'),
                    phone=user_data.get('phone'),
                    telegram_id=user_data.get('telegram_id'),
                    is_active=user_data.get('is_active', True),
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )

                user_id = self.user_repo.create(user)
                if user_id:
                    self.print_success(f"Пользователь {user.username} создан (ID: {user_id})")
                    success += 1
                else:
                    raise ValueError("Ошибка при сохранении в БД")

            except Exception as e:
                self.print_error(f"Ошибка: {e}")
                failed += 1

        print(f"\nРезультат: успешно {success}, ошибок {failed}")

    def _save_user(self, username: str, email: str, full_name: str,
                   department: str, role: str, phone: Optional[str] = None):
        """
        Сохранение пользователя в БД

        Args:
            username: Логин
            email: Email
            full_name: ФИО
            department: Отдел
            role: Роль
            phone: Телефон
        """
        try:
            user = User(
                username=username,
                email=email,
                full_name=full_name,
                department=department,
                role=role,
                phone=phone,
                is_active=True,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )

            user_id = self.user_repo.create(user)

            if user_id:
                self.print_success(f"Пользователь {username} успешно создан! (ID: {user_id})")
            else:
                self.print_error("Не удалось создать пользователя")

        except Exception as e:
            self.print_error(f"Ошибка при сохранении: {e}")

    # ==================== МЕТОДЫ ДЛЯ ВИЗУАЛИЗАЦИИ ====================

    def show_database_schema(self):
        """Отображение схемы базы данных"""
        self.print_header("СХЕМА БАЗЫ ДАННЫХ")

        tables = self.get_tables()

        for table_name in tables:
            print(
                f"\n{Fore.YELLOW if COLORS_AVAILABLE else ''}📋 Таблица: {table_name}{Style.RESET_ALL if COLORS_AVAILABLE else ''}")
            print("-" * 50)

            # Получаем схему
            columns = self.get_table_schema(table_name)
            if columns:
                col_data = []
                for col in columns:
                    col_data.append({
                        'Поле': col['name'],
                        'Тип': col['type'],
                        'PK': '✓' if col['pk'] else '',
                        'NotNull': '✓' if col['notnull'] else '',
                        'Default': col['dflt_value'] or '-'
                    })
                self.print_table(col_data, "Колонки")

            # Получаем внешние ключи
            fks = self.get_foreign_keys(table_name)
            if fks:
                fk_data = []
                for fk in fks:
                    fk_data.append({
                        'Колонка': fk['from'],
                        'Ссылка': f"{fk['table']}({fk['to']})",
                        'On Update': fk['on_update'],
                        'On Delete': fk['on_delete']
                    })
                self.print_table(fk_data, "Внешние ключи")

    def show_table_data(self, table_name: str, limit: int = 50):
        """
        Отображение данных таблицы

        Args:
            table_name: Имя таблицы
            limit: Лимит записей
        """
        tables = self.get_tables()

        if table_name == 'all':
            for tbl in tables:
                self._show_single_table(tbl, limit)
        elif table_name in tables:
            self._show_single_table(table_name, limit)
        else:
            self.print_error(f"Таблица '{table_name}' не найдена")
            self.print_info(f"Доступные таблицы: {', '.join(tables)}")

    def _show_single_table(self, table_name: str, limit: int):
        """
        Отображение одной таблицы

        Args:
            table_name: Имя таблицы
            limit: Лимит записей
        """
        count = self.get_table_count(table_name)

        print(
            f"\n{Fore.YELLOW if COLORS_AVAILABLE else ''}📊 Таблица: {table_name} (всего записей: {count}){Style.RESET_ALL if COLORS_AVAILABLE else ''}")

        if count == 0:
            self.print_warning("Таблица пуста")
            return

        data = self.get_table_data(table_name, limit)

        if data:
            if count > limit:
                self.print_info(f"Показано {limit} из {count} записей")
            self.print_table(data)

    def show_database_stats(self):
        """Отображение статистики по БД"""
        self.print_header("СТАТИСТИКА БАЗЫ ДАННЫХ")

        tables = self.get_tables()
        total_records = 0

        stats = []
        for table in tables:
            count = self.get_table_count(table)
            total_records += count

            # Получаем размер таблицы (приблизительно)
            try:
                conn = self.get_connection()
                cursor = conn.execute(
                    f"SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
                size_info = cursor.fetchone()
                size = size_info[0] if size_info else 0
                size_mb = size / (1024 * 1024)
            except:
                size_mb = 0

            stats.append({
                'Таблица': table,
                'Записей': count,
                'Размер (MB)': round(size_mb, 2)
            })

        stats.append({
            'Таблица': 'ВСЕГО',
            'Записей': total_records,
            'Размер (MB)': sum(s['Размер (MB)'] for s in stats)
        })

        self.print_table(stats, "Статистика таблиц")

    def show_relationships(self):
        """Отображение связей между таблицами"""
        self.print_header("СВЯЗИ МЕЖДУ ТАБЛИЦАМИ")

        tables = self.get_tables()

        for table in tables:
            fks = self.get_foreign_keys(table)
            if fks:
                print(
                    f"\n{Fore.CYAN if COLORS_AVAILABLE else ''}{table} →{Style.RESET_ALL if COLORS_AVAILABLE else ''}")
                for fk in fks:
                    print(f"  {fk['from']} → {fk['table']}.{fk['to']}")

    def interactive_menu(self):
        """Интерактивное меню"""
        while True:
            self.print_header("УПРАВЛЕНИЕ БАЗОЙ ДАННЫХ")

            print("\nДоступные команды:")
            print("  1. Показать все таблицы")
            print("  2. Показать схему БД")
            print("  3. Показать данные таблицы")
            print("  4. Показать статистику")
            print("  5. Показать связи")
            print("  6. Добавить пользователя")
            print("  7. Пакетное добавление пользователей")
            print("  0. Выход")

            choice = input("\nВыберите действие: ").strip()

            if choice == '0':
                break
            elif choice == '1':
                tables = self.get_tables()
                self.print_info(f"Таблицы: {', '.join(tables)}")
            elif choice == '2':
                self.show_database_schema()
            elif choice == '3':
                tables = self.get_tables()
                print(f"\nДоступные таблицы: {', '.join(tables)}")
                table = input("Введите имя таблицы (или 'all'): ").strip()
                if table:
                    self.show_table_data(table)
            elif choice == '4':
                self.show_database_stats()
            elif choice == '5':
                self.show_relationships()
            elif choice == '6':
                self.add_user_interactive()
            elif choice == '7':
                self.batch_add_menu()
            else:
                self.print_error("Неверный выбор")

            if choice != '0':
                input("\nНажмите Enter для продолжения...")

    def batch_add_menu(self):
        """Меню пакетного добавления пользователей"""
        self.print_header("ПАКЕТНОЕ ДОБАВЛЕНИЕ ПОЛЬЗОВАТЕЛЕЙ")

        print("\nПример данных:")
        print("""
        users_data = [
            {
                'username': 'petrov',
                'email': 'petrov@synergy.ru',
                'full_name': 'Петров Петр Петрович',
                'department': 'Деканат',
                'role': 'requester',
                'phone': '+79001234567'
            },
            {
                'username': 'sidorov',
                'email': 'sidorov@synergy.ru',
                'full_name': 'Сидоров Сидор Сидорович',
                'department': 'IT-отдел',
                'role': 'executor'
            }
        ]
        """)

        print("\nВарианты:")
        print("  1. Ввести данные вручную")
        print("  2. Загрузить из файла")
        print("  0. Назад")

        choice = input("\nВыберите вариант: ").strip()

        if choice == '1':
            self.manual_batch_add()
        elif choice == '2':
            self.load_from_file()

    def manual_batch_add(self):
        """Ручной ввод нескольких пользователей"""
        users = []

        print("\nВведите данные пользователей (пустой логин для завершения):")

        while True:
            print(f"\n--- Пользователь {len(users) + 1} ---")

            username = input("Логин (Enter для завершения): ").strip()
            if not username:
                break

            email = input("Email: ").strip()
            if not email:
                self.print_error("Email обязателен")
                continue

            full_name = input("ФИО: ").strip()
            if not full_name:
                self.print_error("ФИО обязательно")
                continue

            department = input("Отдел: ").strip()
            if not department:
                department = "Не указан"

            print("Роль: 1 - Заявитель, 2 - Исполнитель, 3 - Администратор")
            role_choice = input("Номер роли (1-3): ").strip()
            if role_choice == '1':
                role = 'requester'
            elif role_choice == '2':
                role = 'executor'
            elif role_choice == '3':
                role = 'admin'
            else:
                role = 'requester'

            phone = input("Телефон (опционально): ").strip() or None

            users.append({
                'username': username,
                'email': email,
                'full_name': full_name,
                'department': department,
                'role': role,
                'phone': phone
            })

            print(f"✓ Пользователь {username} добавлен в список")

        if users:
            print(f"\nВсего пользователей для добавления: {len(users)}")
            confirm = input("Добавить всех? (д/н): ").strip().lower()
            if confirm in ['д', 'да', 'y', 'yes']:
                self.add_user_batch(users)

    def load_from_file(self):
        """Загрузка пользователей из файла"""
        filename = input("Введите имя файла (users.json): ").strip()
        if not filename:
            filename = "users.json"

        try:
            import json
            with open(filename, 'r', encoding='utf-8') as f:
                users = json.load(f)

            if isinstance(users, dict) and 'users' in users:
                users = users['users']

            if isinstance(users, list):
                self.add_user_batch(users)
            else:
                self.print_error("Файл должен содержать список пользователей")

        except FileNotFoundError:
            self.print_error(f"Файл {filename} не найден")
        except json.JSONDecodeError:
            self.print_error(f"Ошибка парсинга JSON в файле {filename}")
        except Exception as e:
            self.print_error(f"Ошибка при загрузке файла: {e}")


def main():
    """Главная функция"""
    parser = argparse.ArgumentParser(description='Управление базой данных IT-заявок')
    parser.add_argument('--action', '-a', choices=['show', 'add', 'schema', 'stats', 'interactive'],
                        help='Действие: show - показать таблицы, add - добавить пользователя, '
                             'schema - показать схему, stats - статистика, interactive - интерактивный режим')
    parser.add_argument('--table', '-t', help='Имя таблицы для просмотра')
    parser.add_argument('--limit', '-l', type=int, default=50, help='Лимит записей')
    parser.add_argument('--file', '-f', help='Файл с данными для пакетного добавления')

    args = parser.parse_args()

    cli = DatabaseManagerCLI()

    try:
        if args.action == 'interactive' or not args.action:
            cli.interactive_menu()
        elif args.action == 'show':
            if args.table:
                cli.show_table_data(args.table, args.limit)
            else:
                tables = cli.get_tables()
                print(f"Доступные таблицы: {', '.join(tables)}")
        elif args.action == 'schema':
            cli.show_database_schema()
        elif args.action == 'stats':
            cli.show_database_stats()
        elif args.action == 'add':
            if args.file:
                try:
                    import json
                    with open(args.file, 'r', encoding='utf-8') as f:
                        users = json.load(f)
                    if isinstance(users, dict) and 'users' in users:
                        users = users['users']
                    cli.add_user_batch(users)
                except Exception as e:
                    print(f"Ошибка при загрузке файла: {e}")
            else:
                cli.add_user_interactive()

    finally:
        cli.close_connection()


if __name__ == "__main__":
    main()