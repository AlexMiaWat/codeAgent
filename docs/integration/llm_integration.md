# Интеграция модульной архитектуры LLM в Code Agent

## Обзор

Code Agent теперь использует полностью переработанную модульную архитектуру LLM, состоящую из 7 специализированных компонентов. Новая система обеспечивает повышенную надежность, производительность и расширяемость по сравнению с предыдущим монолитным подходом.

## Модульная архитектура компонентов

### Ядро системы

1. **LLMManager** (`src/llm/manager.py`) - Фасад системы
   - Единый интерфейс для всех операций
   - Управление жизненным циклом компонентов
   - Dependency injection всех зависимостей

2. **ModelRegistry** (`src/llm/registry.py`) - Реестр моделей
   - Управление конфигурацией моделей по ролям
   - Сбор статистики производительности
   - Автоматический выбор оптимальных моделей

3. **ClientManager** (`src/llm/client.py`) - Управление API клиентами
   - Абстракция над разными провайдерами
   - Управление соединениями и аутентификацией
   - Обработка сетевых ошибок

4. **StrategyManager** (`src/llm/strategy.py`) - Стратегии генерации
   - Single Model: Быстрая генерация
   - Parallel Generation: Качество через параллельность
   - Fallback Chains: Надежность через резервирование

### Специализированные компоненты

5. **ResponseEvaluator** (`src/llm/evaluator.py`) - Оценка ответов
   - Сравнение нескольких ответов
   - Выбор лучшего по критериям качества
   - Автоматическая оценка через модель-оценщик

6. **JsonValidator** (`src/llm/validator.py`) - Валидация JSON
   - Извлечение JSON из ответов
   - Валидация структуры и схемы
   - Исправление malformed ответов

7. **HealthMonitor** (`src/llm/monitor.py`) - Мониторинг здоровья
   - Фоновые проверки доступности моделей
   - Автоматическое отключение проблемных моделей
   - Попытки восстановления после сбоев

8. **ConfigLoader** (`src/llm/config_loader.py`) - Загрузка конфигурации
   - Загрузка и парсинг YAML конфигураций
   - Подстановка переменных окружения
   - Валидация структуры конфигурации

## Конфигурация модульной архитектуры

### Структура конфигурации (`config/llm_settings.yaml`)

```yaml
# Новая модульная конфигурация LLM (2026-01-23)
llm:
  # Общие настройки системы
  default_provider: openrouter
  request_timeout: 200
  max_retries: 3

  # Настройки компонентов
  components:
    health_monitor:
      enabled: true
      check_interval: 300  # секунд между проверками
      failure_threshold: 3  # отключение после N сбоев

    parallel_generation:
      enabled: true
      evaluator_model: meta-llama/llama-3.2-3b-instruct

  # Модели по ролям (новая структура)
  models:
    primary:
      - name: meta-llama/llama-3.2-1b-instruct
        provider: openrouter
        max_tokens: 4096
        context_window: 131072
        temperature: 0.7
        enabled: true

      - name: microsoft/wizardlm-2-8x22b
        provider: openrouter
        max_tokens: 4096
        context_window: 65536
        temperature: 0.7
        enabled: true

    duplicate:
      - name: google/gemma-2-27b-it
        provider: openrouter
        max_tokens: 2048
        context_window: 8192
        temperature: 0.8
        enabled: true

    reserve:
      - name: mistralai/mistral-small-24b-instruct-2501
        provider: openrouter
        max_tokens: 4096
        context_window: 32768
        temperature: 0.6
        enabled: true

    fallback:
      - name: meta-llama/llama-3.2-3b-instruct
        provider: openrouter
        max_tokens: 4096
        context_window: 131072
        temperature: 0.7
        enabled: true

      - name: kwaipilot/kat-coder-pro:free
        provider: openrouter
        max_tokens: 4096
        context_window: 128000
        temperature: 0.7
        enabled: true

  # Настройки провайдеров
  providers:
    openrouter:
      base_url: "https://openrouter.ai/api/v1"
      timeout: 200
      # API ключ из переменных окружения

  # Стратегии генерации
  strategies:
    default: single_fastest  # single_fastest, parallel_quality, fallback_chain
    json_mode: parallel_with_validation  # специальная стратегия для JSON

  # Устаревшие настройки (для совместимости)
  _legacy_config_support: true
```

### Переменные окружения

```env
OPENROUTER_API_KEY=sk-or-v1-...
```

## Стратегии использования моделей

### 1. Single Model (по умолчанию)

### Использование в Code Agent

#### Базовая генерация через фасад LLMManager

```python
from src.llm.manager import LLMManager

# Создание менеджера (автоматическая инициализация всех компонентов)
llm_manager = LLMManager()

# Генерация ответа (автоматический выбор оптимальной стратегии)
response = await llm_manager.generate_response(
    prompt="Объясни что такое нейронная сеть",
    use_parallel=True,  # Качество важнее скорости
    use_fastest=False
)

print(f"Ответ от {response.model_name}: {response.content}")
```

#### Генерация с типизированными запросами

```python
from src.llm.types import GenerationRequest

# Типизированный запрос для JSON ответов
request = GenerationRequest(
    prompt="Оцени задачу и верни JSON: {'score': 0-10, 'reason': 'пояснение'}",
    response_format={"type": "json_object"},  # Гарантированный JSON
    use_parallel=True  # Параллельная генерация для качества
)

response = await llm_manager.generate_response(request)

# JsonValidator гарантирует валидный JSON
result = response.content  # Уже извлечен и провалидирован
print(f"Оценка: {result['score']}, Причина: {result['reason']}")
```

#### Ручное управление компонентами

```python
# Прямой доступ к компонентам для специфических задач
registry = llm_manager.registry
client = llm_manager.client
evaluator = llm_manager.evaluator

# Получение статистики моделей
models = registry.get_models_by_role(ModelRole.PRIMARY)
stats = {model.name: registry.get_model_stats(model.name) for model in models}

# Проверка здоровья всех моделей
health = await llm_manager.check_health()
healthy_models = [name for name, status in health.items() if status == "healthy"]
```

### Стратегии отказоустойчивости

#### Fallback цепочки в модульной архитектуре

```
User Request
    ↓
StrategyManager._generate_single()
    ↓
ModelRegistry.get_models_by_role(PRIMARY)
    ↓
Попытка PRIMARY моделей по очереди
    ↓ (если все упали)
Попытка DUPLICATE моделей
    ↓ (если все упали)
Попытка RESERVE моделей
    ↓ (если все упали)
Попытка FALLBACK моделей
    ↓
HealthMonitor.update_health_status()
    ↓
RuntimeError или результат
```

**Многоуровневая защита:**
1. **Сетевая**: `ClientManager` обрабатывает таймауты
2. **API**: Автоматическое переключение провайдеров
3. **Модельная**: Fallback цепочки по ролям
4. **Валидационная**: `JsonValidator` обеспечивает корректные ответы

## Интеграция с CrewAI

### Автоматическая интеграция через CrewAILLMWrapper

Новая модульная архитектура полностью совместима с CrewAI через обновленный `CrewAILLMWrapper`:

```python
from src.llm.crewai_llm_wrapper import create_llm_for_crewai
from crewai import Agent

# Создание LLM для CrewAI с новой архитектурой
llm = create_llm_for_crewai(
    config_path="config/llm_settings.yaml",
    use_parallel=True,  # Использовать параллельную генерацию
    strategy="best_of_two"  # или другая стратегия
)

# Использование в агенте CrewAI
agent = Agent(
    role="Code Analyzer",
    goal="Анализировать код и предлагать улучшения",
    backstory="Экспертный анализатор кода с использованием мощных LLM",
    llm=llm,
    verbose=True
)
```

### Интеграция с агентами Code Agent

```python
from src.agents.smart_agent import SmartAgent

# Smart Agent автоматически использует новую LLM архитектуру
agent = SmartAgent(
    project_dir=Path("project"),
    config_path="config/config.yaml"
)

# Внутри Smart Agent:
# - LearningTool для обучения на опыте
# - ContextAnalyzerTool для анализа проекта
# - LLMManager для генерации через новую архитектуру
# - Docker/CodeInterpreterTool при наличии Docker
```

### Преимущества интеграции

- **Прозрачность**: CrewAI агенты работают без изменений API
- **Расширенные возможности**: Доступ ко всем стратегиям модульной архитектуры
- **Мониторинг**: Автоматический health monitoring и статистика
- **Отказоустойчивость**: Fallback цепочки на уровне агентов
    use_fastest=True,
    use_parallel=False
)

agent = Agent(
    role="Developer",
    goal="Write code",
    llm=custom_llm  # Использовать кастомный LLM
)
```

## Тестирование моделей

### Запуск тестов

```python
from src.llm.llm_test_runner import LLMTestRunner
from src.llm.llm_manager import LLMManager

mgr = LLMManager()
runner = LLMTestRunner(mgr)

# Тестирование всех моделей
results = await runner.test_all_models()

# Экспорт результатов
output_path = runner.export_results_markdown()
print(f"Results saved to: {output_path}")
```

### Результаты тестирования

Тестирование создает Markdown отчет с:
- Статусом доступности каждой модели
- Временем отклика
- Статистикой успешных/неудачных запросов
- Рекомендациями по выбору моделей

## Роли моделей (обновлено 2026-01-22)

### Автоматический выбор (новая парадигма)
- **primary/duplicate**: Пустые массивы - автоматический выбор на основе тестирования
- **reserve**: Kwaipilot/kat-coder-pro:free - специализированная модель для кода
- **fallback**: Undi95/remm-slerp-l2-13b, Microsoft/WizardLM-2-8x22b - стабильные модели

### Parallel Models (новая категория)
- **wizardlm-2-8x22b**: Мощная модель для параллельной обработки и оценки
- **phi-3-mini-128k-instruct**: Быстрая модель среднего уровня для параллели
- **evaluator_model**: wizardlm-2-8x22b - специализированная модель для оценки качества

### Новые провайдеры в системе

#### Anthropic Claude-3.5-sonnet
- **Роль**: Высококачественные ответы для сложных задач
- **Особенности**: Максимальное качество, большой контекст (200k)
- **Использование**: Анализ кода, архитектурное планирование

#### OpenAI GPT-4o/GPT-4o-mini
- **Роль**: Быстрые и точные модели общего назначения
- **Особенности**: Оптимизированная производительность, баланс цена/качество
- **Использование**: Универсальные задачи, быстрая обработка

#### Microsoft WizardLM-2-8x22b
- **Роль**: Мощная модель для параллельной обработки
- **Особенности**: Высокая производительность, хороший контекст
- **Использование**: Параллельная оценка, сложные задачи

#### Microsoft Phi-3-mini-128k
- **Роль**: Быстрая модель среднего уровня
- **Особенности**: Компактная, быстрая, достаточный контекст
- **Использование**: Резервная модель, параллельная обработка

## Обработка ошибок

### Автоматический Fallback

При ошибке модели:
1. Логируется ошибка
2. Увеличивается счетчик ошибок модели
3. Автоматически переключается на следующую модель
4. Процесс повторяется до успешного ответа

### Типы ошибок

- **Timeout**: Превышено время ожидания ответа
- **API Error**: Ошибка API провайдера
- **Rate Limit**: Превышен лимит запросов
- **Model Unavailable**: Модель временно недоступна

## Производительность

### Выбор быстрой модели

LLMManager отслеживает время отклика каждой модели и автоматически выбирает самую быструю:

```python
fastest = mgr.get_fastest_model()
print(f"Fastest model: {fastest.name}")
```

### Кэширование статистики

Статистика моделей сохраняется в памяти:
- `last_response_time`: Последнее время отклика
- `success_count`: Количество успешных запросов
- `error_count`: Количество ошибок

## Примеры использования

### Базовое использование

```python
from src.llm.llm_manager import LLMManager

mgr = LLMManager("config/llm_settings.yaml")
response = await mgr.generate_response("Привет, как дела?")

if response.success:
    print(f"Ответ: {response.content}")
    print(f"Модель: {response.model_name}")
    print(f"Время: {response.response_time:.2f}s")
```

### Использование с CrewAI

```python
from src.agents.executor_agent import create_executor_agent
from pathlib import Path

agent = create_executor_agent(
    project_dir=Path("my_project"),
    use_llm_manager=True,
    use_parallel=True  # Параллельный режим
)

# Агент автоматически использует LLMManager
```

### Тестирование моделей

```python
from src.llm.llm_test_runner import LLMTestRunner

runner = LLMTestRunner()
results = await runner.test_all_models()

# Получить список работающих моделей
working = runner.get_working_models()
print(f"Working models: {working}")

# Получить самые быстрые модели
fastest = runner.get_fastest_models()
for model_name, response_time in fastest[:5]:
    print(f"{model_name}: {response_time:.2f}s")
```

## Рекомендации (обновлено 2026-01-22)

### Выбор стратегии

1. **best_of_two (рекомендуется)**: Максимальное качество через параллельную оценку
2. **single_model**: Для простых задач с ограниченным бюджетом
3. **Автоматический fallback**: Всегда включен для надежности

### Выбор провайдеров

1. **Claude-3.5-sonnet**: Для сложного анализа кода и архитектуры
2. **GPT-4o**: Для быстрой и качественной работы общего назначения
3. **WizardLM-2-8x22b**: Для параллельной обработки и оценки
4. **Phi-3-mini-128k**: Для быстрой резервной обработки

### Оптимизация производительности

- **Тестируйте регулярно**: Автоматическое тестирование каждые 24 часа
- **Мониторьте качество**: Отслеживайте метрики через best_of_two
- **Обновляйте конфигурацию**: Новые модели добавляются автоматически
- **Используйте кэширование**: Для повторяющихся запросов

## Ограничения

- Текущая реализация поддерживает только OpenRouter провайдер
- Параллельный режим требует минимум 2 primary модели
- Оценка ответов требует evaluator модель (обычно из duplicate)

## Будущие улучшения

- Поддержка дополнительных провайдеров (OpenAI, Anthropic, Ollama)
- Кэширование ответов для повторяющихся запросов
- Адаптивный выбор моделей на основе типа задачи
- Метрики качества ответов
