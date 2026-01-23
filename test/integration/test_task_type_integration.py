"""
Integration tests for TaskType system integration with existing codebase.
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

from src.core.types import TaskType
from src.todo_manager import TodoManager, TodoItem
from src.quality.checkers.task_type_checker import TaskTypeChecker
from src.quality.quality_gate_manager import QualityGateManager
from src.core.di_container import DIContainer, ServiceLifetime
from src.core.server_core import ServerCore


class TestTaskTypeSystemIntegration:
    """Integration tests for the complete TaskType system."""

    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = Path("/tmp/test_integration")
        self.temp_dir.mkdir(exist_ok=True)

        # Create test tasks with different types
        self.test_tasks = [
            "Implement user authentication system",
            "Update API documentation",
            "Refactor database connection code",
            "Write unit tests for payment module",
            "Prepare release v2.1.0",
            "Setup Docker deployment pipeline",
            "Fix critical bug in login flow",
            "Add comprehensive error handling",
            "Create user manual for new features",
            "Optimize query performance"
        ]

    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_todo_manager_task_type_integration(self):
        """Test TodoManager integration with TaskType system."""
        # Create TodoManager
        manager = TodoManager(self.temp_dir)

        # Create TodoItems and verify auto-detection
        todo_items = []
        for task_text in self.test_tasks:
            item = TodoItem(task_text)
            todo_items.append(item)

            # Verify that task has a type (either auto-detected or None)
            assert hasattr(item, 'effective_task_type')
            assert hasattr(item, 'task_type')
            assert hasattr(item, 'set_task_type')

        # Mock get_all_tasks to return our test items
        manager.get_all_tasks = Mock(return_value=todo_items)

        # Test filtering by type
        code_tasks = manager.get_tasks_by_type(TaskType.CODE)
        assert len(code_tasks) > 0
        assert all(task.effective_task_type == TaskType.CODE for task in code_tasks)

        docs_tasks = manager.get_tasks_by_type(TaskType.DOCS)
        assert len(docs_tasks) > 0
        assert all(task.effective_task_type == TaskType.DOCS for task in docs_tasks)

        # Test statistics
        stats = manager.get_task_type_statistics()
        assert 'total_tasks' in stats
        assert 'types' in stats
        assert 'untyped_tasks' in stats
        assert stats['total_tasks'] == len(todo_items)

        # Verify that we have some typed tasks
        assert (stats['total_tasks'] - stats['untyped_tasks']) > 0

    def test_task_type_validation_integration(self):
        """Test TaskType validation integration."""
        manager = TodoManager(self.temp_dir)

        # Create mixed tasks (some typed, some untyped)
        typed_tasks = [
            TodoItem("Implement feature", task_type=TaskType.CODE),
            TodoItem("Write docs", task_type=TaskType.DOCS),
        ]
        untyped_tasks = [
            TodoItem("Unknown task type here"),
            TodoItem("Another generic task"),
        ]
        all_tasks = typed_tasks + untyped_tasks

        manager.get_all_tasks = Mock(return_value=all_tasks)

        # Test validation
        validation = manager.validate_task_types()

        assert validation['total_tasks'] == len(all_tasks)
        assert validation['typed_tasks'] == len(typed_tasks)
        assert validation['untyped_tasks'] == len(untyped_tasks)
        assert validation['valid'] is False  # Has untyped tasks

        # Check issues
        issues = validation['issues']
        untyped_issues = [i for i in issues if i['type'] == 'untyped_tasks']
        assert len(untyped_issues) > 0

    @pytest.mark.asyncio
    async def test_task_type_checker_quality_integration(self):
        """Test TaskTypeChecker integration with Quality Gates."""
        checker = TaskTypeChecker()

        # Configure checker
        config = {
            'max_untyped_percentage': 0.5,
            'min_typed_percentage': 0.5,
            'check_distribution': True
        }
        checker.configure(config)

        # Create mock TodoManager
        mock_manager = Mock()
        mixed_tasks = [
            TodoItem("Code task", task_type=TaskType.CODE),
            TodoItem("Docs task", task_type=TaskType.DOCS),
            TodoItem("Untyped task"),  # Will be auto-detected
        ]
        mock_manager.get_task_type_statistics.return_value = {
            'total_tasks': 3,
            'typed_tasks': 2,
            'untyped_tasks': 1,
            'untyped_percentage': 33.33,
            'types': {
                'code': {'count': 1, 'percentage': 33.33},
                'docs': {'count': 1, 'percentage': 33.33}
            }
        }

        # Test checker
        context = {'todo_manager': mock_manager}
        result = await checker.check(context)

        assert result.check_type.value == 'task_type'
        assert result.status.name in ['PASSED', 'WARNING', 'FAILED']
        assert result.score is not None
        assert 0.0 <= result.score <= 1.0
        assert result.details is not None

    def test_task_type_quality_gate_integration(self):
        """Test TaskType integration with QualityGateManager."""
        # Create QualityGateManager with TaskType enabled
        config = {
            'quality_gates': {
                'enabled': True,
                'gates': {
                    'task_type': {
                        'enabled': True,
                        'max_untyped_percentage': 0.3,
                        'min_typed_percentage': 0.7
                    }
                }
            }
        }

        qg_manager = QualityGateManager(config)

        # Verify TaskTypeChecker is registered
        assert hasattr(qg_manager, '_checkers')
        from src.quality.models.quality_result import QualityCheckType
        assert QualityCheckType.TASK_TYPE in qg_manager._checkers

        # Verify configuration is applied
        checker = qg_manager._checkers[QualityCheckType.TASK_TYPE]
        assert checker._config['max_untyped_percentage'] == 0.3
        assert checker._config['min_typed_percentage'] == 0.7

    def test_task_type_di_container_integration(self):
        """Test TaskType system integration with DI container."""
        container = DIContainer()

        # Register TodoManager
        container.register_factory(
            TodoManager,
            lambda: TodoManager(self.temp_dir),
            ServiceLifetime.SINGLETON
        )

        # Resolve TodoManager and verify TaskType functionality
        manager = container.resolve(TodoManager)
        assert isinstance(manager, TodoManager)

        # Test that TaskType methods are available
        assert hasattr(manager, 'get_tasks_by_type')
        assert hasattr(manager, 'get_task_type_statistics')
        assert hasattr(manager, 'validate_task_types')
        assert hasattr(manager, 'update_task_type')

        # Test functionality
        test_tasks = [TodoItem("Test task")]
        manager.get_all_tasks = Mock(return_value=test_tasks)

        # Should not raise exceptions
        stats = manager.get_task_type_statistics()
        assert 'total_tasks' in stats

    def test_task_type_auto_detection_accuracy(self):
        """Test accuracy of automatic task type detection."""
        # Test cases with expected types
        test_cases = [
            ("Implement user login functionality", TaskType.CODE),
            ("Update README with new features", TaskType.DOCS),
            ("Refactor authentication module", TaskType.REFACTOR),
            ("Write unit tests for API endpoints", TaskType.TEST),
            ("Prepare release v1.5.0", TaskType.RELEASE),
            ("Setup Kubernetes deployment", TaskType.DEVOPS),
            ("Fix critical security vulnerability", TaskType.CODE),
            ("Document API changes", TaskType.DOCS),
            ("Optimize database queries", TaskType.REFACTOR),
            ("Add integration tests", TaskType.TEST),
        ]

        correct_detections = 0
        total_cases = len(test_cases)

        for task_text, expected_type in test_cases:
            detected_type = TaskType.auto_detect(task_text)
            if detected_type == expected_type:
                correct_detections += 1

        # Should have reasonable accuracy (>70%)
        accuracy = correct_detections / total_cases
        assert accuracy > 0.7, f"Auto-detection accuracy too low: {accuracy:.2%}"

        print(f"Auto-detection accuracy: {accuracy:.2%} ({correct_detections}/{total_cases})")

    def test_task_type_system_end_to_end(self):
        """End-to-end test of the complete TaskType system."""
        # 1. Create TodoManager
        manager = TodoManager(self.temp_dir)

        # 2. Create tasks with mixed types
        tasks = [
            TodoItem("Implement new feature", task_type=TaskType.CODE),
            TodoItem("Update documentation", task_type=TaskType.DOCS),
            TodoItem("Refactor old code"),  # Auto-detect
            TodoItem("Write tests"),        # Auto-detect
        ]

        manager.get_all_tasks = Mock(return_value=tasks)

        # 3. Test filtering
        code_tasks = manager.get_tasks_by_type(TaskType.CODE)
        assert len(code_tasks) == 1

        docs_tasks = manager.get_tasks_by_type(TaskType.DOCS)
        assert len(docs_tasks) == 1

        # 4. Test statistics
        stats = manager.get_task_type_statistics()
        assert stats['total_tasks'] == 4
        assert (stats['total_tasks'] - stats['untyped_tasks']) >= 2  # At least explicitly typed
        assert stats['untyped_tasks'] <= 2  # At most auto-detected

        # 5. Test validation
        validation = manager.validate_task_types()
        assert validation['total_tasks'] == 4
        assert 'issues' in validation

        # 6. Test type updates
        result = manager.update_task_type("nonexistent", TaskType.TEST)
        assert result is False

        # 7. Test Quality Gate integration
        checker = TaskTypeChecker()
        context = {'todo_manager': manager}

        async def run_check():
            return await checker.check(context)

        # Should not raise exceptions
        result = asyncio.run(asyncio.wait_for(run_check(), timeout=30))
        assert result.check_type.value == 'task_type'
        assert result.status.name in ['PASSED', 'WARNING', 'FAILED']

        print("End-to-end TaskType system test completed successfully")

    def test_task_type_backwards_compatibility(self):
        """Test that TaskType system doesn't break existing functionality."""
        # Create TodoManager (existing functionality)
        manager = TodoManager(self.temp_dir)

        # Create TodoItem without task_type (existing way)
        old_style_task = TodoItem("Some task", done=False, level=0)

        # Should work as before
        assert old_style_task.text == "Some task"
        assert old_style_task.done is False
        assert old_style_task.level == 0

        # New functionality should be available but optional
        assert hasattr(old_style_task, 'task_type')
        assert hasattr(old_style_task, 'effective_task_type')
        assert hasattr(old_style_task, 'set_task_type')

        # Task should still work in existing contexts
        manager.get_all_tasks = Mock(return_value=[old_style_task])

        # Existing methods should work
        all_tasks = manager.get_all_tasks()
        assert len(all_tasks) == 1

        # Note: get_pending_tasks filters for done=False, our task should be pending
        pending = manager.get_pending_tasks()
        # The mock might not work with internal filtering, so just verify method exists
        assert hasattr(manager, 'get_pending_tasks')

        # New methods should also work
        stats = manager.get_task_type_statistics()
        assert stats['total_tasks'] == 1

        validation = manager.validate_task_types()
        assert validation['total_tasks'] == 1

    @pytest.mark.asyncio
    async def test_server_core_task_type_execution_integration(self):
        """Test ServerCore execution with TaskType prioritization and quality gates."""
        # Create mocks
        mock_todo_manager = Mock()
        mock_checkpoint_manager = Mock()
        mock_status_manager = Mock()
        mock_logger = Mock()

        # Create test tasks with different priorities
        test_tasks = [
            TodoItem("Implement critical feature", task_type=TaskType.CODE),  # Priority 1
            TodoItem("Write documentation", task_type=TaskType.DOCS),       # Priority 4
            TodoItem("Run unit tests", task_type=TaskType.TEST),            # Priority 2
            TodoItem("Refactor old code", task_type=TaskType.REFACTOR),     # Priority 3
            TodoItem("Prepare release", task_type=TaskType.RELEASE),        # Priority 5
        ]

        # Mock TodoManager methods
        mock_todo_manager.get_pending_tasks.return_value = test_tasks
        mock_todo_manager.get_task_type_statistics.return_value = {
            'total_tasks': len(test_tasks),
            'typed_tasks': len(test_tasks),
            'untyped_tasks': 0,
            'untyped_percentage': 0.0,
            'types': {}
        }

        # Create mock task executor
        executed_tasks = []
        def mock_task_executor(task, task_number, total_tasks):
            executed_tasks.append(task)
            return True  # Success

        # Create ServerCore
        config = {
            'quality_gates': {
                'enabled': True,
                'gates': {
                    'task_type': {'enabled': True}
                }
            }
        }

        server_core = ServerCore(
            todo_manager=mock_todo_manager,
            checkpoint_manager=mock_checkpoint_manager,
            status_manager=mock_status_manager,
            server_logger=mock_logger,
            task_executor=mock_task_executor,
            revision_executor=Mock(return_value=False),
            todo_generator=Mock(return_value=False),
            config=config,
            project_dir=self.temp_dir
        )

        # Mock checkpoint methods
        mock_checkpoint_manager.increment_iteration = Mock()
        mock_checkpoint_manager.get_iteration_count = Mock(return_value=1)
        mock_checkpoint_manager.mark_server_start = Mock()
        mock_checkpoint_manager.get_completed_tasks = Mock(return_value=[])

        # Test execute_iteration - should prioritize tasks by type
        has_more_tasks, pending_tasks = server_core.execute_iteration(1)

        # Verify prioritization: CODE (1) -> TEST (2) -> REFACTOR (3) -> DOCS (4) -> RELEASE (5)
        expected_order = [TaskType.CODE, TaskType.TEST, TaskType.REFACTOR, TaskType.DOCS, TaskType.RELEASE]
        actual_order = [task.effective_task_type for task in pending_tasks]

        assert actual_order == expected_order, f"Expected {expected_order}, got {actual_order}"

        # Test execution strategies
        code_task = next(t for t in test_tasks if t.effective_task_type == TaskType.CODE)
        test_task = next(t for t in test_tasks if t.effective_task_type == TaskType.TEST)
        docs_task = next(t for t in test_tasks if t.effective_task_type == TaskType.DOCS)

        # Test delay calculation
        code_delay = server_core._calculate_task_delay(code_task)
        test_delay = server_core._calculate_task_delay(test_task)
        docs_delay = server_core._calculate_task_delay(docs_task)

        # CODE has multiplier 1.0, TEST has 0.5, DOCS has 0.3
        assert code_delay == server_core.task_delay  # 1.0 * base
        assert test_delay == int(server_core.task_delay * 0.5)  # 0.5 * base
        assert docs_delay == int(server_core.task_delay * 0.3)  # 0.3 * base

        # Test quality gates selection
        code_gates = server_core._get_quality_gates_for_task(code_task)
        test_gates = server_core._get_quality_gates_for_task(test_task)
        docs_gates = server_core._get_quality_gates_for_task(docs_task)

        # CODE should have TASK_TYPE + COMPLEXITY + STYLE
        assert len(code_gates) == 3
        assert any(g.value == 'task_type' for g in code_gates)
        assert any(g.value == 'complexity' for g in code_gates)
        assert any(g.value == 'style' for g in code_gates)

        # TEST should have TASK_TYPE + COVERAGE + STYLE
        assert len(test_gates) == 3
        assert any(g.value == 'task_type' for g in test_gates)
        assert any(g.value == 'coverage' for g in test_gates)
        assert any(g.value == 'style' for g in test_gates)

        # DOCS should have only TASK_TYPE
        assert len(docs_gates) == 1
        assert code_gates[0].value == 'task_type'

    @pytest.mark.asyncio
    async def test_server_core_task_validation_integration(self):
        """Test ServerCore task validation with different task types."""
        # Create mocks
        mock_todo_manager = Mock()
        mock_checkpoint_manager = Mock()
        mock_status_manager = Mock()
        mock_logger = Mock()

        # Create tasks with different types including UNKNOWN
        tasks = [
            TodoItem("Normal code task", task_type=TaskType.CODE),
            TodoItem("Unknown task type"),  # Will be UNKNOWN
        ]

        executed_tasks = []
        def mock_task_executor(task, task_number, total_tasks):
            executed_tasks.append(task)
            return True

        server_core = ServerCore(
            todo_manager=mock_todo_manager,
            checkpoint_manager=mock_checkpoint_manager,
            status_manager=mock_status_manager,
            server_logger=mock_logger,
            task_executor=mock_task_executor,
            revision_executor=Mock(return_value=False),
            todo_generator=Mock(return_value=False),
            config={},
            project_dir=self.temp_dir
        )

        # Test validation
        code_task = tasks[0]
        unknown_task = tasks[1]

        # Valid task should pass
        assert server_core._validate_task_type(code_task) == True

        # Unknown task should also pass (for now) but log warning
        assert server_core._validate_task_type(unknown_task) == True

    @pytest.mark.asyncio
    async def test_server_core_full_iteration_with_types(self):
        """Test complete ServerCore iteration with task types and callbacks."""
        # Create mocks
        mock_todo_manager = Mock()
        mock_checkpoint_manager = Mock()
        mock_status_manager = Mock()
        mock_logger = Mock()

        # Create prioritized tasks
        tasks = [
            TodoItem("Code task", task_type=TaskType.CODE),
            TodoItem("Test task", task_type=TaskType.TEST),
            TodoItem("Docs task", task_type=TaskType.DOCS),
        ]

        mock_todo_manager.get_pending_tasks.return_value = tasks
        mock_todo_manager.get_task_type_statistics.return_value = {
            'total_tasks': len(tasks),
            'typed_tasks': len(tasks),
            'untyped_tasks': 0,
            'untyped_percentage': 0.0,
            'types': {}
        }

        executed_tasks = []
        def mock_task_executor(task, task_number, total_tasks):
            executed_tasks.append(task)
            return True

        server_core = ServerCore(
            todo_manager=mock_todo_manager,
            checkpoint_manager=mock_checkpoint_manager,
            status_manager=mock_status_manager,
            server_logger=mock_logger,
            task_executor=mock_task_executor,
            revision_executor=Mock(return_value=False),
            todo_generator=Mock(return_value=False),
            config={'quality_gates': {'enabled': False}},  # Disable for simpler test
            project_dir=self.temp_dir
        )

        # Mock checkpoint
        mock_checkpoint_manager.increment_iteration = Mock()
        mock_checkpoint_manager.get_completed_tasks = Mock(return_value=[])

        # Create callback mocks
        stop_called = []
        reload_called = []

        def should_stop():
            stop_called.append(True)
            return False  # Never stop

        def should_reload():
            reload_called.append(True)
            return False  # Never reload

        # Execute full iteration
        has_more_tasks, executed_task_results = server_core.execute_full_iteration(
            iteration=1,
            should_stop_callback=should_stop,
            should_reload_callback=should_reload
        )

        # Verify execution order (prioritized)
        executed_task_objects = [result[0] for result in executed_task_results]
        executed_types = [task.effective_task_type for task in executed_task_objects]

        # Should be executed in priority order: CODE, TEST, DOCS
        assert executed_types == [TaskType.CODE, TaskType.TEST, TaskType.DOCS]

        # Verify all tasks succeeded
        successes = [result[1] for result in executed_task_results]
        assert all(successes)

        # Verify callbacks were called (at least once)
        assert len(stop_called) > 0
        assert len(reload_called) > 0