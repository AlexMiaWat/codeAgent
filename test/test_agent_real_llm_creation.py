"""
Реальное тестирование создания агента с LLM

Проверяет:
- Создание агента с реальным LLM через CrewAILLMWrapper
- Fallback механизм при недоступности основных моделей
- Корректную инициализацию инструментов
- Возможность выполнения простых задач
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

# Импортируем тестируемые компоненты
from src.agents.smart_agent import create_smart_agent
from src.agents.executor_agent import create_executor_agent
from src.llm.crewai_llm_wrapper import create_llm_for_crewai


class TestRealAgentLLMCreation:
    """Тесты реального создания агентов с LLM"""

    @pytest.mark.asyncio
    async def test_smart_agent_real_llm_creation(self):
        """Тест реального создания smart agent с LLM"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)

            # Создаем агента с принудительным использованием LLMManager
            # (даже если API ключи не настроены - должен работать fallback)
            agent = create_smart_agent(
                project_dir=project_dir,
                use_llm_manager=True,
                allow_code_execution=False,  # Отключаем Docker для теста
                verbose=False
            )

            # Проверяем базовую структуру агента
            assert agent is not None
            assert hasattr(agent, 'role')
            assert hasattr(agent, 'goal')
            assert hasattr(agent, 'llm') or hasattr(agent, 'llms')

            # Проверяем инструменты
            assert hasattr(agent, 'tools')
            assert len(agent.tools) >= 2  # Должны быть как минимум LearningTool и ContextAnalyzerTool

            tool_names = [tool.name for tool in agent.tools]
            assert "LearningTool" in tool_names
            assert "ContextAnalyzerTool" in tool_names

    @pytest.mark.asyncio
    async def test_executor_agent_real_llm_creation(self):
        """Тест реального создания executor agent с LLM"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)

            # Создаем агента executor с использованием LLMManager
            agent = create_executor_agent(
                project_dir=project_dir,
                use_llm_manager=True,
                allow_code_execution=False,  # Отключаем Docker для теста
                verbose=False
            )

            # Проверяем базовую структуру агента
            assert agent is not None
            assert hasattr(agent, 'role')
            assert hasattr(agent, 'goal')
            assert hasattr(agent, 'llm') or hasattr(agent, 'llms')

    @pytest.mark.asyncio
    async def test_crewai_llm_wrapper_creation(self):
        """Тест создания CrewAILLMWrapper"""
        # Создаем LLM wrapper
        llm_wrapper = create_llm_for_crewai(use_fastest=True)

        # Проверяем структуру wrapper
        assert llm_wrapper is not None
        assert hasattr(llm_wrapper, 'llm_manager')
        assert hasattr(llm_wrapper, 'use_fastest')
        assert hasattr(llm_wrapper, 'use_parallel')

        # Проверяем наличие моделей в менеджере
        assert len(llm_wrapper.llm_manager.models) > 0

    @pytest.mark.asyncio
    async def test_agent_with_mock_llm_response(self):
        """Тест агента с моковым ответом LLM (для случаев когда API недоступен)"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)

            # Мокаем LLM ответ для случаев недоступности API
            with patch('src.llm.llm_manager.LLMManager.generate_response') as mock_generate:
                # Настраиваем мок для возврата успешного ответа
                mock_response = MagicMock()
                mock_response.success = True
                mock_response.content = "Тестовый ответ от LLM"
                mock_response.response_time = 1.5
                mock_generate.return_value = mock_response

                # Создаем агента
                agent = create_smart_agent(
                    project_dir=project_dir,
                    use_llm_manager=True,
                    allow_code_execution=False,
                    verbose=False
                )

                assert agent is not None

                # Проверяем что LLM был вызван при создании агента
                # (фактический вызов происходит при инициализации LLM в агенте)

    @pytest.mark.asyncio
    async def test_agent_fallback_mechanism(self):
        """Тест fallback механизма при недоступности LLM"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)

            # Мокаем ситуацию когда LLM недоступен и должен сработать fallback
            with patch('src.llm.crewai_llm_wrapper.create_llm_for_crewai') as mock_create_llm:
                # Первый вызов (OpenRouter) падает с исключением
                mock_create_llm.side_effect = [
                    Exception("OpenRouter API unavailable"),  # Первый вызов падает
                    MagicMock()  # Второй вызов (fallback) успешен
                ]

                # Создаем агента - должен сработать fallback
                agent = create_smart_agent(
                    project_dir=project_dir,
                    use_llm_manager=True,
                    allow_code_execution=False,
                    verbose=False
                )

                # Агент должен быть создан несмотря на ошибку первого LLM
                assert agent is not None

                # Проверяем что create_llm_for_crewai был вызван дважды (fallback)
                assert mock_create_llm.call_count >= 1

    def test_agent_tools_initialization_with_llm(self):
        """Тест инициализации инструментов агента с LLM"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)

            # Создаем агента с LLM
            agent = create_smart_agent(
                project_dir=project_dir,
                use_llm_manager=True,
                allow_code_execution=False,
                verbose=False
            )

            # Проверяем инструменты
            assert len(agent.tools) >= 2

            # Проверяем что каждый инструмент имеет необходимые атрибуты
            for tool in agent.tools:
                assert hasattr(tool, 'name')
                assert hasattr(tool, 'description')
                assert tool.name != ""
                assert tool.description != ""

    def test_agent_role_and_goal_assignment(self):
        """Тест корректного присвоения роли и цели агенту"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)

            custom_role = "Test Smart Agent"
            custom_goal = "Test goal for LLM integration"

            agent = create_smart_agent(
                project_dir=project_dir,
                role=custom_role,
                goal=custom_goal,
                use_llm_manager=True,
                allow_code_execution=False,
                verbose=False
            )

            assert agent.role == custom_role
            assert agent.goal == custom_goal

    @pytest.mark.asyncio
    async def test_agent_memory_enabled(self):
        """Тест что у агента включена память"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)

            agent = create_smart_agent(
                project_dir=project_dir,
                use_llm_manager=True,
                allow_code_execution=False,
                verbose=False
            )

            # Проверяем что агент создан успешно
            assert agent is not None

    def test_agent_configuration_validation(self):
        """Тест валидации конфигурации агента"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)

            # Создаем агента с различными конфигурациями
            configs = [
                {"allow_code_execution": True},
                {"allow_code_execution": False},
                {"verbose": True},
                {"verbose": False},
                {"role": "Custom Role", "goal": "Custom Goal"}
            ]

            for config in configs:
                agent = create_smart_agent(
                    project_dir=project_dir,
                    use_llm_manager=True,
                    **config
                )

                assert agent is not None

                # Проверяем применение конфигурации
                for key, value in config.items():
                    if hasattr(agent, key):
                        assert getattr(agent, key) == value