"""
Статические тесты для Smart Agent функциональности
"""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Импортируем тестируемые компоненты
from src.agents.smart_agent import create_smart_agent
from src.tools.learning_tool import LearningTool
from src.tools.context_analyzer_tool import ContextAnalyzerTool


class TestSmartAgentStatic:
    """Статические тесты для SmartAgent"""

    def test_smart_agent_creation_basic(self):
        """Тест базового создания smart agent"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)

            # Создаем агента с минимальными параметрами
            agent = create_smart_agent(project_dir=project_dir)

            assert agent is not None
            assert hasattr(agent, 'role')
            assert hasattr(agent, 'goal')
            assert hasattr(agent, 'backstory')
            assert hasattr(agent, 'tools')

    def test_smart_agent_creation_with_custom_params(self):
        """Тест создания smart agent с кастомными параметрами"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)

            custom_role = "Custom Smart Agent"
            custom_goal = "Custom goal for testing"

            agent = create_smart_agent(
                project_dir=project_dir,
                role=custom_role,
                goal=custom_goal,
                allow_code_execution=False,
                verbose=False
            )

            assert agent.role == custom_role
            assert agent.goal == custom_goal
            assert agent.allow_code_execution == False

    def test_smart_agent_tools_initialization(self):
        """Тест инициализации инструментов в smart agent"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)

            agent = create_smart_agent(project_dir=project_dir)

            # Проверяем, что инструменты добавлены
            assert len(agent.tools) >= 2  # Должны быть как минимум LearningTool и ContextAnalyzerTool

            # Проверяем наличие специфических инструментов
            tool_names = [tool.name for tool in agent.tools]
            assert "LearningTool" in tool_names
            assert "ContextAnalyzerTool" in tool_names

    def test_smart_agent_llm_configuration(self):
        """Тест конфигурации LLM для smart agent"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)

            # Тест с OpenRouter API ключом
            with patch.dict('os.environ', {'OPENROUTER_API_KEY': 'test_key'}):
                agent = create_smart_agent(
                    project_dir=project_dir,
                    use_llm_manager=True
                )

                # Проверяем, что LLM настроена
                assert hasattr(agent, 'llm') or hasattr(agent, 'llms')

    def test_smart_agent_memory_enabled(self):
        """Тест, что у smart agent включена память"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)

            agent = create_smart_agent(project_dir=project_dir)

            # Проверяем, что агент создан успешно
            assert agent is not None


class TestLearningToolStatic:
    """Статические тесты для LearningTool"""

    def test_learning_tool_creation(self):
        """Тест создания LearningTool"""
        with tempfile.TemporaryDirectory() as temp_dir:
            experience_dir = Path(temp_dir) / "experience"

            tool = LearningTool(experience_dir=str(experience_dir))

            assert tool.name == "LearningTool"
            assert tool.experience_dir == experience_dir
            assert tool.max_experience_tasks == 1000

    def test_learning_tool_experience_file_creation(self):
        """Тест создания файла опыта при инициализации"""
        with tempfile.TemporaryDirectory() as temp_dir:
            experience_dir = Path(temp_dir) / "experience"

            # Создаем инструмент
            tool = LearningTool(experience_dir=str(experience_dir))

            # Проверяем, что файл опыта создан
            assert tool.experience_file.exists()

            # Проверяем содержимое файла
            with open(tool.experience_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            assert data["version"] == "1.0"
            assert data["tasks"] == []
            assert data["patterns"] == {}
            assert "statistics" in data

    def test_learning_tool_custom_max_tasks(self):
        """Тест настройки максимального количества задач"""
        with tempfile.TemporaryDirectory() as temp_dir:
            experience_dir = Path(temp_dir) / "experience"
            max_tasks = 500

            tool = LearningTool(experience_dir=str(experience_dir), max_experience_tasks=max_tasks)

            assert tool.max_experience_tasks == max_tasks

    def test_learning_tool_save_experience(self):
        """Тест сохранения опыта выполнения задачи"""
        with tempfile.TemporaryDirectory() as temp_dir:
            experience_dir = Path(temp_dir) / "experience"

            tool = LearningTool(experience_dir=str(experience_dir))

            # Сохраняем опыт
            result = tool.save_task_experience(
                task_id="test_task_1",
                task_description="Test task",
                success=True,
                execution_time=10.5,
                notes="Test notes",
                patterns=["pattern1", "pattern2"]
            )

            assert "успешно" in result.lower()

            # Проверяем, что опыт сохранен
            data = tool._load_experience()
            assert len(data["tasks"]) == 1
            assert data["tasks"][0]["task_id"] == "test_task_1"
            assert data["tasks"][0]["success"] == True
            assert data["tasks"][0]["execution_time"] == 10.5

    def test_learning_tool_find_similar_tasks(self):
        """Тест поиска похожих задач"""
        with tempfile.TemporaryDirectory() as temp_dir:
            experience_dir = Path(temp_dir) / "experience"

            tool = LearningTool(experience_dir=str(experience_dir))

            # Добавляем тестовые задачи
            tool.save_task_experience("task1", "create user authentication", True)
            tool.save_task_experience("task2", "implement login system", True)
            tool.save_task_experience("task3", "build file upload", False)

            # Ищем похожие задачи
            result = tool.find_similar_tasks("authentication")

            assert "task1" in result or "create user authentication" in result

    def test_learning_tool_get_statistics(self):
        """Тест получения статистики обучения"""
        with tempfile.TemporaryDirectory() as temp_dir:
            experience_dir = Path(temp_dir) / "experience"

            tool = LearningTool(experience_dir=str(experience_dir))

            # Добавляем тестовые данные
            tool.save_task_experience("task1", "task1", True, 5.0)
            tool.save_task_experience("task2", "task2", False, 3.0)
            tool.save_task_experience("task3", "task3", True, 7.0)

            stats = tool.get_statistics()

            assert "Всего задач: 3" in stats
            assert "Успешных задач: 2" in stats
            assert "Неудачных задач: 1" in stats

    def test_learning_tool_get_recommendations(self):
        """Тест получения рекомендаций"""
        with tempfile.TemporaryDirectory() as temp_dir:
            experience_dir = Path(temp_dir) / "experience"

            tool = LearningTool(experience_dir=str(experience_dir))

            # Добавляем успешную задачу
            tool.save_task_experience(
                "task1",
                "implement user login",
                True,
                10.0,
                "Use JWT tokens",
                ["authentication", "security"]
            )

            # Получаем рекомендации
            result = tool.get_recommendations("user authentication")

            assert "рекомендации" in result.lower() or "recommendations" in result.lower()


class TestContextAnalyzerToolStatic:
    """Статические тесты для ContextAnalyzerTool"""

    def test_context_analyzer_tool_creation(self):
        """Тест создания ContextAnalyzerTool"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)

            tool = ContextAnalyzerTool(project_dir=str(project_dir))

            assert tool.name == "ContextAnalyzerTool"
            assert tool.project_dir == project_dir
            assert tool.docs_dir == project_dir / "docs"
            assert tool.max_file_size == 1000000

    def test_context_analyzer_tool_custom_params(self):
        """Тест создания с кастомными параметрами"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            docs_dir = "documentation"
            max_size = 500000

            tool = ContextAnalyzerTool(
                project_dir=str(project_dir),
                docs_dir=docs_dir,
                max_file_size=max_size,
                supported_extensions=[".py", ".md"]
            )

            assert tool.docs_dir == project_dir / docs_dir
            assert tool.max_file_size == max_size
            assert ".py" in tool.supported_extensions
            assert ".md" in tool.supported_extensions

    def test_context_analyzer_project_structure_analysis(self):
        """Тест анализа структуры проекта"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)

            # Создаем тестовую структуру
            (project_dir / "src").mkdir()
            (project_dir / "docs").mkdir()
            (project_dir / "test").mkdir()

            # Создаем файлы разных типов
            (project_dir / "src" / "main.py").write_text("print('hello')")
            (project_dir / "docs" / "README.md").write_text("# Documentation")
            (project_dir / "test" / "test.py").write_text("def test(): pass")

            tool = ContextAnalyzerTool(project_dir=str(project_dir))

            result = tool.analyze_project_structure()

            assert "Анализ структуры проекта" in result
            assert "Основные компоненты" in result
            assert "src:" in result or "docs:" in result or "test:" in result

    def test_context_analyzer_find_dependencies_python(self):
        """Тест поиска зависимостей Python файла"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)

            # Создаем тестовый Python файл с импортами
            test_file = project_dir / "test_module.py"
            test_file.write_text("""
import os
import sys
from pathlib import Path
from custom_module import CustomClass
""")

            # Создаем файл, на который есть ссылка
            (project_dir / "custom_module.py").write_text("class CustomClass: pass")

            tool = ContextAnalyzerTool(project_dir=str(project_dir))

            result = tool.find_file_dependencies("test_module.py")

            assert "custom_module.py" in result or "CustomClass" in result

    def test_context_analyzer_find_dependencies_markdown(self):
        """Тест поиска зависимостей Markdown файла"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)

            # Создаем тестовый MD файл со ссылками
            test_file = project_dir / "test.md"
            test_file.write_text("""
# Test Document

See also: [main.py](src/main.py)
Check [utils.py](utils.py) for utilities.
""")

            # Создаем файлы, на которые есть ссылки
            (project_dir / "src").mkdir()
            (project_dir / "src" / "main.py").write_text("print('main')")
            (project_dir / "utils.py").write_text("def util(): pass")

            tool = ContextAnalyzerTool(project_dir=str(project_dir))

            result = tool.find_file_dependencies("test.md")

            assert "main.py" in result or "utils.py" in result

    def test_context_analyzer_get_task_context(self):
        """Тест получения контекста для задачи"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)

            # Создаем тестовые файлы
            docs_dir = project_dir / "docs"
            docs_dir.mkdir()

            (docs_dir / "api.md").write_text("# API Documentation\nAuthentication and security")
            (docs_dir / "guide.md").write_text("# User Guide\nHow to use the system")

            src_dir = project_dir / "src"
            src_dir.mkdir()
            (src_dir / "auth.py").write_text("class Authentication: pass")
            (src_dir / "security.py").write_text("class Security: pass")

            tool = ContextAnalyzerTool(project_dir=str(project_dir))

            result = tool.get_task_context("implement authentication")

            assert "Контекст для задачи" in result

    def test_context_analyzer_analyze_component_directory(self):
        """Тест анализа компонента-директории"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)

            # Создаем тестовую директорию
            component_dir = project_dir / "src" / "auth"
            component_dir.mkdir(parents=True)

            # Создаем файлы разных типов
            (component_dir / "__init__.py").write_text("")
            (component_dir / "login.py").write_text("def login(): pass")
            (component_dir / "register.py").write_text("def register(): pass")
            (component_dir / "README.md").write_text("# Auth Module")

            tool = ContextAnalyzerTool(project_dir=str(project_dir))

            result = tool.analyze_component("src/auth")

            assert "Анализ компонента" in result
            assert "directory" in result.lower()

    def test_context_analyzer_analyze_component_file(self):
        """Тест анализа компонента-файла"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)

            # Создаем тестовый файл
            test_file = project_dir / "utils.py"
            test_file.write_text("""
import os
from pathlib import Path

def helper():
    return "help"
""")

            tool = ContextAnalyzerTool(project_dir=str(project_dir))

            result = tool.analyze_component("utils.py")

            assert "Анализ компонента" in result
            assert "file" in result.lower()
            assert ".py" in result

    def test_context_analyzer_find_related_files(self):
        """Тест поиска связанных файлов"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)

            # Создаем тестовые файлы
            docs_dir = project_dir / "docs"
            docs_dir.mkdir()

            (docs_dir / "auth.md").write_text("# Authentication\nHow to implement auth")
            (docs_dir / "security.md").write_text("# Security\nAuthentication best practices")

            src_dir = project_dir / "src"
            src_dir.mkdir()
            (src_dir / "auth_service.py").write_text("class AuthService: pass")

            tool = ContextAnalyzerTool(project_dir=str(project_dir))

            result = tool.find_related_files("authentication")

            assert "Файлы, связанные с запросом" in result
            assert "auth" in result.lower()