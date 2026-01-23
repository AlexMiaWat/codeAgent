"""
Static tests for abstract base classes

This module contains static tests that verify abstract base class
definitions, inheritance, and method implementations without
requiring runtime instantiation.
"""

import inspect
from abc import ABC
from typing import get_type_hints

from src.core.abstract_base import (
    BaseComponent, ConfigurableComponent, MetricsEnabledComponent
)
from src.core.interfaces import (
    IServerComponent, IConfigurable, IMetricsCollector
)


class TestClassDefinitions:
    """Test class definitions and inheritance"""

    def test_base_component_inheritance(self):
        """Test BaseComponent inherits from IServerComponent"""
        assert issubclass(BaseComponent, IServerComponent)
        assert issubclass(BaseComponent, ABC)

    def test_configurable_component_inheritance(self):
        """Test ConfigurableComponent inherits from BaseComponent and IConfigurable"""
        assert issubclass(ConfigurableComponent, BaseComponent)
        assert issubclass(ConfigurableComponent, IConfigurable)
        assert issubclass(ConfigurableComponent, IServerComponent)

    def test_metrics_component_inheritance(self):
        """Test MetricsEnabledComponent inherits from BaseComponent and IMetricsCollector"""
        assert issubclass(MetricsEnabledComponent, BaseComponent)
        assert issubclass(MetricsEnabledComponent, IMetricsCollector)
        assert issubclass(MetricsEnabledComponent, IServerComponent)

    def test_abstract_methods_implemented(self):
        """Test that abstract base classes implement required interface methods"""
        # Check BaseComponent implements IServerComponent methods
        server_methods = [name for name, _ in inspect.getmembers(
            IServerComponent, predicate=inspect.isfunction) if not name.startswith('_')]

        for method in server_methods:
            assert hasattr(BaseComponent, method), f"BaseComponent missing {method}"

        # Check ConfigurableComponent implements IConfigurable methods
        configurable_methods = [name for name, _ in inspect.getmembers(
            IConfigurable, predicate=inspect.isfunction) if not name.startswith('_')]

        for method in configurable_methods:
            assert hasattr(ConfigurableComponent, method), f"ConfigurableComponent missing {method}"

        # Check MetricsEnabledComponent implements IMetricsCollector methods
        metrics_methods = [name for name, _ in inspect.getmembers(
            IMetricsCollector, predicate=inspect.isfunction) if not name.startswith('_')]

        for method in metrics_methods:
            assert hasattr(MetricsEnabledComponent, method), f"MetricsEnabledComponent missing {method}"


class TestMethodImplementations:
    """Test method implementations in abstract base classes"""

    def test_base_component_methods_exist(self):
        """Test BaseComponent has expected methods"""
        expected_methods = [
            'initialize', 'start', 'stop', '_cleanup',
            'get_health', '_get_health_message', '_get_health_metrics',
            '_get_recent_errors', 'is_ready'
        ]

        for method in expected_methods:
            assert hasattr(BaseComponent, method), f"BaseComponent missing {method}"
            assert callable(getattr(BaseComponent, method)), f"{method} should be callable"

    def test_configurable_component_methods_exist(self):
        """Test ConfigurableComponent has expected methods"""
        expected_methods = [
            'configure', 'get_config', 'validate_config',
            '_validate_configuration', '_apply_configuration'
        ]

        for method in expected_methods:
            assert hasattr(ConfigurableComponent, method), f"ConfigurableComponent missing {method}"
            assert callable(getattr(ConfigurableComponent, method)), f"{method} should be callable"

    def test_metrics_component_methods_exist(self):
        """Test MetricsEnabledComponent has expected methods"""
        expected_methods = [
            'collect_metric', 'get_metrics', 'export_metrics',
            'clear_metrics', '_metric_to_dict'
        ]

        for method in expected_methods:
            assert hasattr(MetricsEnabledComponent, method), f"MetricsEnabledComponent missing {method}"
            assert callable(getattr(MetricsEnabledComponent, method)), f"{method} should be callable"


class TestMethodSignatures:
    """Test method signatures match interface expectations"""

    def test_base_component_init_signature(self):
        """Test BaseComponent.__init__ signature"""
        init_sig = inspect.signature(BaseComponent.__init__)
        assert 'name' in init_sig.parameters

    def test_configurable_configure_signature(self):
        """Test ConfigurableComponent.configure signature"""
        from src.core.types import ServerConfig

        configure_sig = inspect.signature(ConfigurableComponent.configure)
        assert 'config' in configure_sig.parameters

    def test_metrics_collect_signature(self):
        """Test MetricsEnabledComponent.collect_metric signature"""
        collect_sig = inspect.signature(MetricsEnabledComponent.collect_metric)
        assert 'name' in collect_sig.parameters
        assert 'value' in collect_sig.parameters
        assert 'tags' in collect_sig.parameters


class TestClassAttributes:
    """Test class attributes and properties"""

    def test_base_component_has_component_name_property(self):
        """Test BaseComponent has component_name property"""
        assert hasattr(BaseComponent, 'component_name')
        # Property should be defined
        assert isinstance(getattr(BaseComponent, 'component_name'), property)

    def test_configurable_component_has_config_attribute(self):
        """Test ConfigurableComponent has _config attribute"""
        # This is checked during initialization, but we can verify the class structure
        assert hasattr(ConfigurableComponent, '_validate_configuration')
        assert hasattr(ConfigurableComponent, '_apply_configuration')

    def test_metrics_component_has_metrics_attributes(self):
        """Test MetricsEnabledComponent has metrics-related attributes"""
        # Test that instance has the attributes after initialization
        component = MetricsEnabledComponent("test")
        assert hasattr(component, '_metrics')
        assert hasattr(component, '_metrics_lock')


class TestInheritanceChain:
    """Test the inheritance chain is correct"""

    def test_inheritance_depth(self):
        """Test inheritance chain depth"""
        # BaseComponent should inherit directly from IServerComponent
        base_mro = BaseComponent.__mro__
        assert IServerComponent in base_mro
        assert ABC in base_mro

        # ConfigurableComponent should inherit from both BaseComponent and IConfigurable
        config_mro = ConfigurableComponent.__mro__
        assert BaseComponent in config_mro
        assert IConfigurable in config_mro
        assert IServerComponent in config_mro

        # MetricsEnabledComponent should inherit from both BaseComponent and IMetricsCollector
        metrics_mro = MetricsEnabledComponent.__mro__
        assert BaseComponent in metrics_mro
        assert IMetricsCollector in metrics_mro
        assert IServerComponent in metrics_mro

    def test_no_multiple_inheritance_conflicts(self):
        """Test that multiple inheritance doesn't create conflicts"""
        # Check that all classes can be created (even though they're abstract)
        # This would fail if there were method resolution conflicts

        # We can't instantiate abstract classes, but we can check MRO
        config_mro = ConfigurableComponent.__mro__
        assert len(config_mro) == len(set(config_mro))  # No duplicates in MRO

        metrics_mro = MetricsEnabledComponent.__mro__
        assert len(metrics_mro) == len(set(metrics_mro))  # No duplicates in MRO


class TestOverrideMethods:
    """Test that override methods are properly defined"""

    def test_base_component_override_methods(self):
        """Test BaseComponent has methods that can be overridden"""
        override_methods = ['_cleanup', '_get_health_message', '_get_health_metrics', '_get_recent_errors']

        for method in override_methods:
            assert hasattr(BaseComponent, method), f"Missing override method {method}"
            # These should be simple implementations that can be overridden
            method_obj = getattr(BaseComponent, method)
            assert callable(method_obj), f"{method} should be callable"

    def test_configurable_component_override_methods(self):
        """Test ConfigurableComponent has methods that can be overridden"""
        override_methods = ['_validate_configuration', '_apply_configuration']

        for method in override_methods:
            assert hasattr(ConfigurableComponent, method), f"Missing override method {method}"

    def test_metrics_component_override_methods(self):
        """Test MetricsEnabledComponent has methods that can be overridden"""
        # _metric_to_dict is an internal method that can be overridden
        assert hasattr(MetricsEnabledComponent, '_metric_to_dict')