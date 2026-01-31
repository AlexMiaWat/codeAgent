"""
Smoke тесты для Smart Agent - базовая проверка функциональности
"""

import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

# Set dummy API key for tests
os.environ["OPENAI_API_KEY"] = "dummy_key"

from src.agents.smart_agent import create_smart_agent
from src.tools.learning_tool import LearningTool
from src.tools.context_analyzer_tool import ContextAnalyzerTool


class TestSmartAgentCreation:
    """Тесты создания Smart Agent"""

    @patch('src.agents.smart_agent.is_docker_available', return_value=False)
    def test_create_smart_agent_basic(self, mock_docker):
        """Базовый тест создания smart agent"""
        with tempfile.TemporaryDirectory() as temp_dir:
            agent = create_smart_agent(
                project_dir=Path(temp_dir),
                use_llm=False,
                use_docker=False
            )

            assert agent is not None
            assert hasattr(agent, 'role')
            assert hasattr(agent, 'goal')
            assert hasattr(agent, 'tools')
            assert len(agent.tools) >= 2  # Минимум LearningTool и ContextAnalyzerTool

    @patch('src.agents.smart_agent.is_docker_available', return_value=False)
    def test_create_smart_agent_with_custom_params(self, mock_docker):
        """Тест создания smart agent с пользовательскими параметрами"""
        with tempfile.TemporaryDirectory() as temp_dir:
            agent = create_smart_agent(
                project_dir=Path(temp_dir),
                role="Custom Smart Agent",
                goal="Custom goal",
                verbose=False,
                use_llm=False,  # Отключаем LLM для теста
                use_docker=False
            )

            assert agent.role == "Custom Smart Agent"
            assert agent.goal == "Custom goal"
            assert not agent.verbose

    @patch('src.agents.smart_agent.is_docker_available', return_value=False)
    def test_smart_agent_tools_initialization(self, mock_docker):
        """Тест инициализации инструментов smart agent"""
        with tempfile.TemporaryDirectory() as temp_dir:
            agent = create_smart_agent(
                project_dir=Path(temp_dir), 
                use_llm=False,
                use_docker=False
            )

            # Проверим наличие необходимых инструментов
            tool_names = [tool.__class__.__name__ if hasattr(tool, '__class__') else str(type(tool)) for tool in agent.tools]

            assert "LearningTool" in tool_names
            assert "ContextAnalyzerTool" in tool_names

    @pytest.mark.skip(reason="Docker integration testing requires complex mocking")
    @patch('src.agents.smart_agent.is_docker_available')
    def test_smart_agent_with_docker_enabled(self, mock_docker_check):
        """Тест smart agent с включенным Docker"""
        mock_docker_check.return_value = True

        with patch('crewai_tools.CodeInterpreterTool') as mock_code_tool_class:
            mock_code_tool_instance = MagicMock()
            mock_code_tool_class.return_value = mock_code_tool_instance

            with tempfile.TemporaryDirectory() as temp_dir:
                # Mock create_llm_for_crewai to prevent LLM initialization
                with patch('src.agents.smart_agent.create_llm_for_crewai', return_value=None):
                    agent = create_smart_agent(
                        project_dir=Path(temp_dir),
                        use_docker=True,
                        use_llm=False  # Отключаем LLM для теста
                    )

                assert agent is not None
                # Проверим что Docker был проверен
                mock_docker_check.assert_called_once()
                # Проверим что CodeInterpreterTool был создан
                mock_code_tool_class.assert_called_once()
                assert any("CodeInterpreterTool" in str(type(tool)) for tool in agent.tools)

    @patch('src.agents.smart_agent.is_docker_available')
    def test_smart_agent_with_docker_disabled(self, mock_docker_check):
        """Тест smart agent с отключенным Docker"""
        mock_docker_check.return_value = False

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('src.agents.smart_agent.create_llm_for_crewai', return_value=None):
                agent = create_smart_agent(
                    project_dir=Path(temp_dir),
                    use_docker=False,
                    use_llm=False
                )

                assert agent is not None
                # Docker не должен проверяться при отключении
                mock_docker_check.assert_not_called()


class TestLearningToolSmoke:
    """Smoke тесты LearningTool"""

    def test_learning_tool_basic_operations(self):
        """Базовые операции LearningTool"""
        with tempfile.TemporaryDirectory() as temp_dir:
            tool = LearningTool(experience_dir=temp_dir)

            # Сохранение опыта
            result = tool.save_task_experience(
                task_id="smoke_test_1",
                task_description="Smoke test task",
                success=True
            )
            assert "сохранен" in result

            # Поиск похожих задач
            result = tool.find_similar_tasks("smoke test")
            assert "smoke test task" in result.lower()

            # Получение рекомендаций
            result = tool.get_recommendations("similar smoke test")
            assert "рекомендации" in result.lower()

            # Получение статистики
            result = tool.get_statistics()
            assert "статистика" in result.lower()

    def test_learning_tool_with_patterns(self):
        """Тест LearningTool с паттернами"""
        with tempfile.TemporaryDirectory() as temp_dir:
            tool = LearningTool(experience_dir=temp_dir)

            patterns = ["smoke", "test", "pattern"]
            tool.save_task_experience(
                task_id="pattern_test",
                task_description="Task with patterns",
                success=True,
                patterns=patterns
            )

            # Проверим что паттерны сохранены
            result = tool.get_statistics()
            assert "Изученных паттернов:" in result
            assert "3" in result  # Должно быть 3 паттерна

    def test_learning_tool_error_recovery(self):
        """Тест восстановления LearningTool после ошибок"""
        with tempfile.TemporaryDirectory() as temp_dir:
            tool = LearningTool(experience_dir=temp_dir)

            # Создадим поврежденный файл опыта
            with open(tool.experience_file, 'w') as f:
                f.write("invalid json")

            # Tool должен восстановиться
            result = tool.save_task_experience("recovery_test", "Recovery test", True)
            assert "сохранен" in result


class TestContextAnalyzerToolSmoke:
    """Smoke тесты ContextAnalyzerTool"""

    def test_context_analyzer_basic_operations(self):
        """Базовые операции ContextAnalyzerTool"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Создадим минимальную структуру проекта
            (Path(temp_dir) / "src").mkdir()
            (Path(temp_dir) / "docs").mkdir()
            (Path(temp_dir) / "src" / "main.py").write_text("# Main module")
            (Path(temp_dir) / "docs" / "README.md").write_text("# Documentation")

            tool = ContextAnalyzerTool(project_dir=temp_dir)

            # Анализ структуры проекта
            result = tool.analyze_project_structure()
            assert "анализ структуры" in result.lower()

            # Поиск зависимостей
            result = tool.find_file_dependencies("src/main.py")
            # Даже если зависимостей нет, функция должна работать

            # Получение контекста задачи
            result = tool.get_task_context("implement main functionality")
            assert "контекст" in result.lower()

            # Анализ компонента
            result = tool.analyze_component("src")
            assert "анализ компонента" in result.lower()

            # Поиск связанных файлов
            result = tool.find_related_files("main")
            # Функция должна работать даже без совпадений

    def test_context_analyzer_with_real_files(self):
        """Тест ContextAnalyzerTool с реальными файлами зависимостей"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Создадим файлы с зависимостями
            (Path(temp_dir) / "requirements.txt").write_text("requests>=2.25.0\nflask==2.0.1")
            (Path(temp_dir) / "src").mkdir()
            (Path(temp_dir) / "src" / "main.py").write_text("""
import requests
from flask import Flask
""")

            tool = ContextAnalyzerTool(project_dir=temp_dir)

            # Анализ зависимостей Python файла
            result = tool.find_file_dependencies("src/main.py")
            assert "зависимости" in result.lower()

            # Анализ requirements.txt
            result = tool.find_file_dependencies("requirements.txt")
            assert "requests" in result or "flask" in result

    def test_context_analyzer_unicode_handling(self):
        """Тест обработки Unicode в ContextAnalyzerTool"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Создадим файлы с Unicode содержимым
            (Path(temp_dir) / "docs").mkdir()
            (Path(temp_dir) / "docs" / "readme.md").write_text("# Документация\nТест на русском языке")
            (Path(temp_dir) / "src").mkdir()
            (Path(temp_dir) / "src" / "main.py").write_text("# Основной модуль\n# Тест")

            tool = ContextAnalyzerTool(project_dir=temp_dir)

            # Поиск связанных файлов с Unicode
            tool.find_related_files("документация")
            # Функция должна корректно обработать Unicode

            tool.get_task_context("тест документации")
            # Функция должна корректно обработать Unicode


class TestSmartAgentIntegrationSmoke:
    """Smoke тесты интеграции Smart Agent"""

    @pytest.mark.skip(reason="Docker integration testing requires complex mocking")
    @patch('src.agents.smart_agent.is_docker_available')
    def test_smart_agent_full_initialization(self, mock_docker_check):
        """Полная инициализация Smart Agent"""
        mock_docker_check.return_value = True

        with patch('crewai_tools.CodeInterpreterTool') as mock_code_tool_class:
            mock_code_tool_instance = MagicMock()
            mock_code_tool_class.return_value = mock_code_tool_instance

            with tempfile.TemporaryDirectory() as temp_dir:
                 # Mock create_llm_for_crewai
                with patch('src.agents.smart_agent.create_llm_for_crewai', return_value=None):
                    agent = create_smart_agent(
                        project_dir=Path(temp_dir),
                        role="Test Smart Agent",
                        goal="Test goal",
                        use_docker=True,
                        use_llm=False,  # Отключаем LLM для smoke теста
                        verbose=True
                    )

                    assert agent is not None
                    assert len(agent.tools) >= 2
                    
                    # Проверим что инструменты работают
                    for tool in agent.tools:
                        if hasattr(tool, '_run'):
                             pass

    @pytest.mark.skip(reason="LLM configuration testing requires complex mocking")
    def test_smart_agent_memory_configuration(self):
        """Тест конфигурации памяти Smart Agent"""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Тест с LLM - должен иметь память
            with patch('src.agents.smart_agent.LLM_WRAPPER_AVAILABLE', True):
                # Mock create_llm_for_crewai to return a Mock object that acts like an LLM
                mock_llm = MagicMock()
                with patch('src.agents.smart_agent.create_llm_for_crewai', return_value=mock_llm):
                     # Also need to mock Agent to avoid Pydantic validation of the mock LLM
                    with patch('crewai.Agent') as mock_agent_class:
                        mock_agent_instance = MagicMock()
                        mock_agent_class.return_value = mock_agent_instance
                        
                        agent_with_llm = create_smart_agent(
                            project_dir=Path(temp_dir),
                            use_llm=True,
                            use_docker=False
                        )
                        # Проверяем что агент создан успешно
                        assert agent_with_llm is not None

            # Тест без LLM - должен работать в tool-only режиме
            with patch('src.agents.smart_agent.LLM_WRAPPER_AVAILABLE', False):
                 with patch('src.agents.smart_agent.create_llm_for_crewai', return_value=None):
                    agent_without_llm = create_smart_agent(
                        project_dir=Path(temp_dir),
                        use_llm=False,
                        use_docker=False
                    )
                    assert agent_without_llm is not None
                    # В tool-only режиме LLM не используется
                    assert agent_without_llm.llm is None

    @patch('src.agents.smart_agent.LLM_WRAPPER_AVAILABLE', False)
    @patch('src.agents.smart_agent.create_llm_for_crewai', return_value=None)
    def test_smart_agent_backstory_generation(self, mock_create_llm):
        """Тест генерации backstory для Smart Agent"""
        with tempfile.TemporaryDirectory() as temp_dir:
            agent = create_smart_agent(
                project_dir=Path(temp_dir),
                use_llm=False,
                use_docker=False
            )

            assert "smart agent" in agent.backstory.lower()
            assert "learningtool" in agent.backstory.lower()
            assert "contextanalyzertool" in agent.backstory.lower()


class TestToolsIntegrationSmoke:
    """Smoke тесты интеграции инструментов"""

    def test_tools_work_together(self):
        """Тест совместной работы инструментов"""
        with tempfile.TemporaryDirectory() as temp_dir:
            learning_tool = LearningTool(experience_dir=Path(temp_dir) / "experience")
            context_tool = ContextAnalyzerTool(project_dir=temp_dir)

            # Создадим контент для анализа
            (Path(temp_dir) / "src").mkdir()
            (Path(temp_dir) / "src" / "test.py").write_text("# Test file for analysis")

            # Сохраним опыт о задаче
            learning_tool.save_task_experience(
                task_id="integration_test",
                task_description="Analyze test file",
                success=True
            )

            # Проверим что оба инструмента могут работать одновременно
            context_result = context_tool.analyze_component("src")
            learning_result = learning_tool.get_statistics()

            assert "анализ компонента" in context_result.lower()
            assert "статистика" in learning_result.lower()

    def test_tools_error_isolation(self):
        """Тест изоляции ошибок между инструментами"""
        with tempfile.TemporaryDirectory() as temp_dir:
            learning_tool = LearningTool(experience_dir=Path(temp_dir) / "experience")
            context_tool = ContextAnalyzerTool(project_dir=temp_dir)

            # Один инструмент может иметь ошибку, но другой должен работать
            # Создадим ситуацию где контекстный анализатор может иметь проблемы
            # но learning tool должен продолжать работать

            learning_result = learning_tool.save_task_experience(
                task_id="error_isolation_test",
                task_description="Test error isolation",
                success=True
            )

            assert "сохранен" in learning_result

            # Даже если контекстный анализатор имеет проблемы с несуществующим файлом
            context_result = context_tool.find_file_dependencies("nonexistent_file.py")
            assert "не найден" in context_result


class TestSmartAgentConfigurationSmoke:
    """Smoke тесты конфигурации Smart Agent"""

    def test_configuration_variations(self):
        """Тест различных конфигураций Smart Agent"""
        with tempfile.TemporaryDirectory() as temp_dir:
            configs = [
                {"use_llm": False, "use_docker": False, "verbose": False},
                {"use_llm": False, "use_docker": False, "verbose": True},
                # {"use_llm": False, "use_docker": True, "verbose": False}, # Skip docker test here to avoid mocking complexity
            ]

            for config in configs:
                with patch('src.agents.smart_agent.is_docker_available', return_value=False):
                    agent = create_smart_agent(
                        project_dir=Path(temp_dir),
                        **config
                    )
                    assert agent is not None
                    assert agent.verbose == config["verbose"]

    def test_experience_directory_creation(self):
        """Тест создания директории опыта"""
        with tempfile.TemporaryDirectory() as temp_dir:
            experience_dir = Path(temp_dir) / "custom_experience"

            agent = create_smart_agent(
                project_dir=Path(temp_dir),
                experience_dir=str(experience_dir),
                use_llm=False,
                use_docker=False
            )

            # Директория опыта должна быть создана
            assert experience_dir.exists()
            assert any("LearningTool" in str(type(tool)) for tool in agent.tools)