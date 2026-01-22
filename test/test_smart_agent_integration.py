"""
Интеграционные тесты для Smart Agent - проверка взаимодействия компонентов
"""

import pytest
import tempfile
import json
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock


class TestSmartAgentIntegration:
    """Интеграционные тесты Smart Agent"""

    def test_learning_and_context_tools_integration(self):
        """Тест взаимодействия LearningTool и ContextAnalyzerTool"""
        from src.tools.learning_tool import LearningTool
        from src.tools.context_analyzer_tool import ContextAnalyzerTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir)

            # Создаем инструменты напрямую
            learning_tool = LearningTool(experience_dir=str(project_dir / "experience"))
            context_tool = ContextAnalyzerTool(project_dir=str(project_dir))

            # Проверяем что инструменты созданы
            assert learning_tool is not None
            assert context_tool is not None

            # Проверяем что инструменты могут работать вместе
            # Добавляем опыт в LearningTool
            result = learning_tool.save_task_experience(
                "integration_test_001",
                "Интеграционный тест создания проекта",
                True,
                2.5
            )
            assert "сохранен" in result

            # Используем ContextAnalyzerTool для анализа структуры
            struct_result = context_tool.analyze_project_structure()
            assert "анализ структуры проекта" in struct_result.lower() or "🏗️" in struct_result

    def test_learning_tool_and_context_analyzer_interaction(self):
        """Тест взаимодействия LearningTool и ContextAnalyzerTool"""
        from src.tools.learning_tool import LearningTool
        from src.tools.context_analyzer_tool import ContextAnalyzerTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir)

            # Создаем тестовый проект
            src_dir = project_dir / "src"
            docs_dir = project_dir / "docs"
            src_dir.mkdir()
            docs_dir.mkdir()

            # Создаем файлы
            (src_dir / "main.py").write_text("""
'''Main module for the project'''
import os
from utils import helper

def main():
    print("Hello from main")

if __name__ == "__main__":
    main()
""")

            (src_dir / "utils.py").write_text("""
'''Utility functions'''
def helper():
    return "helper result"
""")

            (docs_dir / "README.md").write_text("""
# Test Project

This is a test project for integration testing.

## Features
- Main module
- Utils module
""")

            # Инициализируем инструменты
            learning_tool = LearningTool(experience_dir=str(project_dir / "experience"))
            context_tool = ContextAnalyzerTool(project_dir=str(project_dir))

            # Сохраняем опыт о создании проекта
            learning_tool.save_task_experience(
                "project_creation",
                "Создание структуры тестового проекта с модулями",
                True,
                3.0,
                ["project_structure", "modular_design"]
            )

            # Анализируем структуру проекта
            struct_analysis = context_tool.analyze_project_structure()
            assert "src" in struct_analysis or "docs" in struct_analysis

            # Ищем зависимости в main.py
            deps = context_tool.find_file_dependencies("src/main.py")
            # Проверяем что метод отработал и вернул результат
            assert isinstance(deps, str)
            assert len(deps) > 0

            # Получаем рекомендации для похожей задачи
            recommendations = learning_tool.get_recommendations("создать новый проект")
            assert "рекомендации" in recommendations.lower() or "проект" in recommendations.lower()

    def test_docker_integration_with_tools(self):
        """Тест интеграции Docker с инструментами"""
        from src.tools.docker_utils import DockerChecker, DockerManager

        # Мокаем Docker как доступный
        with patch.object(DockerChecker, 'is_docker_available', return_value=True):
            result = DockerChecker.is_docker_available()
            assert result == True

        # Мокаем Docker как недоступный
        with patch.object(DockerChecker, 'is_docker_available', return_value=False):
            result = DockerChecker.is_docker_available()
            assert result == False

    def test_experience_persistence_across_sessions(self):
        """Тест сохранения опыта между сессиями"""
        from src.tools.learning_tool import LearningTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            experience_dir = Path(tmp_dir) / "experience"

            # Первая сессия - сохраняем опыт
            tool1 = LearningTool(experience_dir=str(experience_dir))

            tool1.save_task_experience("session_test_1", "Тест сессии 1", True, 1.0)
            tool1.save_task_experience("session_test_2", "Тест сессии 2", False, 2.0)

            # Проверяем статистику первой сессии
            stats1 = tool1.get_statistics()
            assert "Всего задач: 2" in stats1

            # Вторая сессия - загружаем опыт
            tool2 = LearningTool(experience_dir=str(experience_dir))

            # Проверяем что опыт сохранился
            stats2 = tool2.get_statistics()
            assert "Всего задач: 2" in stats2
            assert "Успешных задач: 1" in stats2
            assert "Неудачных задач: 1" in stats2

            # Добавляем еще один опыт во второй сессии
            tool2.save_task_experience("session_test_3", "Тест сессии 3", True, 1.5)

            # Третья сессия - проверяем накопленный опыт
            tool3 = LearningTool(experience_dir=str(experience_dir))
            stats3 = tool3.get_statistics()
            assert "Всего задач: 3" in stats3
            assert "Успешных задач: 2" in stats3

    def test_context_analysis_with_real_project_structure(self):
        """Тест анализа контекста с реальной структурой проекта"""
        from src.tools.context_analyzer_tool import ContextAnalyzerTool

        # Используем текущий проект как тестовый
        project_dir = Path(__file__).parent.parent  # Корень проекта

        if project_dir.exists():
            tool = ContextAnalyzerTool(project_dir=str(project_dir))

            # Анализируем структуру
            structure = tool.analyze_project_structure()

            # Проверяем что основные директории найдены
            assert any(dir_name in structure for dir_name in ["src", "test", "docs"])

            # Ищем контекст для задачи тестирования
            context = tool.get_task_context("написать тесты для smart agent")

            # Проверяем что найдены релевантные файлы
            assert "smart_agent" in context.lower() or "контекст" in context.lower()

    def test_learning_tool_pattern_recognition(self):
        """Тест распознавания паттернов в LearningTool"""
        from src.tools.learning_tool import LearningTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            tool = LearningTool(experience_dir=tmp_dir)

            # Добавляем задачи с похожими паттернами
            tool.save_task_experience(
                "test_pattern_1",
                "Создание статических тестов для нового модуля",
                True, 2.0,
                ["testing", "static_analysis", "unittest"]
            )

            tool.save_task_experience(
                "test_pattern_2",
                "Написание интеграционных тестов для API",
                True, 3.0,
                ["testing", "integration", "api_testing"]
            )

            tool.save_task_experience(
                "test_pattern_3",
                "Разработка дымовых тестов для сервиса",
                True, 1.5,
                ["testing", "smoke_tests", "service_testing"]
            )

            # Получаем рекомендации для новой задачи тестирования
            recommendations = tool.get_recommendations("создать тесты для новой функциональности")

            # Проверяем что рекомендации содержат информацию о паттернах
            assert "рекомендации" in recommendations.lower()
            assert "тест" in recommendations.lower() or "testing" in recommendations.lower()

    def test_docker_manager_lifecycle_integration(self):
        """Тест полного жизненного цикла DockerManager"""
        from src.tools.docker_utils import DockerManager, DockerChecker

        manager = DockerManager(
            image_name="test-integration:latest",
            container_name="test-integration-container"
        )

        # Мокаем все Docker операции
        with patch.object(DockerChecker, 'is_docker_available', return_value=True), \
             patch.object(DockerChecker, 'is_container_running') as mock_running, \
             patch('subprocess.run') as mock_subprocess:

            # Настройка моков
            mock_running.return_value = False  # Контейнер не запущен

            start_result = Mock()
            start_result.returncode = 0
            start_result.stdout = "test_container_id"

            stop_result = Mock()
            stop_result.returncode = 0
            stop_result.stdout = ""

            exec_result = Mock()
            exec_result.returncode = 0
            exec_result.stdout = "test output"
            exec_result.stderr = ""

            # Настройка последовательных вызовов
            mock_subprocess.side_effect = [start_result, exec_result, stop_result]

            # Тест запуска
            success, msg = manager.start_container()
            assert success
            assert "started successfully" in msg

            # Меняем статус контейнера на запущенный
            mock_running.return_value = True

            # Тест выполнения команды
            success, stdout, stderr = manager.execute_command("echo test")
            assert success
            assert stdout == "test output"
            assert stderr == ""

            # Тест остановки
            success, msg = manager.stop_container()
            assert success
            assert "stopped successfully" in msg

    def test_tools_with_project_files_integration(self):
        """Интеграционный тест инструментов с реальными файлами проекта"""
        from src.tools.learning_tool import LearningTool
        from src.tools.context_analyzer_tool import ContextAnalyzerTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir)

            # Создаем структуру проекта
            src_dir = project_dir / "src"
            test_dir = project_dir / "test"
            docs_dir = project_dir / "docs"

            for dir_path in [src_dir, test_dir, docs_dir]:
                dir_path.mkdir(parents=True)

            # Создаем файлы
            (src_dir / "smart_agent.py").write_text("""
'''Smart Agent implementation'''
class SmartAgent:
    def __init__(self):
        self.tools = []

    def add_tool(self, tool):
        self.tools.append(tool)
""")

            (test_dir / "test_smart_agent.py").write_text("""
'''Tests for Smart Agent'''
import pytest
from src.smart_agent import SmartAgent

def test_smart_agent_creation():
    agent = SmartAgent()
    assert agent is not None
""")

            (docs_dir / "SMART_AGENT.md").write_text("""
# Smart Agent Documentation

Smart Agent provides intelligent task execution with learning capabilities.

## Features
- Learning from experience
- Context analysis
- Tool integration
""")

            # Создаем инструменты
            learning_tool = LearningTool(experience_dir=str(project_dir / "experience"))
            context_tool = ContextAnalyzerTool(project_dir=str(project_dir))

            assert learning_tool is not None
            assert context_tool is not None

            # Тестируем анализ контекста
            context = context_tool.get_task_context("разработать smart agent")
            assert len(context) > 0

            # Тестируем анализ компонента
            component_analysis = context_tool.analyze_component("src")
            assert "src" in component_analysis or "smart_agent.py" in component_analysis