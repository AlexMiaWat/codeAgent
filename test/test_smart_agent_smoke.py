"""
Дымовые тесты для Smart Agent функциональности
Проверяют базовую работоспособность компонентов без углубленного тестирования
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

# Импортируем тестируемые компоненты
from src.agents.smart_agent import create_smart_agent
from src.tools.learning_tool import LearningTool
from src.tools.context_analyzer_tool import ContextAnalyzerTool


class TestSmartAgentSmoke:
    """Дымовые тесты для SmartAgent"""

    def test_smart_agent_creation_smoke(self):
        """Дымовой тест создания smart agent - базовая работоспособность"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)

            # Просто проверяем, что агент создается без ошибок
            agent = create_smart_agent(project_dir=project_dir)

            assert agent is not None
            # Проверяем наличие основных атрибутов
            assert hasattr(agent, 'role')
            assert hasattr(agent, 'goal')

    def test_smart_agent_with_tools_smoke(self):
        """Дымовой тест smart agent с инструментами"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)

            agent = create_smart_agent(project_dir=project_dir, allow_code_execution=False)

            # Проверяем, что инструменты инициализированы
            assert hasattr(agent, 'tools')
            assert len(agent.tools) > 0

    def test_smart_agent_verbose_mode_smoke(self):
        """Дымовой тест verbose режима"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)

            # Тест с verbose=True
            agent_verbose = create_smart_agent(project_dir=project_dir, verbose=True)
            assert agent_verbose.verbose == True

            # Тест с verbose=False
            agent_quiet = create_smart_agent(project_dir=project_dir, verbose=False)
            assert agent_quiet.verbose == False

    @patch('src.agents.smart_agent.os.getenv')
    def test_smart_agent_llm_config_smoke(self, mock_getenv):
        """Дымовой тест конфигурации LLM"""
        mock_getenv.return_value = 'test_api_key'

        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)

            # Не должно быть исключений при настройке LLM
            agent = create_smart_agent(
                project_dir=project_dir,
                use_llm_manager=True
            )

            assert agent is not None

    def test_smart_agent_different_roles_smoke(self):
        """Дымовой тест разных ролей агента"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)

            roles = [
                "Smart Project Executor Agent",
                "AI Assistant",
                "Code Review Agent"
            ]

            for role in roles:
                agent = create_smart_agent(project_dir=project_dir, role=role)
                assert agent.role == role


class TestLearningToolSmoke:
    """Дымовые тесты для LearningTool"""

    def test_learning_tool_basic_operations_smoke(self):
        """Дымовой тест основных операций LearningTool"""
        with tempfile.TemporaryDirectory() as temp_dir:
            experience_dir = Path(temp_dir) / "experience"

            tool = LearningTool(experience_dir=str(experience_dir))

            # Базовые операции не должны вызывать исключений
            result1 = tool.save_task_experience("task1", "test task", True)
            assert isinstance(result1, str)

            result2 = tool.find_similar_tasks("test")
            assert isinstance(result2, str)

            result3 = tool.get_recommendations("test task")
            assert isinstance(result3, str)

            result4 = tool.get_statistics()
            assert isinstance(result4, str)

    def test_learning_tool_different_scenarios_smoke(self):
        """Дымовой тест разных сценариев использования"""
        with tempfile.TemporaryDirectory() as temp_dir:
            experience_dir = Path(temp_dir) / "experience"

            tool = LearningTool(experience_dir=str(experience_dir))

            scenarios = [
                {"task_id": "task1", "description": "create user", "success": True, "time": 5.0},
                {"task_id": "task2", "description": "delete user", "success": False, "time": 2.0},
                {"task_id": "task3", "description": "update profile", "success": True, "time": None},
            ]

            for scenario in scenarios:
                result = tool.save_task_experience(
                    scenario["task_id"],
                    scenario["description"],
                    scenario["success"],
                    scenario["time"]
                )
                assert isinstance(result, str)

    def test_learning_tool_empty_experience_smoke(self):
        """Дымовой тест работы с пустым опытом"""
        with tempfile.TemporaryDirectory() as temp_dir:
            experience_dir = Path(temp_dir) / "experience"

            tool = LearningTool(experience_dir=str(experience_dir))

            # Запросы к пустому опыту не должны падать
            result1 = tool.find_similar_tasks("nonexistent")
            assert isinstance(result1, str)

            result2 = tool.get_recommendations("unknown task")
            assert isinstance(result2, str)

            result3 = tool.get_statistics()
            assert isinstance(result3, str)
            assert "0" in result3  # Должны быть нули в статистике

    def test_learning_tool_large_data_smoke(self):
        """Дымовой тест работы с большим объемом данных"""
        with tempfile.TemporaryDirectory() as temp_dir:
            experience_dir = Path(temp_dir) / "experience"

            tool = LearningTool(experience_dir=str(experience_dir), max_experience_tasks=10)

            # Добавляем много задач (больше лимита)
            for i in range(15):
                tool.save_task_experience(f"task{i}", f"description {i}", i % 2 == 0)

            # Операции должны работать несмотря на ограничение
            stats = tool.get_statistics()
            assert isinstance(stats, str)

            # Проверяем, что лимит respected (не больше max_experience_tasks задач)
            data = tool._load_experience()
            assert len(data["tasks"]) <= 10


class TestContextAnalyzerToolSmoke:
    """Дымовые тесты для ContextAnalyzerTool"""

    def test_context_analyzer_basic_operations_smoke(self):
        """Дымовой тест основных операций ContextAnalyzerTool"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)

            tool = ContextAnalyzerTool(project_dir=str(project_dir))

            # Базовые операции не должны вызывать исключений
            result1 = tool.analyze_project_structure()
            assert isinstance(result1, str)

            result2 = tool.get_task_context("test task")
            assert isinstance(result2, str)

            result3 = tool.find_related_files("test")
            assert isinstance(result3, str)

    def test_context_analyzer_with_files_smoke(self):
        """Дымовой тест работы с файлами"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)

            # Создаем тестовые файлы
            (project_dir / "test.py").write_text("def test(): pass")
            (project_dir / "README.md").write_text("# Test")

            docs_dir = project_dir / "docs"
            docs_dir.mkdir()
            (docs_dir / "guide.md").write_text("# Guide")

            tool = ContextAnalyzerTool(project_dir=str(project_dir))

            # Операции с файлами не должны падать
            result1 = tool.analyze_project_structure()
            assert isinstance(result1, str)

            result2 = tool.find_file_dependencies("test.py")
            assert isinstance(result2, str)

            result3 = tool.analyze_component("test.py")
            assert isinstance(result3, str)

    def test_context_analyzer_different_file_types_smoke(self):
        """Дымовой тест работы с разными типами файлов"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)

            # Создаем файлы разных типов
            test_files = {
                "script.py": "import os\nprint('hello')",
                "config.yaml": "key: value\nlist:\n  - item1\n  - item2",
                "data.json": '{"key": "value", "number": 42}',
                "readme.md": "# Title\n\nSome **bold** text and `code`.",
                "script.js": "function test() { return true; }",
                "style.css": ".class { color: red; }"
            }

            for filename, content in test_files.items():
                (project_dir / filename).write_text(content)

            tool = ContextAnalyzerTool(project_dir=str(project_dir))

            # Анализ структуры должен работать
            result = tool.analyze_project_structure()
            assert isinstance(result, str)
            assert len(result) > 0

    def test_context_analyzer_empty_project_smoke(self):
        """Дымовой тест работы с пустым проектом"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)

            tool = ContextAnalyzerTool(project_dir=str(project_dir))

            # Все операции должны работать даже с пустым проектом
            operations = [
                tool.analyze_project_structure(),
                tool.get_task_context("any task"),
                tool.find_related_files("anything"),
            ]

            for result in operations:
                assert isinstance(result, str)

    def test_context_analyzer_large_files_smoke(self):
        """Дымовой тест работы с большими файлами"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)

            # Создаем большой файл (но не превышающий лимит)
            large_content = "# Large Markdown File\n\n" + "Content line.\n" * 1000
            (project_dir / "large.md").write_text(large_content)

            tool = ContextAnalyzerTool(project_dir=str(project_dir), max_file_size=2000000)

            # Операции должны работать с большими файлами
            result1 = tool.analyze_component("large.md")
            assert isinstance(result1, str)

            result2 = tool.find_related_files("Content")
            assert isinstance(result2, str)

    def test_context_analyzer_nonexistent_files_smoke(self):
        """Дымовой тест работы с несуществующими файлами"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)

            tool = ContextAnalyzerTool(project_dir=str(project_dir))

            # Запросы к несуществующим файлам не должны вызывать исключений
            result1 = tool.find_file_dependencies("nonexistent.py")
            assert isinstance(result1, str)

            result2 = tool.analyze_component("missing_file.txt")
            assert isinstance(result2, str)

            # Должны возвращать сообщения об ошибках, но не падать
            assert "не найден" in result1.lower() or "not found" in result1.lower()
            assert "не найден" in result2.lower() or "not found" in result2.lower()


class TestSmartAgentIntegrationSmoke:
    """Дымовые тесты интеграции компонентов Smart Agent"""

    def test_full_smart_agent_workflow_smoke(self):
        """Дымовой тест полного workflow smart agent"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)

            # Создаем тестовый проект
            src_dir = project_dir / "src"
            src_dir.mkdir()

            docs_dir = project_dir / "docs"
            docs_dir.mkdir()

            (src_dir / "main.py").write_text("def main(): print('Hello')")
            (docs_dir / "README.md").write_text("# Project Documentation")

            # Создаем smart agent
            agent = create_smart_agent(project_dir=project_dir)

            # Проверяем, что все компоненты работают вместе
            assert agent is not None
            assert len(agent.tools) >= 2

            # Проверяем инструменты
            tool_names = [tool.name for tool in agent.tools]
            assert "LearningTool" in tool_names
            assert "ContextAnalyzerTool" in tool_names

    def test_tools_interaction_smoke(self):
        """Дымовой тест взаимодействия инструментов"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)

            # Создаем инструменты
            learning_tool = LearningTool(experience_dir=str(project_dir / "experience"))
            context_tool = ContextAnalyzerTool(project_dir=str(project_dir))

            # Добавляем опыт
            learning_tool.save_task_experience("test_task", "analyze project", True, 5.0)

            # Используем context tool для анализа
            context_result = context_tool.analyze_project_structure()

            # Проверяем, что оба инструмента работают
            assert isinstance(context_result, str)
            assert len(context_result) > 0

            # Проверяем статистику обучения
            stats = learning_tool.get_statistics()
            assert isinstance(stats, str)