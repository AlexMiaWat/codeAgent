# Справочник по конфигурации Code Agent

## Обзор

Code Agent использует модульную систему конфигурации с разделением настроек по файлам YAML. Все конфигурационные файлы находятся в директории `config/`.

## Структура конфигурационных файлов

```
config/
├── config.yaml           # Основные настройки агента и сервера
├── agents.yaml           # Определения агентов CrewAI
├── llm_settings.yaml     # Настройки языковых моделей
├── logging.yaml          # Конфигурация логирования
└── test_config.yaml      # Настройки тестирования
```

## 1. config.yaml - Основные настройки

### Проектные настройки

```yaml
project:
  base_dir: ${PROJECT_DIR}          # Базовая директория проекта
  docs_dir: docs                    # Директория документации
  status_file: codeAgentProjectStatus.md  # Файл статусов
  todo_format: md                   # Формат todo-листа (txt, yaml, md)
```

**Переменные окружения:**
- `PROJECT_DIR` - путь к целевому проекту (обязательно)

### Настройки агента

```yaml
agent:
  role: "Project Executor Agent"    # Роль агента
  goal: "Execute todo items..."     # Цель агента
  backstory: |                      # История агента
    You are an automated code agent...
  allow_code_execution: true        # Разрешить выполнение кода
  verbose: true                     # Подробный вывод
  tools:                            # Используемые инструменты
    - FileReadTool
    - FileWriteTool
```

### Настройки сервера

```yaml
server:
  check_interval: 60                # Интервал проверки задач (сек)
  max_iterations: null              # Максимум итераций (null = бесконечно)
  task_delay: 5                     # Задержка между задачами (сек)

  http_enabled: true                # Включить HTTP сервер
  http_port: 3456                   # Порт HTTP сервера

  auto_reload: true                 # Автоперезапуск
  reload_on_py_changes: true        # Перезапуск при изменении .py
  max_restarts: 3                   # Максимум перезапусков

  auto_todo_generation:             # Автогенерация TODO
    enabled: true
    max_generations_per_session: 5
    output_dir: "todo"
    session_tracker_file: ".codeagent_sessions.json"

  checkpoint:                       # Система checkpoint
    enabled: true
    checkpoint_file: ".codeagent_checkpoint.json"
    max_task_attempts: 3
    keep_completed_tasks: 100
```

### Настройки документации

```yaml
docs:
  supported_extensions: [".md", ".txt", ".rst"]  # Поддерживаемые расширения
  max_file_size: 1000000         # Максимальный размер файла
  results_dir: docs/results      # Директория результатов
  reviews_dir: docs/reviews      # Директория ревью
```

### Настройки логирования

```yaml
logging:
  level: INFO                     # Уровень логирования
  format: "%(asctime)s..."        # Формат сообщений
  file: logs/codeagent.log        # Файл логов
  console: true                   # Вывод в консоль
  color: true                     # Цветной вывод
```

### Smart Agent настройки

```yaml
smart_agent:
  enabled: true                   # Включить Smart Agent
  experience_dir: "smart_experience"  # Директория опыта
  max_experience_tasks: 200       # Максимум задач в опыте

  # Параметры производительности
  max_iter: 25                    # Максимум итераций (увеличено)
  memory: 100                     # Память для контекста (увеличена)
  verbose: true                   # Подробный вывод (оптимизирован)
```

### Настройки Cursor интеграции

```yaml
cursor:
  interface_type: "cli"           # Тип интерфейса (cli, file, api, screenshot)

  cli:                            # Настройки CLI интерфейса
    cli_path: "docker-compose-agent"
    timeout: 1000
    headless: true
    model: "auto"
    fallback_models: ["grok"]
    resilience:                   # Отказоустойчивость
      enable_fallback: true
      max_fallback_attempts: 3
      fallback_retry_delay: 2
      fallback_on_errors: ["billing_error", "timeout"]

  permissions:                    # Разрешения
    enabled: true
    config_file: ".cursor/cli-config.json"
    mcp_approvals_file: ".cursor/mcp-approvals.json"
    allow_shell: ["git", "npm", "python", "pytest"]
    deny_shell: ["rm -rf /"]
    allow_read: ["src/**", "docs/**", "test/**"]
    allow_write: ["src/**", "docs/**", "test/**"]
    deny_write: ["**/*.env", "**/credentials*"]

  screenshot:                     # Настройки скриншотов
    path: "temp/cursor_screenshot.png"
    format: "PNG"
    quality: 95
    window: {title: "Cursor"}
    ocr: {engine: "tesseract", language: "eng+rus"}
    ui: {click_delay: 0.5, type_delay: 0.05}
    reports: {check_interval: 10, file_creation_timeout: 300}
    control_phrases: ["Отчет завершен!", "Тестирование завершено!"]
    error_handling: {max_retries: 3, retry_delay: 5}
```

### Шаблоны инструкций

```yaml
instructions:
  default:
    - instruction_id: 1
      name: "Создание плана"
      for_cursor: true
      template: |
        Переходим к выполнению задачи "{task_name}"...
      wait_for_file: "docs/results/current_plan_{task_id}.md"
      control_phrase: "Отчет завершен!"
      timeout: 300
```

### Настройки тестирования

```yaml
testing:
  enabled: false
  mock_cursor: true
  screenshot_dir: "tests/screenshots"
```

### Git интеграция

```yaml
git:
  auto_commit: true
  commit_message_template: "feat: {task_name} (задача {task_id})"
  branch: main
  remote: origin

  smart_git:                      # Оптимизированная Git интеграция
    enabled: true
    allowed_branches: ["smart"]   # Разрешенные ветки для авто-push
    auto_push_timeout: 60
    remote: origin
```

## 2. agents.yaml - Определения агентов

### Базовый агент исполнителя

```yaml
executor_agent:
  role: "Project Executor Agent"
  goal: "Execute todo items for the project..."
  backstory: |
    You are an automated code agent...
  allow_code_execution: false
  verbose: true
  tools: []
```

### Smart Agent

```yaml
smart_agent:
  role: "Smart Project Executor Agent"
  goal: "Execute tasks using learning from previous executions..."
  backstory: |
    You are a smart agent that learns from task execution history...
  allow_code_execution: true
  verbose: true
  tools:
    - LearningTool
    - ContextAnalyzerTool
```

## 3. llm_settings.yaml - Настройки LLM

### Основные настройки

```yaml
llm:
  default_provider: openrouter     # Провайдер по умолчанию
  default_model: meta-llama/llama-3.2-1b-instruct  # Модель по умолчанию
  timeout: 200                     # Таймаут запросов (сек)
  retry_attempts: 1                # Попытки повторных запросов
  strategy: best_of_two           # Стратегия выбора модели

  model_roles:                     # Роли моделей
    primary: []                    # Основные модели
    duplicate: []                  # Дублирующие модели
    reserve:                       # Резервные модели
      - kwaipilot/kat-coder-pro:free
    fallback:                      # Fallback модели
      - kwaipilot/kat-coder-pro:free
      - meta-llama/llama-3.2-3b-instruct

  parallel:                        # Параллельная обработка
    enabled: true
    models:                        # Модели для параллели
      - microsoft/wizardlm-2-8x22b
      - microsoft/phi-3-mini-128k-instruct
    evaluator_model: microsoft/wizardlm-2-8x22b  # Модель-оценщик
    selection_criteria:            # Критерии выбора
      - quality
      - relevance
      - completeness
      - efficiency
    parallel_timeout: 90           # Таймаут параллельной обработки (сек)
    evaluation_timeout: 30         # Таймаут оценки ответа (сек)

  _last_updated: '2026-01-23T09:24:32.497880'  # Время последнего обновления
  _update_source: auto_test_results             # Источник обновления
  _stats:                                      # Статистика тестирования
    total_tested: 7                             # Всего протестировано моделей
    working_count: 0                            # Количество рабочих моделей
    fastest_model: null                         # Самая быстрая модель
```

**Служебные поля (автоматически обновляются):**

- `_last_updated` - время последнего автоматического обновления конфигурации
- `_update_source` - источник последнего обновления (auto_test_results, manual, etc.)
- `_stats` - статистика тестирования моделей:
  - `total_tested` - общее количество протестированных моделей
  - `working_count` - количество моделей, прошедших тестирование успешно
  - `fastest_model` - модель с минимальным временем отклика

**Логика автоматического выбора моделей:**

- **primary: []** - Автоматически выбираются 2-3 самые производительные модели из доступных. Приоритет отдается моделям с названиями содержащими "wizard", "gpt", "claude", "llama-3".

- **duplicate: []** - Автоматически выбираются модели среднего класса. Исключаются слишком маленькие модели (с "1b", "mini", "small" в названии) и слишком большие (с "70b", "72b", "405b").

- **reserve/fallback** - Для этих ролей рекомендуется явно указывать модели, так как они используются в критических ситуациях и должны быть предсказуемыми.

**Примеры явного назначения:**
```yaml
model_roles:
  primary:
    - microsoft/wizardlm-2-8x22b
    - google/gemma-2-27b-it
  duplicate:
    - microsoft/phi-3-mini-128k-instruct
    - meta-llama/llama-3.2-3b-instruct
  reserve:
    - kwaipilot/kat-coder-pro:free
  fallback:
    - undi95/remm-slerp-l2-13b
```
```

### Провайдеры LLM

```yaml
providers:
  openrouter:
    base_url: https://openrouter.ai/api/v1
    models:
      anthropic:
        - name: anthropic/claude-3.5-sonnet
          max_tokens: 4096
          context_window: 200000
          temperature: 0.7
      openai:
        - name: openai/gpt-4o
          max_tokens: 4096
          context_window: 128000
          temperature: 0.7
        - name: openai/gpt-4o-mini
          max_tokens: 4096
          context_window: 128000
          temperature: 0.7
      microsoft:
        - name: microsoft/wizardlm-2-8x22b
          max_tokens: 4096
          context_window: 65536
          temperature: 0.7
        - name: microsoft/phi-3-mini-128k-instruct
          max_tokens: 4096
          context_window: 128000
          temperature: 0.7
      meta-llama:
        - name: meta-llama/llama-3.2-1b-instruct
          max_tokens: 4096
          context_window: 131072
          temperature: 0.7
        - name: meta-llama/llama-3.2-3b-instruct
          max_tokens: 4096
          context_window: 131072
          temperature: 0.7
```

## 4. logging.yaml - Конфигурация логирования

### Форматтеры

```yaml
formatters:
  default:                         # Стандартный форматтер
    format: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    datefmt: '%Y-%m-%d %H:%M:%S'

  detailed:                        # Детальный форматтер
    format: '%(asctime)s - %(name)s - [%(filename)s:%(lineno)d] - %(message)s'
    datefmt: '%Y-%m-%d %H:%M:%S'

  simple:                          # Простой форматтер
    format: '%(levelname)s - %(message)s'
```

### Обработчики

```yaml
handlers:
  console:                         # Консольный вывод
    class: logging.StreamHandler
    level: INFO
    formatter: default
    stream: ext://sys.stdout

  file:                            # Файловый вывод
    class: logging.handlers.RotatingFileHandler
    level: DEBUG
    formatter: detailed
    filename: logs/codeagent.log
    maxBytes: 10485760             # 10MB
    backupCount: 5
    encoding: utf8

  error_file:                      # Лог ошибок
    class: logging.handlers.RotatingFileHandler
    level: ERROR
    formatter: detailed
    filename: logs/errors.log
    maxBytes: 10485760
    backupCount: 5
    encoding: utf8

  test_file:                       # Лог тестов
    class: logging.handlers.RotatingFileHandler
    level: DEBUG
    formatter: detailed
    filename: logs/tests.log
    maxBytes: 10485760
    backupCount: 3
    encoding: utf8
```

### Логгеры

```yaml
loggers:
  src:                             # Логгер исходного кода
    level: DEBUG
    handlers: [console, file, error_file]
    propagate: false

  test:                            # Логгер тестов
    level: DEBUG
    handlers: [console, test_file]
    propagate: false

  cursor_cli:                      # Логгер Cursor CLI
    level: DEBUG
    handlers: [console, file]
    propagate: false

root:                              # Корневой логгер
  level: INFO
  handlers: [console, file, error_file]
```

## 5. llm_cost_config.yaml - Конфигурация стоимости LLM

### Структура файла стоимости API

```yaml
# Конфигурация стоимости API вызовов для разных моделей
# Стоимость указана в USD за 1K токенов (вход + выход)
# Данные актуальны на 2026-01-22, требуется регулярное обновление

# OpenRouter модели (основной провайдер)
openrouter:
  # Meta модели (относительно дешевые)
  meta-llama/llama-3.2-1b-instruct:
    input_cost_per_1k: 0.00015      # $0.00015 per 1K input tokens
    output_cost_per_1k: 0.00015     # $0.00015 per 1K output tokens
    context_window: 131072
    max_tokens: 4096

  # Microsoft модели (средний уровень стоимости)
  microsoft/phi-3-mini-128k-instruct:
    input_cost_per_1k: 0.00020
    output_cost_per_1k: 0.00020
    context_window: 128000
    max_tokens: 4096

  # Google модели (через OpenRouter)
  google/gemma-2-27b-it:
    input_cost_per_1k: 0.00030
    output_cost_per_1k: 0.00030
    context_window: 8192
    max_tokens: 2048

# Специфические модели (могут иметь другую стоимость)
special_models:
  # Cursor модели (auto, grok) - стоимость неизвестна, требует мониторинга
  auto:
    input_cost_per_1k: 0.0          # Требует измерения
    output_cost_per_1k: 0.0
    context_window: 0
    max_tokens: 0
    note: "Стоимость неизвестна - требует реального мониторинга"
```

### Настройки мониторинга стоимости

```yaml
monitoring:
  # Включить логирование стоимости каждого вызова
  log_costs: true

  # Лимиты расходов (в USD)
  limits:
    daily_limit: 10.0               # Максимум $10 в день
    monthly_limit: 100.0            # Максимум $100 в месяц

  # Уведомления при превышении лимитов (%)
  warning_thresholds: [50, 80, 95]

  # Файл для хранения статистики стоимости
  cost_log_file: "logs/llm_cost_tracking.json"

  # Период агрегации статистики
  aggregation_periods: ["hourly", "daily", "weekly", "monthly"]
```

### Рекомендации по выбору моделей

```yaml
recommendations:
  # Бюджетные модели (для тестирования и разработки)
  budget_models: ["meta-llama/llama-3.2-1b-instruct", "meta-llama/llama-3.2-3b-instruct"]

  # Оптимальные модели (баланс цена/качество)
  balanced_models: ["microsoft/phi-3-mini-128k-instruct", "microsoft/wizardlm-2-8x22b"]

  # Премиум модели (высокое качество, высокая стоимость)
  premium_models: ["google/gemma-2-27b-it", "mistralai/mistral-small-24b-instruct-2501"]

  # Максимальный бюджет на задачу (USD)
  max_cost_per_task: 0.1             # $0.10 на задачу
```

### Использование конфигурации стоимости

```python
from src.cost_monitor import CostMonitor

# Инициализация монитора стоимости
monitor = CostMonitor(config_path="config/llm_cost_config.yaml")

# Проверка лимитов перед вызовом
if monitor.can_make_request(model_name, estimated_tokens):
    # Выполнение запроса
    response = llm_call(model_name, prompt)

    # Логирование стоимости
    monitor.log_request_cost(model_name, input_tokens, output_tokens)

# Получение статистики
stats = monitor.get_cost_statistics()
print(f"Расходы за сегодня: ${stats['daily_cost']:.2f}")
```

## 6. test_config.yaml - Настройки тестирования

### Основные настройки тестирования

```yaml
testing:
  # Общие настройки
  enabled: true                    # Включить тестирование
  mock_external_services: true     # Мокировать внешние сервисы

  # Директории
  test_dir: "test"                 # Директория тестов
  fixtures_dir: "test/fixtures"    # Директория фикстур
  screenshots_dir: "test/screenshots"  # Директория скриншотов

  # Время ожидания
  default_timeout: 30              # Таймаут по умолчанию (сек)
  long_timeout: 300                # Длинный таймаут (сек)

  # Моки и стабы
  mock_cursor: true                # Мокировать Cursor
  mock_llm: true                   # Мокировать LLM
  mock_docker: true                # Мокировать Docker

  # Отчетность
  generate_reports: true           # Генерировать отчеты
  reports_dir: "test/reports"      # Директория отчетов
  coverage_enabled: true           # Включить покрытие кода
  coverage_min: 80                 # Минимальное покрытие (%)
```

### Детальная конфигурация тестового окружения

```yaml
# Настройки проекта (для тестов)
project:
  base_dir: ${PROJECT_DIR}
  docs_dir: docs
  status_file: test_codeAgentProjectStatus.md  # Префикс test_ для изоляции
  todo_format: md

# Настройки агента (безопасные для тестов)
agent:
  role: "Test Agent"
  goal: "Execute test tasks"
  backstory: |
    You are a test agent for automated testing of Code Agent.
    You execute test tasks in isolated test environments.
  allow_code_execution: false       # Отключено для безопасности
  verbose: false                    # Меньше вывода в тестах
  tools: ["FileReadTool", "FileWriteTool"]
  model: "gpt-3.5-turbo"
  allowed_models: ["gpt-3.5-turbo"]

# Настройки сервера (минимальные для тестов)
server:
  check_interval: 5                 # Короткий интервал для тестов
  max_iterations: 10                # Ограничено для тестов
  task_delay: 1                     # Минимальная задержка
  http_enabled: false               # Отключен для изоляции
  http_port: 3457                   # Другой порт
  auto_reload: false                # Отключен в тестах
  reload_on_py_changes: false
  max_restarts: 1

  # Отключена генерация TODO в тестах
  auto_todo_generation:
    enabled: false
    max_generations_per_session: 1
    output_dir: "todo"
    session_tracker_file: ".test_codeagent_sessions.json"

  # Отдельный checkpoint для тестов
  checkpoint:
    enabled: true
    checkpoint_file: ".test_codeagent_checkpoint.json"
    max_task_attempts: 2
    keep_completed_tasks: 10

# Минимальные настройки документации для тестов
docs:
  supported_extensions: [".md", ".txt"]
  max_file_size: 100000              # 100 KB для тестов
  results_dir: docs/results
  reviews_dir: docs/reviews

# Минимальное логирование в тестах
logging:
  level: WARNING                    # Только предупреждения и ошибки
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file: logs/test_code_agent.log    # Отдельный лог для тестов
  console: false                    # Без вывода в консоль
  color: false

# Отключена интеграция с Cursor в тестах
cursor:
  interface_type: "file"            # Файловый интерфейс для тестов
  cli:
    cli_path: null
    timeout: 30                     # Короткий таймаут
    headless: true
    model: ""

# Настройки тестирования
testing:
  enabled: true
  mock_cursor: true                 # Использовать мок вместо реального Cursor
  screenshot_dir: "test/screenshots"
  save_all_screenshots: false

# Отключен Git в тестах
git:
  auto_commit: false
  commit_message_template: "test: {task_name}"
  branch: test
  remote: origin
```

### Изоляция тестового окружения

**Принципы изоляции:**
- Все пути имеют префикс `test_` для отличия от production
- Отключены внешние сервисы (Docker, Cursor, HTTP)
- Минимальный уровень логирования
- Отдельные файлы конфигурации и состояния

**Переменные окружения для тестов:**
```bash
# Установка тестового режима
export TEST_MODE=true
export PROJECT_DIR=/tmp/test_project
export MOCK_EXTERNAL_SERVICES=true
```

**Запуск тестов:**
```bash
# С использованием test_config.yaml
python -m pytest test/ -c config/test_config.yaml

# С мокированием внешних сервисов
python -m pytest test/ --mock-all

# С генерацией отчетов о покрытии
python -m pytest test/ --cov=src/ --cov-report=html
```

## Переменные окружения

### Обязательные переменные

- `PROJECT_DIR` - путь к целевому проекту (абсолютный путь)
- `.env` файл в корне codeAgent/

### Опциональные переменные

#### API ключи
- `OPENROUTER_API_KEY` - ключ для OpenRouter API (основной провайдер LLM)
- `OPENAI_API_KEY` - ключ для OpenAI API (альтернативный провайдер)
- `ANTHROPIC_API_KEY` - ключ для Anthropic API
- `GOOGLE_API_KEY` - ключ для Google AI API

#### Системные настройки
- `DOCKER_AVAILABLE` - принудительно установить статус Docker (true/false/auto)
- `LOG_LEVEL` - уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `LOG_COLORS` - включить цветной вывод логов (true/false)
- `TEST_MODE` - включить тестовый режим (true/false)

#### Производительность и лимиты
- `MAX_MEMORY_MB` - максимальный объем памяти (MB)
- `MAX_CPU_CORES` - максимальное количество ядер CPU
- `REQUEST_TIMEOUT` - таймаут HTTP запросов (секунды)
- `LLM_TIMEOUT` - таймаут LLM запросов (секунды)

#### Безопасность
- `ALLOWED_PATHS` - разрешенные пути для операций с файлами (через запятую)
- `DENIED_PATHS` - запрещенные пути (через запятую)
- `SANDBOX_MODE` - включить песочницу для выполнения кода (true/false)

#### Мониторинг и отладка
- `ENABLE_PROFILING` - включить профилирование производительности (true/false)
- `METRICS_PORT` - порт для метрик Prometheus (число)
- `DEBUG_MODE` - включить подробную отладку (true/false)

### Примеры .env файла

```bash
# Основные настройки
PROJECT_DIR=/home/user/projects/my_project
LOG_LEVEL=INFO
LOG_COLORS=true

# API ключи
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Производительность
MAX_MEMORY_MB=2048
LLM_TIMEOUT=120

# Безопасность
SANDBOX_MODE=true
ALLOWED_PATHS=/home/user/projects,/tmp
```

## Валидация конфигурации

### Проверка корректности

```bash
# Валидация YAML синтаксиса
python -c "import yaml; yaml.safe_load(open('config/config.yaml'))"

# Проверка обязательных полей
python -c "from src.config import Config; Config.validate()"

# Тестирование подключений
python -c "from src.llm import LLMManager; LLMManager.test_connections()"
```

### Распространенные проблемы

1. **Отсутствует PROJECT_DIR**: Установите переменную окружения или создайте `.env` файл
2. **Некорректный YAML**: Проверьте отступы и синтаксис
3. **Отсутствуют API ключи**: Smart Agent перейдет в tool-only режим
4. **Docker недоступен**: Автоматический fallback на режим без code execution

## Миграция конфигурации

### Изменения в версии 2026-01-22

1. **Оптимизация Smart Agent**:
   - Увеличены `max_iter` с 15 до 25
   - Увеличена `memory` с 50 до 100
   - Увеличен `max_experience_tasks` с 100 до 200

2. **Новые LLM провайдеры**:
   - Добавлен Anthropic Claude-3.5-sonnet
   - Добавлены OpenAI GPT-4o/GPT-4o-mini
   - Обновлена best_of_two стратегия

3. **Удаление дублирования**:
   - Убрана секция logging из `config.yaml`
   - Консолидированы настройки агента

### Рекомендации по обновлению

1. Сделайте backup текущих конфигурационных файлов
2. Обновите параметры производительности Smart Agent
3. Добавьте новые LLM провайдеры при необходимости
4. Протестируйте конфигурацию перед запуском

## Примеры реальной конфигурации

### Сценарий 1: Локальная разработка с минимальными ресурсами

```yaml
# config/config.yaml
project:
  base_dir: ${PROJECT_DIR}
  docs_dir: docs
  status_file: codeAgentProjectStatus.md

agent:
  role: "Local Development Agent"
  goal: "Assist with local development tasks"
  allow_code_execution: false  # Безопасность на первом месте
  verbose: true

server:
  check_interval: 30
  http_enabled: false  # Не нужен HTTP сервер локально
  auto_reload: true
  reload_on_py_changes: true

smart_agent:
  enabled: true
  experience_dir: "smart_experience"
  max_iter: 15  # Меньше итераций для быстрой работы
  memory: 50
  verbose: true

logging:
  level: INFO
  console: true
  color: true
```

```yaml
# config/llm_settings.yaml
llm:
  default_provider: openrouter
  timeout: 60  # Короткий таймаут для разработки
  strategy: single  # Одна модель для простоты

  model_roles:
    primary: ["meta-llama/llama-3.2-1b-instruct"]  # Быстрая и дешевая модель
    reserve: ["microsoft/phi-3-mini-128k-instruct"]
    fallback: ["microsoft/wizardlm-2-8x22b"]
```

### Сценарий 2: Production сервер с полным функционалом

```yaml
# config/config.yaml
project:
  base_dir: ${PROJECT_DIR}
  docs_dir: docs
  status_file: codeAgentProjectStatus.md

agent:
  role: "Production Code Agent"
  goal: "Execute complex development tasks autonomously"
  allow_code_execution: true
  verbose: false  # Меньше вывода в продакшене

server:
  check_interval: 60
  max_iterations: null  # Бесконечный цикл
  http_enabled: true
  http_port: 3456
  auto_reload: false  # Стабильность важнее
  max_restarts: 5

  checkpoint:
    enabled: true
    max_task_attempts: 5  # Больше попыток в продакшене

smart_agent:
  enabled: true
  experience_dir: "smart_experience"
  max_experience_tasks: 1000  # Больше опыта
  max_iter: 50  # Больше итераций для сложных задач
  memory: 200  # Больше памяти
  verbose: false

cursor:
  interface_type: "cli"
  permissions:
    enabled: true
    allow_shell: ["git", "npm", "python", "pytest", "docker"]
    allow_write: ["src/**", "docs/**", "test/**"]

logging:
  level: WARNING  # Только важные сообщения
  file: logs/codeagent.log
  console: false
  color: false
```

```yaml
# config/llm_settings.yaml
llm:
  default_provider: openrouter
  timeout: 300  # Длинный таймаут для сложных задач
  strategy: best_of_two  # Качество важнее скорости

  parallel:
    enabled: true
    models: ["microsoft/wizardlm-2-8x22b", "google/gemma-2-27b-it"]
    evaluator_model: "microsoft/wizardlm-2-8x22b"

  model_roles:
    primary: ["microsoft/wizardlm-2-8x22b", "google/gemma-2-27b-it"]
    reserve: ["anthropic/claude-3.5-sonnet"]
    fallback: ["openai/gpt-4o", "meta-llama/llama-3.2-3b-instruct"]
```

### Сценарий 3: Тестирование и CI/CD

```yaml
# config/test_config.yaml
project:
  base_dir: ${PROJECT_DIR}
  status_file: test_codeAgentProjectStatus.md

agent:
  allow_code_execution: false  # Безопасность в тестах
  verbose: false

server:
  check_interval: 5  # Быстрые проверки в тестах
  max_iterations: 10  # Ограничено для тестов
  http_enabled: false

smart_agent:
  enabled: true
  max_iter: 5  # Минимум итераций для тестов
  memory: 20

logging:
  level: ERROR  # Только ошибки в тестах
  console: false
  file: logs/test_codeagent.log

cursor:
  interface_type: "file"  # Файловый интерфейс для тестов

testing:
  enabled: true
  mock_external_services: true
  generate_reports: true
  coverage_enabled: true
```

### Сценарий 4: Ограниченные ресурсы (Raspberry Pi, VPS)

```yaml
# config/config.yaml
project:
  base_dir: ${PROJECT_DIR}

agent:
  allow_code_execution: false  # Экономим ресурсы
  verbose: false

server:
  check_interval: 120  # Редкие проверки
  task_delay: 10

smart_agent:
  enabled: true
  experience_dir: "smart_experience"
  max_experience_tasks: 200  # Меньше опыта
  max_iter: 10  # Меньше итераций
  memory: 30  # Меньше памяти
  verbose: false

logging:
  level: WARNING
  console: true
  color: false
```

```yaml
# config/llm_settings.yaml
llm:
  timeout: 120  # Длинный таймаут для медленных соединений
  strategy: single  # Одна модель для экономии ресурсов

  model_roles:
    primary: ["meta-llama/llama-3.2-1b-instruct"]  # Маленькая модель
    reserve: ["microsoft/phi-3-mini-128k-instruct"]
    fallback: ["meta-llama/llama-3.2-3b-instruct"]
```

## Безопасность конфигурации

### Защита чувствительных данных

- Никогда не коммитьте API ключи в Git
- Используйте `.env` файлы для локальной разработки
- На серверах используйте переменные окружения или secret management

### Разрешения доступа

- Ограничьте доступ к директории `config/` на серверах
- Используйте минимально необходимые разрешения для файлов
- Регулярно проверяйте и обновляйте разрешения

### Мониторинг конфигурации

- Ведите логи изменений конфигурации
- Тестируйте конфигурацию после изменений
- Имейте план rollback при проблемах