"""
Интеграционные тесты для Smart Agent функциональности
Тестируют взаимодействие компонентов между собой
"""

import pytest
import tempfile
import json
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

# Импортируем тестируемые компоненты
from src.agents.smart_agent import create_smart_agent
from src.tools.learning_tool import LearningTool
from src.tools.context_analyzer_tool import ContextAnalyzerTool


class TestSmartAgentIntegration:
    """Интеграционные тесты Smart Agent"""

    def test_smart_agent_tools_integration(self):
        """Тест интеграции инструментов в Smart Agent"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)

            # Создаем smart agent
            agent = create_smart_agent(project_dir=project_dir)

            # Проверяем, что все инструменты правильно интегрированы
            assert len(agent.tools) >= 2

            # Находим инструменты по именам
            learning_tool = None
            context_tool = None

            for tool in agent.tools:
                if tool.name == "LearningTool":
                    learning_tool = tool
                elif tool.name == "ContextAnalyzerTool":
                    context_tool = tool

            assert learning_tool is not None
            assert context_tool is not None

            # Проверяем, что инструменты могут работать
            learning_result = learning_tool._run("get_statistics")
            context_result = context_tool._run("analyze_project")

            assert isinstance(learning_result, str)
            assert isinstance(context_result, str)

    def test_learning_context_tools_data_flow(self):
        """Тест потока данных между LearningTool и ContextAnalyzerTool"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)

            # Создаем инструменты
            learning_tool = LearningTool(experience_dir=str(project_dir / "experience"))
            context_tool = ContextAnalyzerTool(project_dir=str(project_dir))

            # Создаем тестовый проект
            src_dir = project_dir / "src"
            src_dir.mkdir()
            (src_dir / "auth.py").write_text("""
class AuthService:
    def login(self, username, password):
        return True

    def logout(self):
        pass
""")

            docs_dir = project_dir / "docs"
            docs_dir.mkdir()
            (docs_dir / "auth_guide.md").write_text("""
# Authentication Guide

This guide covers authentication implementation.

## Features
- User login
- Session management
- Security best practices
""")

            # ContextAnalyzerTool анализирует проект
            context_result = context_tool._run("analyze_project")

            # LearningTool сохраняет опыт анализа
            task_description = "Проанализировать структуру проекта аутентификации"
            learning_tool._run("save_experience",
                             task_id="analyze_auth_project",
                             task_description=task_description,
                             success=True,
                             execution_time=2.5,
                             notes="Проект содержит модуль аутентификации и документацию")

            # Проверяем, что данные сохранены
            experience = learning_tool._load_experience()
            assert len(experience["tasks"]) == 1
            assert experience["tasks"][0]["task_id"] == "analyze_auth_project"

            # Проверяем, что можно найти похожие задачи
            similar = learning_tool._run("find_similar", query="аутентификации")
            assert "analyze_auth_project" in similar or task_description in similar

    def test_experience_guided_context_analysis(self):
        """Тест использования опыта для улучшения анализа контекста"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)

            # Создаем инструменты
            learning_tool = LearningTool(experience_dir=str(project_dir / "experience"))
            context_tool = ContextAnalyzerTool(project_dir=str(project_dir))

            # Создаем тестовый проект
            src_dir = project_dir / "src"
            src_dir.mkdir()

            (src_dir / "user_service.py").write_text("""
class UserService:
    def create_user(self, data):
        pass

    def get_user(self, user_id):
        pass
""")

            # Сначала выполняем задачу и сохраняем опыт
            learning_tool._run("save_experience",
                             task_id="implement_user_crud",
                             task_description="Реализовать CRUD операции для пользователей",
                             success=True,
                             execution_time=15.0,
                             notes="Использовал паттерн Repository для доступа к данным",
                             patterns=["crud", "repository", "user_management"])

            # Теперь анализируем контекст для похожей задачи
            context_result = context_tool._run("get_context",
                                             task_description="добавить функционал управления пользователями")

            # Получаем рекомендации на основе опыта
            recommendations = learning_tool._run("get_recommendations",
                                               current_task="реализовать управление пользователями")

            # Проверяем, что рекомендации содержат полезную информацию
            assert isinstance(recommendations, str)
            assert len(recommendations) > 0

            # Проверяем, что контекст найден
            assert isinstance(context_result, str)

    def test_smart_agent_workflow_simulation(self):
        """Тест симуляции полного workflow Smart Agent"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)

            # Создаем тестовый проект
            self._create_test_project_structure(project_dir)

            # Создаем smart agent
            agent = create_smart_agent(project_dir=project_dir)

            # Симулируем выполнение задачи
            task_description = "Добавить систему логирования в проект"

            # 1. Анализируем контекст
            context_tools = [t for t in agent.tools if t.name == "ContextAnalyzerTool"]
            assert len(context_tools) == 1
            context_tool = context_tools[0]

            context_info = context_tool._run("get_context", task_description=task_description)

            # 2. Ищем похожие задачи в опыте
            learning_tools = [t for t in agent.tools if t.name == "LearningTool"]
            assert len(learning_tools) == 1
            learning_tool = learning_tools[0]

            # Добавляем некоторый опыт
            learning_tool._run("save_experience",
                             task_id="add_logging_v1",
                             task_description="Добавить базовое логирование в приложение",
                             success=True,
                             execution_time=8.0,
                             patterns=["logging", "monitoring"])

            # 3. Получаем рекомендации
            recommendations = learning_tool._run("get_recommendations",
                                               current_task=task_description)

            # 4. Сохраняем результат выполнения
            learning_tool._run("save_experience",
                             task_id="add_logging_v2",
                             task_description=task_description,
                             success=True,
                             execution_time=12.0,
                             notes="Добавлено структурированное логирование с ротацией")

            # Проверяем, что весь workflow прошел успешно
            assert isinstance(context_info, str)
            assert isinstance(recommendations, str)

            # Проверяем статистику
            stats = learning_tool._run("get_statistics")
            assert "Всего задач: 2" in stats

    def test_smart_agent_docker_fallback_mode(self):
        """Тест fallback режима Smart Agent без Docker"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)

            # Создаем smart agent с принудительным отключением Docker
            agent = create_smart_agent(
                project_dir=project_dir,
                use_docker=False,  # Принудительно отключаем Docker
                allow_code_execution=True
            )

            # Проверяем, что агент создан без CodeInterpreterTool
            tool_names = [tool.__class__.__name__ for tool in agent.tools]
            assert "CodeInterpreterTool" not in tool_names
            assert "LearningTool" in tool_names
            assert "ContextAnalyzerTool" in tool_names

            # Проверяем, что allow_code_execution=False для агента
            assert agent.allow_code_execution == False

            # Проверяем, что основные инструменты работают
            learning_tool = None
            context_tool = None

            for tool in agent.tools:
                if tool.__class__.__name__ == "LearningTool":
                    learning_tool = tool
                elif tool.__class__.__name__ == "ContextAnalyzerTool":
                    context_tool = tool

            assert learning_tool is not None
            assert context_tool is not None

            # Тестируем работу инструментов в fallback режиме
            learning_result = learning_tool._run("get_statistics")
            context_result = context_tool._run("analyze_project")

            assert isinstance(learning_result, str)
            assert isinstance(context_result, str)

    @patch('src.tools.docker_utils.DockerChecker.is_docker_available')
    def test_smart_agent_docker_auto_detection_fallback(self, mock_docker_check):
        """Тест автоопределения Docker с fallback при недоступности"""
        # Мокаем недоступность Docker
        mock_docker_check.return_value = False

        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)

            # Создаем smart agent с автоопределением Docker
            agent = create_smart_agent(
                project_dir=project_dir,
                use_docker=None,  # Автоопределение
                allow_code_execution=True
            )

            # Проверяем, что Docker был проверен
            mock_docker_check.assert_called_once()

            # Проверяем, что агент создан в fallback режиме
            tool_names = [tool.__class__.__name__ for tool in agent.tools]
            assert "CodeInterpreterTool" not in tool_names
            assert "LearningTool" in tool_names
            assert "ContextAnalyzerTool" in tool_names

            # Проверяем, что allow_code_execution=False
            assert agent.allow_code_execution == False

    @patch('src.tools.docker_utils.DockerChecker.is_docker_available')
    def test_smart_agent_docker_forced_fallback_warning(self, mock_docker_check):
        """Тест принудительного использования Docker с предупреждением при недоступности"""
        # Мокаем недоступность Docker
        mock_docker_check.return_value = False

        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)

            # Создаем smart agent с принудительным использованием Docker
            with patch('src.agents.smart_agent.logger') as mock_logger:
                agent = create_smart_agent(
                    project_dir=project_dir,
                    use_docker=True,  # Принудительно включаем Docker
                    allow_code_execution=True
                )

                # Проверяем, что было записано предупреждение
                mock_logger.warning.assert_called_with("Docker forced but not available - falling back to no code execution")

            # Проверяем, что агент создан в fallback режиме несмотря на force=True
            tool_names = [tool.__class__.__name__ for tool in agent.tools]
            assert "CodeInterpreterTool" not in tool_names
            assert agent.allow_code_execution == False

    def test_docker_utils_functionality(self):
        """Тест функциональности Docker утилит"""
        # Тест проверки доступности Docker (может быть доступен или нет в зависимости от среды)
        docker_available = DockerChecker.is_docker_available()
        assert isinstance(docker_available, bool)

        # Тест получения версии Docker
        version = DockerChecker.get_docker_version()
        assert version is None or isinstance(version, str)

        # Тест проверки прав доступа
        perms_ok, perms_msg = DockerChecker.check_docker_permissions()
        assert isinstance(perms_ok, bool)
        assert isinstance(perms_msg, str)

        # Тест получения списка контейнеров
        containers = DockerChecker.get_running_containers()
        assert isinstance(containers, list)

        # Тест проверки запущенного контейнера
        test_container_running = DockerChecker.is_container_running("nonexistent_container_12345")
        assert test_container_running == False

    def test_learning_tool_statistics_accuracy(self):
        """Тест точности статистики LearningTool"""
        with tempfile.TemporaryDirectory() as temp_dir:
            experience_dir = Path(temp_dir) / "experience"

            tool = LearningTool(experience_dir=str(experience_dir))

            # Добавляем тестовые задачи с известными результатами
            test_tasks = [
                {"id": "task1", "desc": "Task 1", "success": True, "time": 10.0},
                {"id": "task2", "desc": "Task 2", "success": True, "time": 15.0},
                {"id": "task3", "desc": "Task 3", "success": False, "time": 5.0},
                {"id": "task4", "desc": "Task 4", "success": True, "time": 20.0},
            ]

            for task in test_tasks:
                tool.save_task_experience(
                    task["id"], task["desc"], task["success"], task["time"]
                )

            # Проверяем статистику
            stats = tool.get_statistics()

            # Должно быть 4 задачи total
            assert "Всего задач: 4" in stats

            # Должно быть 3 успешных
            assert "Успешных задач: 3" in stats

            # Должна быть 1 неудачная
            assert "Неудачных задач: 1" in stats

            # Среднее время: (10+15+5+20)/4 = 12.5
            assert "12.5" in stats or "12,5" in stats

            # Процент успешности: 75%
            assert "75" in stats

    def test_context_analyzer_real_project_analysis(self):
        """Тест анализа реального проекта ContextAnalyzerTool"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)

            # Создаем структуру, похожую на реальный проект
            src_dir = project_dir / "src"
            src_dir.mkdir()

            tools_dir = src_dir / "tools"
            tools_dir.mkdir()

            # Создаем файлы с импортами (имитация реального проекта)
            (src_dir / "__init__.py").write_text("")
            (src_dir / "main.py").write_text("""
from src.tools.learning_tool import LearningTool
from src.tools.context_analyzer_tool import ContextAnalyzerTool

def main():
    print("Starting application")
""")

            (tools_dir / "__init__.py").write_text("")
            (tools_dir / "learning_tool.py").write_text("""
import json
from pathlib import Path

class LearningTool:
    def save_experience(self, task_id, description, success):
        pass
""")

            (tools_dir / "context_analyzer_tool.py").write_text("""
import os
from pathlib import Path

class ContextAnalyzerTool:
    def analyze_project(self):
        return "Analysis complete"
""")

            # Создаем документацию
            docs_dir = project_dir / "docs"
            docs_dir.mkdir()

            (docs_dir / "README.md").write_text("""
# Code Agent Project

This is a smart agent system.

## Features
- Learning from experience
- Context analysis
- Task execution
""")

            (docs_dir / "architecture.md").write_text("""
# Architecture

## Components
- LearningTool: learns from task execution
- ContextAnalyzerTool: analyzes project context
- SmartAgent: orchestrates the process
""")

            # Тестируем анализ
            tool = ContextAnalyzerTool(project_dir=str(project_dir))

            # Анализ структуры проекта
            structure = tool.analyze_project_structure()
            assert "src:" in structure
            assert "docs:" in structure

            # Поиск зависимостей
            deps = tool.find_file_dependencies("src/main.py")
            assert "learning_tool.py" in deps or "context_analyzer_tool.py" in deps

            # Поиск связанных файлов
            related = tool.find_related_files("learning")
            assert len(related) > 0

    def test_tools_concurrent_usage_simulation(self):
        """Тест симуляции одновременного использования инструментов"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)

            # Создаем инструменты
            learning_tool = LearningTool(experience_dir=str(project_dir / "experience"))
            context_tool = ContextAnalyzerTool(project_dir=str(project_dir))

            # Создаем тестовый контент
            (project_dir / "test.py").write_text("def test(): pass")
            (project_dir / "README.md").write_text("# Test")

            # Имитируем параллельное использование
            operations = []

            # Операции learning tool
            operations.append(("learning", learning_tool._run("save_experience",
                                                             task_id="concurrent_test",
                                                             task_description="test concurrent usage",
                                                             success=True)))

            operations.append(("learning", learning_tool._run("get_statistics")))

            # Операции context tool
            operations.append(("context", context_tool._run("analyze_project")))
            operations.append(("context", context_tool._run("find_related_files", query="test")))

            # Проверяем, что все операции завершились успешно
            for op_type, result in operations:
                assert isinstance(result, str)
                assert len(result) > 0

    def _create_test_project_structure(self, project_dir: Path):
        """Вспомогательный метод для создания тестовой структуры проекта"""
        # Создаем основные директории
        src_dir = project_dir / "src"
        src_dir.mkdir()

        test_dir = project_dir / "test"
        test_dir.mkdir()

        docs_dir = project_dir / "docs"
        docs_dir.mkdir()

        # Создаем файлы
        (src_dir / "__init__.py").write_text("")
        (src_dir / "app.py").write_text("""
def main():
    print("Hello World")

if __name__ == "__main__":
    main()
""")

        (src_dir / "utils.py").write_text("""
def helper_function():
    return "helper"

class UtilityClass:
    pass
""")

        (test_dir / "__init__.py").write_text("")
        (test_dir / "test_app.py").write_text("""
def test_main():
    assert True
""")

        (docs_dir / "README.md").write_text("""
# Test Project

A sample project for testing.
""")

        (docs_dir / "guide.md").write_text("""
# User Guide

How to use this project.
""")

        # Создаем конфигурационные файлы
        (project_dir / "pyproject.toml").write_text("""
[tool.poetry]
name = "test-project"
version = "0.1.0"
""")

        (project_dir / "requirements.txt").write_text("""
pytest==7.0.0
requests==2.28.0
""")