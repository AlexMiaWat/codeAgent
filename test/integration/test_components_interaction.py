"""
Интеграционные тесты для проверки взаимодействия компонентов Code Agent

Тестирует взаимодействие между:
- ConfigLoader и EnvConfig
- LLMManager и CrewAILLMWrapper
- Server и TaskManager
- Smart Agent и его инструментами
- Tools между собой
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch


class TestConfigComponentsInteraction:
    """Тесты взаимодействия компонентов конфигурации"""

    def test_config_loader_env_config_interaction(self, monkeypatch):
        """Тест взаимодействия ConfigLoader и EnvConfig"""
        from src.config_loader import ConfigLoader
        from src.config.env_config import EnvConfig

        # Создаем временную директорию для проекта
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir)

            # Устанавливаем PROJECT_DIR в окружение
            monkeypatch.setenv('PROJECT_DIR', str(project_dir))

            # Создаем базовую структуру проекта
            (project_dir / 'docs').mkdir()
            (project_dir / 'todo.md').write_text('# Test Tasks\n- [ ] Test task\n')

            # Создаем конфигурационный файл
            config_file = project_dir / 'config.yaml'
            config_content = {
                'project': {
                    'base_dir': '${PROJECT_DIR}',
                    'docs_dir': 'docs',
                    'status_file': 'codeAgentProjectStatus.md',
                    'todo_format': 'md'
                },
                'agent': {
                    'role': 'Test Agent',
                    'backstory': 'Test backstory'
                }
            }

            with open(config_file, 'w', encoding='utf-8') as f:
                import yaml
                yaml.dump(config_content, f)

            # Загружаем конфигурацию через ConfigLoader
            loader = ConfigLoader(str(config_file))
            config = loader.config

            # Проверяем что переменная окружения была подставлена
            assert str(config['project']['base_dir']) == str(project_dir)

            # Загружаем EnvConfig
            env_config = EnvConfig.load()

            # Проверяем что PROJECT_DIR корректно загружен
            assert env_config.project_dir == project_dir

    def test_env_config_validation_interaction(self):
        """Тест взаимодействия валидации EnvConfig"""
        from src.config.env_config import EnvConfig

        # Создаем валидную конфигурацию
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir)

            # Создаем экземпляр с валидными данными
            config = EnvConfig(
                project_dir=project_dir,
                smart_agent_enabled=True,
                smart_agent_max_experience_tasks=100,
                learning_tool_cache_size=50,
                context_analyzer_max_depth=3,
                log_level='INFO',
                max_file_size=2048
            )

            # Проверяем валидацию
            errors = config.validate()
            assert len(errors) == 0  # Нет ошибок валидации


class TestLLMComponentsInteraction:
    """Тесты взаимодействия LLM компонентов"""

    @patch('src.llm.llm_manager.LLMManager')
    def test_llm_manager_crewai_wrapper_interaction(self, mock_llm_manager_class):
        """Тест взаимодействия LLMManager и CrewAILLMWrapper"""
        from src.llm.crewai_llm_wrapper import create_llm_for_crewai

        # Настраиваем мок LLMManager
        mock_llm_manager = Mock()
        mock_llm_manager_class.return_value = mock_llm_manager
        mock_llm_manager.get_llm.return_value = Mock()

        # Вызываем функцию создания LLM для CrewAI
        llm = create_llm_for_crewai()

        # Проверяем что LLMManager был создан и вызван
        mock_llm_manager_class.assert_called_once()
        mock_llm_manager.get_llm.assert_called_once()

        # Проверяем что вернулся корректный объект
        assert llm is not None

    @patch('src.llm.llm_manager.LLMManager')
    def test_llm_components_error_handling(self, mock_llm_manager_class):
        """Тест обработки ошибок в LLM компонентах"""
        from src.llm.crewai_llm_wrapper import create_llm_for_crewai

        # Настраиваем мок на выброс исключения
        mock_llm_manager_class.side_effect = Exception("Test error")

        # Вызываем функцию и проверяем что исключение обработано
        llm = create_llm_for_crewai()

        # При ошибке должна вернуться None
        assert llm is None


class TestServerTaskManagerInteraction:
    """Тесты взаимодействия Server и TaskManager"""

    def test_server_task_manager_initialization(self, ensure_project_dir_env):
        """Тест инициализации Server с TaskManager"""
        from src.server import CodeAgentServer
        from src.todo_manager import TodoManager

        # Создаем сервер с моками
        with patch('src.server.CodeAgentServer._setup_http_server'):
            with patch('src.server.CodeAgentServer._setup_file_watcher'):
                with patch('src.cursor_cli_interface.CursorCLIInterface.check_availability', return_value=False):
                    server = CodeAgentServer()

                    # Проверяем что TaskManager инициализирован
                    assert hasattr(server, 'todo_manager')
                    assert isinstance(server.todo_manager, TodoManager)

    def test_server_task_execution_workflow(self, ensure_project_dir_env):
        """Тест рабочего процесса выполнения задач"""
        from src.server import CodeAgentServer

        with patch('src.server.CodeAgentServer._setup_http_server'):
            with patch('src.server.CodeAgentServer._setup_file_watcher'):
                with patch('src.cursor_cli_interface.CursorCLIInterface.check_availability', return_value=False):
                    with patch('src.agents.executor_agent.ExecutorAgent') as mock_agent_class:
                        # Настраиваем мок агента
                        mock_agent = Mock()
                        mock_agent_class.return_value = mock_agent
                        mock_agent.execute_task.return_value = "Task completed"

                        server = CodeAgentServer()

                        # Проверяем что сервер может выполнить задачу
                        # (здесь просто проверяем инициализацию компонентов)
                        assert server is not None
                        assert server.todo_manager is not None


class TestSmartAgentToolsInteraction:
    """Тесты взаимодействия Smart Agent и его инструментов"""

    def test_smart_agent_tools_integration(self):
        """Тест интеграции Smart Agent с инструментами"""
        from src.tools.learning_tool import LearningTool
        from src.tools.context_analyzer_tool import ContextAnalyzerTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir)

            # Создаем инструменты
            learning_tool = LearningTool(experience_dir="test_experience")
            context_tool = ContextAnalyzerTool(project_dir=project_dir)

            # Проверяем что инструменты созданы корректно
            assert learning_tool.name == "LearningTool"
            assert context_tool.name == "ContextAnalyzerTool"

            # Проверяем что инструменты имеют необходимые методы
            assert hasattr(learning_tool, '_run')
            assert hasattr(context_tool, '_run')

            # Проверяем что инструменты могут взаимодействовать
            # (оба инструмента работают с файловой системой)
            assert learning_tool.experience_dir.exists()
            assert context_tool.project_dir.exists()

    @patch('src.agents.smart_agent.is_docker_available', return_value=False)
    @patch('src.llm.crewai_llm_wrapper.create_llm_for_crewai', return_value=None)
    def test_smart_agent_full_integration(self, mock_llm, mock_docker):
        """Тест полной интеграции Smart Agent со всеми компонентами"""
        from src.agents.smart_agent import create_smart_agent

        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir)

            # Создаем Smart Agent
            agent = create_smart_agent(
                project_dir=project_dir,
                use_docker=False,
                use_llm=False,
                verbose=False
            )

            # Проверяем что агент создан
            assert agent is not None

            # Проверяем что у агента есть инструменты
            assert hasattr(agent, 'tools')
            assert len(agent.tools) >= 2  # Минимум LearningTool и ContextAnalyzerTool

            # Проверяем типы инструментов
            tool_names = [tool.__class__.__name__ for tool in agent.tools]
            assert "LearningTool" in tool_names
            assert "ContextAnalyzerTool" in tool_names


class TestToolsInteraction:
    """Тесты взаимодействия между инструментами"""

    def test_tools_shared_resources(self):
        """Тест использования общих ресурсов инструментами"""
        from src.tools.learning_tool import LearningTool
        from src.tools.context_analyzer_tool import ContextAnalyzerTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir)

            # Создаем инструменты, которые работают с одной директорией
            learning_tool = LearningTool(experience_dir="shared_experience")
            context_tool = ContextAnalyzerTool(project_dir=project_dir)

            # Оба инструмента могут читать файлы из одной директории
            assert learning_tool.experience_dir.exists()
            assert context_tool.project_dir == project_dir

            # Создаем тестовый файл в директории проекта
            test_file = project_dir / "test.md"
            test_file.write_text("# Test content\n")

            # ContextAnalyzerTool может анализировать этот файл
            # (проверяем что файл доступен)
            assert test_file.exists()
            assert test_file.read_text() == "# Test content\n"

    def test_tools_data_exchange(self):
        """Тест обмена данными между инструментами"""
        from src.tools.learning_tool import LearningTool

        # Создаем LearningTool
        tool = LearningTool(experience_dir="test_exchange")

        # Добавляем тестовый опыт
        test_experience = {
            "task": "test task",
            "solution": "test solution",
            "success": True
        }

        # Сохраняем опыт
        tool.save_experience(test_experience)

        # Проверяем что опыт сохранен
        assert tool.experience_file.exists()

        # Читаем опыт обратно
        experiences = tool.load_experiences()
        assert len(experiences) > 0

        # Проверяем что данные корректны
        found_experience = None
        for exp in experiences:
            if exp.get("task") == "test task":
                found_experience = exp
                break

        assert found_experience is not None
        assert found_experience["solution"] == "test solution"
        assert found_experience["success"]


class TestErrorHandlingIntegration:
    """Тесты интеграции обработки ошибок"""

    def test_component_error_isolation(self):
        """Тест изоляции ошибок между компонентами"""
        from src.config.env_config import EnvConfig

        # Создаем конфигурацию с потенциально проблемными данными
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir)

            # Создаем конфигурацию с граничными значениями
            config = EnvConfig(
                project_dir=project_dir,
                smart_agent_max_experience_tasks=5,  # Ниже минимума
                learning_tool_cache_size=5,          # Ниже минимума
                context_analyzer_max_depth=0,        # Ниже минимума
                max_file_size=512                    # Ниже минимума
            )

            # Проверяем валидацию - должны быть ошибки
            errors = config.validate()
            assert len(errors) > 0

            # Но объект конфигурации создан и функционален
            assert config.project_dir == project_dir
            assert config.smart_agent_max_experience_tasks == 5

    def test_graceful_degradation(self):
        """Тест graceful degradation при недоступности компонентов"""
        from src.agents.smart_agent import create_smart_agent

        with patch('src.agents.smart_agent.is_docker_available', return_value=False):
            with patch('src.llm.crewai_llm_wrapper.create_llm_for_crewai', return_value=None):
                with tempfile.TemporaryDirectory() as tmp_dir:
                    project_dir = Path(tmp_dir)

                    # Создаем агента без LLM и Docker
                    agent = create_smart_agent(
                        project_dir=project_dir,
                        use_docker=False,
                        use_llm=False,
                        allow_code_execution=False,
                        verbose=False
                    )

                    # Агент должен быть создан несмотря на недоступность компонентов
                    assert agent is not None

                    # Проверяем что инструменты адаптировались к отсутствию Docker
                    tool_names = [tool.__class__.__name__ for tool in agent.tools]
                    assert "CodeInterpreterTool" not in tool_names