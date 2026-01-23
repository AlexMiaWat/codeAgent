"""
Static tests for ServerCore

This module contains static tests that verify ServerCore
definitions, methods, and class structure without
requiring runtime instantiation.
"""

import inspect
from abc import ABC
from typing import get_type_hints

from src.core.server_core import ServerCore, QualityGateException, TaskExecutor, RevisionExecutor, TodoGenerator


class TestServerCoreStatic:
    """Static tests for ServerCore"""

    def test_server_core_inherits_from_object(self):
        """Test ServerCore is a concrete class"""
        assert not issubclass(ServerCore, ABC)
        assert inspect.isclass(ServerCore)

    def test_server_core_methods_exist(self):
        """Test ServerCore has expected methods"""
        expected_methods = [
            '__init__', 'start', 'stop', 'run_iteration', 'execute_single_task',
            '_is_quality_gates_enabled', '_get_pending_tasks', '_filter_tasks_by_type',
            '_should_generate_todo', '_should_run_revision', '_get_task_delay'
        ]
        for method in expected_methods:
            assert hasattr(ServerCore, method)
            assert callable(getattr(ServerCore, method))

    def test_server_core_init_signature(self):
        """Test ServerCore.__init__ signature"""
        init_sig = inspect.signature(ServerCore.__init__)
        expected_params = [
            'todo_manager', 'checkpoint_manager', 'status_manager', 'server_logger',
            'task_executor', 'revision_executor', 'todo_generator', 'config',
            'project_dir', 'quality_gate_manager', 'task_delay'
        ]
        for param in expected_params:
            assert param in init_sig.parameters

    def test_server_core_start_signature(self):
        """Test start method signature"""
        sig = inspect.signature(ServerCore.start)
        assert len(sig.parameters) == 1  # self only

    def test_server_core_stop_signature(self):
        """Test stop method signature"""
        sig = inspect.signature(ServerCore.stop)
        assert len(sig.parameters) == 1  # self only

    def test_server_core_run_iteration_signature(self):
        """Test run_iteration method signature"""
        sig = inspect.signature(ServerCore.run_iteration)
        assert len(sig.parameters) == 1  # self only

    def test_execute_single_task_signature(self):
        """Test execute_single_task method signature"""
        sig = inspect.signature(ServerCore.execute_single_task)
        expected_params = ['todo_item', 'task_number', 'total_tasks']
        for param in expected_params:
            assert param in sig.parameters


class TestQualityGateExceptionStatic:
    """Static tests for QualityGateException"""

    def test_quality_gate_exception_inherits_from_exception(self):
        """Test QualityGateException inherits from Exception"""
        assert issubclass(QualityGateException, Exception)

    def test_quality_gate_exception_init_signature(self):
        """Test QualityGateException.__init__ signature"""
        init_sig = inspect.signature(QualityGateException.__init__)
        expected_params = ['message', 'gate_result']
        for param in expected_params:
            assert param in init_sig.parameters

    def test_quality_gate_exception_attributes(self):
        """Test QualityGateException has gate_result attribute"""
        assert hasattr(QualityGateException, 'gate_result')


class TestProtocolDefinitions:
    """Static tests for protocol definitions"""

    def test_task_executor_is_protocol(self):
        """Test TaskExecutor is a Protocol"""
        from typing import Protocol
        assert issubclass(TaskExecutor, Protocol)

    def test_revision_executor_is_protocol(self):
        """Test RevisionExecutor is a Protocol"""
        from typing import Protocol
        assert issubclass(RevisionExecutor, Protocol)

    def test_todo_generator_is_protocol(self):
        """Test TodoGenerator is a Protocol"""
        from typing import Protocol
        assert issubclass(TodoGenerator, Protocol)

    def test_task_executor_methods(self):
        """Test TaskExecutor protocol has expected methods"""
        methods = [name for name, _ in inspect.getmembers(
            TaskExecutor, predicate=inspect.isfunction) if not name.startswith('_')]

        expected_methods = ['__call__']
        for method in expected_methods:
            assert method in methods, f"TaskExecutor missing {method}"

    def test_revision_executor_methods(self):
        """Test RevisionExecutor protocol has expected methods"""
        methods = [name for name, _ in inspect.getmembers(
            RevisionExecutor, predicate=inspect.isfunction) if not name.startswith('_')]

        expected_methods = ['__call__']
        for method in expected_methods:
            assert method in methods, f"RevisionExecutor missing {method}"

    def test_todo_generator_methods(self):
        """Test TodoGenerator protocol has expected methods"""
        methods = [name for name, _ in inspect.getmembers(
            TodoGenerator, predicate=inspect.isfunction) if not name.startswith('_')]

        expected_methods = ['__call__']
        for method in expected_methods:
            assert method in methods, f"TodoGenerator missing {method}"


class TestMethodSignatures:
    """Test method signatures"""

    def test_private_method_signatures(self):
        """Test private method signatures"""
        private_methods = [
            '_is_quality_gates_enabled', '_get_pending_tasks', '_filter_tasks_by_type',
            '_should_generate_todo', '_should_run_revision', '_get_task_delay'
        ]

        for method_name in private_methods:
            method = getattr(ServerCore, method_name)
            sig = inspect.signature(method)
            # Private methods should have self as first parameter
            assert 'self' in sig.parameters


class TestTypeHints:
    """Test type hints for ServerCore methods"""

    def test_server_core_init_hints(self):
        """Test ServerCore.__init__ has type hints"""
        hints = get_type_hints(ServerCore.__init__)
        assert hints, "ServerCore.__init__ should have type hints"

    def test_server_core_public_method_hints(self):
        """Test ServerCore public methods have type hints"""
        public_methods = ['start', 'stop', 'run_iteration', 'execute_single_task']

        for method_name in public_methods:
            method = getattr(ServerCore, method_name)
            hints = get_type_hints(method)
            assert hints, f"{method_name} should have type hints"

    def test_protocol_method_hints(self):
        """Test protocol methods have type hints"""
        protocols = [TaskExecutor, RevisionExecutor, TodoGenerator]

        for protocol in protocols:
            call_method = getattr(protocol, '__call__')
            hints = get_type_hints(call_method)
            assert hints, f"{protocol.__name__}.__call__ should have type hints"


class TestClassHierarchy:
    """Test class hierarchy"""

    def test_server_core_no_multiple_inheritance(self):
        """Test ServerCore doesn't use problematic multiple inheritance"""
        mro = ServerCore.__mro__
        # Should only inherit from object
        assert len(mro) == 2  # ServerCore, object
        assert mro[0] == ServerCore
        assert mro[1] == object

    def test_exception_hierarchy(self):
        """Test exception hierarchy"""
        mro = QualityGateException.__mro__
        # Should inherit from Exception and BaseException
        assert Exception in mro
        assert BaseException in mro[-2]  # Second to last should be BaseException
        assert object in mro[-1]  # Last should be object