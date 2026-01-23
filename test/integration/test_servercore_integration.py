#!/usr/bin/env python3
"""
Интеграционные тесты для ServerCore с компонентами

Тестирует взаимодействие ServerCore с другими компонентами системы:
- DI Container
- Quality Gates
- Todo Manager
- Status Manager
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

# Добавляем src в путь
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.core.server_core import ServerCore, QualityGateException
from src.core.di_container import DIContainer
from src.core.interfaces import ITodoManager, IStatusManager, ICheckpointManager, ILogger
from src.quality import QualityGateManager
from src.quality.models.quality_result import QualityStatus, QualityGateResult, QualityResult, QualityCheckType
from src.todo_manager import TodoItem


class TestServerCoreDIIntegration:
    """Интеграционные тесты ServerCore с DI Container"""

    @pytest.fixture
    def di_container(self):
        """Создание DI Container для тестирования"""
        container = DIContainer()

        # Регистрируем mock компоненты
        todo_manager = MagicMock()
        todo_manager.get_pending_tasks.return_value = []

        checkpoint_manager = MagicMock()
        status_manager = MagicMock()
        server_logger = MagicMock()

        task_executor = AsyncMock(return_value=True)
        revision_executor = AsyncMock(return_value=True)
        todo_generator = AsyncMock(return_value=True)

        # Регистрируем в DI контейнере под правильными интерфейсами
        container.register_instance(ITodoManager, todo_manager)
        container.register_instance(ICheckpointManager, checkpoint_manager)
        container.register_instance(IStatusManager, status_manager)
        container.register_instance(ILogger, server_logger)
        # Регистрируем исполнители как callable объекты
        container.register_instance(type(task_executor), task_executor)
        container.register_instance(type(revision_executor), revision_executor)
        container.register_instance(type(todo_generator), todo_generator)

        return container

    def test_di_container_basic_registration(self, di_container):
        """Тест базовой регистрации компонентов в DI контейнере"""
        # Проверяем что компоненты зарегистрированы
        assert di_container.is_registered(ITodoManager)
        assert di_container.is_registered(IStatusManager)
        assert di_container.is_registered(ICheckpointManager)
        assert di_container.is_registered(ILogger)

    @pytest.mark.asyncio
    async def test_servercore_di_integration_basic(self, di_container):
        """Тест базовой интеграции ServerCore с DI"""
        # Создаем компоненты через DI
        todo_manager = di_container.resolve(MagicMock)
        checkpoint_manager = di_container.resolve(MagicMock)
        status_manager = di_container.resolve(MagicMock)
        server_logger = di_container.resolve(MagicMock)
        task_executor = di_container.resolve(MagicMock)
        revision_executor = di_container.resolve(MagicMock)
        todo_generator = di_container.resolve(MagicMock)

        config = {'quality_gates': {'enabled': False}}
        project_dir = Path("/tmp/test")

        # Создаем ServerCore с компонентами из DI
        server = ServerCore(
            todo_manager=todo_manager,
            checkpoint_manager=checkpoint_manager,
            status_manager=status_manager,
            server_logger=server_logger,
            task_executor=task_executor,
            revision_executor=revision_executor,
            todo_generator=todo_generator,
            config=config,
            project_dir=project_dir,
            quality_gate_manager=None
        )

        # Проверяем что ServerCore создался
        assert server is not None

        # Тестируем базовую функциональность
        todo_item = TodoItem(text="DI Test", category="test", id="di_001")
        result = await server.execute_single_task(todo_item, 1, 1)

        assert result == True
        task_executor.assert_called_once_with(todo_item, task_number=1, total_tasks=1)


class TestServerCoreQualityGatesIntegration:
    """Интеграционные тесты ServerCore с Quality Gates"""

    @pytest.fixture
    def quality_gate_manager(self):
        """Создание QualityGateManager для тестирования"""
        manager = QualityGateManager()
        manager.configure({
            'enabled': True,
            'strict_mode': True,
            'gates': {
                'coverage': {'enabled': True, 'min_coverage': 80.0},
                'complexity': {'enabled': True, 'max_complexity': 10},
                'security': {'enabled': True},
                'style': {'enabled': True}
            }
        })
        return manager

    @pytest.fixture
    def mock_server_components(self):
        """Создание mock компонентов для ServerCore"""
        todo_manager = MagicMock()
        todo_manager.get_pending_tasks.return_value = []

        checkpoint_manager = MagicMock()
        status_manager = MagicMock()
        server_logger = MagicMock()

        task_executor = AsyncMock(return_value=True)
        revision_executor = AsyncMock(return_value=True)
        todo_generator = AsyncMock(return_value=True)

        config = {
            'quality_gates': {
                'enabled': True,
                'strict_mode': True
            }
        }
        project_dir = Path("/tmp/test")

        return {
            'todo_manager': todo_manager,
            'checkpoint_manager': checkpoint_manager,
            'status_manager': status_manager,
            'server_logger': server_logger,
            'task_executor': task_executor,
            'revision_executor': revision_executor,
            'todo_generator': todo_generator,
            'config': config,
            'project_dir': project_dir
        }

    def test_quality_gates_integration_setup(self, quality_gate_manager, mock_server_components):
        """Тест настройки интеграции Quality Gates с ServerCore"""
        server = ServerCore(
            **mock_server_components,
            quality_gate_manager=quality_gate_manager
        )

        assert server.quality_gate_manager == quality_gate_manager
        assert server._is_quality_gates_enabled() == True

    @pytest.mark.asyncio
    async def test_quality_gates_passing_execution(self, quality_gate_manager, mock_server_components):
        """Тест успешного прохождения Quality Gates"""
        # Настраиваем успешный результат quality gates
        successful_result = QualityGateResult(gate_name="integration_test")
        successful_result.add_result(QualityResult(
            check_type=QualityCheckType.COVERAGE,
            status=QualityStatus.PASSED,
            score=0.95
        ))
        successful_result.add_result(QualityResult(
            check_type=QualityCheckType.COMPLEXITY,
            status=QualityStatus.PASSED,
            score=5
        ))

        # Mock quality gate manager
        with patch.object(quality_gate_manager, 'run_all_gates', return_value=successful_result):
            with patch.object(quality_gate_manager, 'should_block_execution', return_value=False):
                server = ServerCore(
                    **mock_server_components,
                    quality_gate_manager=quality_gate_manager
                )

                todo_item = TodoItem(text="Quality Test", category="test", id="qg_pass_001")
                result = await server.execute_single_task(todo_item, 1, 1)

                assert result == True
                mock_server_components['task_executor'].assert_called_once()

    @pytest.mark.asyncio
    async def test_quality_gates_failing_execution(self, quality_gate_manager, mock_server_components):
        """Тест провала Quality Gates блокирует выполнение"""
        # Настраиваем неудачный результат quality gates
        failed_result = QualityGateResult(gate_name="integration_test")
        failed_result.add_result(QualityResult(
            check_type=QualityCheckType.COVERAGE,
            status=QualityStatus.FAILED,
            score=0.5,
            message="Coverage too low"
        ))

        # Mock quality gate manager
        with patch.object(quality_gate_manager, 'run_all_gates', return_value=failed_result):
            with patch.object(quality_gate_manager, 'should_block_execution', return_value=True):
                server = ServerCore(
                    **mock_server_components,
                    quality_gate_manager=quality_gate_manager
                )

                todo_item = TodoItem(text="Quality Test", category="test", id="qg_fail_001")

                # Должен выбросить исключение
                with pytest.raises(QualityGateException) as exc_info:
                    await server.execute_single_task(todo_item, 1, 1)

                assert "Quality gates failed" in str(exc_info.value)
                assert exc_info.value.gate_result == failed_result

                # Задача не должна выполниться
                mock_server_components['task_executor'].assert_not_called()

    @pytest.mark.asyncio
    async def test_quality_gates_warning_non_strict(self, quality_gate_manager, mock_server_components):
        """Тест warning в Quality Gates в non-strict режиме"""
        # Отключаем strict mode
        mock_server_components['config']['quality_gates']['strict_mode'] = False

        # Настраиваем результат с warning
        warning_result = QualityGateResult(gate_name="integration_test")
        warning_result.add_result(QualityResult(
            check_type=QualityCheckType.COVERAGE,
            status=QualityStatus.WARNING,
            score=0.75,
            message="Coverage slightly low"
        ))

        # Mock quality gate manager
        with patch.object(quality_gate_manager, 'run_all_gates', return_value=warning_result):
            with patch.object(quality_gate_manager, 'should_block_execution', return_value=False):  # Non-strict mode
                server = ServerCore(
                    **mock_server_components,
                    quality_gate_manager=quality_gate_manager
                )

                todo_item = TodoItem(text="Quality Test", category="test", id="qg_warn_001")
                result = await server.execute_single_task(todo_item, 1, 1)

                # Задача должна выполниться несмотря на warning
                assert result == True
                mock_server_components['task_executor'].assert_called_once()


class TestServerCoreFullIntegration:
    """Полные интеграционные тесты ServerCore со всеми компонентами"""

    @pytest.fixture
    def full_mock_setup(self):
        """Создание полной mock настройки для комплексного тестирования"""
        # Создаем DI контейнер
        di_container = DIContainer()

        # Регистрируем компоненты
        todo_manager = MagicMock()
        checkpoint_manager = MagicMock()
        status_manager = MagicMock()
        server_logger = MagicMock()
        task_executor = AsyncMock(return_value=True)
        revision_executor = AsyncMock(return_value=True)
        todo_generator = AsyncMock(return_value=True)

        di_container.register_instance(type(todo_manager), todo_manager)
        di_container.register_instance(type(checkpoint_manager), checkpoint_manager)
        di_container.register_instance(type(status_manager), status_manager)
        di_container.register_instance(type(server_logger), server_logger)
        di_container.register_instance(type(task_executor), task_executor)
        di_container.register_instance(type(revision_executor), revision_executor)
        di_container.register_instance(type(todo_generator), todo_generator)

        # Настраиваем Quality Gates
        quality_gate_manager = QualityGateManager()
        quality_gate_manager.configure({
            'enabled': True,
            'strict_mode': False,
            'gates': {
                'coverage': {'enabled': True, 'min_coverage': 70.0},
                'style': {'enabled': True}
            }
        })

        config = {
            'quality_gates': {
                'enabled': True,
                'strict_mode': False
            }
        }
        project_dir = Path("/tmp/integration_test")

        return {
            'di_container': di_container,
            'todo_manager': todo_manager,
            'checkpoint_manager': checkpoint_manager,
            'status_manager': status_manager,
            'server_logger': server_logger,
            'task_executor': task_executor,
            'revision_executor': revision_executor,
            'todo_generator': todo_generator,
            'quality_gate_manager': quality_gate_manager,
            'config': config,
            'project_dir': project_dir
        }

    @pytest.mark.asyncio
    async def test_full_integration_workflow(self, full_mock_setup):
        """Тест полного workflow интеграции компонентов"""
        # Настраиваем успешные quality gates
        successful_result = QualityGateResult(gate_name="full_integration")
        successful_result.add_result(QualityResult(
            check_type=QualityCheckType.COVERAGE,
            status=QualityStatus.PASSED,
            score=0.85
        ))

        # Mock quality gates
        with patch.object(full_mock_setup['quality_gate_manager'], 'run_all_gates', return_value=successful_result):
            with patch.object(full_mock_setup['quality_gate_manager'], 'should_block_execution', return_value=False):
                # Создаем ServerCore
                server = ServerCore(
                    todo_manager=full_mock_setup['todo_manager'],
                    checkpoint_manager=full_mock_setup['checkpoint_manager'],
                    status_manager=full_mock_setup['status_manager'],
                    server_logger=full_mock_setup['server_logger'],
                    task_executor=full_mock_setup['task_executor'],
                    revision_executor=full_mock_setup['revision_executor'],
                    todo_generator=full_mock_setup['todo_generator'],
                    config=full_mock_setup['config'],
                    project_dir=full_mock_setup['project_dir'],
                    quality_gate_manager=full_mock_setup['quality_gate_manager']
                )

                # Проверяем инициализацию
                assert server._is_quality_gates_enabled() == True

                # Создаем задачи разных типов
                tasks = [
                    TodoItem(text="Implement feature", category="code", id="task_001"),
                    TodoItem(text="Write tests", category="test", id="task_002"),
                    TodoItem(text="Update docs", category="docs", id="task_003")
                ]

                # Выполняем задачи
                for i, task in enumerate(tasks, 1):
                    result = await server.execute_single_task(task, i, len(tasks))
                    assert result == True

                # Проверяем что все executors были вызваны
                assert full_mock_setup['task_executor'].call_count == 3

                # Проверяем что quality gates проверялись для каждой задачи
                # (мы не можем проверить точное количество вызовов из-за mock объекта)

    @pytest.mark.asyncio
    async def test_integration_error_handling(self, full_mock_setup):
        """Тест обработки ошибок в интеграции"""
        # Настраиваем failing quality gates
        failed_result = QualityGateResult(gate_name="error_test")
        failed_result.add_result(QualityResult(
            check_type=QualityCheckType.COVERAGE,
            status=QualityStatus.FAILED,
            score=0.4
        ))

        # Mock quality gates failure
        with patch.object(full_mock_setup['quality_gate_manager'], 'run_all_gates', return_value=failed_result):
            with patch.object(full_mock_setup['quality_gate_manager'], 'should_block_execution', return_value=True):
                server = ServerCore(**{k: v for k, v in full_mock_setup.items() if k != 'di_container'})

                todo_item = TodoItem(text="Error Test", category="test", id="error_001")

                # Должен выбросить исключение
                with pytest.raises(QualityGateException):
                    await server.execute_single_task(todo_item, 1, 1)

                # Задача не должна выполниться
                full_mock_setup['task_executor'].assert_not_called()

    @pytest.mark.asyncio
    async def test_integration_task_type_filtering(self, full_mock_setup):
        """Тест фильтрации задач по типу в интеграции"""
        from src.core.types import TaskType

        # Настраиваем успешные quality gates
        successful_result = QualityGateResult(gate_name="filter_test")
        successful_result.add_result(QualityResult(
            check_type=QualityCheckType.COVERAGE,
            status=QualityStatus.PASSED,
            score=0.9
        ))

        with patch.object(full_mock_setup['quality_gate_manager'], 'run_all_gates', return_value=successful_result):
            with patch.object(full_mock_setup['quality_gate_manager'], 'should_block_execution', return_value=False):
                server = ServerCore(**{k: v for k, v in full_mock_setup.items() if k != 'di_container'})

                # Создаем задачи разных типов
                tasks = [
                    TodoItem(text="Code task", category="code", id="filter_001"),
                    TodoItem(text="Test task", category="test", id="filter_002"),
                    TodoItem(text="Doc task", category="docs", id="filter_003")
                ]

                # Тестируем фильтрацию по типу CODE
                code_tasks = server._filter_tasks_by_type(tasks, TaskType.CODE)
                assert len(code_tasks) == 1
                assert code_tasks[0].id == "filter_001"

                # Тестируем фильтрацию по типу TEST
                test_tasks = server._filter_tasks_by_type(tasks, TaskType.TEST)
                assert len(test_tasks) == 1
                assert test_tasks[0].id == "filter_002"

                # Тестируем без фильтрации
                all_tasks = server._filter_tasks_by_type(tasks, None)
                assert len(all_tasks) == 3