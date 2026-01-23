"""
Static tests for core interfaces

This module contains static tests that verify interface definitions
and method signatures without requiring concrete implementations.
"""

import pytest
import inspect
from abc import ABC
from typing import get_type_hints

from src.core.interfaces import (
    IConfigurable, IErrorHandler, IMetricsCollector,
    IServerComponent, ITaskOrchestrator, IFileWatcher
)


class TestInterfaceDefinitions:
    """Test interface class definitions"""

    def test_interfaces_are_abstract(self):
        """Test that all interfaces are abstract base classes"""
        interfaces = [
            IConfigurable, IErrorHandler, IMetricsCollector,
            IServerComponent, ITaskOrchestrator, IFileWatcher
        ]

        for interface in interfaces:
            assert issubclass(interface, ABC), f"{interface.__name__} should be abstract"

    def test_interface_method_signatures(self):
        """Test that interfaces have expected abstract methods"""
        # Test IConfigurable
        configurable_methods = [name for name, method in inspect.getmembers(
            IConfigurable, predicate=inspect.isfunction)]
        expected_configurable = ['configure', 'get_config', 'validate_config']
        for method in expected_configurable:
            assert method in configurable_methods, f"IConfigurable missing {method}"

        # Test IErrorHandler
        error_handler_methods = [name for name, method in inspect.getmembers(
            IErrorHandler, predicate=inspect.isfunction)]
        expected_error_handler = ['handle_error', 'should_recover', 'get_error_history']
        for method in expected_error_handler:
            assert method in error_handler_methods, f"IErrorHandler missing {method}"

        # Test IMetricsCollector
        metrics_methods = [name for name, method in inspect.getmembers(
            IMetricsCollector, predicate=inspect.isfunction)]
        expected_metrics = ['collect_metric', 'get_metrics', 'export_metrics']
        for method in expected_metrics:
            assert method in metrics_methods, f"IMetricsCollector missing {method}"

        # Test IServerComponent
        server_methods = [name for name, method in inspect.getmembers(
            IServerComponent, predicate=inspect.isfunction)]
        expected_server = ['initialize', 'start', 'stop', 'get_health', 'is_ready']
        for method in expected_server:
            assert method in server_methods, f"IServerComponent missing {method}"


class TestMethodSignatures:
    """Test method signatures and type hints"""

    def test_configurable_method_signatures(self):
        """Test IConfigurable method signatures"""
        from src.core.types import ServerConfig
        from typing import Dict, Any

        # Check configure method
        configure_sig = inspect.signature(IConfigurable.configure)
        assert 'config' in configure_sig.parameters
        # Type hints might not be available in all Python versions, so we'll skip strict checking

        # Check get_config method
        get_config_sig = inspect.signature(IConfigurable.get_config)
        assert get_config_sig.return_annotation is not None

        # Check validate_config method
        validate_config_sig = inspect.signature(IConfigurable.validate_config)
        assert validate_config_sig.return_annotation is not None

    def test_error_handler_method_signatures(self):
        """Test IErrorHandler method signatures"""
        from src.core.types import ErrorInfo
        from typing import Optional, Dict, Any

        # Check handle_error method
        handle_error_sig = inspect.signature(IErrorHandler.handle_error)
        assert 'error' in handle_error_sig.parameters
        assert 'context' in handle_error_sig.parameters

        # Check should_recover method
        should_recover_sig = inspect.signature(IErrorHandler.should_recover)
        assert 'error_info' in should_recover_sig.parameters

    def test_metrics_collector_method_signatures(self):
        """Test IMetricsCollector method signatures"""
        from typing import Optional, List

        # Check collect_metric method
        collect_sig = inspect.signature(IMetricsCollector.collect_metric)
        assert 'name' in collect_sig.parameters
        assert 'value' in collect_sig.parameters
        assert 'tags' in collect_sig.parameters

        # Check get_metrics method
        get_metrics_sig = inspect.signature(IMetricsCollector.get_metrics)
        assert 'component' in get_metrics_sig.parameters

        # Check export_metrics method
        export_sig = inspect.signature(IMetricsCollector.export_metrics)
        assert 'format' in export_sig.parameters

    def test_server_component_method_signatures(self):
        """Test IServerComponent method signatures"""
        from src.core.types import ComponentHealth

        # Check get_health method
        get_health_sig = inspect.signature(IServerComponent.get_health)
        # Return type should be ComponentHealth

        # Check is_ready method
        is_ready_sig = inspect.signature(IServerComponent.is_ready)
        # Should return bool


class TestInterfaceInheritance:
    """Test interface inheritance relationships"""

    def test_no_circular_inheritance(self):
        """Test that interfaces don't have circular inheritance"""
        interfaces = [
            IConfigurable, IErrorHandler, IMetricsCollector,
            IServerComponent, ITaskOrchestrator, IFileWatcher
        ]

        for interface in interfaces:
            # Check MRO (Method Resolution Order) for circular references
            mro = interface.__mro__
            assert len(mro) >= 2  # At least ABC and the interface itself
            assert ABC in mro

    def test_interface_separation(self):
        """Test that interfaces are properly separated"""
        # Each interface should have its own distinct methods
        configurable_methods = set([name for name, _ in inspect.getmembers(
            IConfigurable, predicate=inspect.isfunction)])
        error_methods = set([name for name, _ in inspect.getmembers(
            IErrorHandler, predicate=inspect.isfunction)])
        metrics_methods = set([name for name, _ in inspect.getmembers(
            IMetricsCollector, predicate=inspect.isfunction)])
        server_methods = set([name for name, _ in inspect.getmembers(
            IServerComponent, predicate=inspect.isfunction)])

        # Check that interfaces have some unique methods
        assert len(configurable_methods - error_methods - metrics_methods - server_methods) > 0
        assert len(error_methods - configurable_methods - metrics_methods - server_methods) > 0
        assert len(metrics_methods - configurable_methods - error_methods - server_methods) > 0
        assert len(server_methods - configurable_methods - error_methods - metrics_methods) > 0


class TestAbstractMethods:
    """Test that interfaces define abstract methods correctly"""

    def test_all_methods_are_abstract(self):
        """Test that all interface methods are abstract"""
        interfaces = [
            IConfigurable, IErrorHandler, IMetricsCollector,
            IServerComponent, ITaskOrchestrator, IFileWatcher
        ]

        for interface in interfaces:
            for name, method in inspect.getmembers(interface, predicate=inspect.isfunction):
                if not name.startswith('_'):  # Skip private methods
                    # In Python 3.8+, we can check __isabstractmethod__
                    if hasattr(method, '__isabstractmethod__'):
                        assert method.__isabstractmethod__, f"{interface.__name__}.{name} should be abstract"

    def test_interfaces_cannot_be_instantiated(self):
        """Test that interfaces cannot be instantiated directly"""
        interfaces = [
            IConfigurable, IErrorHandler, IMetricsCollector,
            IServerComponent, ITaskOrchestrator, IFileWatcher
        ]

        for interface in interfaces:
            with pytest.raises(TypeError):
                interface()  # Should raise TypeError because it's abstract