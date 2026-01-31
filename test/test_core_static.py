"""
Статические тесты для core архитектуры

Тестирует:
- Интерфейсы (IAgent, IServer, IManager и т.д.)
- DI контейнер
- ServerCore
- Абстрактные базовые классы
- Типы и перечисления
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from typing import Dict, Any, Optional, List, Type, TypeVar
from abc import ABC, abstractmethod
from datetime import datetime

from src.core.di_container import DIContainer, ServiceDescriptor, ServiceLifetime, DependencyInjectionException
from src.core.server_core import ServerCore
from src.core.abstract_base import BaseComponent
from src.core.interfaces.iagent import IAgent
from src.core.interfaces.iserver import IServer
from src.core.interfaces.imanager import IManager
from src.core.interfaces.itaskmanager import ITaskManager
from src.core.interfaces.istatus_manager import IStatusManager
from src.core.interfaces.icheckpoint_manager import ICheckpointManager
from src.core.interfaces.itodo_manager import ITodoManager
from src.core.interfaces.ilogger import ILogger
from src.core.types import TaskType


class TestCoreInterfaces:
    """Тесты для интерфейсов core модуля"""

    def test_i_manager_interface(self):
        """Проверяет интерфейс IManager"""
        # Проверяем, что это абстрактный базовый класс
        assert issubclass(IManager, ABC)

        # Проверяем обязательные методы
        interface_methods = [
            'initialize', 'shutdown', 'get_status', 'get_metrics'
        ]

        for method in interface_methods:
            assert hasattr(IManager, method)

        # Проверяем, что методы абстрактные
        import inspect
        for method_name in interface_methods:
            method = getattr(IManager, method_name)
            assert hasattr(method, '__isabstractmethod__')

    def test_i_agent_interface(self):
        """Проверяет интерфейс IAgent"""
        assert issubclass(IAgent, IManager)

        # Проверяем дополнительные методы агента
        agent_methods = [
            'create_agent', 'get_agent', 'list_agents', 'delete_agent',
            'execute_task', 'get_agent_status', 'get_agent_metrics'
        ]

        for method in agent_methods:
            assert hasattr(IAgent, method)

    def test_i_server_interface(self):
        """Проверяет интерфейс IServer"""
        assert issubclass(IServer, IManager)

        # Проверяем методы сервера
        server_methods = [
            'start', 'stop', 'restart', 'get_server_status',
            'get_active_tasks', 'cancel_task', 'get_server_metrics'
        ]

        for method in server_methods:
            assert hasattr(IServer, method)

    def test_i_task_manager_interface(self):
        """Проверяет интерфейс ITaskManager"""
        assert issubclass(ITaskManager, IManager)

        # Проверяем методы управления задачами
        task_methods = [
            'create_task', 'get_task', 'update_task', 'delete_task',
            'list_tasks', 'execute_task', 'cancel_task', 'get_task_status'
        ]

        for method in task_methods:
            assert hasattr(ITaskManager, method)

    def test_i_status_manager_interface(self):
        """Проверяет интерфейс IStatusManager"""
        assert issubclass(IStatusManager, IManager)

        # Проверяем методы управления статусом
        status_methods = [
            'set_status', 'get_status', 'update_status', 'get_status_history',
            'clear_status', 'get_status_summary'
        ]

        for method in status_methods:
            assert hasattr(IStatusManager, method)

    def test_i_checkpoint_manager_interface(self):
        """Проверяет интерфейс ICheckpointManager"""
        assert issubclass(ICheckpointManager, IManager)

        # Проверяем методы управления чекпоинтами
        checkpoint_methods = [
            'create_checkpoint', 'restore_checkpoint', 'list_checkpoints',
            'delete_checkpoint', 'get_checkpoint_info'
        ]

        for method in checkpoint_methods:
            assert hasattr(ICheckpointManager, method)

    def test_i_todo_manager_interface(self):
        """Проверяет интерфейс ITodoManager"""
        assert issubclass(ITodoManager, IManager)

        # Проверяем методы управления TODO
        todo_methods = [
            'create_todo', 'get_todo', 'update_todo', 'delete_todo',
            'list_todos', 'complete_todo', 'get_todo_status'
        ]

        for method in todo_methods:
            assert hasattr(ITodoManager, method)

    def test_i_logger_interface(self):
        """Проверяет интерфейс ILogger"""
        assert issubclass(ILogger, IManager)

        # Проверяем методы логирования
        logger_methods = [
            'log', 'info', 'warning', 'error', 'debug',
            'get_logs', 'clear_logs', 'set_log_level'
        ]

        for method in logger_methods:
            assert hasattr(ILogger, method)


class TestDIContainerStatic:
    """Статические тесты для DI контейнера"""

    def test_di_container_initialization(self):
        """Тестирует инициализацию DI контейнера"""
        container = DIContainer()

        assert hasattr(container, '_services')
        assert hasattr(container, '_singletons')
        assert isinstance(container._services, dict)
        assert isinstance(container._singletons, dict)

    def test_service_lifetime_enum(self):
        """Тестирует перечисление ServiceLifetime"""
        expected_lifetimes = {'SINGLETON', 'TRANSIENT', 'SCOPED'}

        actual_lifetimes = {lifetime.name for lifetime in ServiceLifetime}
        assert actual_lifetimes == expected_lifetimes

        # Проверяем значения
        assert ServiceLifetime.SINGLETON.value == "singleton"
        assert ServiceLifetime.TRANSIENT.value == "transient"
        assert ServiceLifetime.SCOPED.value == "scoped"

    def test_service_descriptor_creation(self):
        """Тестирует создание ServiceDescriptor"""
        # Создаем простой класс для тестирования
        class TestService:
            pass

        descriptor = ServiceDescriptor(
            service_type=TestService,
            implementation_type=TestService,
            lifetime=ServiceLifetime.SINGLETON
        )

        assert descriptor.service_type == TestService
        assert descriptor.implementation_type == TestService
        assert descriptor.lifetime == ServiceLifetime.SINGLETON
        assert descriptor.factory is None
        assert descriptor.instance is None
        assert descriptor.is_resolving == False

    def test_service_descriptor_with_factory(self):
        """Тестирует ServiceDescriptor с фабрикой"""
        class TestService:
            pass

        def factory():
            return TestService()

        descriptor = ServiceDescriptor(
            service_type=TestService,
            factory=factory,
            lifetime=ServiceLifetime.TRANSIENT
        )

        assert descriptor.factory == factory
        assert descriptor.implementation_type == TestService
        assert descriptor.lifetime == ServiceLifetime.TRANSIENT

    def test_service_descriptor_with_instance(self):
        """Тестирует ServiceDescriptor с предсозданным экземпляром"""
        class TestService:
            def __init__(self, value: int = 42):
                self.value = value

        instance = TestService(100)

        descriptor = ServiceDescriptor(
            service_type=TestService,
            instance=instance,
            lifetime=ServiceLifetime.SINGLETON
        )

        assert descriptor.instance == instance
        assert descriptor.instance.value == 100

    def test_di_container_registration_methods(self):
        """Тестирует методы регистрации сервисов"""
        container = DIContainer()

        # Проверяем наличие методов регистрации
        assert hasattr(container, 'register_singleton')
        assert hasattr(container, 'register_transient')
        assert hasattr(container, 'register_factory')
        assert hasattr(container, 'register_instance')
        assert hasattr(container, 'resolve')

        # Проверяем, что методы возвращают self для chaining
        class TestService:
            pass

        result = container.register_singleton(TestService)
        assert result is container

        result = container.register_transient(TestService)
        assert result is container

    def test_di_container_resolve_method_signature(self):
        """Проверяет сигнатуру метода resolve"""
        import inspect

        container = DIContainer()
        sig = inspect.signature(container.resolve)

        assert 'service_type' in sig.parameters

    def test_dependency_injection_exception(self):
        """Тестирует пользовательское исключение"""
        assert issubclass(DependencyInjectionException, Exception)

        # Проверяем, что можно создать исключение
        exc = DependencyInjectionException("Test error")
        assert str(exc) == "Test error"


class TestAbstractBaseClasses:
    """Тесты для абстрактных базовых классов"""

    def test_base_component(self):
        """Тестирует BaseComponent"""
        from src.core.abstract_base import BaseComponent

        # Проверяем, что можно создать экземпляр
        component = BaseComponent("test_component")
        assert isinstance(component, BaseComponent)
        assert component.component_name == "test_component"


class TestServerCoreStatic:
    """Статические тесты для ServerCore"""

    def test_server_core_initialization(self):
        """Тестирует базовую инициализацию ServerCore"""
        # Мокаем зависимости
        mock_todo_manager = Mock()
        mock_status_manager = Mock()
        mock_checkpoint_manager = Mock()
        mock_logger = Mock()

        # Проверяем, что класс существует и имеет правильную структуру
        assert hasattr(ServerCore, '__init__')

        # Проверяем сигнатуру конструктора
        import inspect
        sig = inspect.signature(ServerCore.__init__)
        expected_params = ['self', 'todo_manager', 'status_manager', 'checkpoint_manager', 'logger', 'config']
        actual_params = list(sig.parameters.keys())
        assert all(param in actual_params for param in expected_params[:5])  # config - optional

    def test_server_core_attributes(self):
        """Проверяет атрибуты ServerCore"""
        # Проверяем, что класс имеет ожидаемые атрибуты
        assert hasattr(ServerCore, 'run_main_loop')
        assert hasattr(ServerCore, 'process_single_task')
        assert hasattr(ServerCore, 'handle_no_tasks_scenario')
        assert hasattr(ServerCore, 'get_execution_delay')

    def test_server_core_async_methods(self):
        """Проверяет асинхронные методы ServerCore"""
        # Основные методы должны быть асинхронными
        assert asyncio.iscoroutinefunction(ServerCore.run_main_loop)
        assert asyncio.iscoroutinefunction(ServerCore.process_single_task)

    def test_server_core_constants(self):
        """Проверяет константы ServerCore"""
        # Проверяем наличие типичных констант
        assert hasattr(ServerCore, 'DEFAULT_EXECUTION_DELAY')
        assert hasattr(ServerCore, 'MAX_RETRY_ATTEMPTS')
        assert hasattr(ServerCore, 'REVISION_CHECK_INTERVAL')


class TestCoreTypes:
    """Тесты для типов core модуля"""

    def test_task_type_enum(self):
        """Тестирует перечисление TaskType"""
        expected_types = {
            'CODE', 'DOCS', 'REFACTOR', 'TEST', 'RELEASE', 'DEVOPS', 'UNKNOWN'
        }

        actual_types = {task_type.name for task_type in TaskType}
        assert actual_types == expected_types

        # Проверяем значения
        assert TaskType.CODE.value == "code"
        assert TaskType.DOCS.value == "docs"
        assert TaskType.TEST.value == "test"
        assert TaskType.RELEASE.value == "release"
        assert TaskType.DEVOPS.value == "devops"
        assert TaskType.UNKNOWN.value == "unknown"

    def test_task_type_from_string(self):
        """Тестирует создание TaskType из строки"""
        # Проверяем, что можно получить enum по значению
        assert TaskType('code') == TaskType.CODE
        assert TaskType('docs') == TaskType.DOCS
        assert TaskType('test') == TaskType.TEST

        with pytest.raises(ValueError):
            TaskType('invalid_type')


class TestCoreTypeAnnotations:
    """Тесты для корректности type annotations"""

    def test_di_container_type_annotations(self):
        """Проверяет type annotations в DI контейнере"""
        import inspect

        # Проверяем сигнатуры ключевых методов
        sig = inspect.signature(DIContainer.register_singleton)
        assert 'service_type' in sig.parameters
        assert 'implementation_type' in sig.parameters

        sig = inspect.signature(DIContainer.resolve)
        assert 'service_type' in sig.parameters

    def test_interface_type_annotations(self):
        """Проверяет type annotations в интерфейсах"""
        import inspect

        # Проверяем метод initialize в IManager
        sig = inspect.signature(IManager.initialize)
        assert len(sig.parameters) >= 1  # self

        # Проверяем метод create_agent в IAgent
        sig = inspect.signature(IAgent.create_agent)
        assert 'agent_type' in sig.parameters
        assert 'config' in sig.parameters


class TestCoreErrorHandling:
    """Тесты для обработки ошибок в core модулях"""

    def test_di_container_error_handling(self):
        """Тестирует обработку ошибок в DI контейнере"""
        container = DIContainer()

        # Пытаемся разрешить незарегистрированный сервис
        class UnknownService:
            pass

        with pytest.raises(DependencyInjectionException):
            container.resolve(UnknownService)

    def test_service_descriptor_validation(self):
        """Тестирует валидацию ServiceDescriptor"""
        # Проверяем, что нельзя создать descriptor без service_type
        with pytest.raises(TypeError):
            ServiceDescriptor()

        # Проверяем создание с минимальными параметрами
        class TestService:
            pass

        descriptor = ServiceDescriptor(service_type=TestService)
        assert descriptor.service_type == TestService
        assert descriptor.implementation_type == TestService
        assert descriptor.lifetime == ServiceLifetime.TRANSIENT