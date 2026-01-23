"""
Smoke tests for ServerCore

This module contains smoke tests that verify basic functionality
of ServerCore can be instantiated and basic operations work.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock
from pathlib import Path

from src.core.server_core import ServerCore, QualityGateException
from src.todo_manager import TodoItem


class TestServerCoreSmoke:
    """Smoke tests for ServerCore basic functionality"""

    @pytest.fixture
    def mock_components(self):
        """Create mock components for ServerCore"""
        todo_manager = MagicMock()
        todo_manager.get_pending_tasks.return_value = []

        checkpoint_manager = MagicMock()
        status_manager = MagicMock()
        server_logger = MagicMock()

        task_executor = AsyncMock(return_value=True)
        revision_executor = AsyncMock(return_value=True)
        todo_generator = AsyncMock(return_value=True)

        config = {'quality_gates': {'enabled': False}}
        project_dir = Path("/tmp/test")
        quality_gate_manager = None

        return {
            'todo_manager': todo_manager,
            'checkpoint_manager': checkpoint_manager,
            'status_manager': status_manager,
            'server_logger': server_logger,
            'task_executor': task_executor,
            'revision_executor': revision_executor,
            'todo_generator': todo_generator,
            'config': config,
            'project_dir': project_dir,
            'quality_gate_manager': quality_gate_manager
        }

    def test_server_core_creation(self, mock_components):
        """Test ServerCore can be created"""
        server = ServerCore(**mock_components)
        assert server is not None
        assert isinstance(server, ServerCore)

    def test_server_core_initialization(self, mock_components):
        """Test ServerCore initializes correctly"""
        server = ServerCore(**mock_components)

        # Check that components are stored
        assert server.todo_manager == mock_components['todo_manager']
        assert server.checkpoint_manager == mock_components['checkpoint_manager']
        assert server.status_manager == mock_components['status_manager']
        assert server.server_logger == mock_components['server_logger']
        assert server.task_executor == mock_components['task_executor']
        assert server.revision_executor == mock_components['revision_executor']
        assert server.todo_generator == mock_components['todo_generator']
        assert server.config == mock_components['config']
        assert server.project_dir == mock_components['project_dir']
        assert server.quality_gate_manager == mock_components['quality_gate_manager']

    def test_server_core_basic_properties(self, mock_components):
        """Test ServerCore basic properties"""
        server = ServerCore(**mock_components)

        # Should have default task delay
        assert hasattr(server, 'task_delay')
        assert server.task_delay == 1.0  # default value

        # Should have iteration counter
        assert hasattr(server, '_iteration_count')
        assert server._iteration_count == 0

    def test_quality_gates_disabled_check(self, mock_components):
        """Test quality gates disabled check"""
        server = ServerCore(**mock_components)
        assert server._is_quality_gates_enabled() == False

    def test_quality_gates_enabled_check(self, mock_components):
        """Test quality gates enabled check"""
        mock_components['config']['quality_gates']['enabled'] = True
        server = ServerCore(**mock_components)
        assert server._is_quality_gates_enabled() == True

    @pytest.mark.asyncio
    async def test_execute_single_task_success(self, mock_components):
        """Test successful single task execution"""
        server = ServerCore(**mock_components)

        # Create test todo item
        todo_item = TodoItem(
            text="Test task",
            category="test",
            id="test_001"
        )

        # Execute task
        result = await server.execute_single_task(todo_item, 1, 1)

        # Should return True
        assert result == True

        # Should call task executor
        mock_components['task_executor'].assert_called_once_with(todo_item, task_number=1, total_tasks=1)

    @pytest.mark.asyncio
    async def test_execute_single_task_failure(self, mock_components):
        """Test failed single task execution"""
        # Make task executor return False
        mock_components['task_executor'] = AsyncMock(return_value=False)

        server = ServerCore(**mock_components)

        todo_item = TodoItem(
            text="Test task",
            category="test",
            id="test_002"
        )

        result = await server.execute_single_task(todo_item, 1, 1)

        # Should return False
        assert result == False

        # Should still call task executor
        mock_components['task_executor'].assert_called_once()

    def test_get_pending_tasks(self, mock_components):
        """Test getting pending tasks"""
        # Mock todo manager to return some tasks
        tasks = [
            TodoItem(text="Task 1", category="test", id="1"),
            TodoItem(text="Task 2", category="code", id="2")
        ]
        mock_components['todo_manager'].get_pending_tasks.return_value = tasks

        server = ServerCore(**mock_components)

        pending = server._get_pending_tasks()
        assert len(pending) == 2
        assert pending[0].text == "Task 1"
        assert pending[1].text == "Task 2"

    def test_filter_tasks_by_type_no_filter(self, mock_components):
        """Test filtering tasks by type with no filter"""
        tasks = [
            TodoItem(text="Code task", category="code", id="1"),
            TodoItem(text="Test task", category="test", id="2"),
            TodoItem(text="Doc task", category="docs", id="3")
        ]

        server = ServerCore(**mock_components)

        # No type filter
        filtered = server._filter_tasks_by_type(tasks, None)
        assert len(filtered) == 3

    def test_should_generate_todo_no_tasks(self, mock_components):
        """Test should generate todo when no tasks"""
        mock_components['todo_manager'].get_pending_tasks.return_value = []

        server = ServerCore(**mock_components)

        should_generate = server._should_generate_todo()
        assert should_generate == True

    def test_should_generate_todo_has_tasks(self, mock_components):
        """Test should generate todo when has tasks"""
        tasks = [TodoItem(text="Task", category="test", id="1")]
        mock_components['todo_manager'].get_pending_tasks.return_value = tasks

        server = ServerCore(**mock_components)

        should_generate = server._should_generate_todo()
        assert should_generate == False

    def test_should_run_revision_logic(self, mock_components):
        """Test revision running logic"""
        # Mock having tasks
        tasks = [TodoItem(text="Task", category="test", id="1")]
        mock_components['todo_manager'].get_pending_tasks.return_value = tasks

        server = ServerCore(**mock_components)

        # Should not run revision when has tasks
        should_run = server._should_run_revision()
        assert should_run == False

        # Should run revision when no tasks
        mock_components['todo_manager'].get_pending_tasks.return_value = []
        should_run = server._should_run_revision()
        assert should_run == True

    def test_get_task_delay(self, mock_components):
        """Test getting task delay"""
        server = ServerCore(**mock_components)

        delay = server._get_task_delay()
        assert delay == 1.0  # default

        # Test with custom delay
        mock_components['task_delay'] = 2.5
        server_custom = ServerCore(**mock_components)
        delay = server_custom._get_task_delay()
        assert delay == 2.5


class TestServerCoreQualityGates:
    """Smoke tests for ServerCore quality gates functionality"""

    @pytest.fixture
    def mock_quality_gate_manager(self):
        """Create mock quality gate manager"""
        manager = MagicMock()
        return manager

    @pytest.fixture
    def mock_components_with_qg(self, mock_components, mock_quality_gate_manager):
        """Create mock components with quality gates enabled"""
        mock_components['config']['quality_gates']['enabled'] = True
        mock_components['quality_gate_manager'] = mock_quality_gate_manager
        return mock_components

    def test_quality_gates_enabled_with_manager(self, mock_components_with_qg):
        """Test quality gates enabled with manager"""
        server = ServerCore(**mock_components_with_qg)
        assert server._is_quality_gates_enabled() == True

    @pytest.mark.asyncio
    async def test_quality_gates_passing(self, mock_components_with_qg, mock_quality_gate_manager):
        """Test quality gates passing allows execution"""
        from src.quality.models.quality_result import QualityGateResult, QualityResult, QualityStatus, QualityCheckType

        # Mock passing quality gate result
        passing_result = QualityGateResult(gate_name="test")
        passing_result.add_result(QualityResult(
            check_type=QualityCheckType.COVERAGE,
            status=QualityStatus.PASSED,
            score=0.9
        ))

        mock_quality_gate_manager.run_all_gates = AsyncMock(return_value=passing_result)
        mock_quality_gate_manager.should_block_execution.return_value = False

        server = ServerCore(**mock_components_with_qg)

        todo_item = TodoItem(text="Test", category="test", id="1")
        result = await server.execute_single_task(todo_item, 1, 1)

        assert result == True
        mock_components_with_qg['task_executor'].assert_called_once()

    @pytest.mark.asyncio
    async def test_quality_gates_failing_strict(self, mock_components_with_qg, mock_quality_gate_manager):
        """Test quality gates failing blocks execution in strict mode"""
        from src.quality.models.quality_result import QualityGateResult, QualityResult, QualityStatus, QualityCheckType

        mock_components_with_qg['config']['quality_gates']['strict_mode'] = True

        # Mock failing quality gate result
        failing_result = QualityGateResult(gate_name="test")
        failing_result.add_result(QualityResult(
            check_type=QualityCheckType.COVERAGE,
            status=QualityStatus.FAILED,
            score=0.3
        ))

        mock_quality_gate_manager.run_all_gates = AsyncMock(return_value=failing_result)
        mock_quality_gate_manager.should_block_execution.return_value = True

        server = ServerCore(**mock_components_with_qg)

        todo_item = TodoItem(text="Test", category="test", id="2")

        # Should raise QualityGateException
        with pytest.raises(QualityGateException):
            await server.execute_single_task(todo_item, 1, 1)

        # Task executor should not be called
        mock_components_with_qg['task_executor'].assert_not_called()


class TestQualityGateExceptionSmoke:
    """Smoke tests for QualityGateException"""

    def test_exception_creation(self):
        """Test QualityGateException can be created"""
        exc = QualityGateException("Test message")
        assert str(exc) == "Test message"
        assert exc.gate_result is None

    def test_exception_with_gate_result(self):
        """Test QualityGateException with gate result"""
        from src.quality.models.quality_result import QualityGateResult

        gate_result = QualityGateResult(gate_name="test")
        exc = QualityGateException("Failed gates", gate_result)

        assert str(exc) == "Failed gates"
        assert exc.gate_result == gate_result

    def test_exception_inheritance(self):
        """Test QualityGateException inherits from Exception"""
        exc = QualityGateException("Test")
        assert isinstance(exc, Exception)
        assert isinstance(exc, BaseException)