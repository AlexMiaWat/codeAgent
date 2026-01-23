"""
Dependency Injection Container for Code Agent.

This module provides a simple but powerful DI container that manages
component registration, dependency resolution, and lifecycle management.
Follows SOLID principles and enables loose coupling between components.
"""

import logging
from typing import Dict, Any, Type, TypeVar, Optional, Callable, Union, List, get_origin, get_args
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ServiceLifetime(Enum):
    """Service lifetime scopes."""
    SINGLETON = "singleton"  # One instance for the entire application lifetime
    TRANSIENT = "transient"  # New instance each time requested
    SCOPED = "scoped"       # One instance per scope (not implemented yet)


class ServiceDescriptor:
    """
    Descriptor for a service registration.

    Contains information about how to create and manage a service instance.
    """

    def __init__(
        self,
        service_type: Type[T],
        implementation_type: Optional[Type[T]] = None,
        factory: Optional[Callable] = None,
        lifetime: ServiceLifetime = ServiceLifetime.TRANSIENT,
        instance: Optional[T] = None
    ):
        """
        Initialize service descriptor.

        Args:
            service_type: The service interface/abstract type
            implementation_type: The concrete implementation type
            factory: Factory function to create instances
            lifetime: Service lifetime scope
            instance: Pre-created instance for singleton services
        """
        self.service_type = service_type
        self.implementation_type = implementation_type or service_type
        self.factory = factory
        self.lifetime = lifetime
        self.instance = instance
        self.is_resolving = False  # Prevent circular dependencies


class DependencyInjectionException(Exception):
    """Exception raised when DI container encounters an error."""
    pass


class DIContainer:
    """
    Dependency Injection Container.

    Provides registration and resolution of services with support for:
    - Constructor injection
    - Singleton and transient lifetimes
    - Factory functions
    - Circular dependency detection
    """

    def __init__(self):
        """Initialize the DI container."""
        self._services: Dict[Type, ServiceDescriptor] = {}
        self._singletons: Dict[Type, Any] = {}
        logger.info("DI Container initialized")

    def register_singleton(self, service_type: Type[T], implementation_type: Optional[Type[T]] = None) -> 'DIContainer':
        """
        Register a service as a singleton.

        Args:
            service_type: The service interface type
            implementation_type: The concrete implementation type (optional)

        Returns:
            Self for method chaining
        """
        descriptor = ServiceDescriptor(
            service_type=service_type,
            implementation_type=implementation_type,
            lifetime=ServiceLifetime.SINGLETON
        )
        self._services[service_type] = descriptor
        logger.debug(f"Registered singleton: {service_type.__name__}")
        return self

    def register_transient(self, service_type: Type[T], implementation_type: Optional[Type[T]] = None) -> 'DIContainer':
        """
        Register a service as transient.

        Args:
            service_type: The service interface type
            implementation_type: The concrete implementation type (optional)

        Returns:
            Self for method chaining
        """
        descriptor = ServiceDescriptor(
            service_type=service_type,
            implementation_type=implementation_type,
            lifetime=ServiceLifetime.TRANSIENT
        )
        self._services[service_type] = descriptor
        logger.debug(f"Registered transient: {service_type.__name__}")
        return self

    def register_factory(self, service_type: Type[T], factory: Callable[[], T], lifetime: ServiceLifetime = ServiceLifetime.TRANSIENT) -> 'DIContainer':
        """
        Register a service using a factory function.

        Args:
            service_type: The service interface type
            factory: Factory function that creates service instances
            lifetime: Service lifetime scope

        Returns:
            Self for method chaining
        """
        descriptor = ServiceDescriptor(
            service_type=service_type,
            factory=factory,
            lifetime=lifetime
        )
        self._services[service_type] = descriptor
        logger.debug(f"Registered factory for: {service_type.__name__}")
        return self

    def register_instance(self, service_type: Type[T], instance: T) -> 'DIContainer':
        """
        Register a pre-created instance as a singleton.

        Args:
            service_type: The service interface type
            instance: The pre-created instance

        Returns:
            Self for method chaining
        """
        descriptor = ServiceDescriptor(
            service_type=service_type,
            instance=instance,
            lifetime=ServiceLifetime.SINGLETON
        )
        self._services[service_type] = descriptor
        self._singletons[service_type] = instance
        logger.debug(f"Registered instance for: {service_type.__name__}")
        return self

    def resolve(self, service_type: Type[T]) -> T:
        """
        Resolve a service instance.

        Args:
            service_type: The service type to resolve

        Returns:
            Service instance

        Raises:
            DependencyInjectionException: If service cannot be resolved
        """
        if service_type not in self._services:
            raise DependencyInjectionException(f"Service {service_type.__name__} is not registered")

        descriptor = self._services[service_type]

        # Return singleton instance if it exists
        if descriptor.lifetime == ServiceLifetime.SINGLETON and service_type in self._singletons:
            return self._singletons[service_type]

        # Check for circular dependency
        if descriptor.is_resolving:
            raise DependencyInjectionException(f"Circular dependency detected for {service_type.__name__}")

        try:
            descriptor.is_resolving = True
            instance = self._create_instance(descriptor)
            descriptor.is_resolving = False

            # Store singleton instance
            if descriptor.lifetime == ServiceLifetime.SINGLETON:
                self._singletons[service_type] = instance

            return instance

        except Exception as e:
            descriptor.is_resolving = False
            raise DependencyInjectionException(f"Failed to resolve {service_type.__name__}: {e}") from e

    def _create_instance(self, descriptor: ServiceDescriptor) -> Any:
        """
        Create an instance using the descriptor.

        Args:
            descriptor: Service descriptor

        Returns:
            Created instance
        """
        if descriptor.instance is not None:
            return descriptor.instance

        if descriptor.factory is not None:
            return descriptor.factory()

        if descriptor.implementation_type is None:
            raise DependencyInjectionException(f"No implementation type for {descriptor.service_type.__name__}")

        # Use constructor injection
        return self._create_with_constructor_injection(descriptor.implementation_type)

    def _create_with_constructor_injection(self, implementation_type: Type[T]) -> T:
        """
        Create an instance using constructor injection.

        Args:
            implementation_type: The implementation type to instantiate

        Returns:
            Created instance with injected dependencies
        """
        import inspect

        # Get constructor signature
        init_signature = inspect.signature(implementation_type.__init__)
        parameters = init_signature.parameters

        # Skip 'self' parameter
        param_names = [name for name in parameters.keys() if name != 'self']

        # Resolve dependencies for each parameter
        kwargs = {}
        for param_name in param_names:
            param = parameters[param_name]

            # Try to resolve by parameter type annotation first
            service_type = None
            if param.annotation != inspect.Parameter.empty:
                # Direct type annotation match
                if param.annotation in self._services:
                    service_type = param.annotation
                else:
                    # Handle Optional[T] and Union[T, None] annotations
                    origin = get_origin(param.annotation)
                    if origin in (Union, type(Optional)):
                        # Extract the non-None type from Optional/Union
                        args = get_args(param.annotation)
                        for arg in args:
                            if arg != type(None) and arg in self._services:
                                service_type = arg
                                break

            # Fallback to name-based resolution if type annotation didn't work
            if service_type is None:
                service_type = self._find_service_type_by_name(param_name)

            if service_type:
                kwargs[param_name] = self.resolve(service_type)
            elif param.default != inspect.Parameter.empty:
                # Use default value if available
                continue
            else:
                raise DependencyInjectionException(
                    f"Cannot resolve parameter '{param_name}' (type: {param.annotation}) for {implementation_type.__name__}"
                )

        return implementation_type(**kwargs)

    def _find_service_type_by_name(self, name: str) -> Optional[Type]:
        """
        Find a registered service type by name.

        This is a simple implementation that tries to match service names.
        In a more advanced implementation, you might use annotations or other metadata.

        Args:
            name: Parameter name to match

        Returns:
            Matching service type or None
        """
        # Convert parameter name to potential service type names
        candidates = [
            name,  # exact match
            name.lower(),
            name.upper(),
            ''.join(word.capitalize() for word in name.split('_')),  # snake_case to PascalCase
        ]

        for candidate in candidates:
            for service_type in self._services.keys():
                if service_type.__name__.lower() == candidate.lower():
                    return service_type

        return None

    def is_registered(self, service_type: Type[T]) -> bool:
        """
        Check if a service type is registered.

        Args:
            service_type: Service type to check

        Returns:
            True if registered, False otherwise
        """
        return service_type in self._services

    def dispose(self) -> None:
        """
        Dispose of the container and clean up resources.

        This will dispose of all singleton instances that implement IDisposable.
        """
        for service_type, instance in self._singletons.items():
            if hasattr(instance, 'dispose') and callable(getattr(instance, 'dispose')):
                try:
                    instance.dispose()
                    logger.debug(f"Disposed {service_type.__name__}")
                except Exception as e:
                    logger.warning(f"Error disposing {service_type.__name__}: {e}")

        self._services.clear()
        self._singletons.clear()
        logger.info("DI Container disposed")


def create_default_container(project_dir: Path, config: Dict[str, Any], status_file: Path) -> DIContainer:
    """
    Create a DI container with default service registrations for Code Agent.

    Args:
        project_dir: Project directory path
        config: Configuration dictionary
        status_file: Path to status file

    Returns:
        Configured DI container
    """
    # Import interfaces
    try:
        from .interfaces import ITodoManager, IStatusManager, ICheckpointManager, ILogger
        from ..todo_manager import TodoManager
        from ..status_manager import StatusManager
        from ..checkpoint_manager import CheckpointManager
        from ..task_logger import ServerLogger
    except ImportError:
        # Fallback for test environment
        import sys
        import os
        current_dir = Path(__file__).parent
        src_dir = current_dir.parent
        if str(src_dir) not in sys.path:
            sys.path.insert(0, str(src_dir))

        from src.core.interfaces import ITodoManager, IStatusManager, ICheckpointManager, ILogger
        from src.todo_manager import TodoManager
        from src.status_manager import StatusManager
        from src.checkpoint_manager import CheckpointManager
        from src.task_logger import ServerLogger

    container = DIContainer()

    # Register TodoManager with factory
    def create_todo_manager():
        return TodoManager(project_dir=project_dir, config=config.get('todo_manager', {}))
    container.register_factory(ITodoManager, create_todo_manager)

    # Register StatusManager with factory
    def create_status_manager():
        return StatusManager(status_file=status_file, config=config.get('status_manager', {}))
    container.register_factory(IStatusManager, create_status_manager)

    # Register CheckpointManager with factory
    def create_checkpoint_manager():
        checkpoint_file = config.get('checkpoint_file', '.codeagent_checkpoint.json')
        # Checkpoint файлы хранятся в каталоге codeAgent, а не в целевом проекте
        codeagent_dir = Path(__file__).parent.parent.parent
        return CheckpointManager(project_dir=codeagent_dir, config={'checkpoint_file': checkpoint_file})
    container.register_factory(ICheckpointManager, create_checkpoint_manager)

    # Register Logger with factory
    def create_logger():
        return ServerLogger(config=config.get('logging', {}))
    container.register_factory(ILogger, create_logger)

    logger.info("Default DI container created with core services")
    return container