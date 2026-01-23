# Руководство по работе с типами задач

Полное руководство по использованию системы типизации задач в Code Agent.

## Обзор

Система типов задач позволяет автоматически категоризировать задачи проекта, обеспечивать их правильное распределение и проводить анализ качества проекта. Типы задач помогают в приоритизации, фильтрации и контроле качества разработки.

## Типы задач

### Основные типы

Code Agent поддерживает следующие типы задач:

| Тип | Описание | Примеры | Приоритет |
|-----|----------|---------|-----------|
| `CODE` | Разработка нового функционала, исправление багов | Добавление новых функций, исправление ошибок, реализация алгоритмов | 1 (высший) |
| `TEST` | Написание и выполнение тестов | Модульные тесты, интеграционные тесты, автоматизация тестирования | 2 |
| `REFACTOR` | Рефакторинг существующего кода | Оптимизация кода, устранение дублирования, улучшение архитектуры | 3 |
| `DOCS` | Создание и обновление документации | API документация, руководства пользователя, комментарии к коду | 4 |
| `RELEASE` | Подготовка релизов, версионирование | Создание релизов, обновление changelog, тегирование | 5 |
| `DEVOPS` | Инфраструктура, CI/CD, развертывание | Docker, Kubernetes, настройка CI/CD, мониторинг | 6 (низший) |

### Приоритеты

Типы задач имеют приоритеты от 1 (высший) до 6 (низший). Приоритеты используются для:
- Определения порядка выполнения задач
- Анализа распределения рабочей нагрузки
- Качественной оценки проекта

## Автоматическое определение типов

### Как работает автоопределение

Code Agent автоматически определяет тип задачи на основе анализа текста задачи. Система использует ключевые слова и фразы для классификации:

```python
from src.core.types import TaskType

# Примеры автоматического определения
TaskType.auto_detect("Implement user authentication")        # → CODE
TaskType.auto_detect("Write unit tests for API")             # → TEST
TaskType.auto_detect("Refactor database queries")            # → REFACTOR
TaskType.auto_detect("Update API documentation")             # → DOCS
TaskType.auto_detect("Prepare release v2.0")                  # → RELEASE
TaskType.auto_detect("Setup Docker deployment")              # → DEVOPS
```

### Правила определения

#### CODE (Разработка)
Ключевые слова: implement, add, create, develop, build, fix, bug, feature, component, module

#### TEST (Тестирование)
Ключевые слова: test, testing, pytest, unittest, integration, coverage, assert, fixture

#### REFACTOR (Рефакторинг)
Ключевые слова: refactor, optimize, clean, extract, restructure, improve, simplify

#### DOCS (Документация)
Ключевые слова: doc, document, readme, guide, tutorial, api, comment, description

#### RELEASE (Релиз)
Ключевые слова: release, version, tag, changelog, deploy, package, publish

#### DEVOPS (DevOps)
Ключевые слова: docker, kubernetes, ci/cd, pipeline, deploy, infrastructure, monitoring, config

## Работа с задачами

### Создание задач с типами

```python
from src.todo_manager import TodoManager
from src.core.types import TaskType

manager = TodoManager()

# Создание задачи с явным типом
task1 = manager.add_todo("Implement user login", task_type=TaskType.CODE)
task2 = manager.add_todo("Write API tests", task_type=TaskType.TEST)

# Создание задачи без типа (будет определен автоматически)
task3 = manager.add_todo("Update documentation")  # → DOCS
```

### Фильтрация задач по типам

```python
# Получение всех задач определенного типа
code_tasks = manager.get_tasks_by_type(TaskType.CODE)
test_tasks = manager.get_tasks_by_type(TaskType.TEST)

# Получение задач без типа
untyped_tasks = manager.get_tasks_by_type(None)
```

### Обновление типа задачи

```python
# Обновление типа по ID задачи
success = manager.update_task_type("task_123", TaskType.REFACTOR)

# Сброс типа (включение автоопределения)
success = manager.update_task_type("task_123", None)
```

## Статистика и анализ

### Получение статистики

```python
# Полная статистика по типам задач
stats = manager.get_task_type_statistics()

print(f"Всего задач: {stats['total_tasks']}")
print(f"Без типа: {stats['untyped_percentage']}%")

# Распределение по типам
for type_name, type_info in stats['types'].items():
    print(f"{type_name}: {type_info['count']} задач ({type_info['percentage']}%)")
```

### Валидация типов задач

```python
# Проверка корректности распределения типов
validation = manager.validate_task_types()

if not validation['valid']:
    print("Найдены проблемы с типами задач:")
    for issue in validation['issues']:
        print(f"- {issue['message']} ({issue['severity']})")
```

## Качество проекта (Quality Gates)

### Task Type Checker

Code Agent включает проверку качества типов задач, которая оценивает:

- Процент задач без типов (не должен превышать 30%)
- Минимальный процент типизированных задач (не менее 70%)
- Сбалансированность распределения типов

### Конфигурация проверки

```yaml
# config/config.yaml
quality_gates:
  task_type:
    enabled: true
    max_untyped_percentage: 0.3    # Максимум 30% без типов
    min_typed_percentage: 0.7      # Минимум 70% с типами
    check_distribution: true       # Проверять распределение
```

### Результаты проверки

Пример успешной проверки:
```
✅ PASSED: Типы задач корректны (Score: 0.95)
   - Всего задач: 50
   - Типизировано: 48 (96.0%)
   - Без типа: 2 (4.0%)
```

Пример проверки с предупреждением:
```
⚠️  WARNING: Найдены проблемы с типами задач (Score: 0.75)
   - Слишком много задач без типа: 35.0% (макс. 30.0%)
   - Отсутствуют типы: test, release
```

## Лучшие практики

### 1. Явное указание типов

Для критически важных задач указывайте тип явно:

```python
# Плохо
manager.add_todo("Fix critical bug in payment system")

# Хорошо
manager.add_todo("Fix critical bug in payment system", task_type=TaskType.CODE)
```

### 2. Регулярная проверка качества

Запускайте проверки качества регулярно:

```python
from src.quality.quality_gate_manager import QualityGateManager

quality_manager = QualityGateManager()
result = await quality_manager.run_quality_checks(context={'todo_manager': manager})

if result.status != QualityStatus.PASSED:
    print("Требуется внимание к типам задач!")
```

### 3. Сбалансированное распределение

Следите за распределением типов задач:
- Не более 70% задач одного типа
- Минимум 1% для каждого типа (при >10 задачах)
- Сбалансированная нагрузка по типам

### 4. Автоопределение vs явное указание

- **Автоопределение**: подходит для простых задач с очевидными ключевыми словами
- **Явное указание**: необходимо для сложных задач или когда автоопределение может ошибиться

## Расширение системы типов

### Добавление новых типов

Для добавления нового типа задач:

1. Обновите enum `TaskType` в `src/core/types.py`
2. Добавьте ключевые слова для автоопределения
3. Обновите приоритет
4. Добавьте тесты

```python
class TaskType(Enum):
    # Существующие типы...
    DESIGN = "design"  # Новый тип для дизайнерских задач
```

### Кастомные правила определения

Для сложных случаев можно расширить логику автоопределения в методе `auto_detect()` класса `TaskType`.

## Интеграция с другими компонентами

### Система логирования

Типы задач интегрированы с системой логирования:

```
2026-01-23 10:30:15 INFO TaskType.CODE: Начат анализ задачи "Implement feature"
2026-01-23 10:30:16 INFO TaskType.DOCS: Задача автоматически определена как документация
```

### API сервера

Типы задач доступны через REST API:

```bash
# Получение статистики
GET /api/tasks/types/statistics

# Получение задач по типу
GET /api/tasks?type=code

# Обновление типа задачи
PUT /api/tasks/{task_id}/type
```

## Устранение неполадок

### Проблема: Задача определена неправильно

**Решение:**
```python
# Явно укажите правильный тип
manager.update_task_type(task_id, TaskType.CORRECT_TYPE)
```

### Проблема: Слишком много задач без типов

**Решение:**
```python
# Проверьте статистику
stats = manager.get_task_type_statistics()
print(f"Без типов: {stats['untyped_percentage']}%")

# Добавьте типы для нетипизированных задач
for task in manager.get_all_tasks():
    if not task.effective_task_type:
        manager.update_task_type(task.id, TaskType.auto_detect(task.text))
```

### Проблема: Quality Gate fails

**Решение:**
1. Проверьте конфигурацию quality gates
2. Убедитесь, что процент типизированных задач >= 70%
3. Проверьте распределение типов на сбалансированность

## Заключение

Система типов задач является важной частью Code Agent, обеспечивая:
- Автоматическую категоризацию задач
- Качественный контроль проекта
- Анализ распределения нагрузки
- Улучшенную организацию работы

Следуйте рекомендациям этого руководства для эффективного использования системы типов задач.