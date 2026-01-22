"""
Простой тест импортов Smart Agent без зависимостей
"""

import pytest
import sys
from pathlib import Path

# Добавляем src в путь для импорта
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))


class TestSmartAgentSimple:
    """Простые тесты Smart Agent без зависимостей"""

    def test_imports(self):
        """Тест базовых импортов Smart Agent"""
        # Проверяем импорт из __init__.py
        from src.agents import create_smart_agent
        assert create_smart_agent is not None
        assert callable(create_smart_agent)

        # Проверяем импорт инструментов
        from src.tools.learning_tool import LearningTool
        assert LearningTool is not None

        from src.tools.context_analyzer_tool import ContextAnalyzerTool
        assert ContextAnalyzerTool is not None

        # Проверяем импорт smart_agent модуля
        import src.agents.smart_agent as smart_agent_module
        assert smart_agent_module is not None

    def test_learning_tool_basic(self):
        """Тест базовой функциональности LearningTool без зависимостей"""
        from src.tools.learning_tool import LearningTool

        # Создаем инструмент
        tool = LearningTool(experience_dir="test_smart_experience")

        # Проверяем создание директории опыта
        assert tool.experience_dir.exists()

        # Проверяем создание файла опыта
        assert tool.experience_file.exists()

        # Проверяем базовые атрибуты
        assert tool.name == "LearningTool"
        assert "обучения" in tool.description.lower()

    def test_context_analyzer_tool_basic(self):
        """Тест базовой функциональности ContextAnalyzerTool без зависимостей"""
        from src.tools.context_analyzer_tool import ContextAnalyzerTool

        # Создаем инструмент
        tool = ContextAnalyzerTool(project_dir=".")

        # Проверяем базовые атрибуты
        assert tool.name == "ContextAnalyzerTool"
        assert "анализа контекста" in tool.description.lower()
        assert tool.project_dir == Path(".")

        # Проверяем поддерживаемые расширения
        assert ".py" in tool.supported_extensions
        assert ".md" in tool.supported_extensions