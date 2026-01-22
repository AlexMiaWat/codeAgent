# Настройка Smart Agent

## Обзор

Smart Agent - это расширенная версия Project Executor Agent с инструментами обучения и анализа контекста проекта. Smart Agent использует исторические данные о выполненных задачах для улучшения качества выполнения новых задач.

## Архитектура

### Инструменты Smart Agent

#### LearningTool
- **Назначение**: Поиск похожих задач в истории выполнения
- **Функциональность**:
  - Нормализация текста запросов
  - Поиск по описаниям задач
  - Возврат релевантных примеров решений
- **Файл**: `src/tools/learning_tool.py`

#### ContextAnalyzerTool
- **Назначение**: Анализ зависимостей и контекста проекта
- **Функциональность**:
  - Анализ Python импортов
  - Определение зависимостей между файлами
  - Анализ структуры проекта
- **Файл**: `src/tools/context_analyzer_tool.py`

## Конфигурация

### Основные настройки в config/agents.yaml

```yaml
smart_agent:
  role: "Smart Project Executor Agent"
  goal: "Execute tasks using learning from previous executions and project context analysis with optimized LLM settings"
  backstory: |
    You are a smart agent that learns from task execution history and analyzes project context.
    You use LearningTool and ContextAnalyzerTool to improve task execution quality.
    Optimized for performance with best_of_two strategy and parallel model evaluation.
  allow_code_execution: true
  verbose: true
  tools:
    - LearningTool
    - ContextAnalyzerTool
```

### Переменные окружения (.env)

```bash
# Включить smart режим агента
SMART_AGENT_ENABLED=true

# Директория для хранения опыта smartAgent
SMART_AGENT_EXPERIENCE_DIR=smart_experience

# Максимальное количество задач в истории опыта
SMART_AGENT_MAX_EXPERIENCE_TASKS=200

# Параметры производительности
SMART_AGENT_MAX_ITER=25
SMART_AGENT_MEMORY=100
SMART_AGENT_VERBOSE=true

# Настройки LearningTool
LEARNING_TOOL_ENABLE_INDEXING=true
LEARNING_TOOL_CACHE_SIZE=1000
LEARNING_TOOL_CACHE_TTL=3600

# Настройки ContextAnalyzerTool
CONTEXT_ANALYZER_DEEP_ANALYSIS=true
CONTEXT_ANALYZER_SUPPORTED_LANGUAGES=python,javascript,typescript,java,cpp
CONTEXT_ANALYZER_MAX_DEPTH=5
```

## Изменения в конфигурации (относительно стандартного агента)

### 1. Оптимизация LLM настроек

В `config/llm_settings.yaml` добавлены специальные настройки для Smart Agent:
- Стратегия `best_of_two` для выбора лучшей модели
- Параллельная обработка запросов
- Оптимизированные параметры температуры и топ-п

### 2. Конфигурация Docker

В `config/config.yaml` добавлена поддержка Docker режима для Smart Agent:
```yaml
smart_agent:
  enabled: true
  docker_mode: true
  experience_dir: smart_experience
```

### 3. Автоматические коммиты

Настроена автоматическая система коммитов для ветки `smart`:
- Автоматические коммиты после выполнения задач
- Специальные сообщения коммитов для Smart Agent
- Интеграция с системой логирования

## Запуск Smart Agent

### Через командную строку

```bash
# Активация smart режима
export SMART_AGENT_ENABLED=true

# Запуск агента
python main.py --agent smart_agent
```

### Через Docker

```bash
# Сборка и запуск через Docker Compose
docker-compose -f docker/docker-compose.agent.yml up --build
```

## Хранение опыта

### Структура директории smart_experience

```
smart_experience/
├── tasks.json          # История выполненных задач
├── patterns.json       # Обнаруженные паттерны решений
└── cache/             # Кэш результатов анализа
    ├── learning_cache.json
    └── context_cache.json
```

### Формат хранения задач

```json
{
  "task_id": "task_1234567890",
  "description": "Настройка интеграции с Smart Agent",
  "status": "completed",
  "execution_time": 45.2,
  "tools_used": ["LearningTool", "ContextAnalyzerTool"],
  "success_patterns": ["docker_integration", "config_optimization"],
  "timestamp": "2026-01-22T22:43:22Z"
}
```

## Мониторинг и отладка

### Логи Smart Agent

Логи Smart Agent записываются в отдельные файлы:
- `logs/smart_agent.log` - основные логи работы
- `logs/smart_agent_errors.log` - логи ошибок
- `logs/smart_agent_performance.log` - метрики производительности

### Метрики производительности

Smart Agent отслеживает следующие метрики:
- Время выполнения задач
- Эффективность поиска похожих задач
- Точность анализа зависимостей
- Успешность применения паттернов решений

## Известные ограничения

### Текущие проблемы (по состоянию на 2026-01-23)

1. **Производительность LearningTool**: Полный перебор без индексации
2. **Ограниченный анализ зависимостей**: Только Python импорты
3. **Отсутствие интеграционных тестов**: Только базовые unit тесты

### Планируемые улучшения

1. **Оптимизация поиска**: Добавление индексации и кеширования
2. **Расширение анализа**: Поддержка JavaScript/TypeScript зависимостей
3. **Тестовое покрытие**: Интеграционные и нагрузочные тесты

## Резервное копирование

### Автоматическое резервное копирование опыта

```bash
# Скрипт для резервного копирования
scripts/backup_smart_experience.sh
```

### Восстановление из резервной копии

```bash
# Скрипт для восстановления
scripts/restore_smart_experience.sh
```

## Безопасность

### Ограничения доступа

- Опыт Smart Agent хранится локально
- Нет передачи данных во внешние сервисы
- Контроль доступа через переменные окружения

### Аудит действий

Все действия Smart Agent логируются с указанием:
- Времени выполнения
- Использованных инструментов
- Результатов анализа
- Принятых решений

## Troubleshooting

### Распространенные проблемы

1. **Smart Agent не запускается**
   - Проверьте переменную `SMART_AGENT_ENABLED=true`
   - Убедитесь в наличии директории `smart_experience`

2. **Низкая производительность**
   - Включите индексацию: `LEARNING_TOOL_ENABLE_INDEXING=true`
   - Настройте размер кэша: `LEARNING_TOOL_CACHE_SIZE=1000`

3. **Ошибки анализа зависимостей**
   - Проверьте корректность структуры проекта
   - Убедитесь в наличии необходимых файлов (requirements.txt, pyproject.toml)

## Ссылки

- [Основная документация](../../README.md)
- [Руководство по конфигурации](CONFIGURATION_GUIDE.md)
- [API документация](../core/API_REFERENCE.md)
- [Примеры использования](../../examples/)