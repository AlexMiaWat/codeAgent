# Dependency Injection Container

## Обзор

Dependency Injection (DI) контейнер Code Agent представляет собой мощную систему управления зависимостями, построенную на принципах SOLID и обеспечивающую слабую связанность компонентов.

## Основные концепции

### Service Lifetime

Контейнер поддерживает три типа времени жизни сервисов:

- **SINGLETON**: Одна экземпляр на все приложение. Экономит ресурсы для тяжелых объектов.
- **TRANSIENT**: Новый экземпляр при каждом запросе. Гарантирует изоляцию.
- **SCOPED**: Один экземпляр на область видимости (пока не реализован).

### Service Descriptor

Каждый зарегистрированный сервис описывается дескриптором, содержащим:
- Тип сервиса (интерфейс)
- Тип реализации (конкретный класс)
- Фабричную функцию (опционально)
- Время жизни
- Предварительно созданный экземпляр

## API контейнера

### Регистрация сервисов

```python
# Регистрация с автоматическим разрешением зависимостей
container.register(IService, ServiceImpl)

# Регистрация с фабричной функцией
container.register(IService, factory=lambda: ServiceImpl())

# Регистрация предварительно созданного экземпляра
container.register_instance(IService, instance)
```

### Разрешение зависимостей

```python
# Получение экземпляра сервиса
service = container.resolve(IService)

# Проверка наличия регистрации
if container.is_registered(IService):
    service = container.resolve(IService)
```

### Управление жизненным циклом

```python
# Создание скоупа для ограничения времени жизни
with container.create_scope() as scope:
    service = scope.resolve(IService)  # Новый экземпляр в скоупе
```

## Фабрика контейнера

Система предоставляет фабричную функцию для создания настроенного контейнера:

```python
from src.core.di_container import create_default_container

# Создание контейнера с базовой конфигурацией
container = create_default_container(project_dir, config_data, status_file)

# Регистрация основных менеджеров
container.register_instance(ITodoManager, todo_manager)
container.register_instance(IStatusManager, status_manager)
container.register_instance(ICheckpointManager, checkpoint_manager)
container.register_instance(ILogger, logger)
```

## Преимущества DI

### 1. Разделение ответственности
Каждый компонент отвечает только за свою функциональность, зависимости инжектируются извне.

### 2. Тестируемость
Легкая замена зависимостей на mock-объекты в тестах.

### 3. Гибкость конфигурации
Возможность замены реализаций без изменения кода.

### 4. Управление жизненным циклом
Централизованное управление созданием и уничтожением объектов.

## Использование в Code Agent

### Инициализация в ServerCore

```python
class ServerCore:
    def __init__(
        self,
        todo_manager: ITodoManager,
        checkpoint_manager: ICheckpointManager,
        status_manager: IStatusManager,
        logger: ILogger
    ):
        self.todo_manager = todo_manager
        self.checkpoint_manager = checkpoint_manager
        self.status_manager = status_manager
        self.logger = logger
```

### Регистрация в основном сервере

```python
# В CodeAgentServer.__init__
self.di_container = create_default_container(self.project_dir, self.config.config_data, self.status_file)

# Регистрация существующих менеджеров
self.di_container.register_instance(ITodoManager, self.todo_manager)
self.di_container.register_instance(IStatusManager, self.status_manager)
self.di_container.register_instance(ICheckpointManager, self.checkpoint_manager)
self.di_container.register_instance(ILogger, self.server_logger)
```

## Интерфейсы системы

### Базовые интерфейсы

- `IManager`: Базовый интерфейс для всех менеджеров
- `ITodoManager`: Управление задачами проекта
- `IStatusManager`: Управление статусами выполнения
- `ICheckpointManager`: Управление контрольными точками
- `ILogger`: Логирование операций

### Принципы проектирования

Система следует принципам SOLID:

1. **Single Responsibility**: Каждый интерфейс отвечает за одну область ответственности
2. **Open/Closed**: Интерфейсы открыты для расширения через новые реализации
3. **Liskov Substitution**: Любая реализация интерфейса может заменить другую
4. **Interface Segregation**: Интерфейсы разделены по функциональности
5. **Dependency Inversion**: Код зависит от абстракций, а не от конкретных реализаций

## Тестирование

Для тестирования DI предусмотрены специальные интеграционные тесты:

- `test/test_di_integration.py`: Тесты интеграции компонентов
- `test/test_di_smoke.py`: Базовые smoke-тесты
- `test/test_di_solid.py`: Тесты соблюдения SOLID принципов
- `test/test_di_static.py`: Статические тесты конфигурации

## Производительность

DI контейнер оптимизирован для высокой производительности:

- Ленивая инициализация singleton-сервисов
- Кэширование разрешенных зависимостей
- Минимальные накладные расходы на разрешение
- Поддержка асинхронных фабрик (в будущем)

## Будущие улучшения

- Реализация SCOPED lifetime для веб-запросов
- Асинхронная инициализация тяжелых сервисов
- Интеграция с внешними DI фреймворками (например, dependency-injector)
- Метрики использования и мониторинг производительности