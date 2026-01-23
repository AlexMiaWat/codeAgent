"""
Статические тесты для Smart Agent - проверка типов, атрибутов, интерфейсов
"""

import pytest
import tempfile
import os
from pathlib import Path
from typing import Optional
from unittest.mock import Mock, patch


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


class TestSmartAgentStatic:
    """Статические тесты Smart Agent"""

    def test_create_smart_agent_function_signature(self):
        """Проверка сигнатуры функции create_smart_agent"""
        from src.agents.smart_agent import create_smart_agent
        import inspect

        # Проверяем сигнатуру функции
        sig = inspect.signature(create_smart_agent)
        expected_params = [
            'project_dir', 'docs_dir', 'experience_dir', 'role', 'goal',
            'backstory', 'allow_code_execution', 'use_docker', 'verbose',
            'use_llm', 'llm_config_path', 'max_experience_tasks'
        ]

        actual_params = list(sig.parameters.keys())
        assert actual_params == expected_params

        # Проверяем типы параметров
        params = sig.parameters

        # Обязательные параметры
        assert params['project_dir'].default == inspect.Parameter.empty
        assert params['project_dir'].annotation == Path

        # Опциональные параметры
        assert params['docs_dir'].annotation == Optional[Path]
        assert params['experience_dir'].annotation is str
        assert params['role'].annotation is str
        assert params['goal'].annotation is str
        assert params['backstory'].annotation == Optional[str]
        assert params['allow_code_execution'].annotation is bool
        assert params['use_docker'].annotation is bool
        assert params['verbose'].annotation is bool
        assert params['use_llm'].annotation is bool
        assert params['llm_config_path'].annotation is str
        assert params['max_experience_tasks'].annotation is int

    def test_create_smart_agent_return_type(self, dummy_openai_key):
        """Проверка типа возвращаемого значения create_smart_agent"""
        from src.agents.smart_agent import create_smart_agent
        from crewai import Agent

        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir)

            with patch('src.agents.smart_agent.is_docker_available', return_value=False):
                with patch('src.agents.smart_agent.LLM_WRAPPER_AVAILABLE', False):
                    with patch('src.agents.smart_agent.create_llm_for_crewai', return_value=None):
                        agent = create_smart_agent(project_dir=project_dir, use_llm=False)

                    assert agent is not None
                    assert isinstance(agent, Agent)

    def test_smart_agent_attributes(self, dummy_openai_key):
        """Проверка атрибутов созданного Smart Agent"""
        from src.agents.smart_agent import create_smart_agent

        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir)

            with patch('src.agents.smart_agent.is_docker_available', return_value=False):
                with patch('src.agents.smart_agent.LLM_WRAPPER_AVAILABLE', False):
                    with patch('src.agents.smart_agent.create_llm_for_crewai', return_value=None):
                        agent = create_smart_agent(
                            project_dir=project_dir,
                            role="Test Smart Agent",
                            goal="Test goal",
                            use_llm=False
                        )

                    # Проверяем основные атрибуты агента
                    assert hasattr(agent, 'role')
                    assert hasattr(agent, 'goal')
                    assert hasattr(agent, 'backstory')
                    assert hasattr(agent, 'tools')
                    assert hasattr(agent, 'verbose')

                    # Проверяем значения атрибутов
                    assert agent.role == "Test Smart Agent"
                    assert agent.goal == "Test goal"
                    assert agent.verbose  # default value

    def test_smart_agent_tools_structure(self, dummy_openai_key):
        """Проверка структуры инструментов Smart Agent"""
        from src.agents.smart_agent import create_smart_agent
        from src.tools.learning_tool import LearningTool
        from src.tools.context_analyzer_tool import ContextAnalyzerTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir)

            with patch('src.agents.smart_agent.is_docker_available', return_value=False):
                with patch('src.agents.smart_agent.LLM_WRAPPER_AVAILABLE', False):
                    with patch('src.agents.smart_agent.create_llm_for_crewai', return_value=None):
                        agent = create_smart_agent(project_dir=project_dir, use_llm=False)

                    # Проверяем что у агента есть инструменты
                    assert hasattr(agent, 'tools')
                    assert agent.tools is not None
                    assert len(agent.tools) >= 2  # минимум LearningTool и ContextAnalyzerTool

                    # Проверяем типы инструментов
                    tool_classes = [tool.__class__ for tool in agent.tools]
                    assert LearningTool in tool_classes
                    assert ContextAnalyzerTool in tool_classes

    def test_smart_agent_backstory_generation(self, dummy_openai_key):
        """Проверка генерации backstory для Smart Agent"""
        from src.agents.smart_agent import create_smart_agent

        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir)

            with patch('src.agents.smart_agent.is_docker_available', return_value=True) as mock_docker:
                with patch('src.agents.smart_agent.LLM_WRAPPER_AVAILABLE', True):
                    with patch('src.agents.smart_agent.create_llm_for_crewai', return_value=Mock()):
                        agent = create_smart_agent(project_dir=project_dir, use_llm=False)

                    # Проверяем что Docker проверка была вызвана
                    mock_docker.assert_called_once()

                    assert agent.backstory is not None
                    assert "smart agent" in agent.backstory.lower()
                    assert "learning" in agent.backstory.lower()
                    assert "context" in agent.backstory.lower()

    def test_smart_agent_configuration_parameters(self, dummy_openai_key):
        """Проверка применения конфигурационных параметров"""
        from src.agents.smart_agent import create_smart_agent

        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir)

            test_params = {
                'role': 'Custom Smart Agent',
                'goal': 'Custom test goal',
                'verbose': False,
                'allow_code_execution': False,
                'use_docker': False,
                'use_llm': False,
                'max_experience_tasks': 500
            }

            agent = create_smart_agent(project_dir=project_dir, **test_params)

            # Проверяем применение параметров
            assert agent.role == test_params['role']
            assert agent.goal == test_params['goal']
            assert agent.verbose == test_params['verbose']

    def test_smart_agent_tools_initialization(self, dummy_openai_key):
        """Проверка корректной инициализации инструментов"""
        from src.agents.smart_agent import create_smart_agent
        from src.tools.learning_tool import LearningTool
        from src.tools.context_analyzer_tool import ContextAnalyzerTool

        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir)
            experience_dir = "custom_experience"

            with patch('src.agents.smart_agent.is_docker_available', return_value=False):
                with patch('src.agents.smart_agent.create_llm_for_crewai', return_value=None):
                    agent = create_smart_agent(
                        project_dir=project_dir,
                        experience_dir=experience_dir,
                        use_llm=False
                    )

                    # Находим инструменты по типам
                    learning_tools = [t for t in agent.tools if isinstance(t, LearningTool)]
                    context_tools = [t for t in agent.tools if isinstance(t, ContextAnalyzerTool)]

                    assert len(learning_tools) == 1
                    assert len(context_tools) == 1

                    # Проверяем конфигурацию LearningTool
                    learning_tool = learning_tools[0]
                    assert learning_tool.experience_dir.name == experience_dir

                    # Проверяем конфигурацию ContextAnalyzerTool
                    context_tool = context_tools[0]
                    assert str(context_tool.project_dir) == str(project_dir)


class TestSmartAgentConstants:
    """Тесты констант и конфигураций Smart Agent"""

    def test_default_values(self):
        """Проверка значений по умолчанию"""
        from src.agents.smart_agent import create_smart_agent

        # Проверяем значения по умолчанию через сигнатуру
        import inspect
        sig = inspect.signature(create_smart_agent)

        assert sig.parameters['role'].default == "Smart Project Executor Agent"
        assert sig.parameters['experience_dir'].default == "smart_experience"
        assert sig.parameters['verbose'].default
        assert sig.parameters['allow_code_execution'].default
        assert sig.parameters['use_docker'].default
        assert sig.parameters['use_llm'].default
        assert sig.parameters['max_experience_tasks'].default == 1000

    def test_backstory_components(self, dummy_openai_key):
        """Проверка компонентов backstory"""
        from src.agents.smart_agent import create_smart_agent

        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir)

            # Тест с Docker без LLM
            with patch('src.agents.smart_agent.is_docker_available', return_value=True):
                with patch('src.agents.smart_agent.LLM_WRAPPER_AVAILABLE', False):
                    with patch('src.agents.smart_agent.create_llm_for_crewai', return_value=None):
                        agent_with_docker = create_smart_agent(project_dir=project_dir, use_llm=False)
                        assert "with code execution" in agent_with_docker.backstory
                        assert "in tool-only mode" in agent_with_docker.backstory

            # Тест без Docker и LLM
            with patch('src.agents.smart_agent.is_docker_available', return_value=False):
                with patch('src.agents.smart_agent.LLM_WRAPPER_AVAILABLE', False):
                    with patch('src.agents.smart_agent.create_llm_for_crewai', return_value=None):
                        agent_without_both = create_smart_agent(project_dir=project_dir, use_llm=False)
                        assert "without code execution" in agent_without_both.backstory
                        assert "in tool-only mode" in agent_without_both.backstory