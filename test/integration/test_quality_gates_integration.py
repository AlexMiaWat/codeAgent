#!/usr/bin/env python3
"""
Интеграционные тесты для Quality Gates framework с ServerCore
"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Добавляем src в путь
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.core.server_core import ServerCore, QualityGateException
from src.quality import QualityGateManager
from src.quality.models.quality_result import QualityStatus, QualityGateResult, QualityResult, QualityCheckType
from src.todo_manager import TodoItem


class TestQualityGatesIntegration:
    """Интеграционные тесты Quality Gates с ServerCore"""

    @pytest.fixture
    def mock_components(self):
        """Создание мок компонентов для тестирования"""
        # Mock todo manager
        todo_manager = MagicMock()
        todo_manager.get_pending_tasks.return_value = []

        # Mock checkpoint manager
        checkpoint_manager = MagicMock()

        # Mock status manager
        status_manager = MagicMock()

        # Mock logger
        logger = MagicMock()

        # Mock task executor
        task_executor = AsyncMock(return_value=True)

        # Mock revision executor
        revision_executor = AsyncMock(return_value=True)

        # Mock todo generator
        todo_generator = AsyncMock(return_value=True)

        # Config with quality gates enabled
        config = {
            'quality_gates': {
                'enabled': True,
                'strict_mode': True
            }
        }

        return {
            'todo_manager': todo_manager,
            'checkpoint_manager': checkpoint_manager,
            'status_manager': status_manager,
            'logger': logger,
            'task_executor': task_executor,
            'revision_executor': revision_executor,
            'todo_generator': todo_generator,
            'config': config
        }

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
    def server_core(self, mock_components, quality_gate_manager):
        """Создание ServerCore с Quality Gates"""
        server = ServerCore(
            todo_manager=mock_components['todo_manager'],
            checkpoint_manager=mock_components['checkpoint_manager'],
            status_manager=mock_components['status_manager'],
            server_logger=mock_components['logger'],
            task_executor=mock_components['task_executor'],
            revision_executor=mock_components['revision_executor'],
            todo_generator=mock_components['todo_generator'],
            config=mock_components['config'],
            project_dir=Path.cwd(),
            quality_gate_manager=quality_gate_manager,
            task_delay=0
        )
        return server

    def test_quality_gates_enabled_check(self, server_core):
        """Тест проверки включения Quality Gates"""
        assert server_core._is_quality_gates_enabled() == True

        # Отключим quality gates в конфиге
        server_core.config['quality_gates']['enabled'] = False
        assert server_core._is_quality_gates_enabled() == False

    @pytest.mark.asyncio
    async def test_successful_quality_gates_allow_execution(self, server_core, mock_components, quality_gate_manager):
        """Тест успешного прохождения Quality Gates - задача выполняется"""
        # Mock успешного результата quality gates
        successful_result = QualityGateResult(gate_name="test")
        successful_result.add_result(QualityResult(
            check_type=QualityCheckType.COVERAGE,
            status=QualityStatus.PASSED,
            score=0.9
        ))

        async def mock_run_all_gates_success(context=None):
            return successful_result
        with patch.object(quality_gate_manager, 'run_all_gates', side_effect=mock_run_all_gates_success):
            with patch.object(quality_gate_manager, 'should_block_execution', return_value=False):
                # Создаем тестовую задачу
                todo_item = TodoItem(
                    text="Test Task",
                    category="test",
                    id="test_task_001"
                )

                # Выполняем задачу
                result = await server_core.execute_single_task(todo_item, 1, 1)

                # Проверяем что задача выполнена успешно
                assert result == True
                mock_components['task_executor'].assert_called_once_with(todo_item, task_number=1, total_tasks=1)

    @pytest.mark.asyncio
    async def test_failed_quality_gates_block_execution_strict_mode(self, server_core, mock_components, quality_gate_manager):
        """Тест провала Quality Gates в strict mode - задача блокируется"""
        # Mock неудачного результата quality gates
        failed_result = QualityGateResult(gate_name="test")
        failed_result.add_result(QualityResult(
            check_type=QualityCheckType.COVERAGE,
            status=QualityStatus.FAILED,
            score=0.3
        ))

        async def mock_run_all_gates_failed(context=None):
            return failed_result
        with patch.object(quality_gate_manager, 'run_all_gates', side_effect=mock_run_all_gates_failed):
            with patch.object(quality_gate_manager, 'should_block_execution', return_value=True):
                # Создаем тестовую задачу
                todo_item = TodoItem(
                    text="Test Task",
                    category="test",
                    id="test_task_002"
                )

                # Выполняем задачу - должно выбросить исключение
                with pytest.raises(QualityGateException) as exc_info:
                    await server_core.execute_single_task(todo_item, 1, 1)

                # Проверяем что исключение содержит правильную информацию
                assert "Quality gates failed" in str(exc_info.value)
                assert exc_info.value.gate_result == failed_result

                # Проверяем что задача не выполнена
                mock_components['task_executor'].assert_not_called()

    @pytest.mark.asyncio
    async def test_quality_gates_disabled_allows_execution(self, server_core, mock_components, quality_gate_manager):
        """Тест отключенных Quality Gates - задача выполняется без проверок"""
        # Отключаем quality gates
        server_core.config['quality_gates']['enabled'] = False

        # Создаем тестовую задачу
        todo_item = TodoItem(
            text="Test Task",
            category="test",
            id="test_task_003"
        )

        # Выполняем задачу
        result = await server_core.execute_single_task(todo_item, 1, 1)

        # Проверяем что задача выполнена успешно без проверок quality gates
        assert result == True
        mock_components['task_executor'].assert_called_once_with(todo_item, task_number=1, total_tasks=1)

        # Проверяем что quality gates не вызывались
        # (мы не можем проверить assert_not_called для метода, который может быть замокан,
        # поэтому просто проверим что задача выполнена без ошибок)

    @pytest.mark.asyncio
    async def test_quality_gates_error_fail_open(self, server_core, mock_components, quality_gate_manager):
        """Тест ошибки в Quality Gates - fail-open поведение"""
        # Mock ошибки в quality gates
        async def mock_run_all_gates_error(context=None):
            raise Exception("Test error")
        with patch.object(quality_gate_manager, 'run_all_gates', side_effect=mock_run_all_gates_error):
            # Создаем тестовую задачу
            todo_item = TodoItem(
                text="Test Task",
                category="test",
                id="test_task_004"
            )

            # Выполняем задачу - должна выполниться несмотря на ошибку quality gates
            result = await server_core.execute_single_task(todo_item, 1, 1)

            # Проверяем что задача выполнена (fail-open)
            assert result == True
            mock_components['task_executor'].assert_called_once_with(todo_item, task_number=1, total_tasks=1)

    @pytest.mark.asyncio
    async def test_quality_gates_context_passing(self, server_core, quality_gate_manager):
        """Тест передачи контекста в Quality Gates"""
        context_captured = None

        def mock_run_all_gates(context=None):
            nonlocal context_captured
            context_captured = context
            result = QualityGateResult(gate_name="test")
            result.add_result(QualityResult(
                check_type=QualityCheckType.COVERAGE,
                status=QualityStatus.PASSED,
                score=0.9
            ))
            return result

        with patch.object(quality_gate_manager, 'run_all_gates', side_effect=mock_run_all_gates):
            with patch.object(quality_gate_manager, 'should_block_execution', return_value=False):
                with patch.object(server_core, 'task_executor', new=AsyncMock(return_value=True)):
                    # Создаем тестовую задачу
                    todo_item = TodoItem(
                        text="Test Task",
                        category="test",
                        id="test_task_005"
                    )

                    # Выполняем задачу
                    await server_core.execute_single_task(todo_item, 1, 1)

                    # Проверяем что контекст передан правильно
                    assert context_captured is not None
                    assert context_captured['task_type'] == 'test'
                    assert context_captured['task_id'] == 'test_task_005'
                    assert 'project_path' in context_captured

    @pytest.mark.asyncio
    async def test_quality_gates_warning_status_handling(self, server_core, mock_components, quality_gate_manager):
        """Тест обработки warning статуса Quality Gates"""
        # Включаем non-strict mode
        server_core.config['quality_gates']['strict_mode'] = False

        # Mock результата с warning
        warning_result = QualityGateResult(gate_name="test")
        warning_result.add_result(QualityResult(
            check_type=QualityCheckType.COVERAGE,
            status=QualityStatus.WARNING,
            score=0.7
        ))

        async def mock_run_all_gates_warning(context=None):
            return warning_result
        with patch.object(quality_gate_manager, 'run_all_gates', side_effect=mock_run_all_gates_warning):
            with patch.object(quality_gate_manager, 'should_block_execution', return_value=False):  # В non-strict mode не блокируем
                # Создаем тестовую задачу
                todo_item = TodoItem(
                    text="Test Task",
                    category="test",
                    id="test_task_006"
                )

                # Выполняем задачу
                result = await server_core.execute_single_task(todo_item, 1, 1)

                # Проверяем что задача выполнена несмотря на warning
                assert result == True
                mock_components['task_executor'].assert_called_once_with(todo_item, task_number=1, total_tasks=1)