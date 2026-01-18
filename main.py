"""
Точка входа в Code Agent Server

Запуск сервера агента:
    python main.py
"""

from src.server import CodeAgentServer


def main():
    """Главная функция для запуска сервера"""
    server = CodeAgentServer()
    server.start()


if __name__ == "__main__":
    main()
