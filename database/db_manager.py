"""Менеджер для работы с LiteSQL"""

import sqlite3
from contextlib import contextmanager
from typing import List, Dict, Any
import os

from config import Config
from database.models import SCHEMA


class DatabaseManager:
    """Синглтон для управления подключением к БД"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        # Создаем директорию для БД, если её нет
        os.makedirs(os.path.dirname(Config.DATABASE_PATH), exist_ok=True)

        self.connection = None
        self._init_database()
        self._initialized = True

    def _init_database(self):
        """Инициализация базы данных"""
        try:
            with self.get_connection() as conn:
                conn.executescript(SCHEMA)
                conn.commit()
                self._init_default_data(conn)
        except Exception as e:
            print(f"Ошибка инициализации БД: {e}")

    def _init_default_data(self, conn):
        """Заполнение справочников начальными данными"""
        cursor = conn.cursor()

        # Проверяем, есть ли уже статусы
        cursor.execute("SELECT COUNT(*) FROM statuses")
        if cursor.fetchone()[0] == 0:
            statuses = [
                (1, 'Новая', 'new', '#3498db', 1, 0),
                (2, 'В работе', 'in_progress', '#f39c12', 2, 0),
                (3, 'Решена', 'resolved', '#2ecc71', 3, 1),
                (4, 'Закрыта', 'closed', '#95a5a6', 4, 1),
                (5, 'Отклонена', 'rejected', '#e74c3c', 5, 1)
            ]
            cursor.executemany(
                "INSERT INTO statuses (id, name, code, color, 'order', is_final) VALUES (?, ?, ?, ?, ?, ?)",
                statuses
            )

        # Проверяем, есть ли уже категории
        cursor.execute("SELECT COUNT(*) FROM categories")
        if cursor.fetchone()[0] == 0:
            categories = [
                ('Оборудование', 'Проблемы с компьютером, принтером и т.д.', 24, 1),
                ('Программное обеспечение', 'Проблемы с установкой и работой ПО', 24, 1),
                ('Доступы', 'Выдача прав, создание учетных записей', 48, 1),
                ('Сеть', 'Проблемы с интернетом, Wi-Fi', 8, 1),
                ('Прочее', 'Другие вопросы', 72, 1)
            ]
            cursor.executemany(
                "INSERT INTO categories (name, description, sla_hours, is_active) VALUES (?, ?, ?, ?)",
                categories
            )

        conn.commit()

    @contextmanager
    def get_connection(self):
        """Контекстный менеджер для подключения к БД"""
        conn = sqlite3.connect(Config.DATABASE_PATH)
        conn.row_factory = sqlite3.Row  # Возвращаем строки как словари
        try:
            yield conn
        finally:
            conn.close()

    def execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Выполнение запроса с возвратом результатов"""
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def execute_insert(self, query: str, params: tuple = ()) -> int:
        """Выполнение вставки с возвратом ID"""
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            conn.commit()
            return cursor.lastrowid

    def execute_update(self, query: str, params: tuple = ()) -> int:
        """Выполнение обновления с возвратом количества измененных строк"""
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            conn.commit()
            return cursor.rowcount


if __name__ == "__main__":
    if not os.path.exists(Config.DATABASE_PATH):
        print("База данных создана")
    else:
        print("База данных уже существует")

    db_manager = DatabaseManager()
    # Проверяем, что таблица users существует
    users = db_manager.execute_query("SELECT * FROM users")
    print(f"{users}")
    # # Добавляем админа по умолчанию
    # db_manager.execute_insert("INSERT INTO users (username, password) VALUES (?, ?)", ("admin", "adminpass"))
