# Интеграция LLM провайдеров в Code Agent

## Обзор

Code Agent использует систему управления несколькими LLM моделями (`LLMManager`) для автоматического выбора оптимальных моделей, обработки ошибок и повышения надежности работы агента.

## Архитектура

### Компоненты

1. **LLMManager** (`src/llm/llm_manager.py`)
   - Управление несколькими моделями от разных провайдеров
   - Автоматический выбор самой быстрой модели
   - Fallback на резервные модели при ошибках
   - Параллельное выполнение через две модели с выбором лучшего ответа

2. **LLMTestRunner** (`src/llm/llm_test_runner.py`)
   - Тестирование доступности моделей
   - Измерение времени отклика
   - Экспорт результатов тестирования

3. **CrewAILLMWrapper** (`src/llm/crewai_llm_wrapper.py`)
   - Обертка для использования LLMManager в CrewAI
   - Прозрачная интеграция с агентами CrewAI

## Конфигурация

### Файл `config/llm_settings.yaml` (актуальная конфигурация 2026-01-22)

```yaml
llm:
  default_provider: openrouter
  default_model: meta-llama/llama-3.2-1b-instruct
  timeout: 200
  retry_attempts: 1
  strategy: best_of_two

  # Роли моделей (обновлено)
  model_roles:
    primary: []  # Автоматический выбор
    duplicate: []  # Автоматический выбор
    reserve:
      - kwaipilot/kat-coder-pro:free
    fallback:
      - undi95/remm-slerp-l2-13b
      - microsoft/wizardlm-2-8x22b

  # Параллельная обработка (новое)
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

  _last_updated: '2026-01-22T21:05:01.819254'
  _update_source: auto_test_results

providers:
  openrouter:
    base_url: https://openrouter.ai/api/v1
    models:
      # Новые провайдеры (2026-01-22)
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
      google:
        - name: google/gemma-2-27b-it
          max_tokens: 2048
          context_window: 8192
          temperature: 0.7
      mistralai:
        - name: mistralai/mistral-small-24b-instruct-2501
          max_tokens: 4096
          context_window: 32768
          temperature: 0.7
      kwaipilot:
        - name: kwaipilot/kat-coder-pro:free
          max_tokens: 4096
          context_window: 128000
          temperature: 0.7
      undi95:
        - name: undi95/remm-slerp-l2-13b
          max_tokens: 1536
          context_window: 6144
          temperature: 0.7
```

### Переменные окружения

```env
OPENROUTER_API_KEY=sk-or-v1-...
```

## Стратегии использования моделей

### 1. Single Model (по умолчанию)

Используется одна модель с автоматическим fallback:

```python
from src.llm.llm_manager import LLMManager

mgr = LLMManager()
response = await mgr.generate_response(
    prompt="Привет",
    use_fastest=True,
    use_parallel=False
)
```

**Поведение:**
- Выбирается самая быстрая primary модель
- При ошибке автоматически переключается на следующую модель из fallback списка
- Продолжает до успешного ответа или исчерпания всех моделей

### 2. Parallel (Best of Two) - Оптимизированная стратегия

Используются две модели параллельно с интеллектуальным выбором лучшего ответа:

```python
# Автоматически используется best_of_two стратегия
response = await mgr.generate_response(
    prompt="Анализируй этот код",
    strategy="best_of_two"  # Новая стратегия
)
```

**Поведение best_of_two:**
- Выбираются две оптимальные модели из parallel.models
- Модели WizardLM-2-8x22b и Phi-3-mini-128k-instruct работают параллельно
- Оценка качества через evaluator_model (WizardLM-2-8x22b)
- Критерии оценки: quality, relevance, completeness, efficiency
- Выбирается ответ с наивысшей комплексной оценкой

**Преимущества новой стратегии:**
- **Качество**: Двойная проверка повышает качество ответов
- **Надежность**: Fallback при ошибках одной из моделей
- **Производительность**: Параллельное выполнение не увеличивает общее время
- **Интеллект**: Оценщик учитывает контекст и сложность задачи

### 3. Fallback Chain

Автоматический переход на резервные модели:

```
Primary → Duplicate → Reserve → Fallback
```

Каждая категория моделей используется при ошибке предыдущей.

## Интеграция с CrewAI

### Автоматическая интеграция

LLMManager автоматически интегрируется в агентов CrewAI через `CrewAILLMWrapper`:

```python
from src.agents.executor_agent import create_executor_agent

agent = create_executor_agent(
    project_dir=Path("project"),
    use_llm_manager=True,  # Включить LLMManager
    use_parallel=False      # Использовать параллельный режим
)
```

### Ручная интеграция

```python
from src.llm.crewai_llm_wrapper import create_llm_for_crewai
from crewai import Agent

custom_llm = create_llm_for_crewai(
    config_path="config/llm_settings.yaml",
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
