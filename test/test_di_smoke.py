"""
Smoke tests for Dependency Injection Container

This module contains smoke tests that verify basic functionality
of DI container can be instantiated and basic operations work.
"""

import pytest
from unittest.mock import MagicMock

from src.core.di_container import DIContainer, ServiceLifetime, DependencyInjectionException


class TestDIContainerSmoke:
    """Smoke tests for DIContainer basic functionality"""

    def test_di_container_creation(self):
        """Test DIContainer can be created"""
        container = DIContainer()
        assert container is not None
        assert isinstance(container, DIContainer)

    def test_di_container_initial_state(self):
        """Test DIContainer initial state"""
        container = DIContainer()

        # Should have empty services dict
        assert len(container._services) == 0
        assert len(container._singletons) == 0

        # Should not have any registered services
        assert not container.is_registered(str)

    def test_register_transient_service(self):
        """Test registering a transient service"""
        container = DIContainer()

        # Register a simple class
        container.register_transient(str, str)

        # Should be registered
        assert container.is_registered(str)

        # Should be able to resolve
        instance = container.resolve(str)
        assert isinstance(instance, str)
        assert instance == ""  # default str

    def test_register_singleton_service(self):
        """Test registering a singleton service"""
        container = DIContainer()

        # Create a mock class
        class TestService:
            def __init__(self):
                self.value = 42

        container.register_singleton(TestService)

        # Should be registered
        assert container.is_registered(TestService)

        # Should return same instance
        instance1 = container.resolve(TestService)
        instance2 = container.resolve(TestService)

        assert instance1 is instance2
        assert instance1.value == 42
        assert instance2.value == 42

    def test_register_instance(self):
        """Test registering a pre-created instance"""
        container = DIContainer()

        # Create instance
        test_instance = {"key": "value"}

        container.register_instance(dict, test_instance)

        # Should be registered
        assert container.is_registered(dict)

        # Should return the same instance
        resolved = container.resolve(dict)
        assert resolved is test_instance
        assert resolved["key"] == "value"

    def test_register_factory(self):
        """Test registering a factory function"""
        container = DIContainer()

        def create_list():
            return [1, 2, 3]

        container.register_factory(list, create_list, ServiceLifetime.TRANSIENT)

        # Should be registered
        assert container.is_registered(list)

        # Should create new instances each time
        instance1 = container.resolve(list)
        instance2 = container.resolve(list)

        assert instance1 == [1, 2, 3]
        assert instance2 == [1, 2, 3]
        assert instance1 is not instance2  # Different instances

    def test_method_chaining(self):
        """Test method chaining for registration"""
        container = DIContainer()

        # Should return self for chaining
        result = container.register_transient(str, str)
        assert result is container

        result2 = result.register_singleton(int, int)
        assert result2 is container

    def test_get_registered_services(self):
        """Test getting list of registered services"""
        container = DIContainer()

        # Initially empty
        services = container.get_registered_services()
        assert len(services) == 0

        # Register some services
        container.register_transient(str, str)
        container.register_singleton(int, int)

        services = container.get_registered_services()
        assert len(services) == 2
        assert str in services
        assert int in services

    def test_clear_container(self):
        """Test clearing the container"""
        container = DIContainer()

        # Register services
        container.register_transient(str, str)
        container.register_singleton(int, int)

        assert len(container.get_registered_services()) == 2

        # Clear
        container.clear()

        assert len(container.get_registered_services()) == 0
        assert len(container._services) == 0
        assert len(container._singletons) == 0


class TestDIContainerErrorHandling:
    """Smoke tests for DI container error handling"""

    def test_resolve_unregistered_service(self):
        """Test resolving unregistered service raises exception"""
        container = DIContainer()

        with pytest.raises(DependencyInjectionException):
            container.resolve(str)

    def test_register_none_service_type(self):
        """Test registering None as service type raises exception"""
        container = DIContainer()

        with pytest.raises(DependencyInjectionException):
            container.register_transient(None, str)

    def test_register_invalid_implementation(self):
        """Test registering invalid implementation type"""
        container = DIContainer()

        with pytest.raises(DependencyInjectionException):
            container.register_transient(str, 123)  # int is not a type

    def test_register_factory_invalid_lifetime(self):
        """Test registering factory with invalid lifetime"""
        container = DIContainer()

        def factory():
            return "test"

        # This should work - invalid lifetime should be handled
        container.register_factory(str, factory, "invalid_lifetime")

        # But resolution should work
        instance = container.resolve(str)
        assert instance == "test"


class TestDIContainerAdvanced:
    """Advanced smoke tests for DI container"""

    def test_singleton_vs_transient(self):
        """Test singleton vs transient lifetime behavior"""
        container = DIContainer()

        class Counter:
            def __init__(self):
                self.count = 0

        # Register as transient
        container.register_transient(Counter, Counter)

        instance1 = container.resolve(Counter)
        instance2 = container.resolve(Counter)

        # Different instances
        assert instance1 is not instance2

        # Clear and register as singleton
        container.clear()
        container.register_singleton(Counter, Counter)

        instance3 = container.resolve(Counter)
        instance4 = container.resolve(Counter)

        # Same instance
        assert instance3 is instance4

    def test_factory_with_dependencies(self):
        """Test factory function that uses other services"""
        container = DIContainer()

        # Register a base service
        container.register_instance(str, "base_value")

        # Register factory that depends on the base service
        def create_derived():
            base = container.resolve(str)
            return f"derived_{base}"

        container.register_factory(list, create_derived, ServiceLifetime.TRANSIENT)

        # Should work
        instance = container.resolve(list)
        assert instance == "derived_base_value"

    def test_complex_registration_scenario(self):
        """Test complex registration scenario"""
        container = DIContainer()

        # Register multiple services of different types
        container.register_singleton(str, str)
        container.register_transient(int, int)
        container.register_instance(float, 3.14)

        def create_dict():
            s = container.resolve(str)
            i = container.resolve(int)
            f = container.resolve(float)
            return {"str": s, "int": i, "float": f}

        container.register_factory(dict, create_dict, ServiceLifetime.SINGLETON)

        # Resolve complex service
        result = container.resolve(dict)
        expected = {"str": "", "int": 0, "float": 3.14}
        assert result == expected

        # Should be singleton
        result2 = container.resolve(dict)
        assert result is result2