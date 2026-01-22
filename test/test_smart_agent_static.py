"""
Статические тесты для Smart Agent и его инструментов
"""

import pytest
import sys
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock


class TestSmartAgentImports:
    """Тесты импортов Smart Agent"""

    def test_smart_agent_import(self):
        """Тест импорта SmartAgent"""
        try:
            from src.agents.smart_agent import create_smart_agent
            assert create_smart_agent is not None
        except ImportError as e:
            pytest.fail(f"Не удалось импортировать SmartAgent: {e}")

    def test_learning_tool_import(self):
        """Тест импорта LearningTool"""
        try:
            from src.tools.learning_tool import LearningTool
            assert LearningTool is not None
        except ImportError as e:
            pytest.fail(f"Не удалось импортировать LearningTool: {e}")

    def test_context_analyzer_import(self):
        """Тест импорта ContextAnalyzerTool"""
        try:
            from src.tools.context_analyzer_tool import ContextAnalyzerTool
            assert ContextAnalyzerTool is not None
        except ImportError as e:
            pytest.fail(f"Не удалось импортировать ContextAnalyzerTool: {e}")

    def test_docker_checker_import(self):
        """Тест импорта DockerChecker"""
        try:
            from src.tools.docker_utils import DockerChecker
            assert DockerChecker is not None
        except ImportError as e:
            pytest.fail(f"Не удалось импортировать DockerChecker: {e}")


class TestSmartAgentStructure:
    """Тесты структуры классов Smart Agent"""

    def test_learning_tool_class_structure(self):
        """Тест структуры класса LearningTool"""
        from src.tools.learning_tool import LearningTool

        # Создаем экземпляр для проверки атрибутов
        tool = LearningTool()

        # Проверяем наличие основных атрибутов
        assert hasattr(tool, 'name')
        assert hasattr(tool, 'description')
        assert hasattr(tool, 'experience_dir')
        assert hasattr(tool, 'max_experience_tasks')

        # Проверяем значения по умолчанию
        assert tool.name == "LearningTool"
        # Проверяем что description содержит информацию об инструменте
        assert len(tool.description) > 0

    def test_context_analyzer_tool_class_structure(self):
        """Тест структуры класса ContextAnalyzerTool"""
        from src.tools.context_analyzer_tool import ContextAnalyzerTool

        # Создаем экземпляр для проверки атрибутов
        tool = ContextAnalyzerTool()

        # Проверяем наличие основных атрибутов
        assert hasattr(tool, 'name')
        assert hasattr(tool, 'description')
        assert hasattr(tool, 'project_dir')
        assert hasattr(tool, 'docs_dir')

        # Проверяем значения по умолчанию
        assert tool.name == "ContextAnalyzerTool"
        # Проверяем что description содержит информацию об инструменте
        assert len(tool.description) > 0

    def test_docker_checker_class_structure(self):
        """Тест структуры класса DockerChecker"""
        from src.tools.docker_utils import DockerChecker

        # Проверяем наличие основных методов
        assert hasattr(DockerChecker, 'is_docker_available')
        assert hasattr(DockerChecker, 'get_docker_version')
        assert hasattr(DockerChecker, 'check_docker_permissions')
        assert hasattr(DockerChecker, 'get_running_containers')
        assert hasattr(DockerChecker, 'is_container_running')

        # Проверяем что методы callable
        assert callable(DockerChecker.is_docker_available)
        assert callable(DockerChecker.get_docker_version)


class TestSmartAgentInitialization:
    """Тесты инициализации компонентов Smart Agent"""

    def test_learning_tool_initialization(self, tmp_path):
        """Тест инициализации LearningTool"""
        from src.tools.learning_tool import LearningTool

        experience_dir = tmp_path / "experience"
        tool = LearningTool(experience_dir=str(experience_dir), max_experience_tasks=50)

        assert tool.experience_dir == experience_dir
        assert tool.max_experience_tasks == 50
        assert tool.experience_file == experience_dir / "experience.json"

        # Проверяем создание директории
        assert experience_dir.exists()
        assert tool.experience_file.exists()

    def test_context_analyzer_tool_initialization(self, tmp_path):
        """Тест инициализации ContextAnalyzerTool"""
        from src.tools.context_analyzer_tool import ContextAnalyzerTool

        project_dir = tmp_path / "project"
        docs_dir = project_dir / "docs"
        project_dir.mkdir()
        docs_dir.mkdir()

        tool = ContextAnalyzerTool(
            project_dir=str(project_dir),
            docs_dir=str(docs_dir),
            max_file_size=500000
        )

        assert str(tool.project_dir) == str(project_dir)
        assert str(tool.docs_dir) == str(docs_dir)
        assert tool.max_file_size == 500000

    def test_docker_manager_initialization(self):
        """Тест инициализации DockerManager"""
        from src.tools.docker_utils import DockerManager

        manager = DockerManager(
            image_name="test-image:latest",
            container_name="test-container"
        )

        assert manager.image_name == "test-image:latest"
        assert manager.container_name == "test-container"


class TestSmartAgentMethodsExistence:
    """Тесты наличия методов в классах"""

    def test_learning_tool_methods(self):
        """Тест наличия методов LearningTool"""
        from src.tools.learning_tool import LearningTool

        tool = LearningTool()

        # Проверяем наличие основных методов
        assert hasattr(tool, '_run')
        assert hasattr(tool, 'save_task_experience')
        assert hasattr(tool, 'find_similar_tasks')
        assert hasattr(tool, 'get_recommendations')
        assert hasattr(tool, 'get_statistics')

    def test_context_analyzer_tool_methods(self):
        """Тест наличия методов ContextAnalyzerTool"""
        from src.tools.context_analyzer_tool import ContextAnalyzerTool

        tool = ContextAnalyzerTool()

        # Проверяем наличие основных методов
        assert hasattr(tool, '_run')
        assert hasattr(tool, 'analyze_project_structure')
        assert hasattr(tool, 'find_file_dependencies')
        assert hasattr(tool, 'get_task_context')
        assert hasattr(tool, 'analyze_component')
        assert hasattr(tool, 'find_related_files')

    def test_docker_manager_methods(self):
        """Тест наличия методов DockerManager"""
        from src.tools.docker_utils import DockerManager

        manager = DockerManager()

        # Проверяем наличие основных методов
        assert hasattr(manager, 'start_container')
        assert hasattr(manager, 'stop_container')
        assert hasattr(manager, 'execute_command')


class TestSmartAgentConstants:
    """Тесты констант и настроек по умолчанию"""

    def test_default_values(self):
        """Тест значений по умолчанию"""
        from src.tools.learning_tool import LearningTool
        from src.tools.context_analyzer_tool import ContextAnalyzerTool
        from src.tools.docker_utils import DockerManager

        # LearningTool
        tool = LearningTool()
        assert tool.experience_dir == Path("smart_experience")
        assert tool.max_experience_tasks == 1000

        # ContextAnalyzerTool
        tool = ContextAnalyzerTool()
        assert tool.project_dir == Path(".")
        assert tool.docs_dir == tool.project_dir / "docs"
        assert tool.max_file_size == 1000000
        assert ".py" in tool.supported_extensions
        assert ".md" in tool.supported_extensions

        # DockerManager
        manager = DockerManager()
        assert manager.image_name == "cursor-agent:latest"
        assert manager.container_name == "cursor-agent-life"


class TestSmartAgentErrorHandling:
    """Тесты обработки ошибок"""

    def test_learning_tool_with_invalid_path(self):
        """Тест LearningTool с некорректным путем"""
        from src.tools.learning_tool import LearningTool

        # Создаем инструмент с путем к несуществующей директории
        tool = LearningTool(experience_dir="/nonexistent/path")

        # Проверяем что директория будет создана
        assert tool.experience_dir.exists()
        assert tool.experience_file.exists()

    def test_context_analyzer_tool_with_invalid_path(self):
        """Тест ContextAnalyzerTool с некорректным путем"""
        from src.tools.context_analyzer_tool import ContextAnalyzerTool

        # Создаем инструмент с путем к несуществующей директории
        tool = ContextAnalyzerTool(project_dir="/nonexistent/project")

        # Проверяем основные атрибуты
        assert str(tool.project_dir) == "/nonexistent/project"
        assert str(tool.docs_dir) == "/nonexistent/project/docs"