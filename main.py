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
    print("✓ База данных готова")

    # Запуск CLI интерфейса
    app = CLIApp()
    app.run()


if __name__ == "__main__":
    main()
