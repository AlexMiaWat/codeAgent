"""
Дымовые тесты для core архитектуры

Проверяют базовую работоспособность:
- DI контейнер может регистрировать и разрешать сервисы
- ServerCore может быть создан и выполнять базовые операции
- Интерфейсы правильно реализованы
- Компоненты могут взаимодействовать
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
import asyncio
from typing import Dict, Any, Optional, Type

from src.core.di_container import DIContainer, ServiceDescriptor, ServiceLifetime, DependencyInjectionException
from src.core.server_core import ServerCore
from src.core.abstract_base import BaseComponent
from src.core.interfaces.iagent import IAgent
from src.core.interfaces.iserver import IServer
from src.core.interfaces.imanager import IManager
from src.core.types import TaskType


class TestDIContainerSmoke:
    """Дымовые тесты для DI контейнера"""

    def test_container_creation(self):
        """Проверяет создание DI контейнера"""
        container = DIContainer()

        assert container is not None
        assert hasattr(container, '_services')
        assert hasattr(container, '_singletons')
        assert isinstance(container._services, dict)
        assert isinstance(container._singletons, dict)

    def test_register_singleton_service(self):
        """Проверяет регистрацию singleton сервиса"""
        container = DIContainer()

        class TestService:
            def __init__(self):
                self.value = "test"

        # Регистрируем сервис
        container.register_singleton(TestService)

        # Проверяем, что сервис зарегистрирован
        assert TestService in container._services

        # Разрешаем сервис
        instance1 = container.resolve(TestService)
        instance2 = container.resolve(TestService)

        assert instance1 is not None
        assert instance2 is not None
        # Singleton - должна быть одна и та же instance
        assert instance1 is instance2
        assert instance1.value == "test"

    def test_register_transient_service(self):
        """Проверяет регистрацию transient сервиса"""
        container = DIContainer()

        class TestService:
            def __init__(self):
                self.id = id(self)

        # Регистрируем transient сервис
        container.register_transient(TestService)

        # Разрешаем сервис несколько раз
        instance1 = container.resolve(TestService)
        instance2 = container.resolve(TestService)

        assert instance1 is not None
        assert instance2 is not None
        # Transient - должны быть разные instances
        assert instance1 is not instance2
        assert instance1.id != instance2.id

    def test_register_factory_service(self):
        """Проверяет регистрацию сервиса через фабрику"""
        container = DIContainer()

        class TestService:
            def __init__(self, name: str):
                self.name = name

        def factory():
            return TestService("factory_created")

        # Регистрируем фабрику
        container.register_factory(TestService, factory)

        # Разрешаем сервис
        instance = container.resolve(TestService)

        assert instance is not None
        assert instance.name == "factory_created"

    def test_register_instance_service(self):
        """Проверяет регистрацию предсозданного экземпляра"""
        container = DIContainer()

        class TestService:
            def __init__(self, value: int):
                self.value = value

        # Создаем экземпляр
        instance = TestService(42)

        # Регистрируем экземпляр
        container.register_instance(TestService, instance)

        # Разрешаем сервис
        resolved = container.resolve(TestService)

        assert resolved is not None
        assert resolved is instance  # Должен вернуться тот же экземпляр
        assert resolved.value == 42

    def test_service_with_dependencies(self):
        """Проверяет разрешение сервисов с зависимостями"""
        container = DIContainer()

        class Logger:
            def log(self, message: str):
                return f"LOG: {message}"

        class Database:
            def __init__(self, logger: Logger):
                self.logger = logger

            def connect(self):
                return self.logger.log("Database connected")

        # Регистрируем сервисы
        container.register_singleton(Logger)
        container.register_transient(Database)

        # Разрешаем сервисы
        db = container.resolve(Database)

        assert db is not None
        assert hasattr(db, 'logger')
        assert db.connect() == "LOG: Database connected"

    def test_circular_dependency_detection(self):
        """Проверяет обнаружение циклических зависимостей"""
        container = DIContainer()

        class ServiceA:
            def __init__(self, service_b: 'ServiceB'):
                self.service_b = service_b

        class ServiceB:
            def __init__(self, service_a: ServiceA):
                self.service_a = service_a

        # Регистрируем сервисы с циклической зависимостью
        container.register_transient(ServiceA)
        container.register_transient(ServiceB)

        # Попытка разрешить должна вызвать исключение
        with pytest.raises(DependencyInjectionException):
            container.resolve(ServiceA)

    def test_method_chaining(self):
        """Проверяет chaining методов регистрации"""
        container = DIContainer()

        class ServiceA:
            pass

        class ServiceB:
            pass

        # Метод chaining должен работать
        result = container.register_singleton(ServiceA).register_transient(ServiceB)

        assert result is container

        # Проверяем, что оба сервиса зарегистрированы
        assert ServiceA in container._services
        assert ServiceB in container._services

    def test_resolve_nonexistent_service(self):
        """Проверяет разрешение несуществующего сервиса"""
        container = DIContainer()

        class NonExistentService:
            pass

        # Попытка разрешить незарегистрированный сервис должна вызвать исключение
        with pytest.raises(DependencyInjectionException):
            container.resolve(NonExistentService)


class TestServerCoreSmoke:
    """Дымовые тесты для ServerCore"""

    def test_server_core_creation(self):
        """Проверяет создание ServerCore"""
        # Мокаем зависимости
        mock_todo_manager = Mock()
        mock_status_manager = Mock()
        mock_checkpoint_manager = Mock()
        mock_logger = Mock()

        server_core = ServerCore(
            todo_manager=mock_todo_manager,
            status_manager=mock_status_manager,
            checkpoint_manager=mock_checkpoint_manager,
            logger=mock_logger
        )

        assert server_core is not None
        assert hasattr(server_core, 'todo_manager')
        assert hasattr(server_core, 'status_manager')
        assert hasattr(server_core, 'checkpoint_manager')
        assert hasattr(server_core, 'logger')

    @patch('src.core.server_core.QualityGateManager')
    @patch('src.core.server_core.MultiLevelVerificationManager')
    def test_server_core_with_dependencies(self, mock_verification, mock_quality):
        """Проверяет создание ServerCore с зависимостями"""
        # Мокаем зависимости
        mock_todo_manager = Mock()
        mock_status_manager = Mock()
        mock_checkpoint_manager = Mock()
        mock_logger = Mock()

        # Мокаем компоненты верификации
        mock_quality_instance = Mock()
        mock_quality.return_value = mock_quality_instance

        mock_verification_instance = Mock()
        mock_verification.return_value = mock_verification_instance

        server_core = ServerCore(
            todo_manager=mock_todo_manager,
            status_manager=mock_status_manager,
            checkpoint_manager=mock_checkpoint_manager,
            logger=mock_logger
        )

        assert server_core is not None
        # Проверяем, что компоненты верификации созданы
        assert hasattr(server_core, 'quality_gate_manager')
        assert hasattr(server_core, 'verification_manager')

    @patch('src.core.server_core.QualityGateManager')
    @patch('src.core.server_core.MultiLevelVerificationManager')
    def test_server_core_run_main_loop(self, mock_verification, mock_quality):
        """Проверяет запуск основного цикла"""
        # Мокаем зависимости
        mock_todo_manager = Mock()
        mock_status_manager = Mock()
        mock_checkpoint_manager = Mock()
        mock_logger = Mock()

        # Настраиваем моки
        mock_todo_manager.get_pending_tasks = AsyncMock(return_value=[])
        mock_quality.return_value = Mock()
        mock_verification.return_value = Mock()

        server_core = ServerCore(
            todo_manager=mock_todo_manager,
            status_manager=mock_status_manager,
            checkpoint_manager=mock_checkpoint_manager,
            logger=mock_logger
        )

        async def test():
            # Основной цикл должен выполниться без ошибок
            try:
                await asyncio.wait_for(server_core.run_main_loop(), timeout=1.0)
            except asyncio.TimeoutError:
                # Таймаут нормален для бесконечного цикла
                pass
            except Exception as e:
                pytest.fail(f"Unexpected exception in main loop: {e}")

        asyncio.run(test())

    @patch('src.core.server_core.QualityGateManager')
    @patch('src.core.server_core.MultiLevelVerificationManager')
    def test_server_core_process_single_task(self, mock_verification, mock_quality):
        """Проверяет обработку отдельной задачи"""
        # Мокаем зависимости
        mock_todo_manager = Mock()
        mock_status_manager = Mock()
        mock_checkpoint_manager = Mock()
        mock_logger = Mock()

        # Настраиваем моки
        mock_todo_manager.get_task = AsyncMock(return_value=Mock(id="test_task", type=TaskType.CODE))
        mock_todo_manager.update_task_status = AsyncMock()
        mock_quality.return_value = Mock()
        mock_verification.return_value = Mock()

        server_core = ServerCore(
            todo_manager=mock_todo_manager,
            status_manager=mock_status_manager,
            checkpoint_manager=mock_checkpoint_manager,
            logger=mock_logger
        )

        async def test():
            # Обработка задачи должна выполниться без ошибок
            await server_core.process_single_task("test_task_id")

            # Проверяем, что методы были вызваны
            mock_todo_manager.get_task.assert_called_once_with("test_task_id")

        asyncio.run(test())

    def test_server_core_get_execution_delay(self):
        """Проверяет получение задержки выполнения"""
        # Мокаем зависимости
        mock_todo_manager = Mock()
        mock_status_manager = Mock()
        mock_checkpoint_manager = Mock()
        mock_logger = Mock()

        server_core = ServerCore(
            todo_manager=mock_todo_manager,
            status_manager=mock_status_manager,
            checkpoint_manager=mock_checkpoint_manager,
            logger=mock_logger
        )

        delay = server_core.get_execution_delay()

        assert isinstance(delay, (int, float))
        assert delay >= 0

    def test_server_core_constants(self):
        """Проверяет константы ServerCore"""
        # Проверяем наличие основных констант
        assert hasattr(ServerCore, 'DEFAULT_EXECUTION_DELAY')
        assert hasattr(ServerCore, 'MAX_RETRY_ATTEMPTS')
        assert hasattr(ServerCore, 'REVISION_CHECK_INTERVAL')

        # Проверяем значения констант
        assert ServerCore.DEFAULT_EXECUTION_DELAY >= 0
        assert ServerCore.MAX_RETRY_ATTEMPTS > 0
        assert ServerCore.REVISION_CHECK_INTERVAL > 0


class TestAbstractBaseClassesSmoke:
    """Дымовые тесты для базовых классов"""

    def test_base_component_creation(self):
        """Проверяет создание BaseComponent"""
        component = BaseComponent("test_component")

        assert component is not None
        assert component.component_name == "test_component"

    def test_base_component_methods(self):
        """Проверяет методы BaseComponent"""
        component = BaseComponent("test_component")

        # Проверяем базовую функциональность
        assert component.initialize() == True
        assert component.start() == True
        assert component.stop() == True

        status = component.get_status()
        assert status is not None

        health = component.get_health()
        assert health is not None
        assert hasattr(health, 'status')


class TestCoreInterfacesSmoke:
    """Дымовые тесты для интерфейсов core"""

    def test_interface_inheritance(self):
        """Проверяет наследование интерфейсов"""
        # Проверяем, что интерфейсы правильно наследуются
        assert issubclass(IAgent, IManager)
        assert issubclass(IServer, IManager)
        assert issubclass(BaseManager, IManager)

    def test_interface_method_signatures(self):
        """Проверяет сигнатуры методов интерфейсов"""
        import inspect

        # Проверяем, что основные методы определены
        manager_methods = ['initialize', 'shutdown', 'get_status', 'get_metrics']
        for method in manager_methods:
            assert hasattr(IManager, method)

        # BaseComponent имеет синхронные методы
        component_methods = ['initialize', 'start', 'stop', 'get_status', 'get_health']
        for method in component_methods:
            assert hasattr(BaseComponent, method)


class TestCoreIntegrationSmoke:
    """Дымовые тесты интеграции core компонентов"""

    def test_di_container_with_managers(self):
        """Проверяет работу DI контейнера с менеджерами"""
        container = DIContainer()

        # Регистрируем менеджеры
        container.register_singleton(BaseManager)

        # Разрешаем менеджер
        manager = container.resolve(BaseManager)

        assert manager is not None
        assert isinstance(manager, BaseManager)
        assert isinstance(manager, IManager)

    @patch('src.core.server_core.QualityGateManager')
    @patch('src.core.server_core.MultiLevelVerificationManager')
    def test_server_core_full_initialization(self, mock_verification, mock_quality):
        """Проверяет полную инициализацию ServerCore"""
        # Мокаем все зависимости
        mock_todo_manager = Mock()
        mock_status_manager = Mock()
        mock_checkpoint_manager = Mock()
        mock_logger = Mock()

        # Настраиваем моки для компонентов
        mock_quality_instance = Mock()
        mock_quality_instance.run_quality_checks = AsyncMock(return_value=[])
        mock_quality.return_value = mock_quality_instance

        mock_verification_instance = Mock()
        mock_verification_instance.run_verification_pipeline = AsyncMock(return_value=Mock())
        mock_verification.return_value = mock_verification_instance

        # Создаем ServerCore
        server_core = ServerCore(
            todo_manager=mock_todo_manager,
            status_manager=mock_status_manager,
            checkpoint_manager=mock_checkpoint_manager,
            logger=mock_logger
        )

        assert server_core is not None

        # Проверяем, что все компоненты инициализированы
        assert hasattr(server_core, 'quality_gate_manager')
        assert hasattr(server_core, 'verification_manager')
        assert hasattr(server_core, 'todo_manager')
        assert hasattr(server_core, 'status_manager')
        assert hasattr(server_core, 'checkpoint_manager')
        assert hasattr(server_core, 'logger')

    def test_task_type_enum_usage(self):
        """Проверяет использование TaskType enum"""
        # Проверяем, что можем использовать enum значения
        assert TaskType.CODE == TaskType.CODE
        assert TaskType.DOCS == TaskType.DOCS
        assert TaskType.TEST == TaskType.TEST

        # Проверяем строковые значения
        assert TaskType.CODE.value == "code"
        assert TaskType.DOCS.value == "docs"
        assert TaskType.TEST.value == "test"

    def test_service_descriptor_properties(self):
        """Проверяет свойства ServiceDescriptor"""
        class TestService:
            pass

        descriptor = ServiceDescriptor(
            service_type=TestService,
            lifetime=ServiceLifetime.SINGLETON
        )

        assert descriptor.service_type == TestService
        assert descriptor.implementation_type == TestService
        assert descriptor.lifetime == ServiceLifetime.SINGLETON
        assert descriptor.factory is None
        assert descriptor.instance is None
        assert descriptor.is_resolving == False

    def test_di_container_complex_scenario(self):
        """Проверяет сложный сценарий с DI контейнером"""
        container = DIContainer()

        class ILogger:
            def log(self, message: str) -> str:
                return f"LOG: {message}"

        class IDatabase:
            def __init__(self, logger: ILogger):
                self.logger = logger

            def connect(self) -> str:
                return self.logger.log("Connecting to database")

        class IUserService:
            def __init__(self, database: IDatabase, logger: ILogger):
                self.database = database
                self.logger = logger

            def get_user(self, user_id: int) -> str:
                db_result = self.database.connect()
                return self.logger.log(f"Getting user {user_id}: {db_result}")

        # Регистрируем сервисы
        container.register_singleton(ILogger)
        container.register_transient(IDatabase)
        container.register_transient(IUserService)

        # Разрешаем сложный сервис
        user_service = container.resolve(IUserService)

        assert user_service is not None
        assert hasattr(user_service, 'database')
        assert hasattr(user_service, 'logger')
        assert hasattr(user_service.database, 'logger')

        # Проверяем работу
        result = user_service.get_user(123)
        assert "LOG:" in result
        assert "Getting user 123:" in result