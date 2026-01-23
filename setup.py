"""
Setup script for Code Agent project
"""

from setuptools import setup, find_packages

setup(
    name="code-agent",
    version="0.1.0",
    description="Code Agent на базе CrewAI для автоматизации работы с проектами",
    author="Code Agent Team",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.8",
    install_requires=[
        # CrewAI framework (основной фреймворк)
        "crewai>=0.1.0,<2.0.0",
        "crewai-tools>=0.1.0,<2.0.0",

        # YAML и конфигурация
        "pyyaml>=6.0,<7.0",

        # Переменные окружения
        "python-dotenv>=1.0.0,<1.2.0",

        # Для работы с Cursor IDE (UI автоматизация)
        "pyautogui>=0.9.54,<1.0.0",
        "pytesseract>=0.3.10,<0.4.0",
        "Pillow>=10.0.0,<11.0.0",
        "opencv-python>=4.8.0,<5.0.0",
        "mss>=9.0.1,<10.0.0",
        "pygetwindow>=0.0.9,<1.0.0",

        # Для работы с файлами и репортами
        "watchdog>=3.0.0,<5.0.0",
        "aiofiles>=23.2.0,<24.0.0",

        # Для работы с Git
        "GitPython>=3.1.40,<4.0.0",

        # Для улучшенного логирования
        "colorlog>=6.8.0,<7.0.0",
        "rich>=13.7.0,<14.0.0",

        # Для HTTP сервера
        "flask>=2.3.0,<3.1.0",
    ],
    extras_require={
        "dev": [
            # Тестирование
            "pytest>=7.4.0,<8.0.0",
            "pytest-cov>=4.1.0,<5.0.0",
            "pytest-mock>=3.11.1,<4.0.0",
            "pytest-asyncio>=0.21.0,<1.0.0",
            "pytest-timeout>=2.1.0,<3.0.0",
            "pytest-xdist>=3.3.0,<4.0.0",
            "pytest-sugar>=0.9.7,<1.0.0",

            # Форматирование и линтинг
            "black>=23.0.0,<24.0.0",
            "ruff>=0.1.0,<1.0.0",
            "mypy>=1.0.0,<2.0.0",

            # Анализ качества кода
            "radon>=6.0.0,<7.0.0",
            "bandit>=1.7.0,<2.0.0",
        ],
        "test": [
            # Тестирование
            "pytest>=7.4.0,<8.0.0",
            "pytest-cov>=4.1.0,<5.0.0",
            "pytest-mock>=3.11.1,<4.0.0",
            "pytest-asyncio>=0.21.0,<1.0.0",
            "pytest-timeout>=2.1.0,<3.0.0",
            "pytest-xdist>=3.3.0,<4.0.0",
            "pytest-sugar>=0.9.7,<1.0.0",
            "pytest-html>=3.2.0,<4.0.0",

            # Покрытие кода
            "coverage>=7.2.0,<8.0.0",

            # Моки и фикстуры
            "responses>=0.23.0,<1.0.0",
            "faker>=19.0.0,<20.0.0",
        ],
    },
)