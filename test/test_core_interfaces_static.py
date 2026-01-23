"""
Static tests for core interfaces

This module contains static tests that verify core interface
definitions, abstract methods, and inheritance without
requiring runtime instantiation.
"""

import inspect
from abc import ABC
from typing import get_type_hints

from src.core.interfaces import (
    IAgent, IServer, ITaskManager, ITodoManager,
    IStatusManager, ICheckpointManager, ILogger, IManager
)


class TestCoreInterfacesStatic:
    """Static tests for core interfaces"""

    def test_i_agent_is_abstract(self):
        """Test IAgent is abstract base class"""
        assert issubclass(IAgent, ABC)

    def test_i_server_is_abstract(self):
        """Test IServer is abstract base class"""
        assert issubclass(IServer, ABC)

    def test_i_task_manager_is_abstract(self):
        """Test ITaskManager is abstract base class"""
        assert issubclass(ITaskManager, ABC)

    def test_i_todo_manager_is_abstract(self):
        """Test ITodoManager is abstract base class"""
        assert issubclass(ITodoManager, ABC)

    def test_i_status_manager_is_abstract(self):
        """Test IStatusManager is abstract base class"""
        assert issubclass(IStatusManager, ABC)

    def test_i_checkpoint_manager_is_abstract(self):
        """Test ICheckpointManager is abstract base class"""
        assert issubclass(ICheckpointManager, ABC)

    def test_i_logger_is_abstract(self):
        """Test ILogger is abstract base class"""
        assert issubclass(ILogger, ABC)

    def test_i_manager_is_abstract(self):
        """Test IManager is abstract base class"""
        assert issubclass(IManager, ABC)


class TestIAgentMethods:
    """Test IAgent interface methods"""

    def test_i_agent_methods_exist(self):
        """Test IAgent has expected abstract methods"""
        methods = [name for name, _ in inspect.getmembers(
            IAgent, predicate=inspect.isfunction) if not name.startswith('_')]

        expected_methods = ['execute_task', 'configure', 'get_status']
        for method in expected_methods:
            assert method in methods, f"IAgent missing {method}"

    def test_i_agent_execute_task_signature(self):
        """Test execute_task method signature"""
        sig = inspect.signature(IAgent.execute_task)
        expected_params = ['todo_item', 'task_number', 'total_tasks']
        for param in expected_params:
            assert param in sig.parameters

    def test_i_agent_configure_signature(self):
        """Test configure method signature"""
        sig = inspect.signature(IAgent.configure)
        expected_params = ['config']
        for param in expected_params:
            assert param in sig.parameters

    def test_i_agent_get_status_signature(self):
        """Test get_status method signature"""
        sig = inspect.signature(IAgent.get_status)
        assert len(sig.parameters) == 1  # self only


class TestIServerMethods:
    """Test IServer interface methods"""

    def test_i_server_methods_exist(self):
        """Test IServer has expected abstract methods"""
        methods = [name for name, _ in inspect.getmembers(
            IServer, predicate=inspect.isfunction) if not name.startswith('_')]

        expected_methods = ['start', 'stop', 'get_status', 'configure']
        for method in expected_methods:
            assert method in methods, f"IServer missing {method}"

    def test_i_server_start_signature(self):
        """Test start method signature"""
        sig = inspect.signature(IServer.start)
        assert len(sig.parameters) == 1  # self only

    def test_i_server_stop_signature(self):
        """Test stop method signature"""
        sig = inspect.signature(IServer.stop)
        assert len(sig.parameters) == 1  # self only

    def test_i_server_get_status_signature(self):
        """Test get_status method signature"""
        sig = inspect.signature(IServer.get_status)
        assert len(sig.parameters) == 1  # self only

    def test_i_server_configure_signature(self):
        """Test configure method signature"""
        sig = inspect.signature(IServer.configure)
        expected_params = ['config']
        for param in expected_params:
            assert param in sig.parameters


class TestITaskManagerMethods:
    """Test ITaskManager interface methods"""

    def test_i_task_manager_methods_exist(self):
        """Test ITaskManager has expected abstract methods"""
        methods = [name for name, _ in inspect.getmembers(
            ITaskManager, predicate=inspect.isfunction) if not name.startswith('_')]

        expected_methods = ['execute_task', 'get_status', 'configure']
        for method in expected_methods:
            assert method in methods, f"ITaskManager missing {method}"

    def test_i_task_manager_execute_task_signature(self):
        """Test execute_task method signature"""
        sig = inspect.signature(ITaskManager.execute_task)
        expected_params = ['todo_item', 'task_number', 'total_tasks']
        for param in expected_params:
            assert param in sig.parameters


class TestITodoManagerMethods:
    """Test ITodoManager interface methods"""

    def test_i_todo_manager_methods_exist(self):
        """Test ITodoManager has expected abstract methods"""
        methods = [name for name, _ in inspect.getmembers(
            ITodoManager, predicate=inspect.isfunction) if not name.startswith('_')]

        expected_methods = ['get_pending_tasks', 'mark_completed', 'mark_failed', 'add_task', 'get_all_tasks']
        for method in expected_methods:
            assert method in methods, f"ITodoManager missing {method}"

    def test_i_todo_manager_get_pending_tasks_signature(self):
        """Test get_pending_tasks method signature"""
        sig = inspect.signature(ITodoManager.get_pending_tasks)
        assert len(sig.parameters) == 1  # self only

    def test_i_todo_manager_mark_completed_signature(self):
        """Test mark_completed method signature"""
        sig = inspect.signature(ITodoManager.mark_completed)
        expected_params = ['task_id']
        for param in expected_params:
            assert param in sig.parameters

    def test_i_todo_manager_add_task_signature(self):
        """Test add_task method signature"""
        sig = inspect.signature(ITodoManager.add_task)
        expected_params = ['todo_item']
        for param in expected_params:
            assert param in sig.parameters


class TestIStatusManagerMethods:
    """Test IStatusManager interface methods"""

    def test_i_status_manager_methods_exist(self):
        """Test IStatusManager has expected abstract methods"""
        methods = [name for name, _ in inspect.getmembers(
            IStatusManager, predicate=inspect.isfunction) if not name.startswith('_')]

        expected_methods = ['update_status', 'get_current_status', 'get_task_history', 'configure']
        for method in expected_methods:
            assert method in methods, f"IStatusManager missing {method}"

    def test_i_status_manager_update_status_signature(self):
        """Test update_status method signature"""
        sig = inspect.signature(IStatusManager.update_status)
        expected_params = ['task_id', 'status', 'message']
        for param in expected_params:
            assert param in sig.parameters


class TestICheckpointManagerMethods:
    """Test ICheckpointManager interface methods"""

    def test_i_checkpoint_manager_methods_exist(self):
        """Test ICheckpointManager has expected abstract methods"""
        methods = [name for name, _ in inspect.getmembers(
            ICheckpointManager, predicate=inspect.isfunction) if not name.startswith('_')]

        expected_methods = ['save_checkpoint', 'load_checkpoint', 'list_checkpoints', 'configure']
        for method in expected_methods:
            assert method in methods, f"ICheckpointManager missing {method}"

    def test_i_checkpoint_manager_save_checkpoint_signature(self):
        """Test save_checkpoint method signature"""
        sig = inspect.signature(ICheckpointManager.save_checkpoint)
        expected_params = ['task_id', 'data']
        for param in expected_params:
            assert param in sig.parameters


class TestILoggerMethods:
    """Test ILogger interface methods"""

    def test_i_logger_methods_exist(self):
        """Test ILogger has expected abstract methods"""
        methods = [name for name, _ in inspect.getmembers(
            ILogger, predicate=inspect.isfunction) if not name.startswith('_')]

        expected_methods = ['info', 'warning', 'error', 'debug', 'configure']
        for method in expected_methods:
            assert method in methods, f"ILogger missing {method}"

    def test_i_logger_info_signature(self):
        """Test info method signature"""
        sig = inspect.signature(ILogger.info)
        expected_params = ['message', 'extra']
        for param in expected_params:
            assert param in sig.parameters


class TestIManagerMethods:
    """Test IManager interface methods"""

    def test_i_manager_methods_exist(self):
        """Test IManager has expected abstract methods"""
        methods = [name for name, _ in inspect.getmembers(
            IManager, predicate=inspect.isfunction) if not name.startswith('_')]

        expected_methods = ['configure', 'get_status']
        for method in expected_methods:
            assert method in methods, f"IManager missing {method}"


class TestTypeHints:
    """Test type hints for interface methods"""

    def test_i_agent_method_hints(self):
        """Test IAgent methods have type hints"""
        methods_to_check = ['execute_task', 'configure', 'get_status']
        for method_name in methods_to_check:
            method = getattr(IAgent, method_name)
            hints = get_type_hints(method)
            assert hints, f"{method_name} should have type hints"

    def test_i_server_method_hints(self):
        """Test IServer methods have type hints"""
        methods_to_check = ['start', 'stop', 'get_status', 'configure']
        for method_name in methods_to_check:
            method = getattr(IServer, method_name)
            hints = get_type_hints(method)
            assert hints, f"{method_name} should have type hints"

    def test_i_task_manager_method_hints(self):
        """Test ITaskManager methods have type hints"""
        methods_to_check = ['execute_task', 'get_status', 'configure']
        for method_name in methods_to_check:
            method = getattr(ITaskManager, method_name)
            hints = get_type_hints(method)
            assert hints, f"{method_name} should have type hints"


class TestClassHierarchy:
    """Test class hierarchy"""

    def test_no_multiple_inheritance_conflicts(self):
        """Test that interface hierarchies don't have conflicts"""
        interfaces = [IAgent, IServer, ITaskManager, ITodoManager,
                     IStatusManager, ICheckpointManager, ILogger, IManager]

        for interface in interfaces:
            mro = interface.__mro__
            # Should have ABC and object in MRO
            assert ABC in mro, f"{interface.__name__} should inherit from ABC"
            assert object in mro[-1], f"{interface.__name__} MRO should end with object"