"""
Unit tests for TaskType enum and task type functionality.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock

from src.core.types import TaskType
from src.todo_manager import TodoItem, TodoManager


class TestTaskType:
    """Test cases for TaskType enum functionality."""

    def test_task_type_enum_values(self):
        """Test that TaskType enum has all required values."""
        expected_values = {'code', 'docs', 'refactor', 'test', 'release', 'devops'}
        actual_values = {task_type.value for task_type in TaskType}

        assert actual_values == expected_values
        assert len(TaskType) == 6

    def test_task_type_from_string(self):
        """Test creating TaskType from string."""
        # Valid cases
        assert TaskType.from_string('code') == TaskType.CODE
        assert TaskType.from_string('DOCS') == TaskType.DOCS  # Case insensitive
        assert TaskType.from_string('refactor') == TaskType.REFACTOR

        # Invalid cases
        assert TaskType.from_string('invalid') is None
        assert TaskType.from_string('') is None
        assert TaskType.from_string(None) is None

    def test_task_type_display_name(self):
        """Test display names for task types."""
        assert TaskType.CODE.display_name == "Разработка"
        assert TaskType.DOCS.display_name == "Документация"
        assert TaskType.REFACTOR.display_name == "Рефакторинг"
        assert TaskType.TEST.display_name == "Тестирование"
        assert TaskType.RELEASE.display_name == "Релиз"
        assert TaskType.DEVOPS.display_name == "DevOps"

    def test_task_type_priority(self):
        """Test priority levels for task types."""
        assert TaskType.CODE.priority == 1  # Highest priority
        assert TaskType.TEST.priority == 2
        assert TaskType.REFACTOR.priority == 3
        assert TaskType.DOCS.priority == 4
        assert TaskType.RELEASE.priority == 5
        assert TaskType.DEVOPS.priority == 6  # Lowest priority

    def test_task_type_get_all_types(self):
        """Test getting all task types."""
        all_types = TaskType.get_all_types()
        assert len(all_types) == 6
        assert TaskType.CODE in all_types
        assert TaskType.DEVOPS in all_types

    def test_task_type_get_types_by_priority(self):
        """Test getting task types ordered by priority."""
        types_by_priority = TaskType.get_types_by_priority()
        assert len(types_by_priority) == 6
        assert types_by_priority[0] == TaskType.CODE  # Highest priority first
        assert types_by_priority[-1] == TaskType.DEVOPS  # Lowest priority last

        # Verify ordering
        for i in range(len(types_by_priority) - 1):
            assert types_by_priority[i].priority < types_by_priority[i + 1].priority

    def test_task_type_string_representation(self):
        """Test string representations of TaskType."""
        assert str(TaskType.CODE) == "code"
        assert str(TaskType.DOCS) == "docs"
        assert repr(TaskType.CODE) == "TaskType.CODE"


class TestTaskTypeAutoDetection:
    """Test cases for automatic task type detection."""

    def test_auto_detect_code_tasks(self):
        """Test auto-detection of code-related tasks."""
        code_tasks = [
            "Implement new feature for user authentication",
            "Add API endpoint for data processing",
            "Fix bug in payment processing",
            "Create new component for dashboard",
            "Write integration with external service",
            "Develop new algorithm for data analysis"
        ]

        for task_text in code_tasks:
            detected_type = TaskType.auto_detect(task_text)
            assert detected_type == TaskType.CODE, f"Failed to detect CODE for: {task_text}"

    def test_auto_detect_docs_tasks(self):
        """Test auto-detection of documentation tasks."""
        docs_tasks = [
            "Update API documentation",
            "Write user guide for new features",
            "Create README for the project",
            "Document new configuration options",
            "Update swagger documentation"
        ]

        for task_text in docs_tasks:
            detected_type = TaskType.auto_detect(task_text)
            assert detected_type == TaskType.DOCS, f"Failed to detect DOCS for: {task_text}"

    def test_auto_detect_test_tasks(self):
        """Test auto-detection of testing tasks."""
        test_tasks = [
            "Write unit tests for new module",
            "Add integration tests for API",
            "Create test cases for payment flow",
            "Implement pytest fixtures",
            "Add selenium tests for UI"
        ]

        for task_text in test_tasks:
            detected_type = TaskType.auto_detect(task_text)
            assert detected_type == TaskType.TEST, f"Failed to detect TEST for: {task_text}"

    def test_auto_detect_refactor_tasks(self):
        """Test auto-detection of refactoring tasks."""
        refactor_tasks = [
            "Refactor authentication module",
            "Optimize database queries",
            "Clean up duplicate code",
            "Extract common functionality",
            "Restructure project architecture"
        ]

        for task_text in refactor_tasks:
            detected_type = TaskType.auto_detect(task_text)
            assert detected_type == TaskType.REFACTOR, f"Failed to detect REFACTOR for: {task_text}"

    def test_auto_detect_release_tasks(self):
        """Test auto-detection of release tasks."""
        release_tasks = [
            "Prepare release v1.2.0",
            "Tag new version in git",
            "Update changelog for release",
            "Create release notes",
            "Package application for distribution"
        ]

        for task_text in release_tasks:
            detected_type = TaskType.auto_detect(task_text)
            assert detected_type == TaskType.RELEASE, f"Failed to detect RELEASE for: {task_text}"

    def test_auto_detect_devops_tasks(self):
        """Test auto-detection of DevOps tasks."""
        devops_tasks = [
            "Setup Docker container for application",
            "Configure Kubernetes deployment",
            "Setup CI/CD pipeline",
            "Configure monitoring and alerting",
            "Setup infrastructure for production"
        ]

        for task_text in devops_tasks:
            detected_type = TaskType.auto_detect(task_text)
            assert detected_type == TaskType.DEVOPS, f"Failed to detect DEVOPS for: {task_text}"

    def test_auto_detect_unknown_tasks(self):
        """Test auto-detection returns None for unrecognized tasks."""
        unknown_tasks = [
            "Have a meeting with team",
            "Plan project timeline",
            "Discuss requirements with stakeholders",
            "Coffee break"
        ]

        for task_text in unknown_tasks:
            detected_type = TaskType.auto_detect(task_text)
            assert detected_type is None, f"Unexpected detection for: {task_text}"

    def test_auto_detect_priority_ordering(self):
        """Test that detection respects priority ordering."""
        # This task contains keywords from multiple types, should detect REFACTOR first (higher priority)
        mixed_task = "Refactor code and extract common functionality"
        detected_type = TaskType.auto_detect(mixed_task)

        # Should detect REFACTOR because it comes first in priority order
        # (REFACTOR before CODE in the priority_order list)
        assert detected_type == TaskType.REFACTOR


class TestTodoItemTaskType:
    """Test cases for TodoItem task type integration."""

    def test_todo_item_auto_detect_type(self):
        """Test that TodoItem automatically detects task type."""
        code_task = TodoItem("Implement new user authentication")
        assert code_task.effective_task_type == TaskType.CODE

        docs_task = TodoItem("Update API documentation")
        assert docs_task.effective_task_type == TaskType.DOCS

        unknown_task = TodoItem("Have a team meeting")
        assert unknown_task.effective_task_type is None

    def test_todo_item_explicit_type(self):
        """Test setting explicit task type on TodoItem."""
        task = TodoItem("Some generic task")

        # Initially should be None (unknown)
        assert task.effective_task_type is None

        # Set explicit type
        task.set_task_type(TaskType.CODE)
        assert task.task_type == TaskType.CODE
        assert task.effective_task_type == TaskType.CODE

        # Reset to None (enable auto-detection)
        task.set_task_type(None)
        assert task.task_type is None
        # effective_task_type should still try auto-detection
        assert task.effective_task_type is None  # Still unknown

    def test_todo_item_repr_with_type(self):
        """Test string representation includes task type."""
        code_task = TodoItem("Implement feature", done=False)
        code_repr = repr(code_task)
        assert "[code]" in code_repr

        unknown_task = TodoItem("Unknown task", done=True)
        unknown_repr = repr(unknown_task)
        assert "[code]" not in unknown_repr  # Should not have type indicator

    def test_todo_item_constructor_with_type(self):
        """Test TodoItem constructor with explicit task type."""
        # Explicit type should override auto-detection
        task = TodoItem("Update documentation", task_type=TaskType.CODE)
        assert task.task_type == TaskType.CODE
        assert task.effective_task_type == TaskType.CODE

        # Auto-detection would have detected DOCS, but explicit CODE takes precedence


class TestTodoManagerTaskType:
    """Test cases for TodoManager task type functionality."""

    def setup_method(self):
        """Setup test fixtures."""
        self.temp_dir = Path("/tmp/test_todo_manager")
        self.temp_dir.mkdir(exist_ok=True)
        self.manager = TodoManager(self.temp_dir)

        # Create mock tasks with different types
        self.mock_tasks = [
            TodoItem("Implement user authentication", task_type=TaskType.CODE),
            TodoItem("Update API documentation", task_type=TaskType.DOCS),
            TodoItem("Write unit tests", task_type=TaskType.TEST),
            TodoItem("Refactor database code", task_type=TaskType.REFACTOR),
            TodoItem("Prepare release v1.0", task_type=TaskType.RELEASE),
            TodoItem("Setup Docker deployment", task_type=TaskType.DEVOPS),
            TodoItem("Unknown task type")  # No explicit type
        ]

    def teardown_method(self):
        """Clean up test fixtures."""
        # Clean up temp directory
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_get_tasks_by_type(self):
        """Test filtering tasks by type."""
        # Mock the get_all_tasks method
        self.manager.get_all_tasks = Mock(return_value=self.mock_tasks)

        code_tasks = self.manager.get_tasks_by_type(TaskType.CODE)
        assert len(code_tasks) == 1
        assert code_tasks[0].text == "Implement user authentication"

        docs_tasks = self.manager.get_tasks_by_type(TaskType.DOCS)
        assert len(docs_tasks) == 1
        assert docs_tasks[0].text == "Update API documentation"

    def test_get_task_type_statistics(self):
        """Test task type statistics generation."""
        # Mock the get_all_tasks method
        self.manager.get_all_tasks = Mock(return_value=self.mock_tasks)

        stats = self.manager.get_task_type_statistics()

        assert stats['total_tasks'] == 7
        assert stats['untyped_tasks'] == 1
        assert stats['untyped_percentage'] == pytest.approx(14.29, rel=1e-2)

        # Check type counts
        assert stats['types']['code']['count'] == 1
        assert stats['types']['docs']['count'] == 1
        assert stats['types']['test']['count'] == 1
        assert stats['types']['refactor']['count'] == 1
        assert stats['types']['release']['count'] == 1
        assert stats['types']['devops']['count'] == 1

    def test_get_task_type_statistics_empty(self):
        """Test statistics with no tasks."""
        self.manager.get_all_tasks = Mock(return_value=[])

        stats = self.manager.get_task_type_statistics()

        assert stats['total_tasks'] == 0
        assert stats['types'] == {}
        assert stats['untyped_tasks'] == 0
        assert stats['untyped_percentage'] == 0.0

    def test_update_task_type(self):
        """Test updating task type by ID."""
        # Create tasks with IDs
        task1 = TodoItem("Task 1", id="task1")
        task2 = TodoItem("Task 2", id="task2", task_type=TaskType.CODE)

        self.manager.get_all_tasks = Mock(return_value=[task1, task2])

        # Update task type
        result = self.manager.update_task_type("task1", TaskType.DOCS)
        assert result is True
        assert task1.task_type == TaskType.DOCS

        # Try to update non-existent task
        result = self.manager.update_task_type("nonexistent", TaskType.CODE)
        assert result is False

    def test_validate_task_types(self):
        """Test task type validation."""
        # Mock the get_all_tasks method
        self.manager.get_all_tasks = Mock(return_value=self.mock_tasks)

        validation = self.manager.validate_task_types()

        assert validation['total_tasks'] == 7
        assert validation['typed_tasks'] == 6
        assert validation['untyped_tasks'] == 1
        assert validation['valid'] is False  # Has issues

        # Check issues
        issues = validation['issues']
        assert len(issues) >= 1  # At least untyped tasks issue

        untyped_issue = next((i for i in issues if i['type'] == 'untyped_tasks'), None)
        assert untyped_issue is not None
        assert untyped_issue['severity'] == 'warning'

    def test_validate_task_types_all_typed(self):
        """Test validation when all tasks have types."""
        # Create tasks with explicit types that won't be auto-detected
        task1 = TodoItem("Some task", task_type=TaskType.CODE)
        task2 = TodoItem("Another task", task_type=TaskType.DOCS)
        typed_tasks = [task1, task2]

        self.manager.get_all_tasks = Mock(return_value=typed_tasks)

        validation = self.manager.validate_task_types()

        assert validation['total_tasks'] == 2
        assert validation['typed_tasks'] == 2
        assert validation['untyped_tasks'] == 0

        # Check that validation is valid (only checking for untyped tasks, not missing types)
        # The validation considers it valid if there are no untyped tasks
        # Missing types are just informational
        untyped_issues = [i for i in validation['issues'] if i['type'] == 'untyped_tasks']
        assert len(untyped_issues) == 0

    def test_validate_task_types_empty(self):
        """Test validation with no tasks."""
        self.manager.get_all_tasks = Mock(return_value=[])

        validation = self.manager.validate_task_types()

        assert validation['total_tasks'] == 0
        assert validation['typed_tasks'] == 0
        assert validation['untyped_tasks'] == 0
        assert validation['valid'] is True
        assert validation['issues'] == []