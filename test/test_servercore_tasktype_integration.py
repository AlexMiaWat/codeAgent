"""
Test integration of ServerCore with TaskType system
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, AsyncMock
from collections import defaultdict

from src.core.server_core import ServerCore
from src.todo_manager import TodoItem
from src.core.types import TaskType


class TestServerCoreTaskTypeIntegration:
    """Test ServerCore integration with TaskType system"""

    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = Path(tempfile.mkdtemp())

        # Create mock managers
        self.mock_todo_manager = Mock()
        self.mock_checkpoint_manager = Mock()
        self.mock_status_manager = Mock()
        self.mock_logger = Mock()

        # Create ServerCore
        self.server_core = ServerCore(
            todo_manager=self.mock_todo_manager,
            checkpoint_manager=self.mock_checkpoint_manager,
            status_manager=self.mock_status_manager,
            server_logger=self.mock_logger,
            task_executor=Mock(),
            revision_executor=Mock(),
            todo_generator=Mock(),
            config={},
            project_dir=self.temp_dir,
            auto_todo_enabled=False
        )

    def teardown_method(self):
        """Clean up"""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_task_prioritization_by_type(self):
        """Test that tasks are prioritized by type"""
        # Create tasks of different types
        tasks = [
            TodoItem("Documentation task", task_type=TaskType.DOCS),  # Priority 4
            TodoItem("Code task", task_type=TaskType.CODE),          # Priority 1 (highest)
            TodoItem("Test task", task_type=TaskType.TEST),          # Priority 2
            TodoItem("Refactor task", task_type=TaskType.REFACTOR),  # Priority 3
        ]

        # Mock get_pending_tasks to return our tasks
        self.mock_todo_manager.get_pending_tasks.return_value = tasks
        self.mock_checkpoint_manager.get_completed_tasks.return_value = []

        # Execute iteration
        has_more_tasks, pending_tasks = self.server_core.execute_iteration(1)

        # Check that tasks are prioritized (CODE first, then TEST, etc.)
        assert len(pending_tasks) == 4
        assert pending_tasks[0].effective_task_type == TaskType.CODE
        assert pending_tasks[1].effective_task_type == TaskType.TEST
        assert pending_tasks[2].effective_task_type == TaskType.REFACTOR
        assert pending_tasks[3].effective_task_type == TaskType.DOCS

    def test_task_type_strategies_applied(self):
        """Test that different execution strategies are applied based on task type"""
        # Test CODE strategy
        code_strategy = self.server_core._get_execution_strategy(
            TodoItem("Code task", task_type=TaskType.CODE)
        )
        assert code_strategy['priority'] == 1
        assert code_strategy['batch_size'] == 3
        assert code_strategy['delay_multiplier'] == 1.0
        assert code_strategy['quality_gates_required'] is True

        # Test DOCS strategy
        docs_strategy = self.server_core._get_execution_strategy(
            TodoItem("Docs task", task_type=TaskType.DOCS)
        )
        assert docs_strategy['priority'] == 4
        assert docs_strategy['batch_size'] == 5
        assert docs_strategy['delay_multiplier'] == 0.3
        assert docs_strategy['quality_gates_required'] is False

        # Test unknown type strategy
        unknown_strategy = self.server_core._get_execution_strategy(
            TodoItem("Unknown task")
        )
        assert unknown_strategy['priority'] == 99
        assert unknown_strategy['batch_size'] == 1
        assert unknown_strategy['delay_multiplier'] == 1.0

    def test_task_delay_calculation_by_type(self):
        """Test that task delays are calculated based on task type"""
        base_delay = 5
        self.server_core.task_delay = base_delay

        # Test CODE task (multiplier 1.0)
        code_task = TodoItem("Code task", task_type=TaskType.CODE)
        code_delay = self.server_core._calculate_task_delay(code_task)
        assert code_delay == int(base_delay * 1.0)  # Should be 5

        # Test DOCS task (multiplier 0.3)
        docs_task = TodoItem("Docs task", task_type=TaskType.DOCS)
        docs_delay = self.server_core._calculate_task_delay(docs_task)
        assert docs_delay == int(base_delay * 0.3)  # Should be 1 (int(1.5) = 1)

        # Test RELEASE task (multiplier 2.0)
        release_task = TodoItem("Release task", task_type=TaskType.RELEASE)
        release_delay = self.server_core._calculate_task_delay(release_task)
        assert release_delay == int(base_delay * 2.0)  # Should be 10

    def test_quality_gates_applied_by_task_type(self):
        """Test that quality gates are applied based on task type"""
        # Enable quality gates globally
        self.server_core.config = {'quality_gates': {'enabled': True}}

        # CODE tasks should require quality gates
        code_task = TodoItem("Code task", task_type=TaskType.CODE)
        assert self.server_core._should_apply_quality_gates(code_task) is True

        # DOCS tasks should not require quality gates
        docs_task = TodoItem("Docs task", task_type=TaskType.DOCS)
        assert self.server_core._should_apply_quality_gates(docs_task) is False

        # Test with quality gates disabled globally
        self.server_core.config = {'quality_gates': {'enabled': False}}
        assert self.server_core._should_apply_quality_gates(code_task) is False
        assert self.server_core._should_apply_quality_gates(docs_task) is False

    def test_batch_execution_by_task_type(self):
        """Test that tasks are executed in batches by type"""
        # Create tasks of different types
        tasks = [
            TodoItem("Code 1", task_type=TaskType.CODE),
            TodoItem("Code 2", task_type=TaskType.CODE),
            TodoItem("Code 3", task_type=TaskType.CODE),
            TodoItem("Code 4", task_type=TaskType.CODE),  # Should be in next batch
            TodoItem("Test 1", task_type=TaskType.TEST),
            TodoItem("Docs 1", task_type=TaskType.DOCS),
            TodoItem("Docs 2", task_type=TaskType.DOCS),
            TodoItem("Docs 3", task_type=TaskType.DOCS),
            TodoItem("Docs 4", task_type=TaskType.DOCS),
            TodoItem("Docs 5", task_type=TaskType.DOCS),  # Should be in next batch
        ]

        # Mock get_pending_tasks
        self.mock_todo_manager.get_pending_tasks.return_value = tasks
        self.mock_checkpoint_manager.get_completed_tasks.return_value = []

        # Execute iteration
        has_more_tasks, pending_tasks = self.server_core.execute_iteration(1)

        # Verify tasks are returned (prioritized)
        assert len(pending_tasks) == 10
        # CODE tasks should come first
        code_tasks = [t for t in pending_tasks if t.effective_task_type == TaskType.CODE]
        assert len(code_tasks) == 4

    def test_servercore_handles_task_type_auto_detection(self):
        """Test that ServerCore works with auto-detected task types"""
        # Create tasks without explicit types (will use auto-detection)
        tasks = [
            TodoItem("Implement user authentication system"),  # Should be CODE
            TodoItem("Update API documentation"),              # Should be DOCS
            TodoItem("Write unit tests for payment module"),   # Should be TEST
        ]

        self.mock_todo_manager.get_pending_tasks.return_value = tasks
        self.mock_checkpoint_manager.get_completed_tasks.return_value = []

        # Execute iteration
        has_more_tasks, pending_tasks = self.server_core.execute_iteration(1)

        # Tasks should be prioritized based on auto-detected types
        assert len(pending_tasks) == 3
        # CODE task should come first (priority 1)
        assert pending_tasks[0].text == "Implement user authentication system"

    def test_execution_strategies_initialization(self):
        """Test that execution strategies are properly initialized"""
        strategies = self.server_core._execution_strategies

        assert len(strategies) == 6  # All TaskType values

        # Check CODE strategy
        code_strategy = strategies[TaskType.CODE]
        assert code_strategy['priority'] == 1
        assert code_strategy['batch_size'] == 3
        assert code_strategy['quality_gates_required'] is True

        # Check DOCS strategy
        docs_strategy = strategies[TaskType.DOCS]
        assert docs_strategy['priority'] == 4
        assert docs_strategy['batch_size'] == 5
        assert docs_strategy['quality_gates_required'] is False

        # Check RELEASE strategy (most conservative)
        release_strategy = strategies[TaskType.RELEASE]
        assert release_strategy['priority'] == 5
        assert release_strategy['batch_size'] == 1
        assert release_strategy['max_failures'] == 0  # Zero tolerance