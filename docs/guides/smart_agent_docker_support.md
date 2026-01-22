# Smart Agent: Docker и LLM интеграция

## Обзор

Smart Agent поддерживает два уровня гибкости:

1. **Docker поддержка**: Опциональное использование Docker для безопасного выполнения кода
2. **LLM интеграция**: Многоуровневый fallback механизм для работы с языковыми моделями

Если Docker или LLM недоступны, агент автоматически переключается в соответствующие fallback режимы, сохраняя функциональность через инструменты обучения и анализа.

## Режимы работы

### 1. Полный режим (с Docker)

**Требования:**
- Docker установлен и запущен
- Пользователь имеет права на выполнение Docker команд
- Установлен `crewai_tools` с `CodeInterpreterTool`

**Возможности:**
- Безопасное выполнение кода в изолированных контейнерах
- CodeInterpreterTool для анализа и выполнения кода
- Полная функциональность code execution

### 2. Fallback режим (без Docker)

**Когда активируется:**
- Docker не установлен
- Docker daemon не запущен
- Нет прав доступа к Docker
- Ошибки импорта CodeInterpreterTool
- Явное отключение через параметр `use_docker=False`

**Возможности:**
- Анализ кода и документации
- Обучение на предыдущих задачах
- Рекомендации на основе опыта
- Анализ структуры проекта
- Поиск зависимостей и связей

## Конфигурация

### Параметры create_smart_agent()

```python
from src.agents import create_smart_agent
from pathlib import Path

# Полная конфигурация с оптимизацией производительности
agent = create_smart_agent(
    project_dir=Path("my_project"),
    # Docker настройки
    use_docker=None,  # Автоопределение доступности Docker
    # LLM настройки
    use_llm_manager=True,  # Включить LLM интеграцию
    llm_config_path="config/llm_settings.yaml",
    # Параметры производительности (новые)
    max_iter=25,  # Максимальное количество итераций (увеличено для сложных задач)
    memory=100,   # Память для хранения контекста
    verbose=True, # Подробное логирование (можно отключить в production)
    # Опыт и обучение
    experience_dir="smart_experience",  # Директория для хранения опыта
    max_experience_tasks=1000,  # Максимальное количество задач в опыте
    # Режим работы
    allow_code_execution=True  # Разрешить выполнение кода
)

# Минимальная конфигурация
agent = create_smart_agent(project_dir=Path("my_project"))

# Принудительное отключение Docker
agent = create_smart_agent(
    project_dir=Path("my_project"),
    use_docker=False,  # Всегда fallback режим
    use_llm=False      # Отключить LLM интеграцию
)
```

### Переменные окружения

- `DOCKER_AVAILABLE` - принудительно установить статус Docker (true/false)

## Docker Utils

Smart Agent включает утилиты для работы с Docker:

### DockerChecker

```python
from src.tools import DockerChecker

# Проверка доступности Docker
available = DockerChecker.is_docker_available()

# Получение версии Docker
version = DockerChecker.get_docker_version()

# Проверка прав доступа
perms_ok, perms_msg = DockerChecker.check_docker_permissions()

# Получение списка запущенных контейнеров
containers = DockerChecker.get_running_containers()

# Проверка конкретного контейнера
is_running = DockerChecker.is_container_running("cursor-agent-life")
```

### DockerManager

```python
from src.tools import DockerManager

# Создание менеджера
manager = DockerManager(
    image_name="cursor-agent:latest",
    container_name="cursor-agent-life"
)

# Запуск контейнера
success, message = manager.start_container(workspace_path="/path/to/project")

# Остановка контейнера
success, message = manager.stop_container()

# Выполнение команды в контейнере
success, stdout, stderr = manager.execute_command("python --version")
```

## Обработка ошибок

### Логирование

Smart Agent ведет подробное логирование процесса определения Docker:

```
INFO: Docker auto-detection: available
INFO: CodeInterpreterTool added successfully (Docker available)
```

```
INFO: Docker auto-detection: not available
INFO: CodeInterpreterTool skipped (Docker not available - fallback mode)
```

```
WARNING: Docker forced but not available - falling back to no code execution
ERROR: Docker check failed: [error message]
```

### Fallback поведение

При недоступности Docker:

1. **CodeInterpreterTool не добавляется** в список инструментов
2. **allow_code_execution устанавливается в False** для агента
3. **Backstory обновляется** для отражения ограничений
4. **Агент продолжает работу** с LearningTool и ContextAnalyzerTool

## Тестирование

### Тесты без Docker

```bash
# Запуск тестов в fallback режиме
pytest test/test_smart_agent_integration.py::TestSmartAgentIntegration::test_smart_agent_docker_fallback_mode -v

# Тест автоопределения
pytest test/test_smart_agent_integration.py::TestSmartAgentIntegration::test_smart_agent_docker_auto_detection_fallback -v

# Тест принудительного режима
pytest test/test_smart_agent_integration.py::TestSmartAgentIntegration::test_smart_agent_docker_forced_fallback_warning -v
```

### Моки для тестирования

```python
from unittest.mock import patch

# Мокаем недоступность Docker
with patch('src.tools.docker_utils.DockerChecker.is_docker_available', return_value=False):
    agent = create_smart_agent(project_dir=Path("."), use_docker=None)
    # Агент будет в fallback режиме
```

## Советы по использованию

### Рекомендации

1. **Используйте автоопределение** (`use_docker=None`) для автоматического выбора режима
2. **В CI/CD средах** явно отключайте Docker если он не нужен
3. **Для разработки** с Docker получаете максимальную функциональность
4. **Для анализа кода** fallback режим полностью функционален

### Производительность

- **С Docker**: +CodeInterpreterTool, но требуется время на запуск контейнеров
- **Без Docker**: Быстрее запуск, меньше зависимостей, но без code execution

### Безопасность

- **С Docker**: Код выполняется в изолированных контейнерах
- **Без Docker**: Нет рисков выполнения кода, только анализ

## Troubleshooting

### Docker не обнаруживается

1. Проверьте установку: `docker --version`
2. Проверьте запуск daemon: `docker info`
3. Проверьте права: `docker ps`

### CodeInterpreterTool не работает

1. Установите crewai_tools: `pip install crewai[tools]`
2. Проверьте Docker доступность
3. Проверьте логи агента

### Fallback режим не активируется

1. Проверьте логи на ошибки Docker проверки
2. Явно установите `use_docker=False` для тестирования
3. Проверьте, что LearningTool и ContextAnalyzerTool работают

## Архитектура

```
SmartAgent Creation Flow:
1. Проверка Docker доступности
2. Определение режима (full/fallback)
3. Добавление инструментов:
   - Full: CodeInterpreterTool + LearningTool + ContextAnalyzerTool
   - Fallback: LearningTool + ContextAnalyzerTool
4. Настройка backstory в зависимости от режима
5. Создание CrewAI агента
```

## Расширение

Для добавления новых инструментов с поддержкой Docker:

```python
# В create_smart_agent()
if docker_available:
    try:
        tools.append(DockerDependentTool())
    except Exception as e:
        logger.warning(f"Docker tool failed: {e}")
else:
    tools.append(FallbackTool())
```

## Оптимизация конфигурации (2026-01-22)

### Параметры производительности

Последние обновления включают оптимизацию для работы с современными LLM:

| Параметр | Новое значение | Предыдущее | Эффект |
|----------|----------------|------------|--------|
| `max_iter` | 25 | 15 | Лучше справляется со сложными задачами |
| `memory` | 100 | 50 | Увеличивает контекст для длинных сессий |
| `max_experience_tasks` | 200 | 100 | Больше опыта для обучения |
| `verbose` | Оптимизирован | - | Можно отключать в production |

### LLM стратегия best_of_two

Обновлена стратегия выбора моделей:

```yaml
# config/llm_settings.yaml
llm:
  strategy: best_of_two
  model_roles:
    primary:
    - microsoft/wizardlm-2-8x22b  # Мощная модель для сложных задач
    duplicate: []
    reserve:
    - microsoft/phi-3-mini-128k-instruct  # Быстрая модель среднего уровня
    fallback:
    - meta-llama/llama-3.2-3b-instruct   # Стабильная модель для fallback
    - meta-llama/llama-3.2-1b-instruct   # Легкая модель для простых задач
  parallel:
    enabled: true
    models:
    - microsoft/wizardlm-2-8x22b
    - microsoft/phi-3-mini-128k-instruct
    evaluator_model: microsoft/wizardlm-2-8x22b
    selection_criteria:
    - quality
    - relevance
    - completeness
    - efficiency
```

## Улучшения инструментов

### ContextAnalyzerTool

Добавлена поддержка Unicode и улучшенный поиск:

```python
# Новая функция нормализации Unicode текста
def normalize_unicode_text(text: str) -> str:
    """
    Нормализует Unicode текст для улучшения поиска и сравнения.
    - Приводит к нижнему регистру
    - Удаляет диакритические знаки
    - Нормализует Unicode (NFD)
    """
    normalized = unicodedata.normalize('NFD', text)
    normalized = ''.join(char for char in normalized if unicodedata.category(char) != 'Mn')
    return normalized.lower()
```

**Преимущества:**
- Лучший поиск по не-ASCII тексту
- Case-insensitive поиск
- Поддержка различных языков и кодировок

## LLM интеграция

Smart Agent поддерживает многоуровневый fallback механизм для работы с языковыми моделями:

### Уровни LLM интеграции

#### 1. Продвинутые модели через OpenRouter

**Требования:**
- Наличие `OPENROUTER_API_KEY` в переменных окружения
- Конфигурация в `config/llm_settings.yaml`

**Возможности:**
- Доступ к продвинутым моделям (Grok, Claude, GPT-4 и др.)
- Высокое качество ответов для сложных задач

#### 2. LLMManager с автоматическим fallback

**Требования:**
- Конфигурация моделей в `config/llm_settings.yaml`
- Доступ к API ключам (OpenAI, OpenRouter, etc.)

**Возможности:**
- Автоматический выбор самой быстрой модели
- Fallback на резервные модели при ошибках
- Поддержка ролей моделей (primary, duplicate, reserve, fallback)

#### 3. Graceful degradation (tool-only режим)

**Когда активируется:**
- Отсутствие API ключей для внешних сервисов
- Ошибки подключения к LLM сервисам
- Явное отключение LLM через конфигурацию

**Возможности:**
- Работа только с инструментами (без LLM)
- LearningTool для обучения на опыте
- ContextAnalyzerTool для анализа проекта
- Docker-based code execution (если доступен)

### Конфигурация LLM

#### Параметры create_smart_agent()

```python
from src.agents import create_smart_agent
from pathlib import Path

# Полный режим с LLM (рекомендуется)
agent = create_smart_agent(
    project_dir=Path("my_project"),
    use_llm_manager=True,  # Использовать LLMManager
    llm_config_path="config/llm_settings.yaml"
)

# Tool-only режим (без LLM)
agent = create_smart_agent(
    project_dir=Path("my_project"),
    use_llm_manager=False  # Отключить LLM, работать только с инструментами
)
```

#### Переменные окружения

- `OPENROUTER_API_KEY` - Ключ для доступа к OpenRouter API
- `OPENAI_API_KEY` - Ключ для доступа к OpenAI API
- Другие ключи согласно конфигурации в `llm_settings.yaml`

### Архитектура LLM интеграции

```
SmartAgent LLM Flow:
1. Попытка использовать OpenRouter (если есть OPENROUTER_API_KEY)
   ├── Успех: Продвинутые модели через OpenRouter
   └── Неудача: Переход к уровню 2
2. Попытка использовать LLMManager (если use_llm_manager=True)
   ├── Успех: Автоматический выбор модели с fallback
   └── Неудача: Переход к уровню 3
3. Graceful degradation: Tool-only режим
   └── Работа с LearningTool + ContextAnalyzerTool + Docker (опционально)
```

### Тестирование LLM интеграции

#### Тесты с LLM

```bash
# Все Smart Agent тесты (рекомендуется запускать отдельно от unified runner)
pytest test/test_smart_agent*.py -v

# Интеграционные тесты структуры и методов
pytest test/test_smart_agent_integration.py -v

# Дымовые тесты базовой функциональности
pytest test/test_smart_agent_smoke.py -v

# Статические тесты импортов и классов
pytest test/test_smart_agent_static.py -v

# Основные тесты Smart Agent с новыми параметрами
pytest test/test_smart_agent.py::test_smart_agent_creation -v
pytest test/test_smart_agent.py::test_smart_agent_with_custom_params -v
```

#### Моки для тестирования

```python
from unittest.mock import patch

# Мокаем отсутствие API ключей
with patch.dict(os.environ, {}, clear=True):
    agent = create_smart_agent(project_dir=Path("."), use_llm_manager=True)
    # Агент будет в tool-only режиме

# Мокаем успешное подключение к LLM
with patch('src.llm.crewai_llm_wrapper.create_llm_for_crewai') as mock_llm:
    mock_llm.return_value = MockLLMWrapper()
    agent = create_smart_agent(project_dir=Path("."), use_llm_manager=True)
    # Агент будет использовать LLM
```

### Новые провайдеры LLM

Добавлена поддержка дополнительных провайдеров:

- **Anthropic Claude-3.5-sonnet**: Высококачественные ответы для сложных задач
- **OpenAI GPT-4o/GPT-4o-mini**: Быстрые и точные модели
- **Microsoft WizardLM-2-8x22b**: Мощная модель для параллельной обработки
- **Microsoft Phi-3-mini-128k**: Быстрая модель среднего уровня

### Производительность и выбор режима

| Режим | Производительность | Качество ответов | Зависимости | Новые возможности |
|-------|-------------------|------------------|-------------|-------------------|
| OpenRouter + Новые модели | Высокая | Максимальное | OPENROUTER_API_KEY | WizardLM, Claude-3.5, GPT-4o |
| LLMManager с best_of_two | Средняя | Высокое + Стабильность | API ключи в конфиге | Параллельная оценка, критерии качества |
| Tool-only с Unicode | Максимальная | Среднее (улучшенные инструменты) | Нет внешних зависимостей | Unicode поиск, больше опыта |

### Советы по LLM интеграции

1. **Для production**: Используйте OpenRouter для максимального качества
2. **Для разработки**: LLMManager с fallback обеспечивает надежность
3. **Для CI/CD**: Tool-only режим гарантирует стабильность без внешних зависимостей
4. **Для анализа кода**: Все режимы полностью функциональны

### Troubleshooting LLM

#### Агент не использует LLM

1. Проверьте наличие API ключей: `echo $OPENROUTER_API_KEY`
2. Проверьте конфигурацию: `cat config/llm_settings.yaml`
3. Проверьте логи на ошибки подключения
4. Убедитесь, что `use_llm_manager=True`

#### Низкое качество ответов

1. Проверьте доступность моделей в OpenRouter
2. Обновите конфигурацию моделей в `llm_settings.yaml`
3. Проверьте логи на fallback между моделями

#### Tool-only режим не активируется

1. Убедитесь, что нет API ключей в окружении
2. Проверьте логи на graceful degradation
3. Убедитесь, что инструменты работают корректно