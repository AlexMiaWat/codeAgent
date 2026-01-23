"""
Static tests for Dependency Injection Container

This module contains static tests that verify DI container
definitions, interfaces, and method implementations without
requiring runtime instantiation.
"""

import inspect
from abc import ABC
from typing import get_type_hints

from src.core.di_container import (
    DIContainer, ServiceDescriptor, ServiceLifetime, DependencyInjectionException
)


class TestDIContainerStatic:
    """Static tests for DIContainer"""

    def test_di_container_inherits_from_object(self):
        """Test DIContainer is a concrete class"""
        assert not issubclass(DIContainer, ABC)
        assert inspect.isclass(DIContainer)

    def test_di_container_methods_exist(self):
        """Test DIContainer has expected methods"""
        expected_methods = [
            '__init__', 'register_singleton', 'register_transient',
            'register_factory', 'register_instance', 'resolve',
            'is_registered', 'dispose'
        ]
        for method in expected_methods:
            assert hasattr(DIContainer, method)
            assert callable(getattr(DIContainer, method))

    def test_di_container_init_signature(self):
        """Test DIContainer.__init__ signature"""
        init_sig = inspect.signature(DIContainer.__init__)
        assert len(init_sig.parameters) == 1  # self only

    def test_register_singleton_signature(self):
        """Test register_singleton method signature"""
        sig = inspect.signature(DIContainer.register_singleton)
        expected_params = ['service_type', 'implementation_type']
        for param in expected_params:
            assert param in sig.parameters

    def test_register_transient_signature(self):
        """Test register_transient method signature"""
        sig = inspect.signature(DIContainer.register_transient)
        expected_params = ['service_type', 'implementation_type']
        for param in expected_params:
            assert param in sig.parameters

    def test_resolve_signature(self):
        """Test resolve method signature"""
        sig = inspect.signature(DIContainer.resolve)
        expected_params = ['service_type']
        for param in expected_params:
            assert param in sig.parameters

    def test_register_factory_signature(self):
        """Test register_factory method signature"""
        sig = inspect.signature(DIContainer.register_factory)
        expected_params = ['service_type', 'factory', 'lifetime']
        for param in expected_params:
            assert param in sig.parameters


class TestServiceDescriptorStatic:
    """Static tests for ServiceDescriptor"""

    def test_service_descriptor_init_signature(self):
        """Test ServiceDescriptor.__init__ signature"""
        init_sig = inspect.signature(ServiceDescriptor.__init__)
        expected_params = ['service_type', 'implementation_type', 'factory', 'lifetime', 'instance']
        for param in expected_params:
            assert param in init_sig.parameters

    def test_service_descriptor_attributes(self):
        """Test ServiceDescriptor has expected attributes"""
        expected_attrs = ['service_type', 'implementation_type', 'factory', 'lifetime', 'instance', 'is_resolving']
        for attr in expected_attrs:
            assert hasattr(ServiceDescriptor, attr)


class TestServiceLifetimeEnum:
    """Static tests for ServiceLifetime enum"""

    def test_service_lifetime_values(self):
        """Test ServiceLifetime enum has expected values"""
        assert ServiceLifetime.SINGLETON.value == "singleton"
        assert ServiceLifetime.TRANSIENT.value == "transient"
        assert ServiceLifetime.SCOPED.value == "scoped"

    def test_service_lifetime_all_values(self):
        """Test all ServiceLifetime values are present"""
        expected_values = ["singleton", "transient", "scoped"]
        actual_values = [lifetime.value for lifetime in ServiceLifetime]
        assert set(actual_values) == set(expected_values)


class TestDependencyInjectionException:
    """Static tests for DependencyInjectionException"""

    def test_exception_inherits_from_exception(self):
        """Test DependencyInjectionException inherits from Exception"""
        assert issubclass(DependencyInjectionException, Exception)


class TestMethodSignatures:
    """Test method signatures and type hints"""

    def test_di_container_register_instance_signature(self):
        """Test register_instance method signature"""
        sig = inspect.signature(DIContainer.register_instance)
        expected_params = ['service_type', 'instance']
        for param in expected_params:
            assert param in sig.parameters

    def test_di_container_is_registered_signature(self):
        """Test is_registered method signature"""
        sig = inspect.signature(DIContainer.is_registered)
        expected_params = ['service_type']
        for param in expected_params:
            assert param in sig.parameters

    def test_di_container_get_registered_services_signature(self):
        """Test get_registered_services method signature"""
        sig = inspect.signature(DIContainer.get_registered_services)
        assert len(sig.parameters) == 1  # self only

    def test_di_container_clear_signature(self):
        """Test clear method signature"""
        sig = inspect.signature(DIContainer.clear)
        assert len(sig.parameters) == 1  # self only


class TestTypeHints:
    """Test type hints for DI container methods"""

    def test_di_container_register_singleton_hints(self):
        """Test register_singleton has type hints"""
        method = DIContainer.register_singleton
        hints = get_type_hints(method)
        assert hints, "register_singleton should have type hints"

    def test_di_container_resolve_hints(self):
        """Test resolve method has type hints"""
        method = DIContainer.resolve
        hints = get_type_hints(method)
        assert hints, "resolve should have type hints"

    def test_service_descriptor_init_hints(self):
        """Test ServiceDescriptor.__init__ has type hints"""
        hints = get_type_hints(ServiceDescriptor.__init__)
        assert hints, "ServiceDescriptor.__init__ should have type hints"


class TestClassHierarchy:
    """Test class hierarchy and inheritance"""

    def test_di_container_no_multiple_inheritance(self):
        """Test DIContainer doesn't use problematic multiple inheritance"""
        mro = DIContainer.__mro__
        # Should only inherit from object
        assert len(mro) == 2  # DIContainer, object
        assert mro[0] == DIContainer
        assert mro[1] == object

    def test_service_descriptor_no_inheritance(self):
        """Test ServiceDescriptor doesn't inherit from other classes"""
        mro = ServiceDescriptor.__mro__
        assert len(mro) == 2  # ServiceDescriptor, object
        assert mro[0] == ServiceDescriptor
        assert mro[1] == object