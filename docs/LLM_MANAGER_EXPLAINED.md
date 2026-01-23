# Новая модульная архитектура LLM Manager

## Обзор

**LLM модуль** - это полностью переработанная система управления LLM провайдерами с модульной архитектурой. Вместо монолитного `LLMManager` теперь используется система из 7 специализированных компонентов, каждый из которых отвечает за конкретную задачу.

**Ключевые преимущества новой архитектуры:**
- **Модульность**: Каждый компонент имеет единственную ответственность
- **Тестируемость**: Изолированное тестирование каждого модуля
- **Расширяемость**: Легкое добавление новых провайдеров и стратегий
- **Надежность**: Многоуровневая обработка ошибок
- **Производительность**: Параллельное выполнение и оптимизации

## Архитектура компонентов

### Фасад: LLMManager

**Центральный компонент системы - фасад для всех операций:**

```python
from src.llm.manager import LLMManager

# Создание менеджера с автоматической инициализацией всех компонентов
llm_manager = LLMManager(config_path="config/llm_settings.yaml")

# Единый интерфейс для всех операций
response = await llm_manager.generate_response(
    prompt="Объясни что такое async/await",
    use_parallel=True,  # Автоматический выбор лучшей стратегии
    use_fastest=True
)
```

**Ответственности LLMManager:**
- Управление жизненным циклом всех компонентов
- Dependency injection зависимостей
- Единый интерфейс для внешнего мира
- Координация между компонентами

### 1. ModelRegistry - Реестр моделей

**Управление конфигурацией и статистикой моделей:**

```python
from src.llm.registry import ModelRegistry

registry = ModelRegistry(config_loader)
models = registry.get_models_by_role(ModelRole.PRIMARY)
fastest = registry.get_fastest_model()
```

**Функции:**
- Загрузка конфигурации моделей из YAML
- Управление ролями моделей (PRIMARY, DUPLICATE, RESERVE, FALLBACK)
- Сбор статистики производительности
- Выбор оптимальной модели по критериям

### 2. ClientManager - Управление API клиентами

**Абстракция над различными LLM провайдерами:**

```python
from src.llm.client import ClientManager

client_manager = ClientManager(config_loader)
response = await client_manager.call_model(model_config, prompt)
```

**Функции:**
- Создание клиентов для разных провайдеров (OpenRouter, OpenAI, etc.)
- Управление аутентификацией и соединениями
- Маршрутизация запросов к правильным провайдерам
- Обработка сетевых ошибок и таймаутов

### 3. StrategyManager - Стратегии генерации

**Логика выбора и выполнения стратегий генерации:**

```python
from src.llm.strategy import StrategyManager

strategy = StrategyManager(registry, client, evaluator, validator)

# Быстрая генерация через одну модель
response = await strategy.generate(request)

# Параллельная генерация для качества
response = await strategy.generate_parallel(request)
```

**Стратегии:**
- **Single Model**: Быстрая генерация через оптимальную модель
- **Parallel Generation**: Две модели одновременно для выбора лучшего
- **Fallback Chains**: Последовательное переключение при ошибках

### 4. ResponseEvaluator - Оценка ответов

**Автоматическая оценка качества ответов:**

```python
from src.llm.evaluator import ResponseEvaluator

evaluator = ResponseEvaluator(client_manager)
score = await evaluator.evaluate_response(prompt, response_content)
best = await evaluator.select_best_response(responses)
```

**Функции:**
- Оценка ответов по критериям (relevance, completeness, accuracy)
- Сравнение нескольких ответов
- Выбор оптимального ответа для пользователя

### 5. JsonValidator - Валидация JSON

**Специализированная валидация JSON ответов:**

```python
from src.llm.validator import JsonValidator

validator = JsonValidator()
is_valid, json_obj = validator.validate_and_extract(response_text)
```

**Функции:**
- Проверка корректности JSON структуры
- Извлечение JSON из markdown кода
- Исправление malformed JSON
- Типобезопасность ответов

### 6. HealthMonitor - Мониторинг здоровья

**Фоновый мониторинг доступности моделей:**

```python
from src.llm.monitor import HealthMonitor

monitor = HealthMonitor(registry, client)
await monitor.start_monitoring()  # Запуск фонового мониторинга

# Проверка здоровья всех моделей
health_status = await monitor.check_health()
```

**Функции:**
- Регулярная проверка доступности моделей
- Автоматическое отключение проблемных моделей
- Попытки восстановления упавших моделей
- Уведомления о проблемах

### 7. ConfigLoader - Загрузка конфигурации

**Универсальный загрузчик конфигураций:**

```python
from src.llm.config_loader import ConfigLoader

loader = ConfigLoader("config/llm_settings.yaml")
config = loader.load_config()
```

**Функции:**
- Загрузка и парсинг YAML конфигураций
- Подстановка переменных окружения (${ENV_VARS})
- Валидация структуры конфигурации
- Горячая перезагрузка настроек

## Как работает новая архитектура

### Инициализация системы

```python
from src.llm.manager import LLMManager

# Автоматическая инициализация всех компонентов
llm_manager = LLMManager(config_path="config/llm_settings.yaml")

# Что происходит внутри:
# 1. ConfigLoader загружает и валидирует конфигурацию
# 2. ModelRegistry инициализирует модели по ролям
# 3. ClientManager создает клиентов для провайдеров
# 4. StrategyManager подготавливает стратегии генерации
# 5. ResponseEvaluator и JsonValidator готовы к работе
# 6. HealthMonitor запускает фоновый мониторинг
```

### Базовое использование

```python
# Простая генерация (автоматический выбор стратегии)
response = await llm_manager.generate_response(
    prompt="Объясни что такое нейронная сеть",
    use_fastest=True,   # Приоритет скорости
    use_parallel=False  # Одномодельный режим
)

if response.success:
    print(f"Ответ: {response.content}")
    print(f"Модель: {response.model_name}")
    print(f"Время: {response.response_time:.2f}s")
```

**Внутренний поток:**
1. `LLMManager` делегирует запрос `StrategyManager`
2. `StrategyManager` запрашивает самую быструю модель у `ModelRegistry`
3. `ClientManager` выполняет вызов через соответствующий API клиент
4. При успехе `JsonValidator` проверяет ответ (если JSON режим)
5. `ModelRegistry` обновляет статистику модели
6. Возвращается результат

### JSON Mode (структурированные ответы)

```python
from src.llm.types import GenerationRequest

request = GenerationRequest(
    prompt="""Оцени задачу и верни JSON:
{
  "usefulness_percent": число от 0 до 100,
  "reasoning": "пояснение"
}""",
    response_format={"type": "json_object"}  # JSON режим
)

response = await llm_manager.generate_response(request)
```

**Работа через компоненты:**
1. `StrategyManager` определяет использование параллельной генерации для JSON
2. `ClientManager` отправляет запросы к моделям
3. `JsonValidator` проверяет каждый ответ:
   - Извлекает JSON из markdown кода
   - Валидирует структуру
   - Исправляет malformed JSON
4. `ResponseEvaluator` выбирает лучший валидный JSON ответ
5. Возвращается гарантированно валидный JSON

### Параллельный режим (Best-of-Two)

```python
request = GenerationRequest(
    prompt="Объясни принципы SOLID",
    use_parallel=True  # Включаем параллельный режим
)

response = await llm_manager.generate_response(request)
```

**Параллельное выполнение:**
1. `StrategyManager._generate_parallel()` запускает две модели одновременно
2. `asyncio.gather()` выполняет оба вызова параллельно
3. `ClientManager` обрабатывает API вызовы
4. `JsonValidator` проверяет ответы (если JSON режим)
5. `ResponseEvaluator` сравнивает ответы:
   - Оценивает каждый по критериям качества
   - Выбирает ответ с максимальным score
6. `ModelRegistry` обновляет статистику обеих моделей
7. Возвращается лучший ответ

**Преимущества:**
- Повышение качества ответов (выбирается лучший)
- Повышение надежности (если одна упала, вторая работает)
- Параллельное выполнение не увеличивает время ожидания

## Примеры использования в Code Agent

### Пример 1: Проверка полезности задачи

**Где используется:** `src/server.py` → `_check_task_usefulness()`

```python
from src.llm.manager import LLMManager
from src.llm.types import GenerationRequest

async def check_task_usefulness(self, todo_item: TodoItem) -> Tuple[float, Optional[str]]:
    """Проверяет является ли задача полезной или это мусор"""

    llm_manager = LLMManager()

    prompt = f"""Оцени полезность этого пункта из TODO списка.

ПУНКТ TODO: {todo_item.text}

Оцени полезность задачи в процентах от 0% до 100%:
- 0-15% - это мусор/шум
- 16-50% - слабая полезность
- 51-80% - средняя полезность
- 81-100% - высокая полезность

Верни JSON объект:
{{
  "usefulness_percent": число от 0 до 100,
  "comment": "краткий комментарий"
}}"""

    request = GenerationRequest(
        prompt=prompt,
        response_format={"type": "json_object"},  # Гарантированный JSON
        use_parallel=True  # Лучшее качество для важных решений
    )

    response = await llm_manager.generate_response(request)

    # JsonValidator гарантирует валидный JSON
    json_obj = response.content  # Уже извлечен и провалидирован
    usefulness = json_obj.get('usefulness_percent', 50.0)
    comment = json_obj.get('comment', 'Нет комментария')

    return usefulness, comment
```

**Что делает в новой архитектуре:**
- **JsonValidator** гарантирует валидный JSON ответ
- **ResponseEvaluator** выбирает лучший анализ из параллельных моделей
- **StrategyManager** автоматически использует параллельную генерацию для JSON
- **HealthMonitor** обеспечивает доступность моделей в фоне

### Пример 2: Проверка соответствия TODO плану

**Где используется:** `src/server.py` → `_check_todo_matches_plan()`

```python
async def check_todo_matches_plan(self, task_id: str, todo_item: TodoItem) -> Tuple[bool, Optional[str]]:
    """Проверяет соответствует ли пункт TODO пунктам плана"""

    llm_manager = LLMManager()

    prompt = f"""Проверь, соответствует ли пункт туду пунктам плана.

ПУНКТ ТУДУ: {todo_item.text}

ПЛАН ВЫПОЛНЕНИЯ: {plan_content}

Ответь ТОЛЬКО в формате JSON:
{{
  "matches": true/false,
  "reason": "краткая причина несоответствия (если matches=false)"
}}"""

    request = GenerationRequest(
        prompt=prompt,
        response_format={"type": "json_object"},  # Структурированный ответ
        use_parallel=False,  # Быстрая проверка, качество не критично
        use_fastest=True     # Приоритет скорости
    )

    response = await llm_manager.generate_response(request)

    # Автоматическая JSON валидация и извлечение
    json_obj = response.content
    matches = json_obj.get('matches', True)
    reason = json_obj.get('reason', None)

    return matches, reason
```

**Оптимизации в новой архитектуре:**
- **ModelRegistry** выбирает самую быструю доступную модель
- **JsonValidator** автоматически извлекает JSON из любого формата
- **ConfigLoader** позволяет настроить стратегию под конкретную задачу

## Механизмы отказоустойчивости

### Fallback цепочки

**Принцип работы в новой архитектуре:**

```
User Request
    ↓
StrategyManager._generate_single()
    ↓
ModelRegistry.get_models_by_role(PRIMARY)
    ↓
[PRIMARY модель 1, PRIMARY модель 2, ...]
    ↓
ClientManager.call_model() по очереди
    ↓ (если успех)
JsonValidator.validate_json() [для JSON режима]
    ↓
ModelRegistry.update_model_stats()
    ↓
Return response
    ↓ (если все PRIMARY упали)
DUPLICATE модели
    ↓ (если все DUPLICATE упали)
RESERVE модели
    ↓ (если все RESERVE упали)
FALLBACK модели
    ↓ (все упали)
RuntimeError: All models failed
```

**Реализация через компоненты:**

```python
# StrategyManager._generate_with_fallback()
async def _generate_with_fallback(self, request: GenerationRequest) -> ModelResponse:
    """Генерация с многоуровневой fallback цепочкой"""

    # Порядок ролей: PRIMARY → DUPLICATE → RESERVE → FALLBACK
    roles_order = [ModelRole.PRIMARY, ModelRole.DUPLICATE,
                   ModelRole.RESERVE, ModelRole.FALLBACK]

    for role in roles_order:
        models = self.registry.get_models_by_role(role)

        for model in models:
            try:
                response = await self.client.call_model(model, request.prompt)

                if response.success:
                    # Валидация JSON если требуется
                    if request.response_format:
                        is_valid, extracted = self.validator.validate_and_extract(response.content)
                        if not is_valid:
                            continue  # Пробуем следующую модель

                        response.content = extracted

                    # Обновляем статистику и возвращаем
                    self.registry.update_model_stats(model.name, success=True, response_time=response.response_time)
                    return response

                else:
                    # Модель упала - обновляем статистику ошибок
                    self.registry.update_model_stats(model.name, success=False, response_time=response.response_time)
                    continue

            except Exception as e:
                logger.error(f"Error calling {model.name}: {e}")
                continue

    # Все модели во всех ролях провалились
    raise RuntimeError("All models in fallback chain failed")
```

**Уровни отказоустойчивости:**
1. **Сетевые ошибки**: `ClientManager` обрабатывает таймауты и соединения
2. **API ошибки**: Автоматическое переключение на резервные модели
3. **JSON ошибки**: `JsonValidator` обеспечивает корректные ответы
4. **Мониторинг**: `HealthMonitor` автоматически отключает проблемные модели

### Параллельная генерация (Best-of-Two)

**Одновременное выполнение для качества:**

```
User Request
    ↓
StrategyManager._generate_parallel()
    ↓
asyncio.gather([
    ClientManager.call_model(model1),
    ClientManager.call_model(model2)
])
    ↓
[Response1, Response2]
    ↓
JsonValidator.validate_and_extract() [для каждого]
    ↓
ResponseEvaluator.compare_responses()
    ↓
Выбор по score (relevance, completeness, efficiency)
    ↓
ModelRegistry.update_stats(оба ответа)
    ↓
Return лучший ответ
```

**Реализация через компоненты:**

```python
# StrategyManager._generate_parallel()
async def _generate_parallel(self, request: GenerationRequest) -> ModelResponse:
    """Параллельная генерация с выбором лучшего ответа"""

    # Получаем две модели для параллельного выполнения
    models = self.registry.get_parallel_models()

    # Параллельное выполнение через asyncio.gather
    responses = await asyncio.gather(
        self.client.call_model(models[0], request.prompt),
        self.client.call_model(models[1], request.prompt),
        return_exceptions=True
    )

    # Фильтруем успешные ответы
    valid_responses = []
    for response in responses:
        if isinstance(response, Exception):
            continue  # Пропускаем исключения

        if response.success:
            # JSON валидация если требуется
            if request.response_format:
                is_valid, extracted = self.validator.validate_and_extract(response.content)
                if is_valid:
                    response.content = extracted
                    valid_responses.append(response)
            else:
                valid_responses.append(response)

    # Обработка результатов
    if len(valid_responses) == 1:
        # Только один успешный ответ
        self.registry.update_model_stats(valid_responses[0].model_name, success=True,
                                       response_time=valid_responses[0].response_time)
        return valid_responses[0]

    elif len(valid_responses) == 2:
        # Оба ответа успешны - выбираем лучший
        best_response = await self.evaluator.select_best_response(
            request.prompt, valid_responses
        )

        # Обновляем статистику для обеих моделей
        for resp in valid_responses:
            self.registry.update_model_stats(resp.model_name, success=True,
                                           response_time=resp.response_time)

        return best_response

    else:
        # Все модели провалились - fallback на последовательную генерацию
        return await self._generate_with_fallback(request)
```

**Критерии оценки ResponseEvaluator:**

```python
# ResponseEvaluator.select_best_response()
async def select_best_response(self, prompt: str, responses: List[ModelResponse]) -> ModelResponse:
    """Выбор лучшего ответа на основе комплексной оценки"""

    evaluations = []
    for response in responses:
        score = await self._evaluate_single_response(prompt, response.content)
        evaluations.append((response, score))

    # Выбираем ответ с максимальным score
    best_response, best_score = max(evaluations, key=lambda x: x[1])

    logger.info(f"Selected best response with score {best_score:.2f}")
    return best_response

async def _evaluate_single_response(self, prompt: str, content: str) -> float:
    """Оценка ответа по критериям качества"""

    eval_prompt = f"""Оцени качество ответа на запрос:

ЗАПРОС: {prompt}

ОТВЕТ: {content}

Оцени по шкале 0-10:
- Relevance (релевантность): насколько ответ соответствует запросу
- Completeness (полнота): насколько ответ полный
- Accuracy (точность): насколько ответ точен
- Clarity (ясность): насколько ответ понятен

Верни средний score (число от 0 до 10)."""

    eval_response = await self.client.call_model(self.evaluator_model, eval_prompt)

    try:
        score = float(eval_response.content.strip())
        return min(max(score, 0.0), 10.0)  # Ограничиваем 0-10
    except:
        return 5.0  # Средний score при ошибке парсинга
```

**Преимущества параллельной генерации:**
- **Качество**: Выбор лучшего из нескольких вариантов
- **Надежность**: Работает даже если одна модель упала
- **Производительность**: Время = max(время_модели1, время_модели2), не сумма
- **Резервирование**: Автоматический fallback при проблемах

## Конфигурация новой архитектуры

### Структура конфигурации (`config/llm_settings.yaml`)

```yaml
llm:
  # Общие настройки
  default_provider: openrouter
  request_timeout: 200
  max_retries: 3

  # Настройки компонентов
  components:
    health_monitor:
      enabled: true
      check_interval: 300  # секунд
      failure_threshold: 3

    parallel_generation:
      enabled: true
      default_evaluator: meta-llama/llama-3.2-3b-instruct

  # Конфигурация моделей по ролям
  models:
    primary:
      - name: meta-llama/llama-3.2-1b-instruct
        provider: openrouter
        max_tokens: 4096
        context_window: 8192
        temperature: 0.7
        enabled: true

      - name: microsoft/wizardlm-2-8x22b
        provider: openrouter
        max_tokens: 4096
        context_window: 32768
        temperature: 0.7
        enabled: true

    duplicate:
      - name: google/gemma-2-27b-it
        provider: openrouter
        max_tokens: 8192
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
        context_window: 8192
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
    json_mode: parallel_with_validation  # Специальная стратегия для JSON
```

## Мониторинг и статистика

### HealthMonitor - Фоновый мониторинг

**Автоматическая проверка здоровья моделей:**

```python
# HealthMonitor работает в фоне каждые 5 минут
health_monitor = HealthMonitor(model_registry, client_manager)
await health_monitor.start_monitoring()

# Проверка статуса всех моделей
status = await health_monitor.check_health()
# {
#   "meta-llama/llama-3.2-1b-instruct": "healthy",
#   "microsoft/wizardlm-2-8x22b": "unhealthy",
#   "google/gemma-2-27b-it": "healthy"
# }
```

**Функции мониторинга:**
- Регулярные health checks всех моделей
- Автоматическое отключение проблемных моделей
- Попытки восстановления после временных сбоев
- Уведомления о проблемах со здоровьем

### ModelRegistry - Статистика производительности

**Автоматический сбор метрик:**

```python
# ModelRegistry обновляет статистику после каждого вызова
registry.update_model_stats(
    model_name="meta-llama/llama-3.2-1b-instruct",
    success=True,
    response_time=1.2
)

# Получение статистики для оптимизации
stats = registry.get_model_stats("meta-llama/llama-3.2-1b-instruct")
# {
#   "last_response_time": 1.2,
#   "error_count": 0,
#   "success_count": 150,
#   "success_rate": 1.0,
#   "average_response_time": 1.1
# }
```

## Резюме новой архитектуры

**Модульная архитектура решает следующие задачи:**

### 1. ✅ **Модульность и поддерживаемость**
- 7 специализированных компонентов вместо монолита
- Четкое разделение ответственностей
- Dependency injection для слабой связанности

### 2. ✅ **Надежность и отказоустойчивость**
- Fallback цепочки: PRIMARY → DUPLICATE → RESERVE → FALLBACK
- Параллельное выполнение для резервирования
- Health monitoring с автоматическим восстановлением

### 3. ✅ **Качество и производительность**
- Best-of-two стратегия для улучшения качества
- JsonValidator для гарантированных структурированных ответов
- Автоматический выбор самых быстрых моделей

### 4. ✅ **Расширяемость**
- Легкое добавление новых провайдеров через ClientManager
- Плагинная система стратегий генерации
- Интерфейсы для кастомных компонентов

### 5. ✅ **Тестируемость**
- Изолированное тестирование каждого компонента
- Mock объекты для зависимостей
- Фикстура для интеграционного тестирования

**Ключевые компоненты:**
- **LLMManager**: Фасад для всей системы
- **ModelRegistry**: Управление моделями и статистикой
- **ClientManager**: API клиенты для провайдеров
- **StrategyManager**: Стратегии генерации ответов
- **ResponseEvaluator**: Оценка качества ответов
- **JsonValidator**: Валидация JSON ответов
- **HealthMonitor**: Мониторинг здоровья моделей
- **ConfigLoader**: Загрузка и валидация конфигурации

**Примеры использования в Code Agent:**
- Проверка полезности задач из TODO (с JSON валидацией)
- Проверка соответствия плана и задач
- Любые задачи требующие высокой надежности или качества ответов
