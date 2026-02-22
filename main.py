"""Главный файл приложения - точка входа"""

import sys
import os

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.db_manager import DatabaseManager
from views.cli_app import CLIApp


def main():
    """Основная функция"""
    print("=" * 60)
    print("   Система управления IT-заявками Университета 'Синергия'")
    print("=" * 60)

    # Инициализация БД
    print("\nИнициализация базы данных...")
    db = DatabaseManager()
    db.execute_insert("CREATE TABLE IF NOT EXISTS users (name TEXT, role TEXT, password TEXT);")
    db.execute_insert("CREATE TABLE IF NOT EXISTS tickets (id INTEGER PRIMARY KEY, title TEXT, description TEXT, status TEXT, creator TEXT, assignee TEXT, created_at TEXT);")
    db.execute_insert("CREATE TABLE IF NOT EXISTS comments (id INTEGER PRIMARY KEY, ticket_id INTEGER, author TEXT, content TEXT, created_at TEXT);")

    users_ = db.execute_query("SELECT name FROM sqlite_master WHERE type='table' AND name='users';")
    print(f"@✓ Пользователи {users_}")
    # if users_ == 0:
    #     db.execute_insert("INSERT INTO users (name, role, password) VALUES ('admin', 'admin', 'adminpass');")
    #     print("✓ Администратор создан: admin/adminpass")

    print("✓ База данных готова")

    # Запуск CLI интерфейса
    app = CLIApp()
    app.run()


if __name__ == "__main__":
    main()
