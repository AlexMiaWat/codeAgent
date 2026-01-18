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

### Файл `config/llm_settings.yaml`

```yaml
llm:
  default_provider: openrouter
  default_model: meta-llama/llama-3.2-1b-instruct
  timeout: 200
  retry_attempts: 1
  strategy: "best_of_two"
  
  # Роли моделей
  model_roles:
    primary: ["meta-llama/llama-3.2-1b-instruct", "microsoft/phi-3-mini-128k-instruct"]
    duplicate: ["meta-llama/llama-3.2-3b-instruct", "microsoft/wizardlm-2-8x22b"]
    reserve: ["google/gemma-2-27b-it", "mistralai/mistral-small-24b-instruct-2501"]
    fallback: ["kwaipilot/kat-coder-pro:free", "undi95/remm-slerp-l2-13b"]

providers:
  openrouter:
    base_url: https://openrouter.ai/api/v1
    api_key: ${OPENROUTER_API_KEY}
    models:
      # Определение моделей...
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

### 2. Parallel (Best of Two)

Используются две модели параллельно, выбирается лучший ответ:

```python
response = await mgr.generate_response(
    prompt="Привет",
    use_fastest=True,
    use_parallel=True
)
```

**Поведение:**
- Запускаются две primary модели параллельно
- Обе модели генерируют ответы одновременно
- Оценка ответов выполняется через evaluator модель
- Выбирается ответ с наивысшей оценкой

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

## Роли моделей

### Primary (Рабочие)
- Основные модели для повседневной работы
- Быстрые и надежные
- Используются по умолчанию

### Duplicate (Дублирующие)
- Альтернативные модели с похожими характеристиками
- Используются для параллельного выполнения
- Могут использоваться как evaluator для оценки ответов

### Reserve (Резервные)
- Резервные модели на случай проблем с primary
- Обычно более мощные, но медленнее
- Используются при fallback

### Fallback (Последний резерв)
- Модели на случай полного отказа остальных
- Могут быть бесплатными или с ограничениями
- Используются только в крайнем случае

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

## Рекомендации

1. **Для разработки**: Используйте бесплатные модели (fallback)
2. **Для продакшена**: Используйте primary модели с fallback
3. **Для критичных задач**: Используйте parallel режим (best_of_two)
4. **Регулярно тестируйте**: Запускайте `LLMTestRunner` для проверки доступности моделей

## Ограничения

- Текущая реализация поддерживает только OpenRouter провайдер
- Параллельный режим требует минимум 2 primary модели
- Оценка ответов требует evaluator модель (обычно из duplicate)

## Будущие улучшения

- Поддержка дополнительных провайдеров (OpenAI, Anthropic, Ollama)
- Кэширование ответов для повторяющихся запросов
- Адаптивный выбор моделей на основе типа задачи
- Метрики качества ответов
