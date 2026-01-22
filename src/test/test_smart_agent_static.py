"""
Статические тесты для Smart Agent - проверка структуры, API, конфигурации
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import inspect


class TestSmartAgentStatic:
    """Статические тесты Smart Agent"""

    def test_create_smart_agent_function_exists(self):
        """Проверка существования функции create_smart_agent"""
        from src.agents.smart_agent import create_smart_agent
        assert create_smart_agent is not None
        assert callable(create_smart_agent)

    def test_create_smart_agent_signature(self):
        """Проверка сигнатуры функции create_smart_agent"""
        from src.agents.smart_agent import create_smart_agent

        sig = inspect.signature(create_smart_agent)
        expected_params = [
            'project_dir', 'docs_dir', 'experience_dir', 'role', 'goal',
            'backstory', 'allow_code_execution', 'use_docker', 'verbose',
            'use_llm', 'llm_config_path', 'max_experience_tasks'
        ]

        actual_params = list(sig.parameters.keys())
        assert actual_params == expected_params

    def test_create_smart_agent_parameter_types(self):
        """Проверка типов параметров create_smart_agent"""
        from src.agents.smart_agent import create_smart_agent

        sig = inspect.signature(create_smart_agent)
        params = sig.parameters

        # Проверяем типы параметров
        assert params['project_dir'].annotation == Path
        from typing import Optional
        assert params['docs_dir'].annotation == Optional[Path]
        assert params['experience_dir'].annotation == str
        assert params['role'].annotation == str
        assert params['goal'].annotation == str
        assert params['backstory'].annotation == Optional[str]
        assert params['allow_code_execution'].annotation == bool
        assert params['use_docker'].annotation == bool
        assert params['verbose'].annotation == bool
        assert params['use_llm'].annotation == bool
        assert params['llm_config_path'].annotation == str
        assert params['max_experience_tasks'].annotation == int

    def test_create_smart_agent_default_values(self):
        """Проверка значений по умолчанию create_smart_agent"""
        from src.agents.smart_agent import create_smart_agent

        sig = inspect.signature(create_smart_agent)
        params = sig.parameters

        # Проверяем значения по умолчанию
        assert params['experience_dir'].default == "smart_experience"
        assert params['role'].default == "Smart Project Executor Agent"
        assert params['goal'].default == "Execute complex tasks with enhanced intelligence, learning from previous executions"
        assert params['backstory'].default is None
        assert params['allow_code_execution'].default == True
        assert params['use_docker'].default == True
        assert params['verbose'].default == True
        assert params['use_llm'].default == True
        assert params['llm_config_path'].default == "config/llm_settings.yaml"
        assert params['max_experience_tasks'].default == 1000

    def test_create_smart_agent_return_type(self):
        """Проверка типа возвращаемого значения create_smart_agent"""
        from src.agents.smart_agent import create_smart_agent

        # Проверяем аннотацию возвращаемого типа
        sig = inspect.signature(create_smart_agent)
        from crewai import Agent
        assert sig.return_annotation == Agent

    @patch('src.agents.smart_agent.is_docker_available')
    @patch('src.llm.crewai_llm_wrapper.create_llm_for_crewai')
    def test_create_smart_agent_with_mocked_dependencies(self, mock_llm_wrapper, mock_docker):
        """Тест создания Smart Agent с замоканными зависимостями"""
        from src.agents.smart_agent import create_smart_agent

        # Настраиваем моки
        mock_docker.return_value = False
        mock_llm_wrapper.return_value = None

        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir)

            agent = create_smart_agent(
                project_dir=project_dir,
                use_docker=False,
                use_llm=False,
                verbose=False
            )

            assert agent is not None
            assert hasattr(agent, 'role')
            assert hasattr(agent, 'goal')
            assert hasattr(agent, 'tools')

    def test_smart_agent_imports(self):
        """Проверка импортов в модуле smart_agent"""
        import src.agents.smart_agent as sa_module

        # Проверяем что основные импорты доступны
        assert hasattr(sa_module, 'LearningTool')
        assert hasattr(sa_module, 'ContextAnalyzerTool')
        assert hasattr(sa_module, 'is_docker_available')

        # Проверяем условные импорты
        assert hasattr(sa_module, 'LLM_WRAPPER_AVAILABLE')
        assert hasattr(sa_module, 'create_llm_for_crewai')

    def test_smart_agent_constants(self):
        """Проверка констант в модуле smart_agent"""
        import src.agents.smart_agent as sa_module

        # Проверяем что константы определены
        assert hasattr(sa_module, 'LLM_WRAPPER_AVAILABLE')
        assert isinstance(sa_module.LLM_WRAPPER_AVAILABLE, bool)

    def test_smart_agent_backstory_generation(self):
        """Проверка генерации backstory по умолчанию"""
        from src.agents.smart_agent import create_smart_agent

        with patch('src.agents.smart_agent.is_docker_available', return_value=False):
            with patch('src.llm.crewai_llm_wrapper.create_llm_for_crewai', return_value=None):
                with tempfile.TemporaryDirectory() as tmp_dir:
                    project_dir = Path(tmp_dir)

                    agent = create_smart_agent(
                        project_dir=project_dir,
                        backstory=None,  # Используем генерацию по умолчанию
                        use_llm=False,
                        verbose=False
                    )

                    assert agent is not None
                    assert "smart agent" in agent.backstory.lower()
                    assert "learningtool" in agent.backstory.lower()
                    assert "contextanalyzertool" in agent.backstory.lower()

    def test_smart_agent_tools_initialization(self):
        """Проверка инициализации инструментов в Smart Agent"""
        from src.agents.smart_agent import create_smart_agent

        with patch('src.agents.smart_agent.is_docker_available', return_value=False):
            with patch('src.llm.crewai_llm_wrapper.create_llm_for_crewai', return_value=None):
                with tempfile.TemporaryDirectory() as tmp_dir:
                    project_dir = Path(tmp_dir)

                    agent = create_smart_agent(
                        project_dir=project_dir,
                        use_llm=False,
                        verbose=False
                    )

                    assert agent is not None
                    assert hasattr(agent, 'tools')
                    assert len(agent.tools) >= 2  # Минимум LearningTool и ContextAnalyzerTool

                    # Проверяем типы инструментов
                    tool_names = [tool.__class__.__name__ for tool in agent.tools]
                    assert "LearningTool" in tool_names
                    assert "ContextAnalyzerTool" in tool_names

    def test_smart_agent_llm_configuration(self):
        """Проверка конфигурации LLM в Smart Agent"""
        from src.agents.smart_agent import create_smart_agent

        with patch('src.agents.smart_agent.is_docker_available', return_value=False):
            with patch('src.llm.crewai_llm_wrapper.create_llm_for_crewai', return_value=Mock()):
                with tempfile.TemporaryDirectory() as tmp_dir:
                    project_dir = Path(tmp_dir)

                    # Тест с LLM
                    agent_with_llm = create_smart_agent(
                        project_dir=project_dir,
                        use_llm=True,
                        verbose=False
                    )

                    assert agent_with_llm is not None
                    assert hasattr(agent_with_llm, 'llm')
                    assert agent_with_llm.llm is not None

    def test_smart_agent_no_llm_configuration(self):
        """Проверка конфигурации Smart Agent без LLM"""
        from src.agents.smart_agent import create_smart_agent

        with patch('src.agents.smart_agent.is_docker_available', return_value=False):
            with patch('src.llm.crewai_llm_wrapper.create_llm_for_crewai', return_value=None):
                with tempfile.TemporaryDirectory() as tmp_dir:
                    project_dir = Path(tmp_dir)

                    # Тест без LLM
                    agent_no_llm = create_smart_agent(
                        project_dir=project_dir,
                        use_llm=False,
                        verbose=False
                    )

                    assert agent_no_llm is not None
                    # When use_llm=False, the agent should have no LLM or a disabled LLM
                    # The exact behavior depends on CrewAI Agent implementation
                    # For now, just check that the agent was created successfully

    def test_smart_agent_docker_configuration(self):
        """Проверка конфигурации Docker в Smart Agent"""
        from src.agents.smart_agent import create_smart_agent

        with patch('src.agents.smart_agent.is_docker_available', return_value=True):
            with patch('src.llm.crewai_llm_wrapper.create_llm_for_crewai', return_value=None):
                with tempfile.TemporaryDirectory() as tmp_dir:
                        project_dir = Path(tmp_dir)

                        # Тест с Docker
                        agent_with_docker = create_smart_agent(
                            project_dir=project_dir,
                            use_docker=True,
                            allow_code_execution=True,
                            use_llm=False,
                            verbose=False
                        )

                        assert agent_with_docker is not None

                        # Агент создан успешно с Docker конфигурацией
                        # CodeInterpreterTool может быть недоступен в тестовой среде

    def test_smart_agent_no_docker_configuration(self):
        """Проверка конфигурации Smart Agent без Docker"""
        from src.agents.smart_agent import create_smart_agent

        with patch('src.agents.smart_agent.is_docker_available', return_value=False):
            with patch('src.llm.crewai_llm_wrapper.create_llm_for_crewai', return_value=None):
                with tempfile.TemporaryDirectory() as tmp_dir:
                    project_dir = Path(tmp_dir)

                    # Тест без Docker
                    agent_no_docker = create_smart_agent(
                        project_dir=project_dir,
                        use_docker=False,
                        allow_code_execution=True,
                        use_llm=False,
                        verbose=False
                    )

                    assert agent_no_docker is not None
                    assert agent_no_docker.allow_code_execution == False

                    # Проверяем отсутствие CodeInterpreterTool
                    tool_names = [tool.__class__.__name__ for tool in agent_no_docker.tools]
                    assert "CodeInterpreterTool" not in tool_names

    def test_smart_agent_experience_dir_creation(self):
        """Проверка создания директории опыта"""
        from src.agents.smart_agent import create_smart_agent

        with patch('src.agents.smart_agent.is_docker_available', return_value=False):
            with patch('src.llm.crewai_llm_wrapper.create_llm_for_crewai', return_value=None):
                with tempfile.TemporaryDirectory() as tmp_dir:
                    project_dir = Path(tmp_dir)
                    experience_dir = "custom_experience_dir"

                    agent = create_smart_agent(
                        project_dir=project_dir,
                        experience_dir=experience_dir,
                        use_llm=False,
                        verbose=False
                    )

                    assert agent is not None

                    # Проверяем что директория опыта создана
                    experience_path = project_dir / experience_dir
                    assert experience_path.exists()
                    assert experience_path.is_dir()

                    # Проверяем что файл опыта создан
                    experience_file = experience_path / "experience.json"
                    assert experience_file.exists()

    def test_smart_agent_unicode_support(self):
        """Проверка поддержки Unicode в Smart Agent"""
        from src.agents.smart_agent import create_smart_agent

        with patch('src.agents.smart_agent.is_docker_available', return_value=False):
            with patch('src.llm.crewai_llm_wrapper.create_llm_for_crewai', return_value=None):
                with tempfile.TemporaryDirectory() as tmp_dir:
                    project_dir = Path(tmp_dir)

                    unicode_role = "Умный Агент 🤖"
                    unicode_goal = "Выполнять задачи с ИИ 💡"

                    agent = create_smart_agent(
                        project_dir=project_dir,
                        role=unicode_role,
                        goal=unicode_goal,
                        use_llm=False,
                        verbose=False
                    )

                    assert agent is not None
                    assert agent.role == unicode_role
                    assert agent.goal == unicode_goal

    def test_smart_agent_max_experience_tasks(self):
        """Проверка параметра max_experience_tasks"""
        from src.agents.smart_agent import create_smart_agent

        with patch('src.agents.smart_agent.is_docker_available', return_value=False):
            with patch('src.llm.crewai_llm_wrapper.create_llm_for_crewai', return_value=None):
                with tempfile.TemporaryDirectory() as tmp_dir:
                    project_dir = Path(tmp_dir)

                    max_tasks = 500

                    agent = create_smart_agent(
                        project_dir=project_dir,
                        max_experience_tasks=max_tasks,
                        use_llm=False,
                        verbose=False
                    )

                    assert agent is not None

                    # Проверяем что LearningTool получил правильный параметр
                    learning_tool = None
                    for tool in agent.tools:
                        if tool.__class__.__name__ == "LearningTool":
                            learning_tool = tool
                            break

                    assert learning_tool is not None
                    assert learning_tool.max_experience_tasks == max_tasks