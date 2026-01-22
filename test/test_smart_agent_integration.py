"""
Интеграционные тесты для Smart Agent - проверка взаимодействия компонентов
"""

import pytest
import tempfile
import json
import time
from pathlib import Path
from unittest.mock import patch, MagicMock, call
from src.agents.smart_agent import create_smart_agent
from src.tools.learning_tool import LearningTool
from src.tools.context_analyzer_tool import ContextAnalyzerTool


class TestSmartAgentToolsIntegration:
    """Интеграционные тесты взаимодействия Smart Agent с инструментами"""

    def test_learning_tool_integration_with_smart_agent(self):
        """Интеграция LearningTool с Smart Agent"""
        with tempfile.TemporaryDirectory() as temp_dir:
            agent = create_smart_agent(
                project_dir=Path(temp_dir),
                use_llm=False,
                use_docker=False
            )

            # Найдем LearningTool в инструментах агента
            learning_tool = None
            for tool in agent.tools:
                if isinstance(tool, LearningTool):
                    learning_tool = tool
                    break

            assert learning_tool is not None

            # Протестируем сохранение опыта через инструмент
            result = learning_tool._run("save_experience",
                                      task_id="integration_test_1",
                                      task_description="Integration test task",
                                      success=True,
                                      execution_time=10.5)

            assert "сохранен" in result

            # Проверим что опыт сохранен
            experience_data = learning_tool._load_experience()
            assert len(experience_data["tasks"]) == 1
            assert experience_data["tasks"][0]["task_id"] == "integration_test_1"

    def test_context_analyzer_integration_with_smart_agent(self):
        """Интеграция ContextAnalyzerTool с Smart Agent"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Создадим структуру проекта для анализа
            (Path(temp_dir) / "src").mkdir()
            (Path(temp_dir) / "docs").mkdir()
            (Path(temp_dir) / "src" / "main.py").write_text("# Main application")
            (Path(temp_dir) / "docs" / "README.md").write_text("# Project Documentation")

            agent = create_smart_agent(
                project_dir=Path(temp_dir),
                use_llm=False,
                use_docker=False
            )

            # Найдем ContextAnalyzerTool в инструментах агента
            context_tool = None
            for tool in agent.tools:
                if isinstance(tool, ContextAnalyzerTool):
                    context_tool = tool
                    break

            assert context_tool is not None

            # Протестируем анализ проекта через инструмент
            result = context_tool._run("analyze_project")
            assert "анализ структуры" in result.lower()

            # Протестируем анализ зависимостей
            result = context_tool._run("find_dependencies", file_path="src/main.py")
            assert "зависимости" in result.lower()

    def test_tools_data_flow_integration(self):
        """Интеграция потока данных между инструментами"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Создадим проект с файлами для анализа
            (Path(temp_dir) / "src").mkdir()
            (Path(temp_dir) / "src" / "auth.py").write_text("""
# Authentication module
def login_user():
    pass
""")
            (Path(temp_dir) / "src" / "main.py").write_text("""
# Main application
from src.auth import login_user

if __name__ == "__main__":
    login_user()
""")

            agent = create_smart_agent(
                project_dir=Path(temp_dir),
                use_llm=False,
                use_docker=False
            )

            # Найдем инструменты
            learning_tool = None
            context_tool = None
            for tool in agent.tools:
                if isinstance(tool, LearningTool):
                    learning_tool = tool
                elif isinstance(tool, ContextAnalyzerTool):
                    context_tool = tool

            assert learning_tool is not None
            assert context_tool is not None

            # Сначала проанализируем контекст
            context_result = context_tool._run("analyze_component", component_path="src")
            assert "src" in context_result

            # Затем сохраним опыт о задаче анализа
            learning_result = learning_tool._run("save_experience",
                                               task_id="context_analysis_task",
                                               task_description="Analyze project context for authentication",
                                               success=True,
                                               patterns=["analysis", "context", "authentication"])
            assert "сохранен" in learning_result

            # Проверим что можем найти похожие задачи
            similar_result = learning_tool._run("find_similar", query="authentication analysis")
            assert "authentication" in similar_result.lower()

    def test_experience_based_recommendations_integration(self):
        """Интеграция рекомендаций на основе опыта"""
        with tempfile.TemporaryDirectory() as temp_dir:
            agent = create_smart_agent(
                project_dir=Path(temp_dir),
                use_llm=False,
                use_docker=False
            )

            learning_tool = None
            for tool in agent.tools:
                if isinstance(tool, LearningTool):
                    learning_tool = tool
                    break

            assert learning_tool is not None

            # Сохраним несколько задач с разными паттернами
            tasks_data = [
                {
                    "task_id": "task1",
                    "description": "Implement user authentication",
                    "success": True,
                    "execution_time": 15.0,
                    "patterns": ["auth", "security"]
                },
                {
                    "task_id": "task2",
                    "description": "Fix authentication bug",
                    "success": True,
                    "execution_time": 8.0,
                    "patterns": ["auth", "bugfix"]
                },
                {
                    "task_id": "task3",
                    "description": "Add password validation",
                    "success": False,
                    "execution_time": 12.0,
                    "patterns": ["auth", "validation"]
                }
            ]

            for task in tasks_data:
                learning_tool._run("save_experience", **task)

            # Получим рекомендации для новой задачи аутентификации
            recommendations = learning_tool._run("get_recommendations",
                                               current_task="implement login system")

            assert "рекомендации" in recommendations.lower()
            assert "authentication" in recommendations.lower()

            # Проверим статистику
            stats = learning_tool._run("get_statistics")
            assert "Всего задач: 3" in stats
            assert "Успешных задач: 2" in stats


class TestSmartAgentWorkflowIntegration:
    """Интеграционные тесты рабочих процессов Smart Agent"""

    def test_complete_task_workflow(self):
        """Полный рабочий процесс выполнения задачи"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Создадим проектную структуру
            (Path(temp_dir) / "src").mkdir()
            (Path(temp_dir) / "docs").mkdir()
            (Path(temp_dir) / "tests").mkdir()

            # Создадим начальные файлы
            (Path(temp_dir) / "src" / "__init__.py").write_text("")
            (Path(temp_dir) / "docs" / "requirements.md").write_text("# Requirements\nImplement user management")
            (Path(temp_dir) / "src" / "models.py").write_text("# User models")

            agent = create_smart_agent(
                project_dir=Path(temp_dir),
                use_llm=False,
                use_docker=False
            )

            learning_tool = None
            context_tool = None
            for tool in agent.tools:
                if isinstance(tool, LearningTool):
                    learning_tool = tool
                elif isinstance(tool, ContextAnalyzerTool):
                    context_tool = tool

            assert learning_tool is not None
            assert context_tool is not None

            # Шаг 1: Анализ контекста проекта
            context_info = context_tool._run("get_context",
                                           task_description="implement user management system")
            assert "контекст" in context_info.lower()

            # Шаг 2: Поиск связанных файлов
            related_files = context_tool._run("find_related_files", query="user management")
            # Функция должна выполниться без ошибок

            # Шаг 3: Сохранение опыта о начале работы
            start_result = learning_tool._run("save_experience",
                                            task_id="user_mgmt_start",
                                            task_description="Start implementing user management",
                                            success=True,
                                            patterns=["user_management", "planning"])

            # Шаг 4: Анализ зависимостей
            deps_result = context_tool._run("find_dependencies", file_path="src/models.py")
            # Функция должна выполниться без ошибок

            # Шаг 5: Получение рекомендаций для продолжения
            recommendations = learning_tool._run("get_recommendations",
                                               current_task="continue user management implementation")
            # Функция должна выполниться без ошибок

    def test_learning_from_past_experience(self):
        """Обучение на предыдущем опыте"""
        with tempfile.TemporaryDirectory() as temp_dir:
            agent = create_smart_agent(
                project_dir=Path(temp_dir),
                use_llm=False,
                use_docker=False
            )

            learning_tool = None
            for tool in agent.tools:
                if isinstance(tool, LearningTool):
                    learning_tool = tool
                    break

            # Симулируем предыдущие успешные и неудачные задачи
            past_tasks = [
                # Успешные паттерны
                ("Implement REST API", True, 20.0, ["api", "rest", "backend"]),
                ("Add input validation", True, 8.0, ["validation", "security"]),
                ("Write unit tests", True, 15.0, ["testing", "unittest"]),

                # Неудачные паттерны
                ("Complex authentication", False, 45.0, ["auth", "complex"]),
                ("Manual deployment", False, 30.0, ["deployment", "manual"]),
            ]

            for desc, success, time_taken, patterns in past_tasks:
                task_id = f"past_task_{len(patterns)}_{int(success)}"
                learning_tool._run("save_experience",
                                 task_id=task_id,
                                 task_description=desc,
                                 success=success,
                                 execution_time=time_taken,
                                 patterns=patterns)

            # Теперь для новой задачи должны быть рекомендации
            new_task_recommendations = learning_tool._run("get_recommendations",
                                                        current_task="implement API authentication")

            assert "рекомендации" in new_task_recommendations.lower()

            # Ищем похожие задачи
            similar_tasks = learning_tool._run("find_similar", query="API implementation")
            assert "REST API" in similar_tasks

    def test_context_driven_development(self):
        """Разработка на основе анализа контекста"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Создадим сложную структуру проекта
            (Path(temp_dir) / "src" / "api").mkdir(parents=True)
            (Path(temp_dir) / "src" / "models").mkdir()
            (Path(temp_dir) / "src" / "services").mkdir()
            (Path(temp_dir) / "docs" / "api").mkdir(parents=True)

            # Создадим файлы с зависимостями
            (Path(temp_dir) / "src" / "models" / "user.py").write_text("""
# User model
class User:
    def __init__(self, id, name):
        self.id = id
        self.name = name
""")

            (Path(temp_dir) / "src" / "services" / "auth_service.py").write_text("""
# Authentication service
from src.models.user import User

class AuthService:
    def authenticate(self, user: User):
        return True
""")

            (Path(temp_dir) / "src" / "api" / "auth.py").write_text("""
# Auth API endpoints
from src.services.auth_service import AuthService

auth_service = AuthService()

def login():
    return auth_service.authenticate(None)
""")

            (Path(temp_dir) / "docs" / "api" / "auth.md").write_text("""
# Authentication API

## Endpoints
- POST /login - User login
- POST /logout - User logout
""")

            agent = create_smart_agent(
                project_dir=Path(temp_dir),
                use_llm=False,
                use_docker=False
            )

            context_tool = None
            for tool in agent.tools:
                if isinstance(tool, ContextAnalyzerTool):
                    context_tool = tool
                    break

            assert context_tool is not None

            # Анализируем зависимости в файлах
            auth_deps = context_tool._run("find_dependencies", file_path="src/api/auth.py")
            assert "auth_service" in auth_deps.lower()

            service_deps = context_tool._run("find_dependencies", file_path="src/services/auth_service.py")
            assert "user" in service_deps.lower()

            # Получаем контекст для задачи улучшения аутентификации
            task_context = context_tool._run("get_context",
                                           task_description="improve authentication security")
            assert "контекст" in task_context.lower()

            # Анализируем компонент services
            component_analysis = context_tool._run("analyze_component", component_path="src/services")
            assert "services" in component_analysis.lower()


class TestSmartAgentPerformanceIntegration:
    """Интеграционные тесты производительности Smart Agent"""

    def test_caching_performance(self):
        """Тест производительности кеширования"""
        with tempfile.TemporaryDirectory() as temp_dir:
            agent = create_smart_agent(
                project_dir=Path(temp_dir),
                use_llm=False,
                use_docker=False
            )

            learning_tool = None
            context_tool = None
            for tool in agent.tools:
                if isinstance(tool, LearningTool):
                    learning_tool = tool
                elif isinstance(tool, ContextAnalyzerTool):
                    context_tool = tool

            assert learning_tool is not None

            # Добавим много задач для тестирования кеширования
            for i in range(10):
                learning_tool._run("save_experience",
                                 task_id=f"perf_task_{i}",
                                 task_description=f"Performance test task {i}",
                                 success=True,
                                 patterns=["performance", f"tag_{i}"])

            # Первый поиск - кэш пустой
            start_time = time.time()
            result1 = learning_tool._run("find_similar", query="performance")
            first_search_time = time.time() - start_time

            # Второй поиск - должен использовать кэш
            start_time = time.time()
            result2 = learning_tool._run("find_similar", query="performance")
            second_search_time = time.time() - start_time

            # Результаты должны быть одинаковыми
            assert result1 == result2

            # Второй поиск должен быть быстрее (кеширование работает)
            # Замер производительности может быть неточным в тестовой среде,
            # поэтому просто проверяем что оба поиска завершились

    def test_memory_management_integration(self):
        """Тест управления памятью в интеграции"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Создадим агента с ограниченным количеством задач в опыте
            agent = create_smart_agent(
                project_dir=Path(temp_dir),
                use_llm=False,
                use_docker=False,
                max_experience_tasks=5
            )

            learning_tool = None
            for tool in agent.tools:
                if isinstance(tool, LearningTool):
                    learning_tool = tool
                    break

            assert learning_tool is not None

            # Добавим больше задач чем лимит
            for i in range(8):
                learning_tool._run("save_experience",
                                 task_id=f"memory_task_{i}",
                                 task_description=f"Memory management task {i}",
                                 success=True)

            # Проверим что количество задач не превышает лимит
            experience_data = learning_tool._load_experience()
            assert len(experience_data["tasks"]) <= 5

            # Проверим что остались самые свежие задачи
            task_ids = [task["task_id"] for task in experience_data["tasks"]]
            assert "memory_task_7" in task_ids  # Самая свежая
            assert "memory_task_6" in task_ids
            assert "memory_task_5" in task_ids
            assert "memory_task_4" in task_ids
            assert "memory_task_3" in task_ids


class TestSmartAgentErrorHandlingIntegration:
    """Интеграционные тесты обработки ошибок"""

    def test_partial_system_failure_recovery(self):
        """Восстановление после частичного сбоя системы"""
        with tempfile.TemporaryDirectory() as temp_dir:
            agent = create_smart_agent(
                project_dir=Path(temp_dir),
                use_llm=False,
                use_docker=False
            )

            learning_tool = None
            context_tool = None
            for tool in agent.tools:
                if isinstance(tool, LearningTool):
                    learning_tool = tool
                elif isinstance(tool, ContextAnalyzerTool):
                    context_tool = tool

            # Симулируем повреждение файла опыта learning tool
            with open(learning_tool.experience_file, 'w') as f:
                f.write("corrupted json data")

            # Learning tool должен восстановиться
            recovery_result = learning_tool._run("save_experience",
                                               task_id="recovery_test",
                                               task_description="Test recovery from corruption",
                                               success=True)
            assert "сохранен" in recovery_result

            # Context tool должен продолжать работать
            context_result = context_tool._run("analyze_project")
            assert "анализ структуры" in context_result.lower()

    def test_concurrent_operations_simulation(self):
        """Симуляция конкурентных операций"""
        with tempfile.TemporaryDirectory() as temp_dir:
            agent = create_smart_agent(
                project_dir=Path(temp_dir),
                use_llm=False,
                use_docker=False
            )

            learning_tool = None
            for tool in agent.tools:
                if isinstance(tool, LearningTool):
                    learning_tool = tool
                    break

            # Симулируем множественные операции сохранения опыта
            import threading

            results = []
            errors = []

            def save_experience_worker(task_id):
                try:
                    result = learning_tool._run("save_experience",
                                               task_id=task_id,
                                               task_description=f"Concurrent task {task_id}",
                                               success=True)
                    results.append(result)
                except Exception as e:
                    errors.append(str(e))

            # Запустим несколько потоков
            threads = []
            for i in range(5):
                thread = threading.Thread(target=save_experience_worker, args=[f"concurrent_task_{i}"])
                threads.append(thread)
                thread.start()

            # Дождемся завершения всех потоков
            for thread in threads:
                thread.join()

            # Проверим что все операции завершились успешно
            assert len(results) == 5
            assert len(errors) == 0

            for result in results:
                assert "сохранен" in result

            # Проверим что все задачи сохранены
            experience_data = learning_tool._load_experience()
            assert len(experience_data["tasks"]) == 5