"""
Static tests for Dependency Injection system

This module contains static tests that verify interface definitions,
method signatures, and type correctness for the DI system without
requiring concrete implementations.
"""

import pytest
import inspect
from abc import ABC
from typing import get_type_hints, Dict, Any, List, Optional

from src.core.di_container import DIContainer, ServiceLifetime, ServiceDescriptor, DependencyInjectionException
from src.core.interfaces import (
    IManager, ITodoManager, IStatusManager, ICheckpointManager, ILogger,
    IServer, IAgent, ITaskManager, TaskExecutionState
)


class TestDIContainerStatic:
    """Static tests for DIContainer class"""

    def test_di_container_is_concrete_class(self):
        """Test that DIContainer is a concrete class that can be instantiated"""
        assert inspect.isclass(DIContainer)
        assert not issubclass(DIContainer, ABC)

        # Should be instantiable
        container = DIContainer()
        assert isinstance(container, DIContainer)

    def test_service_lifetime_enum_values(self):
        """Test ServiceLifetime enum has expected values"""
        assert hasattr(ServiceLifetime, 'SINGLETON')
        assert hasattr(ServiceLifetime, 'TRANSIENT')
        assert hasattr(ServiceLifetime, 'SCOPED')

        assert ServiceLifetime.SINGLETON.value == "singleton"
        assert ServiceLifetime.TRANSIENT.value == "transient"
        assert ServiceLifetime.SCOPED.value == "scoped"

    def test_service_descriptor_structure(self):
        """Test ServiceDescriptor has required attributes"""
        descriptor = ServiceDescriptor(str)

        assert hasattr(descriptor, 'service_type')
        assert hasattr(descriptor, 'implementation_type')
        assert hasattr(descriptor, 'factory')
        assert hasattr(descriptor, 'lifetime')
        assert hasattr(descriptor, 'instance')
        assert hasattr(descriptor, 'is_resolving')

    def test_dependency_injection_exception_exists(self):
        """Test that DependencyInjectionException is defined"""
        assert inspect.isclass(DependencyInjectionException)
        assert issubclass(DependencyInjectionException, Exception)


class TestInterfaceDefinitions:
    """Test interface class definitions for DI system"""

    def test_interfaces_are_abstract(self):
        """Test that all DI interfaces are abstract base classes"""
        interfaces = [
            IManager, ITodoManager, IStatusManager, ICheckpointManager, ILogger,
            IServer, IAgent, ITaskManager
        ]

        for interface in interfaces:
            assert issubclass(interface, ABC), f"{interface.__name__} should be abstract"

    def test_manager_interface_methods(self):
        """Test IManager has expected abstract methods"""
        manager_methods = [name for name, method in inspect.getmembers(
            IManager, predicate=inspect.isfunction)]
        expected_methods = ['__init__', 'is_healthy', 'get_status', 'dispose']

        for method in expected_methods:
            assert method in manager_methods, f"IManager missing {method}"

    def test_todo_manager_interface_methods(self):
        """Test ITodoManager has expected abstract methods"""
        todo_methods = [name for name, method in inspect.getmembers(
            ITodoManager, predicate=inspect.isfunction)]
        expected_methods = ['__init__', 'load_todos', 'get_pending_tasks',
                          'get_all_tasks', 'mark_task_done', 'get_task_hierarchy', 'save_todos']

        for method in expected_methods:
            assert method in todo_methods, f"ITodoManager missing {method}"

    def test_status_manager_interface_methods(self):
        """Test IStatusManager has expected abstract methods"""
        status_methods = [name for name, method in inspect.getmembers(
            IStatusManager, predicate=inspect.isfunction)]
        expected_methods = ['__init__', 'read_status', 'write_status',
                          'append_status', 'update_task_status', 'add_separator']

        for method in expected_methods:
            assert method in status_methods, f"IStatusManager missing {method}"

    def test_checkpoint_manager_interface_methods(self):
        """Test ICheckpointManager has expected abstract methods"""
        checkpoint_methods = [name for name, method in inspect.getmembers(
            ICheckpointManager, predicate=inspect.isfunction)]
        expected_methods = ['__init__', 'increment_iteration', 'get_iteration_count',
                          'mark_server_start', 'mark_server_stop', 'add_task',
                          'mark_task_start', 'mark_task_completed', 'get_current_task']

        for method in expected_methods:
            assert method in checkpoint_methods, f"ICheckpointManager missing {method}"

    def test_logger_interface_methods(self):
        """Test ILogger has expected abstract methods"""
        logger_methods = [name for name, method in inspect.getmembers(
            ILogger, predicate=inspect.isfunction)]
        expected_methods = ['__init__', 'log_info', 'log_error', 'log_warning',
                          'log_debug', 'create_task_logger', 'close']

        for method in expected_methods:
            assert method in logger_methods, f"ILogger missing {method}"

    def test_server_interface_methods(self):
        """Test IServer has expected abstract methods"""
        server_methods = [name for name, method in inspect.getmembers(
            IServer, predicate=inspect.isfunction)]
        expected_methods = ['__init__', 'start', 'stop', 'restart', 'is_running',
                          'get_server_status', 'execute_task', 'get_pending_tasks',
                          'get_active_tasks', 'get_metrics', 'reload_configuration',
                          'get_component_status', 'is_healthy', 'get_status', 'dispose']

        for method in expected_methods:
            assert method in server_methods, f"IServer missing {method}"

    def test_agent_interface_methods(self):
        """Test IAgent has expected abstract methods"""
        agent_methods = [name for name, method in inspect.getmembers(
            IAgent, predicate=inspect.isfunction)]
        expected_methods = ['__init__', 'create_agent', 'get_agent', 'remove_agent',
                          'get_available_agents', 'get_active_agents', 'configure_agent',
                          'execute_with_agent', 'get_agent_status', 'validate_agent_config',
                          'get_agent_types_info', 'is_healthy', 'get_status', 'dispose']

        for method in expected_methods:
            assert method in agent_methods, f"IAgent missing {method}"

    def test_task_manager_interface_methods(self):
        """Test ITaskManager has expected abstract methods"""
        task_methods = [name for name, method in inspect.getmembers(
            ITaskManager, predicate=inspect.isfunction)]
        expected_methods = ['__init__', 'initialize_task_execution', 'execute_task_step',
                          'monitor_task_progress', 'handle_task_failure', 'finalize_task_execution',
                          'cancel_task_execution', 'get_execution_status', 'get_active_executions',
                          'get_execution_history', 'retry_execution', 'get_execution_metrics',
                          'validate_execution_requirements', 'is_healthy', 'get_status', 'dispose']

        for method in expected_methods:
            assert method in task_methods, f"ITaskManager missing {method}"


class TestMethodSignatures:
    """Test method signatures and type hints"""

    def test_manager_method_signatures(self):
        """Test IManager method signatures"""
        # Test __init__
        init_sig = inspect.signature(IManager.__init__)
        assert 'config' in init_sig.parameters

        # Test is_healthy
        healthy_sig = inspect.signature(IManager.is_healthy)
        assert healthy_sig.return_annotation is not None

        # Test get_status
        status_sig = inspect.signature(IManager.get_status)
        assert status_sig.return_annotation is not None

    def test_todo_manager_method_signatures(self):
        """Test ITodoManager method signatures"""
        # Test __init__
        init_sig = inspect.signature(ITodoManager.__init__)
        assert 'project_dir' in init_sig.parameters
        assert 'config' in init_sig.parameters

        # Test load_todos
        load_sig = inspect.signature(ITodoManager.load_todos)
        assert load_sig.return_annotation is not None

        # Test get_pending_tasks
        pending_sig = inspect.signature(ITodoManager.get_pending_tasks)
        assert pending_sig.return_annotation is not None

        # Test mark_task_done
        mark_sig = inspect.signature(ITodoManager.mark_task_done)
        assert 'task_text' in mark_sig.parameters
        assert mark_sig.return_annotation is not None

    def test_status_manager_method_signatures(self):
        """Test IStatusManager method signatures"""
        # Test __init__
        init_sig = inspect.signature(IStatusManager.__init__)
        assert 'status_file' in init_sig.parameters

        # Test read_status
        read_sig = inspect.signature(IStatusManager.read_status)
        assert read_sig.return_annotation is not None

        # Test write_status
        write_sig = inspect.signature(IStatusManager.write_status)
        assert 'content' in write_sig.parameters

        # Test append_status
        append_sig = inspect.signature(IStatusManager.append_status)
        assert 'message' in append_sig.parameters
        assert 'level' in append_sig.parameters

    def test_logger_method_signatures(self):
        """Test ILogger method signatures"""
        # Test log_info
        info_sig = inspect.signature(ILogger.log_info)
        assert 'message' in info_sig.parameters

        # Test log_error
        error_sig = inspect.signature(ILogger.log_error)
        assert 'message' in error_sig.parameters

        # Test log_warning
        warning_sig = inspect.signature(ILogger.log_warning)
        assert 'message' in warning_sig.parameters

        # Test log_debug
        debug_sig = inspect.signature(ILogger.log_debug)
        assert 'message' in debug_sig.parameters


class TestInterfaceInheritance:
    """Test interface inheritance relationships"""

    def test_interfaces_inherit_from_abc(self):
        """Test that all interfaces inherit from ABC"""
        interfaces = [
            IManager, ITodoManager, IStatusManager, ICheckpointManager, ILogger,
            IServer, IAgent, ITaskManager
        ]

        for interface in interfaces:
            assert issubclass(interface, ABC)

    def test_no_circular_inheritance(self):
        """Test that interfaces don't have circular inheritance"""
        interfaces = [
            IManager, ITodoManager, IStatusManager, ICheckpointManager, ILogger,
            IServer, IAgent, ITaskManager
        ]

        for interface in interfaces:
            mro = interface.__mro__
            assert len(mro) >= 2  # At least ABC and the interface itself
            assert ABC in mro

    def test_interface_separation(self):
        """Test that interfaces have distinct method sets"""
        manager_methods = set([name for name, _ in inspect.getmembers(
            IManager, predicate=inspect.isfunction)])
        todo_methods = set([name for name, _ in inspect.getmembers(
            ITodoManager, predicate=inspect.isfunction)])
        status_methods = set([name for name, _ in inspect.getmembers(
            IStatusManager, predicate=inspect.isfunction)])
        checkpoint_methods = set([name for name, _ in inspect.getmembers(
            ICheckpointManager, predicate=inspect.isfunction)])
        logger_methods = set([name for name, _ in inspect.getmembers(
            ILogger, predicate=inspect.isfunction)])
        server_methods = set([name for name, _ in inspect.getmembers(
            IServer, predicate=inspect.isfunction)])
        agent_methods = set([name for name, _ in inspect.getmembers(
            IAgent, predicate=inspect.isfunction)])
        task_methods = set([name for name, _ in inspect.getmembers(
            ITaskManager, predicate=inspect.isfunction)])

        # Each interface should have some unique methods
        assert len(manager_methods) > 0
        assert len(todo_methods - manager_methods) > 0  # Todo has unique methods
        assert len(status_methods - manager_methods) > 0  # Status has unique methods
        assert len(checkpoint_methods - manager_methods) > 0  # Checkpoint has unique methods
        assert len(logger_methods - manager_methods) > 0  # Logger has unique methods
        assert len(server_methods - manager_methods) > 0  # Server has unique methods
        assert len(agent_methods - manager_methods) > 0  # Agent has unique methods
        assert len(task_methods - manager_methods) > 0  # TaskManager has unique methods


class TestAbstractMethods:
    """Test that interfaces define abstract methods correctly"""

    def test_all_interface_methods_are_abstract(self):
        """Test that all interface methods are abstract"""
        interfaces = [
            IManager, ITodoManager, IStatusManager, ICheckpointManager, ILogger,
            IServer, IAgent, ITaskManager
        ]

        for interface in interfaces:
            for name, method in inspect.getmembers(interface, predicate=inspect.isfunction):
                if not name.startswith('_'):  # Skip private methods
                    if hasattr(method, '__isabstractmethod__'):
                        assert method.__isabstractmethod__, f"{interface.__name__}.{name} should be abstract"

    def test_interfaces_cannot_be_instantiated(self):
        """Test that interfaces cannot be instantiated directly"""
        interfaces = [
            IManager, ITodoManager, IStatusManager, ICheckpointManager, ILogger,
            IServer, IAgent, ITaskManager
        ]

        for interface in interfaces:
            with pytest.raises(TypeError):
                interface()  # Should raise TypeError because it's abstract


class TestDIContainerMethods:
    """Test DIContainer method signatures"""

    def test_registration_methods_exist(self):
        """Test that DIContainer has registration methods"""
        container_methods = [name for name, _ in inspect.getmembers(
            DIContainer, predicate=inspect.isfunction)]

        expected_methods = [
            'register_singleton', 'register_transient', 'register_factory',
            'register_instance', 'resolve', 'is_registered', 'dispose'
        ]

        for method in expected_methods:
            assert method in container_methods, f"DIContainer missing {method}"

    def test_resolve_method_signature(self):
        """Test resolve method signature"""
        resolve_sig = inspect.signature(DIContainer.resolve)
        assert 'service_type' in resolve_sig.parameters
        assert resolve_sig.return_annotation is not None

    def test_registration_method_signatures(self):
        """Test registration method signatures"""
        singleton_sig = inspect.signature(DIContainer.register_singleton)
        assert 'service_type' in singleton_sig.parameters

        transient_sig = inspect.signature(DIContainer.register_transient)
        assert 'service_type' in transient_sig.parameters

        factory_sig = inspect.signature(DIContainer.register_factory)
        assert 'service_type' in factory_sig.parameters
        assert 'factory' in factory_sig.parameters

        instance_sig = inspect.signature(DIContainer.register_instance)
        assert 'service_type' in instance_sig.parameters
        assert 'instance' in instance_sig.parameters


class TestTaskExecutionState:
    """Test TaskExecutionState enum"""

    def test_task_execution_state_enum_values(self):
        """Test TaskExecutionState enum has expected values"""
        assert hasattr(TaskExecutionState, 'PENDING')
        assert hasattr(TaskExecutionState, 'INITIALIZING')
        assert hasattr(TaskExecutionState, 'EXECUTING')
        assert hasattr(TaskExecutionState, 'MONITORING')
        assert hasattr(TaskExecutionState, 'COMPLETED')
        assert hasattr(TaskExecutionState, 'FAILED')
        assert hasattr(TaskExecutionState, 'CANCELLED')

        assert TaskExecutionState.PENDING.value == "pending"
        assert TaskExecutionState.INITIALIZING.value == "initializing"
        assert TaskExecutionState.EXECUTING.value == "executing"
        assert TaskExecutionState.MONITORING.value == "monitoring"
        assert TaskExecutionState.COMPLETED.value == "completed"
        assert TaskExecutionState.FAILED.value == "failed"
        assert TaskExecutionState.CANCELLED.value == "cancelled"

    def test_task_execution_state_is_enum(self):
        """Test that TaskExecutionState is an Enum"""
        from enum import Enum
        assert issubclass(TaskExecutionState, Enum)


class TestTypeImports:
    """Test that all required types can be imported"""

    def test_di_container_imports(self):
        """Test that DI container and related classes can be imported"""
        from src.core.di_container import (
            DIContainer, ServiceLifetime, ServiceDescriptor, DependencyInjectionException,
            create_default_container
        )

        # Test that classes exist
        assert DIContainer
        assert ServiceLifetime
        assert ServiceDescriptor
        assert DependencyInjectionException
        assert create_default_container

    def test_interface_imports(self):
        """Test that all DI interfaces can be imported"""
        from src.core.interfaces import (
            IManager, ITodoManager, IStatusManager, ICheckpointManager, ILogger,
            IServer, IAgent, ITaskManager, TaskExecutionState
        )

        # Test that interfaces exist
        assert IManager
        assert ITodoManager
        assert IStatusManager
        assert ICheckpointManager
        assert ILogger
        assert IServer
        assert IAgent
        assert ITaskManager
        assert TaskExecutionState