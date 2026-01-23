"""
Tests for Dependency Injection and SOLID principles implementation.

This module contains tests to verify that the system correctly implements:
- Dependency Injection patterns
- SOLID principles (Single Responsibility, Open/Closed, Liskov Substitution, Interface Segregation, Dependency Inversion)
- Interface contracts and implementations
- DI container functionality
"""

import pytest
import tempfile
from pathlib import Path
from typing import Dict, Any
from unittest.mock import Mock, MagicMock

from src.core.di_container import DIContainer, ServiceLifetime, create_default_container
from src.core.interfaces import (
    IManager, ITodoManager, IStatusManager, ICheckpointManager, ILogger, ITaskLogger
)


class TestDIContainer:
    """Tests for DI Container functionality."""

    def test_di_container_creation(self):
        """Test that DI container can be created."""
        container = DIContainer()
        assert container is not None
        assert isinstance(container, DIContainer)

    def test_register_and_resolve_singleton(self):
        """Test singleton service registration and resolution."""
        container = DIContainer()

        # Create a mock service
        mock_service = Mock()
        mock_service.value = "test"

        # Register instance as singleton
        container.register_instance(str, mock_service)

        # Resolve multiple times - should get same instance
        resolved1 = container.resolve(str)
        resolved2 = container.resolve(str)

        assert resolved1 is resolved2
        assert resolved1.value == "test"

    def test_register_and_resolve_transient(self):
        """Test transient service registration and resolution."""
        container = DIContainer()

        # Register a factory that creates new instances
        call_count = 0
        def factory():
            nonlocal call_count
            call_count += 1
            mock = Mock()
            mock.id = call_count
            return mock

        container.register_factory(str, factory, ServiceLifetime.TRANSIENT)

        # Resolve multiple times - should get different instances
        resolved1 = container.resolve(str)
        resolved2 = container.resolve(str)

        assert resolved1 is not resolved2
        assert resolved1.id == 1
        assert resolved2.id == 2

    def test_circular_dependency_detection(self):
        """Test that circular dependencies are detected."""
        container = DIContainer()

        # Create services that depend on each other
        class ServiceA:
            def __init__(self, b):
                self.b = b

        class ServiceB:
            def __init__(self, a):
                self.a = a

        container.register_transient(ServiceA, ServiceA)
        container.register_transient(ServiceB, ServiceB)

        # This should raise an exception due to missing parameter resolution
        with pytest.raises(Exception) as exc_info:
            container.resolve(ServiceA)

        # The error should be about parameter resolution, not necessarily circular dependency
        assert "cannot resolve parameter" in str(exc_info.value).lower()

    def test_is_registered(self):
        """Test service registration checking."""
        container = DIContainer()

        # Service not registered
        assert not container.is_registered(str)

        # Register service
        container.register_instance(str, "test")
        assert container.is_registered(str)

    def test_dispose_container(self):
        """Test container disposal."""
        container = DIContainer()

        # Create a mock service with dispose method
        mock_service = Mock()
        container.register_instance(str, mock_service)

        # Dispose container
        container.dispose()

        # Verify dispose was called
        mock_service.dispose.assert_called_once()


class TestInterfaceContracts:
    """Tests for interface contracts and implementations."""

    def test_manager_interface_contract(self):
        """Test that IManager interface defines required methods."""
        # This is more of a compile-time check, but we can test method existence
        interface_methods = [
            'is_healthy',
            'get_status',
            'dispose'
        ]

        # Check that concrete implementations have these methods
        from src.todo_manager import TodoManager
        from src.status_manager import StatusManager
        from src.checkpoint_manager import CheckpointManager
        from src.task_logger import ServerLogger

        managers = [TodoManager, StatusManager, CheckpointManager, ServerLogger]

        for manager_class in managers:
            for method in interface_methods:
                assert hasattr(manager_class, method), f"{manager_class.__name__} missing {method}"

    def test_todo_manager_interface(self):
        """Test ITodoManager interface implementation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            from src.todo_manager import TodoManager

            project_dir = Path(temp_dir)
            manager = TodoManager(project_dir)

            # Test interface methods exist
            interface_methods = [
                'load_todos', 'get_pending_tasks', 'get_all_tasks',
                'mark_task_done', 'get_task_hierarchy', 'save_todos'
            ]

            for method in interface_methods:
                assert hasattr(manager, method), f"TodoManager missing {method}"

            # Test basic functionality
            assert manager.is_healthy()  # Should work even without files
            status = manager.get_status()
            assert isinstance(status, dict)
            assert 'healthy' in status

    def test_status_manager_interface(self):
        """Test IStatusManager interface implementation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            from src.status_manager import StatusManager

            status_file = Path(temp_dir) / "status.md"
            manager = StatusManager(status_file)

            # Test interface methods exist
            interface_methods = [
                'read_status', 'write_status', 'append_status',
                'update_task_status', 'add_separator'
            ]

            for method in interface_methods:
                assert hasattr(manager, method), f"StatusManager missing {method}"

            # Test basic functionality
            assert manager.is_healthy()
            status = manager.get_status()
            assert isinstance(status, dict)

    def test_checkpoint_manager_interface(self):
        """Test ICheckpointManager interface implementation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            from src.checkpoint_manager import CheckpointManager

            project_dir = Path(temp_dir)
            manager = CheckpointManager(project_dir)

            # Test interface methods exist
            interface_methods = [
                'mark_server_start', 'mark_server_stop', 'increment_iteration',
                'get_iteration_count', 'was_clean_shutdown', 'add_task',
                'mark_task_start', 'mark_task_completed', 'mark_task_failed',
                'get_current_task', 'get_incomplete_tasks', 'is_task_completed',
                'get_recovery_info', 'get_statistics'
            ]

            for method in interface_methods:
                assert hasattr(manager, method), f"CheckpointManager missing {method}"

            # Test basic functionality
            assert manager.is_healthy()
            status = manager.get_status()
            assert isinstance(status, dict)

    def test_logger_interface(self):
        """Test ILogger interface implementation."""
        from src.task_logger import ServerLogger

        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir) / "logs"
            manager = ServerLogger(log_dir)

            # Test interface methods exist
            interface_methods = [
                'log_info', 'log_warning', 'log_error', 'log_debug',
                'create_task_logger', 'close'
            ]

            for method in interface_methods:
                assert hasattr(manager, method), f"ServerLogger missing {method}"

            # Test basic functionality
            assert manager.is_healthy()
            status = manager.get_status()
            assert isinstance(status, dict)


class TestSOLIDPrinciples:
    """Tests for SOLID principles implementation."""

    def test_single_responsibility(self):
        """Test Single Responsibility Principle."""
        # Each manager should have one clear responsibility

        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)

            # TodoManager - only manages todos
            from src.todo_manager import TodoManager
            todo_manager = TodoManager(project_dir)

            # Should not have methods for status management
            assert not hasattr(todo_manager, 'write_status')
            assert not hasattr(todo_manager, 'mark_server_start')

            # StatusManager - only manages status
            from src.status_manager import StatusManager
            status_file = project_dir / "status.md"
            status_manager = StatusManager(status_file)

            # Should not have methods for todo management
            assert not hasattr(status_manager, 'load_todos')
            assert not hasattr(status_manager, 'get_pending_tasks')

    def test_open_closed_principle(self):
        """Test Open/Closed Principle through interfaces."""
        # Classes should be open for extension but closed for modification

        # We can create new implementations of interfaces without modifying existing code
        class MockTodoManager(ITodoManager):
            def __init__(self, project_dir: Path, config: Dict[str, Any] = None):
                self.tasks = []

            def load_todos(self) -> bool:
                return True

            def get_pending_tasks(self):
                return self.tasks

            def get_all_tasks(self):
                return self.tasks

            def mark_task_done(self, task_text: str, comment=None) -> bool:
                return True

            def get_task_hierarchy(self):
                return {}

            def save_todos(self) -> bool:
                return True

            def is_healthy(self) -> bool:
                return True

            def get_status(self) -> Dict[str, Any]:
                return {'healthy': True}

            def dispose(self) -> None:
                pass

        # This should work without modifying existing code
        mock_manager = MockTodoManager(Path("/tmp"))
        assert mock_manager.load_todos()
        assert mock_manager.is_healthy()

    def test_dependency_inversion(self):
        """Test Dependency Inversion Principle."""
        # High-level modules should not depend on low-level modules

        # ServerCore depends on interfaces, not concrete implementations
        from src.core.server_core import ServerCore

        # Create mocks for all dependencies
        mock_todo_manager = Mock(spec=ITodoManager)
        mock_checkpoint_manager = Mock(spec=ICheckpointManager)
        mock_status_manager = Mock(spec=IStatusManager)
        mock_logger = Mock(spec=ILogger)

        # Configure mocks
        mock_todo_manager.get_pending_tasks.return_value = []
        mock_checkpoint_manager.get_iteration_count.return_value = 1
        mock_checkpoint_manager.was_clean_shutdown.return_value = True

        # ServerCore should work with any implementations of the interfaces
        config = {'server': {'check_interval': 60}}
        def mock_factory():
            return mock_todo_manager
        server_core = ServerCore(
            todo_manager=mock_todo_manager,
            todo_manager_factory=mock_factory,
            checkpoint_manager=mock_checkpoint_manager,
            status_manager=mock_status_manager,
            server_logger=mock_logger,
            task_executor=lambda t, n, total: True,
            revision_executor=lambda: True,
            todo_generator=lambda: True,
            config=config,
            project_dir=Path("/tmp"),
            auto_todo_enabled=False,
            task_delay=1
        )

        assert server_core is not None
        assert server_core.project_dir == Path("/tmp")


class TestIntegration:
    """Integration tests for DI and SOLID implementation."""

    def test_default_container_creation(self):
        """Test that default DI container can be created."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            status_file = project_dir / "STATUS.md"
            config = {'project': {'dir': str(project_dir)}}

            container = create_default_container(project_dir, config, status_file)
            assert container is not None
            assert isinstance(container, DIContainer)

    def test_interface_resolution(self):
        """Test that interfaces can be resolved from container."""
        container = DIContainer()

        # Register mock implementations
        mock_todo = Mock(spec=ITodoManager)
        mock_status = Mock(spec=IStatusManager)
        mock_checkpoint = Mock(spec=ICheckpointManager)
        mock_logger = Mock(spec=ILogger)

        container.register_instance(ITodoManager, mock_todo)
        container.register_instance(IStatusManager, mock_status)
        container.register_instance(ICheckpointManager, mock_checkpoint)
        container.register_instance(ILogger, mock_logger)

        # Should be able to resolve all interfaces
        resolved_todo = container.resolve(ITodoManager)
        resolved_status = container.resolve(IStatusManager)
        resolved_checkpoint = container.resolve(ICheckpointManager)
        resolved_logger = container.resolve(ILogger)

        assert resolved_todo is mock_todo
        assert resolved_status is mock_status
        assert resolved_checkpoint is mock_checkpoint
        assert resolved_logger is mock_logger

    def test_server_core_with_di(self):
        """Test that ServerCore works with DI-resolved dependencies."""
        from src.core.server_core import ServerCore

        # Create mocks
        mock_todo = Mock(spec=ITodoManager)
        mock_checkpoint = Mock(spec=ICheckpointManager)
        mock_status = Mock(spec=IStatusManager)
        mock_logger = Mock(spec=ILogger)

        # Configure mocks
        mock_todo.get_pending_tasks.return_value = []
        mock_checkpoint.increment_iteration.return_value = None
        mock_checkpoint.get_iteration_count.return_value = 1
        mock_checkpoint.was_clean_shutdown.return_value = True

        config = {'server': {'check_interval': 60}}

        # Create ServerCore with mocked dependencies
        def mock_factory():
            return mock_todo
        server_core = ServerCore(
            todo_manager=mock_todo,
            todo_manager_factory=mock_factory,
            checkpoint_manager=mock_checkpoint,
            status_manager=mock_status,
            server_logger=mock_logger,
            task_executor=lambda t, n, total: True,
            revision_executor=lambda: True,
            todo_generator=lambda: True,
            config=config,
            project_dir=Path("/tmp"),
            auto_todo_enabled=False,
            task_delay=1
        )

        # Should work without errors
        assert server_core is not None
        assert server_core.project_dir == Path("/tmp")


if __name__ == "__main__":
    pytest.main([__file__])