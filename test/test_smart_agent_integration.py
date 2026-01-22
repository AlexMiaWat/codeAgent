"""
Интеграционные тесты для Smart Agent - взаимодействие с инструментами
"""

import pytest
import tempfile
import json
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock


@pytest.fixture
def dummy_openai_key():
    """Фикстура для установки dummy OPENAI_API_KEY"""
    original_key = os.environ.get('OPENAI_API_KEY')
    os.environ['OPENAI_API_KEY'] = 'dummy-key-for-testing'

    yield

    # Восстанавливаем оригинальный ключ
    if original_key is not None:
        os.environ['OPENAI_API_KEY'] = original_key
    elif 'OPENAI_API_KEY' in os.environ:
        del os.environ['OPENAI_API_KEY']


class TestSmartAgentIntegration:
    """Интеграционные тесты Smart Agent"""

    def test_smart_agent_learning_tool_integration(self):
        """Тест интеграции Smart Agent с LearningTool"""
        from src.agents.smart_agent import create_smart_agent
        from src.tools.learning_tool import LearningTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir)

            with patch('src.tools.docker_utils.is_docker_available', return_value=False):
                with patch('src.agents.smart_agent.LLM_WRAPPER_AVAILABLE', False):
                    with patch('src.agents.smart_agent.create_llm_for_crewai', return_value=None):
                        # Дополнительные патчи для полной изоляции LLM зависимостей
                        with patch('crewai.utilities.llm_utils.create_llm', return_value=None):
                            with patch('crewai.llm.LLM', side_effect=Exception("LLM disabled for testing")):
                                with patch.dict('os.environ', {'OPENAI_API_KEY': 'dummy', 'OPENROUTER_API_KEY': ''}, clear=False):
                                    agent = create_smart_agent(project_dir=project_dir, use_llm=False)

                                    # Находим LearningTool среди инструментов агента
                                    learning_tools = [t for t in agent.tools if isinstance(t, LearningTool)]
                                    assert len(learning_tools) == 1

                                    learning_tool = learning_tools[0]

                                    # Проверяем что LearningTool использует правильную директорию опыта
                                    assert learning_tool.experience_dir.exists()
                                    assert learning_tool.experience_file.exists()

                                    # Тестируем сохранение опыта через инструмент агента
                                    result = learning_tool.save_task_experience(
                                        task_id="integration_test_task",
                                        task_description="Integration test task",
                                        success=True,
                                        execution_time=1.5
                                    )

                                    assert "сохранен" in result
                                    assert "успешно" in result

                                    # Проверяем что опыт сохранен в файле
                                    with open(learning_tool.experience_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        assert len(data['tasks']) == 1
                        assert data['tasks'][0]['task_id'] == "integration_test_task"

    def test_smart_agent_context_analyzer_integration(self):
        """Тест интеграции Smart Agent с ContextAnalyzerTool"""
        from src.agents.smart_agent import create_smart_agent
        from src.tools.context_analyzer_tool import ContextAnalyzerTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir)

            # Создаем тестовую структуру проекта
            src_dir = project_dir / "src"
            src_dir.mkdir()
            (src_dir / "main.py").write_text("# Main module")

            docs_dir = project_dir / "docs"
            docs_dir.mkdir()
            (docs_dir / "README.md").write_text("# Documentation")

            with patch('src.tools.docker_utils.is_docker_available', return_value=False):
                with patch('src.agents.smart_agent.LLM_WRAPPER_AVAILABLE', False):
                    with patch('src.agents.smart_agent.create_llm_for_crewai', return_value=None):
                        # Дополнительные патчи для полной изоляции LLM зависимостей
                        with patch('crewai.utilities.llm_utils.create_llm', return_value=None):
                            with patch('crewai.llm.LLM', side_effect=Exception("LLM disabled for testing")):
                                with patch.dict('os.environ', {'OPENAI_API_KEY': 'dummy', 'OPENROUTER_API_KEY': ''}, clear=False):
                                agent = create_smart_agent(project_dir=project_dir, use_llm=False)

                                # Находим ContextAnalyzerTool среди инструментов агента
                    context_tools = [t for t in agent.tools if isinstance(t, ContextAnalyzerTool)]
                    assert len(context_tools) == 1

                    context_tool = context_tools[0]

                    # Проверяем что ContextAnalyzerTool правильно настроен
                    assert str(context_tool.project_dir) == str(project_dir)
                    assert str(context_tool.docs_dir) == str(docs_dir)

                    # Тестируем анализ структуры проекта через инструмент агента
                    result = context_tool.analyze_project_structure()

                    assert "🏗️ Анализ структуры проекта" in result
                    assert "src" in result or "docs" in result

                    # Тестируем получение контекста задачи
                    context_result = context_tool.get_task_context("разработать код")
                    assert "📋 Контекст для задачи" in context_result

    def test_smart_agent_tools_cooperation(self):
        """Тест кооперации инструментов в Smart Agent"""
        from src.agents.smart_agent import create_smart_agent
        from src.tools.learning_tool import LearningTool
        from src.tools.context_analyzer_tool import ContextAnalyzerTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir)

            # Создаем тестовую структуру проекта
            src_dir = project_dir / "src"
            src_dir.mkdir()
            (src_dir / "api.py").write_text("""
# API module
def get_data():
    return "data"
""")

            docs_dir = project_dir / "docs"
            docs_dir.mkdir()
            (docs_dir / "api.md").write_text("# API Documentation\nHow to use API")

            with patch('src.tools.docker_utils.is_docker_available', return_value=False):
                with patch('src.agents.smart_agent.LLM_WRAPPER_AVAILABLE', False):
                    with patch('src.agents.smart_agent.create_llm_for_crewai', return_value=None):
                        # Дополнительные патчи для полной изоляции LLM зависимостей
                        with patch('crewai.utilities.llm_utils.create_llm', return_value=None):
                            with patch('crewai.llm.LLM', side_effect=Exception("LLM disabled for testing")):
                                with patch.dict('os.environ', {'OPENAI_API_KEY': 'dummy', 'OPENROUTER_API_KEY': ''}, clear=False):
                                agent = create_smart_agent(project_dir=project_dir, use_llm=False)

                                # Получаем оба инструмента
                    learning_tools = [t for t in agent.tools if isinstance(t, LearningTool)]
                    context_tools = [t for t in agent.tools if isinstance(t, ContextAnalyzerTool)]

                    assert len(learning_tools) == 1
                    assert len(context_tools) == 1

                    learning_tool = learning_tools[0]
                    context_tool = context_tools[0]

                    # 1. ContextAnalyzerTool анализирует проект
                    project_analysis = context_tool.analyze_project_structure()
                    assert "Основные компоненты" in project_analysis

                    # 2. LearningTool сохраняет опыт анализа
                    save_result = learning_tool.save_task_experience(
                        task_id="project_analysis_task",
                        task_description="Проанализировать структуру проекта",
                        success=True,
                        execution_time=0.5,
                        patterns=["analysis", "structure"]
                    )
                    assert "сохранен" in save_result

                    # 3. LearningTool дает рекомендации на основе сохраненного опыта
                    recommendations = learning_tool.get_recommendations("анализ проекта")
                    assert "Рекомендации" in recommendations
                    assert "project_analysis_task" in recommendations or "успешных" in recommendations

                    # 4. ContextAnalyzerTool находит связанные файлы
                    related_files = context_tool.find_related_files("api")
                    assert "📁 Файлы, связанные с запросом" in related_files

    def test_smart_agent_experience_accumulation(self):
        """Тест накопления опыта в Smart Agent"""
        from src.agents.smart_agent import create_smart_agent
        from src.tools.learning_tool import LearningTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir)

            with patch('src.tools.docker_utils.is_docker_available', return_value=False):
                with patch('src.agents.smart_agent.LLM_WRAPPER_AVAILABLE', False):
                    with patch('src.agents.smart_agent.create_llm_for_crewai', return_value=None):
                        # Дополнительные патчи для полной изоляции LLM зависимостей
                        with patch('crewai.utilities.llm_utils.create_llm', return_value=None):
                            with patch('crewai.llm.LLM', side_effect=Exception("LLM disabled for testing")):
                                with patch.dict('os.environ', {'OPENAI_API_KEY': 'dummy', 'OPENROUTER_API_KEY': ''}, clear=False):
                                # Создаем первого агента
                                agent1 = create_smart_agent(
                                    project_dir=project_dir,
                                    experience_dir="shared_experience",
                                    use_llm=False
                                )

                    learning_tool1 = [t for t in agent1.tools if isinstance(t, LearningTool)][0]

                    # Первый агент сохраняет опыт
                    learning_tool1.save_task_experience("task1", "First task", True, 1.0, ["tag1"])
                    learning_tool1.save_task_experience("task2", "Second task", False, 2.0, ["tag2"])

                    # Создаем второго агента с той же директорией опыта
                    agent2 = create_smart_agent(
                        project_dir=project_dir,
                        experience_dir="shared_experience",
                        use_llm=False
                    )

                    learning_tool2 = [t for t in agent2.tools if isinstance(t, LearningTool)][0]

                    # Второй агент должен видеть опыт первого агента
                    stats = learning_tool2.get_statistics()
                    assert "Всего задач: 2" in stats
                    assert "Успешных задач: 1" in stats
                    assert "Неудачных задач: 1" in stats

                    # Поиск похожих задач должен работать
                    similar = learning_tool2.find_similar_tasks("task")
                    assert "First task" in similar or "Second task" in similar

                    # Второй агент добавляет свой опыт
                    learning_tool2.save_task_experience("task3", "Third task from agent2", True, 1.5, ["tag1"])

                    # Проверяем что опыт накопился
                    stats_final = learning_tool2.get_statistics()
                    assert "Всего задач: 3" in stats_final
                    assert "Успешных задач: 2" in stats_final

    def test_smart_agent_context_learning_integration(self):
        """Тест интеграции контекстного анализа и обучения"""
        from src.agents.smart_agent import create_smart_agent
        from src.tools.learning_tool import LearningTool
        from src.tools.context_analyzer_tool import ContextAnalyzerTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir)

            # Создаем проект с задачами разработки
            src_dir = project_dir / "src"
            src_dir.mkdir()
            (src_dir / "user_service.py").write_text("""
# User service
class UserService:
    def get_user(self, user_id):
        return {"id": user_id, "name": "Test User"}
""")

            docs_dir = project_dir / "docs"
            docs_dir.mkdir()
            (docs_dir / "user_service.md").write_text("""
# User Service API

## Methods
- get_user(user_id): Get user by ID
""")

            with patch('src.tools.docker_utils.is_docker_available', return_value=False):
                with patch('src.agents.smart_agent.LLM_WRAPPER_AVAILABLE', False):
                    with patch('src.agents.smart_agent.create_llm_for_crewai', return_value=None):
                        # Дополнительные патчи для полной изоляции LLM зависимостей
                        with patch('crewai.utilities.llm_utils.create_llm', return_value=None):
                            with patch('crewai.llm.LLM', side_effect=Exception("LLM disabled for testing")):
                                with patch.dict('os.environ', {'OPENAI_API_KEY': 'dummy', 'OPENROUTER_API_KEY': ''}, clear=False):
                                agent = create_smart_agent(project_dir=project_dir, use_llm=False)

                                learning_tool = [t for t in agent.tools if isinstance(t, LearningTool)][0]
                                context_tool = [t for t in agent.tools if isinstance(t, ContextAnalyzerTool)][0]

                                # 1. Анализируем контекст задачи разработки
                    task_context = context_tool.get_task_context("разработать user service")
                    assert "user_service.py" in task_context or "user_service.md" in task_context

                    # 2. Сохраняем опыт успешной разработки
                    learning_tool.save_task_experience(
                        task_id="develop_user_service",
                        task_description="Разработать сервис пользователей с API",
                        success=True,
                        execution_time=3.0,
                        patterns=["api", "service", "user_management"]
                    )

                    # 3. Ищем похожие задачи
                    similar_tasks = learning_tool.find_similar_tasks("service")
                    assert "user service" in similar_tasks.lower() or "похожие задачи" in similar_tasks

                    # 4. Получаем рекомендации для похожей задачи
                    recommendations = learning_tool.get_recommendations("разработать product service")
                    assert "Рекомендации" in recommendations

                    # 5. Анализируем компонент
                    component_analysis = context_tool.analyze_component("src/user_service.py")
                    assert "user_service.py" in component_analysis
                    assert "class UserService" in component_analysis

    def test_smart_agent_error_recovery_integration(self):
        """Тест восстановления после ошибок в интеграции инструментов"""
        from src.agents.smart_agent import create_smart_agent
        from src.tools.learning_tool import LearningTool
        from src.tools.context_analyzer_tool import ContextAnalyzerTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir)

            with patch('src.tools.docker_utils.is_docker_available', return_value=False):
                with patch('src.agents.smart_agent.LLM_WRAPPER_AVAILABLE', False):
                    with patch('src.agents.smart_agent.create_llm_for_crewai', return_value=None):
                        # Дополнительные патчи для полной изоляции LLM зависимостей
                        with patch('crewai.utilities.llm_utils.create_llm', return_value=None):
                            with patch('crewai.llm.LLM', side_effect=Exception("LLM disabled for testing")):
                                with patch.dict('os.environ', {'OPENAI_API_KEY': 'dummy', 'OPENROUTER_API_KEY': ''}, clear=False):
                                agent = create_smart_agent(project_dir=project_dir, use_llm=False)

                                learning_tool = [t for t in agent.tools if isinstance(t, LearningTool)][0]
                                context_tool = [t for t in agent.tools if isinstance(t, ContextAnalyzerTool)][0]

                                # 1. Сохраняем опыт с ошибкой
                    learning_tool.save_task_experience(
                        task_id="error_task",
                        task_description="Task that failed",
                        success=False,
                        execution_time=5.0,
                        notes="Failed due to network timeout"
                    )

                    # 2. Проверяем поиск зависимостей несуществующего файла (graceful error handling)
                    deps_result = context_tool.find_file_dependencies("nonexistent.py")
                    assert isinstance(deps_result, str)
                    assert "не найден" in deps_result or "not found" in deps_result

                    # 3. Проверяем анализ несуществующего компонента
                    analysis_result = context_tool.analyze_component("nonexistent_dir")
                    assert isinstance(analysis_result, str)
                    assert "не найден" in analysis_result or "not found" in analysis_result

                    # 4. Тем не менее, агент продолжает работать
                    stats = learning_tool.get_statistics()
                    assert "Всего задач: 1" in stats
                    assert "Неудачных задач: 1" in stats

                    # 5. Сохраняем успешный опыт после ошибки
                    learning_tool.save_task_experience(
                        task_id="recovery_task",
                        task_description="Task after error recovery",
                        success=True,
                        execution_time=2.0
                    )

                    final_stats = learning_tool.get_statistics()
                    assert "Всего задач: 2" in final_stats
                    assert "Успешных задач: 1" in final_stats


class TestSmartAgentWorkflowIntegration:
    """Тесты рабочих процессов Smart Agent"""

    def test_smart_agent_full_workflow(self):
        """Тест полного рабочего процесса Smart Agent"""
        from src.agents.smart_agent import create_smart_agent
        from src.tools.learning_tool import LearningTool
        from src.tools.context_analyzer_tool import ContextAnalyzerTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir)

            # Создаем структуру проекта
            self._setup_test_project(project_dir)

            with patch('src.tools.docker_utils.is_docker_available', return_value=False):
                with patch('src.agents.smart_agent.LLM_WRAPPER_AVAILABLE', False):
                    with patch('src.agents.smart_agent.create_llm_for_crewai', return_value=None):
                        # Дополнительные патчи для полной изоляции LLM зависимостей
                        with patch('crewai.utilities.llm_utils.create_llm', return_value=None):
                            with patch('crewai.llm.LLM', side_effect=Exception("LLM disabled for testing")):
                                with patch.dict('os.environ', {'OPENAI_API_KEY': 'dummy', 'OPENROUTER_API_KEY': ''}, clear=False):
                                agent = create_smart_agent(project_dir=project_dir, use_llm=False)

                                learning_tool = [t for t in agent.tools if isinstance(t, LearningTool)][0]
                                context_tool = [t for t in agent.tools if isinstance(t, ContextAnalyzerTool)][0]

                                # Шаг 1: Анализ проекта
                    project_structure = context_tool.analyze_project_structure()
                    assert "src" in project_structure
                    assert "docs" in project_structure

                    # Шаг 2: Сохранение опыта анализа
                    learning_tool.save_task_experience(
                        task_id="project_analysis",
                        task_description="Анализ структуры проекта перед разработкой",
                        success=True,
                        patterns=["analysis", "planning"]
                    )

                    # Шаг 3: Поиск контекста для задачи
                    task_context = context_tool.get_task_context("добавить функцию расчета")
                    assert isinstance(task_context, str)

                    # Шаг 4: Поиск связанных файлов
                    related_files = context_tool.find_related_files("calculator")
                    assert isinstance(related_files, str)

                    # Шаг 5: Сохранение опыта выполнения задачи
                    learning_tool.save_task_experience(
                        task_id="implement_calculator",
                        task_description="Реализовать функцию калькулятора",
                        success=True,
                        execution_time=4.5,
                        patterns=["implementation", "calculator", "math"]
                    )

                    # Шаг 6: Получение итоговой статистики
                    final_stats = learning_tool.get_statistics()
                    assert "Всего задач: 2" in final_stats
                    assert "Успешных задач: 2" in final_stats

                    # Шаг 7: Получение рекомендаций для будущих задач
                    recommendations = learning_tool.get_recommendations("добавить новые функции")
                    assert "Рекомендации" in recommendations

    def _setup_test_project(self, project_dir: Path):
        """Настройка тестовой структуры проекта"""
        # Создаем директории
        src_dir = project_dir / "src"
        src_dir.mkdir()

        docs_dir = project_dir / "docs"
        docs_dir.mkdir()

        test_dir = project_dir / "test"
        test_dir.mkdir()

        # Создаем файлы
        (src_dir / "__init__.py").write_text("")
        (src_dir / "calculator.py").write_text("""
# Calculator module
def add(a, b):
    return a + b

def multiply(a, b):
    return a * b
""")

        (src_dir / "utils.py").write_text("""
# Utility functions
def format_number(num):
    return f"{num:.2f}"
""")

        (docs_dir / "README.md").write_text("""
# Test Project

This is a test project for Smart Agent integration testing.

## Features
- Calculator functions
- Utility functions
""")

        (docs_dir / "api.md").write_text("""
# API Documentation

## Calculator Module
- add(a, b): Add two numbers
- multiply(a, b): Multiply two numbers
""")

        (test_dir / "test_calculator.py").write_text("""
# Tests for calculator
import pytest
from src.calculator import add, multiply

def test_add():
    assert add(2, 3) == 5

def test_multiply():
    assert multiply(2, 3) == 6
""")