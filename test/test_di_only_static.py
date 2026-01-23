"""
Static tests for Dependency Injection Container (isolated)

This module contains static tests that verify DI container
definitions without importing other problematic modules.
"""

import pytest
import inspect
from abc import ABC
from typing import get_type_hints

# Import only the DI container module directly
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.di_container import (
    ServiceLifetime,
    ServiceDescriptor,
    DependencyInjectionContainer,
    IServiceProvider,
    ServiceNotFoundError,
    CircularDependencyError
)


class TestServiceLifetimeEnum:
    """Test ServiceLifetime enum"""

    def test_service_lifetime_values(self):
        """Test ServiceLifetime enum has expected values"""
        assert ServiceLifetime.SINGLETON.value == "singleton"
        assert ServiceLifetime.TRANSIENT.value == "transient"
        assert ServiceLifetime.SCOPED.value == "scoped"

    def test_service_lifetime_members(self):
        """Test ServiceLifetime has all expected members"""
        members = [member.value for member in ServiceLifetime]
        assert "singleton" in members
        assert "transient" in members
        assert "scoped" in members


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
        # Check class has expected attributes
        assert hasattr(ServiceDescriptor, 'service_type')
        assert hasattr(ServiceDescriptor, 'implementation_type')
        assert hasattr(ServiceDescriptor, 'factory')
        assert hasattr(ServiceDescriptor, 'lifetime')
        assert hasattr(ServiceDescriptor, 'instance')

    def test_service_descriptor_methods_exist(self):
        """Test ServiceDescriptor has expected methods"""
        expected_methods = ['create_instance', 'is_singleton', 'is_transient', 'is_scoped']
        for method in expected_methods:
            assert hasattr(ServiceDescriptor, method)
            assert callable(getattr(ServiceDescriptor, method))


class TestDependencyInjectionContainerStatic:
    """Static tests for DependencyInjectionContainer"""

    def test_di_container_init_signature(self):
        """Test DependencyInjectionContainer.__init__ signature"""
        init_sig = inspect.signature(DependencyInjectionContainer.__init__)
        # Should accept optional parent container
        assert 'parent' in init_sig.parameters

    def test_di_container_methods_exist(self):
        """Test DependencyInjectionContainer has expected methods"""
        expected_methods = [
            'register', 'register_singleton', 'register_transient', 'register_scoped',
            'register_instance', 'resolve', 'is_registered', 'get_all_registrations',
            'create_scope', 'dispose'
        ]
        for method in expected_methods:
            assert hasattr(DependencyInjectionContainer, method)
            assert callable(getattr(DependencyInjectionContainer, method))

    def test_di_container_inherits_from_iservice_provider(self):
        """Test DependencyInjectionContainer implements IServiceProvider"""
        assert issubclass(DependencyInjectionContainer, IServiceProvider)
        assert issubclass(DependencyInjectionContainer, ABC)


class TestIServiceProviderInterface:
    """Static tests for IServiceProvider interface"""

    def test_iservice_provider_is_abstract(self):
        """Test IServiceProvider is abstract base class"""
        assert issubclass(IServiceProvider, ABC)

    def test_iservice_provider_methods(self):
        """Test IServiceProvider has expected abstract methods"""
        # Get all methods defined in the interface
        methods = [name for name, _ in inspect.getmembers(
            IServiceProvider, predicate=inspect.isfunction) if not name.startswith('_')]

        expected_methods = ['resolve', 'is_registered']
        for method in expected_methods:
            assert method in methods, f"IServiceProvider missing {method}"

    def test_iservice_provider_abstract_methods(self):
        """Test IServiceProvider abstract methods are properly marked"""
        # Abstract methods should raise NotImplementedError when called
        provider = IServiceProvider()

        with pytest.raises(NotImplementedError):
            provider.resolve(str)

        with pytest.raises(NotImplementedError):
            provider.is_registered(str)


class TestCustomExceptions:
    """Static tests for custom exceptions"""

    def test_service_not_found_error_inheritance(self):
        """Test ServiceNotFoundError inherits from Exception"""
        assert issubclass(ServiceNotFoundError, Exception)

    def test_circular_dependency_error_inheritance(self):
        """Test CircularDependencyError inherits from Exception"""
        assert issubclass(CircularDependencyError, Exception)

    def test_exceptions_have_proper_init(self):
        """Test custom exceptions can be instantiated"""
        # These should not raise
        ServiceNotFoundError("test service")
        CircularDependencyError("circular dependency detected")


class TestTypeHintsAndAnnotations:
    """Test type hints and annotations"""

    def test_di_container_type_hints(self):
        """Test DependencyInjectionContainer has proper type hints"""
        # Check some key methods have type hints
        resolve_hints = get_type_hints(DependencyInjectionContainer.resolve)
        assert 'service_type' in resolve_hints
        assert 'return' in resolve_hints

        register_hints = get_type_hints(DependencyInjectionContainer.register)
        assert 'service_type' in register_hints
        assert 'implementation_type' in register_hints

    def test_service_descriptor_type_hints(self):
        """Test ServiceDescriptor has proper type hints"""
        init_hints = get_type_hints(ServiceDescriptor.__init__)
        expected_hints = ['service_type', 'implementation_type', 'factory', 'lifetime', 'instance']
        for hint in expected_hints:
            assert hint in init_hints


class TestMethodSignatures:
    """Test method signatures match expectations"""

    def test_register_method_signature(self):
        """Test register method signature"""
        sig = inspect.signature(DependencyInjectionContainer.register)
        params = list(sig.parameters.keys())
        assert 'self' in params
        assert 'service_type' in params
        assert 'implementation_type' in params
        assert 'lifetime' in params

    def test_resolve_method_signature(self):
        """Test resolve method signature"""
        sig = inspect.signature(DependencyInjectionContainer.resolve)
        params = list(sig.parameters.keys())
        assert 'self' in params
        assert 'service_type' in params

    def test_register_singleton_signature(self):
        """Test register_singleton method signature"""
        sig = inspect.signature(DependencyInjectionContainer.register_singleton)
        params = list(sig.parameters.keys())
        assert 'self' in params
        assert 'service_type' in params
        assert 'implementation_type' in params

    def test_register_transient_signature(self):
        """Test register_transient method signature"""
        sig = inspect.signature(DependencyInjectionContainer.register_transient)
        params = list(sig.parameters.keys())
        assert 'self' in params
        assert 'service_type' in params
        assert 'implementation_type' in params


class TestClassStructure:
    """Test class structure and inheritance"""

    def test_di_container_class_hierarchy(self):
        """Test DI container class hierarchy"""
        # Should inherit from IServiceProvider and ABC
        assert issubclass(DependencyInjectionContainer, IServiceProvider)
        assert issubclass(DependencyInjectionContainer, ABC)

    def test_service_descriptor_no_inheritance(self):
        """Test ServiceDescriptor doesn't inherit from anything special"""
        # ServiceDescriptor is a regular class, not inheriting from ABC
        assert not issubclass(ServiceDescriptor, ABC)

    def test_no_multiple_inheritance_conflicts(self):
        """Test that the class hierarchy doesn't have conflicts"""
        # Check MRO for DI container
        mro = DependencyInjectionContainer.__mro__
        assert IServiceProvider in mro
        assert ABC in mro
        # Should not have duplicates
        assert len(mro) == len(set(mro))


class TestConstantsAndDefaults:
    """Test constants and default values"""

    def test_default_lifetime(self):
        """Test default service lifetime"""
        # Default should be TRANSIENT
        descriptor = ServiceDescriptor(str)
        assert descriptor.lifetime == ServiceLifetime.TRANSIENT

    def test_service_descriptor_defaults(self):
        """Test ServiceDescriptor default values"""
        descriptor = ServiceDescriptor(str)

        assert descriptor.service_type == str
        assert descriptor.implementation_type is None
        assert descriptor.factory is None
        assert descriptor.lifetime == ServiceLifetime.TRANSIENT
        assert descriptor.instance is None