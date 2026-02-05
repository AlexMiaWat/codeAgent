# Интерфейсы системы

## Обзор

Система интерфейсов Code Agent построена на принципах SOLID и обеспечивает слабую связанность компонентов через dependency injection. Все интерфейсы находятся в директории `src/core/interfaces/` и наследуются от базового интерфейса `IManager`.

## Архитектура интерфейсов

### IManager - Базовый интерфейс

```python
class IManager(ABC):
    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Инициализация с конфигурацией"""

    @abstractmethod
    def is_healthy(self) -> bool:
        """Проверка здоровья компонента"""

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Получение статуса компонента"""

    @abstractmethod
    def dispose(self) -> None:
        """Очистка ресурсов"""
```

**Назначение:** Обеспечивает стандартный жизненный цикл для всех менеджеров системы.

### ITodoManager - Управление задачами

**Основные методы:**
- `load_todos()` - Загрузка задач из файла
- `get_pending_tasks()` - Получение незавершенных задач
- `get_all_tasks()` - Получение всех задач
- `mark_task_done()` - Отметка задачи как выполненной
- `get_task_hierarchy()` - Получение иерархии задач
- `save_todos()` - Сохранение состояния задач

**Особенности:**
- Поддерживает различные форматы файлов задач
- Обеспечивает иерархическую структуру задач
- Предоставляет методы для работы с состоянием задач

### IStatusManager - Управление статусами

**Основные методы:**
- `update_task_status()` - Обновление статуса задачи
- `get_task_status()` - Получение статуса задачи
- `get_all_statuses()` - Получение всех статусов
- `clear_completed_statuses()` - Очистка завершенных статусов

**Особенности:**
- Отслеживает прогресс выполнения задач
- Поддерживает различные состояния (pending, in_progress, completed, failed)
- Интегрируется с системой checkpoint

### ICheckpointManager - Управление контрольными точками

**Основные методы:**
- `create_checkpoint()` - Создание контрольной точки
- `load_checkpoint()` - Загрузка контрольной точки
- `list_checkpoints()` - Список доступных контрольных точек
- `restore_from_checkpoint()` - Восстановление из контрольной точки

**Особенности:**
- Обеспечивает отказоустойчивость системы
- Позволяет откатывать изменения
- Интегрируется с git для отслеживания изменений

### ILogger - Логирование операций

**Основные методы:**
- `log_info()` - Информационные сообщения

### ITaskProcessor - Обработка задач
Интерфейс для управления полным жизненным циклом обработки одной задачи, включая определение типа, форматирование инструкций для LLM, выполнение и верификацию.

**Основные методы:**
- `process_task(todo_item, task_number, total_tasks)`: Обрабатывает одну задачу.
- `check_task_usefulness(todo_item)`: Проверяет полезность задачи.
- `check_todo_matches_plan(task_id, todo_item)`: Проверяет соответствие TODO плану.
- `verify_real_work_done(task_id, todo_item, result_content)`: Проверяет выполнение реальной работы.
- `determine_task_type(todo_item)`: Определяет тип задачи.
- `get_instruction_template(task_type, instruction_id)`: Получает шаблон инструкции.
- `get_all_instruction_templates(task_type)`: Получает все шаблоны инструкций.
- `format_instruction(template, todo_item, task_id, instruction_num)`: Форматирует инструкцию.
- `wait_for_result_file(task_id, wait_for_file, control_phrase, timeout)`: Ожидает файл результата от Cursor.
- `execute_task_via_llm(todo_item, task_type, task_logger)`: Выполняет задачу через LLM.

**Особенности:**
- Центральный компонент для выполнения задач, использующий LLM.
- Интегрируется с системой логирования и файловой системой.
- Поддерживает последовательное выполнение инструкций.

### IRevisionProcessor - Обработка ревизий
Интерфейс для выполнения ревизий проекта, например, для анализа текущего состояния, корректировки плана или обнаружения проблем.

**Основные методы:**
- `execute_revision()`: Выполняет ревизию проекта.

**Особенности:**
- Используется для периодической или событийно-ориентированной проверки состояния проекта.
- Может инициировать генерацию новых TODO или корректировку существующих.

### ITodoGenerator - Генерация TODO
Интерфейс для автоматической генерации нового списка задач, когда текущий список пуст или требуется его обновление.

**Основные методы:**
- `generate_new_todo_list()`: Генерирует новый TODO лист.

**Особенности:**
- Обеспечивает непрерывность работы агента, автоматически создавая новые задачи.
- Использует LLM для формирования релевантных задач на основе текущего состояния проекта.
- `log_warning()` - Предупреждения
- `log_error()` - Ошибки
- `log_debug()` - Отладочная информация
- `log_task_start()` - Начало выполнения задачи
- `log_task_end()` - Завершение выполнения задачи
- `log_server_event()` - События сервера

**Особенности:**
- Структурированное логирование с дополнительными данными
- Поддержка разных уровней логирования
- Специализированные методы для задач и сервера

### IServer - Управление сервером

**Основные методы:**
- `start()` - Запуск сервера
- `stop()` - Остановка сервера
- `restart()` - Перезапуск сервера
- `is_running()` - Проверка состояния сервера
- `get_server_status()` - Получение статуса сервера
- `execute_task()` - Выполнение задачи
- `get_pending_tasks()` - Получение ожидающих задач
- `get_active_tasks()` - Получение активных задач
- `get_metrics()` - Получение метрик производительности
- `reload_configuration()` - Перезагрузка конфигурации
- `get_component_status()` - Получение статуса компонента

**Особенности:**
- Управление жизненным циклом сервера
- Координация компонентов системы
- Мониторинг состояния и метрик
- Управление конфигурацией без перезапуска

### IAgent - Управление агентами CrewAI

**Основные методы:**
- `create_agent()` - Создание агента
- `get_agent()` - Получение экземпляра агента
- `remove_agent()` - Удаление агента
- `get_available_agents()` - Получение доступных типов агентов
- `get_active_agents()` - Получение активных агентов
- `configure_agent()` - Конфигурация агента
- `execute_with_agent()` - Выполнение задачи через агента
- `get_agent_status()` - Получение статуса агента
- `validate_agent_config()` - Валидация конфигурации агента
- `get_agent_types_info()` - Получение информации о типах агентов

**Особенности:**
- Управление жизненным циклом агентов CrewAI
- Поддержка разных типов агентов (executor, smart, custom)
- Мониторинг и конфигурация агентов
- Валидация конфигураций и статусов

### ITaskManager - Управление выполнением задач

**Основные методы:**
- `initialize_task_execution()` - Инициализация выполнения задачи
- `execute_task_step()` - Выполнение шага задачи
- `monitor_task_progress()` - Мониторинг прогресса выполнения
- `handle_task_failure()` - Обработка ошибок выполнения
- `finalize_task_execution()` - Финализация выполнения задачи
- `cancel_task_execution()` - Отмена выполнения задачи
- `get_execution_status()` - Получение статуса выполнения
- `get_active_executions()` - Получение активных выполнений
- `get_execution_history()` - Получение истории выполнений
- `retry_execution()` - Повторное выполнение задачи
- `get_execution_metrics()` - Получение метрик выполнения
- `validate_execution_requirements()` - Валидация требований выполнения

**Особенности:**
- Управление жизненным циклом выполнения задач
- Мониторинг прогресса и обработка ошибок
- Поддержка отмены и повторного выполнения
- Метрики производительности и история выполнений
- Отличается от ITodoManager фокусом на исполнении, а не на управлении списком задач

## Принципы проектирования

### Single Responsibility Principle (SRP)
Каждый интерфейс отвечает только за одну область функциональности:
- `ITodoManager` - только управление задачами
- `IStatusManager` - только управление статусами
- `ILogger` - только логирование

### Interface Segregation Principle (ISP)
Интерфейсы разделены по ответственности, клиенты не зависят от методов, которые не используют.

### Dependency Inversion Principle (DIP)
Код зависит от абстракций (интерфейсов), а не от конкретных реализаций.

## Реализации интерфейсов

### TodoManager
Расположение: `src/todo_manager.py`
- Реализует `ITodoManager` и `IManager`
- Работа с файлами `todo/CURRENT.md`
- Поддержка Markdown формата задач

### StatusManager
Расположение: `src/status_manager.py`
- Реализует `IStatusManager` и `IManager`
- Управление статусами выполнения
- Интеграция с checkpoint системой

### CheckpointManager
Расположение: `src/checkpoint_manager.py`
- Реализует `ICheckpointManager` и `IManager`
- Создание и восстановление контрольных точек
- Работа с JSON файлами состояния

### ServerLogger
Расположение: `src/task_logger.py`
- Реализует `ILogger` и `IManager`
- Цветное логирование в консоль
- Поддержка разных типов сообщений

### MockServer
Расположение: `src/core/mock_implementations.py`
- Реализует `IServer` и `IManager`
- Mock-реализация для тестирования DI контейнера
- Базовая функциональность управления сервером

### MockAgentManager
Расположение: `src/core/mock_implementations.py`
- Реализует `IAgent` и `IManager`
- Mock-реализация для тестирования DI контейнера
- Управление mock-агентами для тестирования

### MockTaskManager
Расположение: `src/core/mock_implementations.py`
- Реализует `ITaskManager` и `IManager`
- Mock-реализация для тестирования DI контейнера
- Управление mock-задачами с состояниями выполнения

## Использование в Dependency Injection

### Регистрация в контейнере

```python
from src.core.di_container import create_default_container
from src.core.interfaces import ITodoManager, IStatusManager, ICheckpointManager, ILogger

# Создание контейнера
container = create_default_container(project_dir, config, status_file)

# Регистрация реализаций
container.register_instance(ITodoManager, TodoManager(project_dir))
container.register_instance(IStatusManager, StatusManager(project_dir))
container.register_instance(ICheckpointManager, CheckpointManager(project_dir, checkpoint_file))
container.register_instance(ILogger, ServerLogger())
```

### Разрешение зависимостей

```python
class ServerCore:
    def __init__(
        self,
        todo_manager: ITodoManager,
        status_manager: IStatusManager,
        checkpoint_manager: ICheckpointManager,
        logger: ILogger
    ):
        self.todo_manager = todo_manager
        self.status_manager = status_manager
        self.checkpoint_manager = checkpoint_manager
        self.logger = logger
```

## Тестирование интерфейсов

Для каждого интерфейса предусмотрены тесты:

- **Интеграционные тесты** (`test/test_di_integration.py`): Проверка взаимодействия компонентов
- **Smoke тесты** (`test/test_di_smoke.py`): Базовая функциональность
- **SOLID тесты** (`test/test_di_solid.py`): Соблюдение принципов SOLID
- **Статические тесты** (`test/test_di_static.py`): Корректность конфигурации
- **Новые интерфейсы тесты** (`test/test_interfaces_new.py`): Комплексное тестирование IServer, IAgent, ITaskManager
- **Расширенные статические тесты**: Проверка TaskExecutionState enum и новых интерфейсов

## Преимущества интерфейсной архитектуры

### 1. Тестируемость
Легкая замена реализаций на mock-объекты для unit-тестирования.

### 2. Гибкость
Возможность замены компонентов без изменения кода, использующего их.

### 3. Поддерживаемость
Четкое разделение ответственности упрощает сопровождение и развитие.

### 4. Расширяемость
Новые реализации интерфейсов могут быть добавлены без изменения существующего кода.

## TaskExecutionState - Состояния выполнения задач

Перечисление состояний выполнения задач в `ITaskManager`:

- `PENDING` - Задача ожидает выполнения
- `INITIALIZING` - Инициализация выполнения
- `EXECUTING` - Активное выполнение задачи
- `MONITORING` - Мониторинг выполнения
- `COMPLETED` - Успешное завершение
- `FAILED` - Ошибка выполнения
- `CANCELLED` - Отмена выполнения

## Будущие расширения

- Дальнейшая декомпозиция и специализация интерфейсов по мере роста функциональности.
- Добавление метрик производительности для каждого интерфейса.
- Разработка плагинов и расширений на основе существующей интерфейсной архитектуры.