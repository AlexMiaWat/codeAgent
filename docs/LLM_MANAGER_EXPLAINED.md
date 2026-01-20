# Как работает LLMManager

## Обзор

`LLMManager` - это интеллектуальный менеджер для работы с несколькими LLM моделями одновременно. Он автоматически выбирает оптимальную модель, обрабатывает ошибки через fallback, и может использовать несколько моделей параллельно для повышения качества ответов.

## Архитектура

### Основные компоненты

1. **ModelRole** - роли моделей:
   - `PRIMARY` - основные рабочие модели (быстрые, надежные)
   - `DUPLICATE` - дублирующие модели (резервные копии primary)
   - `RESERVE` - резервные модели (на случай проблем с primary)
   - `FALLBACK` - модели последнего шанса (если все остальные упали)

2. **ModelConfig** - конфигурация модели:
   - Параметры модели (max_tokens, temperature, top_p)
   - Статистика (last_response_time, error_count, success_count)
   - Роль модели в системе

3. **ModelResponse** - ответ модели:
   - Содержимое ответа
   - Время ответа
   - Успешность выполнения
   - Оценка качества (score) - для параллельного режима

## Как это работает

### 1. Инициализация

```python
from src.llm.llm_manager import LLMManager

# Создаем менеджер (загружает конфигурацию из config/llm_settings.yaml)
llm_manager = LLMManager(config_path="config/llm_settings.yaml")
```

**Что происходит:**
- Загружается конфигурация из YAML файла
- Инициализируются модели с их ролями (primary, duplicate, reserve, fallback)
- Создаются клиенты для провайдеров (OpenRouter)
- Модели отсортированы по ролям для fallback цепочки

### 2. Базовое использование (одна модель)

```python
response = await llm_manager.generate_response(
    prompt="Привет, как дела?",
    use_fastest=True,  # Использовать самую быструю модель
    use_parallel=False  # Не использовать параллельный режим
)

if response.success:
    print(f"Ответ: {response.content}")
    print(f"Модель: {response.model_name}")
    print(f"Время: {response.response_time:.2f}s")
```

**Что происходит:**
1. Выбирается самая быстрая PRIMARY модель (по `last_response_time`)
2. Если модель упала → автоматически пробуется следующая в fallback цепочке
3. Fallback цепочка: PRIMARY → DUPLICATE → RESERVE → FALLBACK
4. Возвращается первый успешный ответ

### 3. JSON Mode (структурированные ответы)

```python
json_format = {"type": "json_object"}

response = await llm_manager.generate_response(
    prompt="""Оцени полезность задачи.

ЗАДАЧА: Реализовать поиск по документам

Верни JSON:
{
  "usefulness_percent": число от 0 до 100,
  "comment": "комментарий"
}""",
    use_fastest=True,
    response_format=json_format  # Включаем JSON mode
)

# LLMManager автоматически:
# 1. Проверяет что ответ валидный JSON
# 2. Если модель вернула не-JSON → пробует следующую модель
# 3. Извлекает JSON из markdown code fences если нужно
```

**Что происходит:**
1. Запрос отправляется с `response_format={"type": "json_object"}`
2. Если модель вернула невалидный JSON → автоматически пробуется следующая модель
3. JSON извлекается из markdown (```json ... ```) если нужно
4. Возвращается валидный JSON ответ

### 4. Параллельный режим (best_of_two)

```python
response = await llm_manager.generate_response(
    prompt="Объясни что такое async/await в Python",
    use_parallel=True  # Включаем параллельный режим
)
```

**Что происходит:**
1. Две модели запускаются **параллельно** (одновременно)
2. Обе модели генерируют ответы независимо
3. Модель-оценщик оценивает качество каждого ответа (0-10)
4. Выбирается ответ с максимальной оценкой
5. Если одна модель упала → используется ответ второй
6. Если обе упали → запускается fallback цепочка

**Преимущества:**
- Повышение качества ответов (выбирается лучший)
- Повышение надежности (если одна упала, вторая работает)
- Параллельное выполнение не увеличивает время ожидания

## Примеры использования в Code Agent

### Пример 1: Проверка полезности задачи

**Где используется:** `src/server.py` → `_check_task_usefulness()`

```python
def _check_task_usefulness(self, todo_item: TodoItem) -> Tuple[float, Optional[str]]:
    """Проверяет является ли задача полезной или это мусор"""
    
    llm_manager = LLMManager(config_path="config/llm_settings.yaml")
    
    check_prompt = f"""Оцени полезность этого пункта из TODO списка.

ПУНКТ TODO:
{todo_item.text}

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
    
    json_format = {"type": "json_object"}
    
    response = await llm_manager.generate_response(
        prompt=check_prompt,
        use_fastest=True,
        use_parallel=False,
        response_format=json_format
    )
    
    # Парсим JSON ответ
    json_obj = extract_json_object(response.content)
    usefulness = json_obj.get('usefulness_percent', 50.0)
    comment = json_obj.get('comment', 'Нет комментария')
    
    return usefulness, comment
```

**Что делает:**
- Фильтрует мусор из TODO списков
- Оценивает полезность каждой задачи
- Использует JSON mode для структурированного ответа
- Автоматически переключается на другую модель если текущая не справилась

### Пример 2: Проверка соответствия TODO плану

**Где используется:** `src/server.py` → `_check_todo_matches_plan()`

```python
def _check_todo_matches_plan(self, task_id: str, todo_item: TodoItem) -> Tuple[bool, Optional[str]]:
    """Проверяет соответствует ли пункт TODO пунктам плана"""
    
    llm_manager = LLMManager(config_path="config/llm_settings.yaml")
    
    check_prompt = f"""Проверь, соответствует ли пункт туду пунктам плана.

ПУНКТ ТУДУ:
{todo_item.text}

ПЛАН ВЫПОЛНЕНИЯ:
{plan_content}

Ответь ТОЛЬКО в формате JSON:
{{
  "matches": true/false,
  "reason": "краткая причина несоответствия (если matches=false)"
}}"""
    
    response = await llm_manager.generate_response(
        prompt=check_prompt,
        use_fastest=True,
        use_parallel=False
    )
    
    # Извлекаем JSON из ответа
    json_obj = extract_json_object(response.content)
    matches = json_obj.get('matches', True)
    reason = json_obj.get('reason', None)
    
    return matches, reason
```

**Что делает:**
- Проверяет что TODO пункты соответствуют плану выполнения
- Предотвращает выполнение лишних задач
- Использует LLM для семантического сравнения

## Механизм дублирования и совместного решения

### 1. Fallback цепочка (последовательное дублирование)

**Как работает:**

```
Запрос → PRIMARY модель 1
         ↓ (упала)
         PRIMARY модель 2
         ↓ (упала)
         DUPLICATE модель 1
         ↓ (упала)
         DUPLICATE модель 2
         ↓ (упала)
         RESERVE модель 1
         ↓ (упала)
         FALLBACK модель 1
         ↓ (упала)
         FALLBACK модель 2
         ↓ (все упали)
         ОШИБКА: All models failed
```

**Пример из кода:**

```python
async def _generate_with_fallback(
    self,
    prompt: str,
    primary_model: ModelConfig,
    response_format: Optional[Dict[str, Any]] = None
) -> ModelResponse:
    """Генерация с fallback на резервные модели"""
    
    # Собираем все модели в порядке приоритета
    models_to_try = [primary_model] + self.get_fallback_models()
    # Порядок: PRIMARY → DUPLICATE → RESERVE → FALLBACK
    
    for model_config in models_to_try:
        try:
            response = await self._call_model(prompt, model_config, response_format=response_format)
            
            if response.success:
                # Если JSON mode - проверяем валидность
                if response_format and response_format.get("type") == "json_object":
                    if self._validate_json_response(response.content):
                        return response  # Успех!
                    else:
                        # Невалидный JSON - пробуем следующую модель
                        logger.warning(f"Model {model_config.name} returned invalid JSON. Trying next...")
                        continue
                else:
                    return response  # Успех!
            else:
                # Модель упала - пробуем следующую
                logger.warning(f"Model {model_config.name} failed: {response.error}")
                continue
                
        except Exception as e:
            # Ошибка при вызове - пробуем следующую
            logger.error(f"Error calling model {model_config.name}: {e}")
            continue
    
    # Все модели провалились
    raise RuntimeError("All models failed to generate response")
```

**Преимущества:**
- Автоматическое переключение при ошибках
- Повышение надежности системы
- Прозрачная обработка ошибок для пользователя

### 2. Параллельное дублирование (best_of_two)

**Как работает:**

```
Запрос → [Модель 1] ──┐
         [Модель 2] ──┼──→ [Модель-оценщик] ──→ Лучший ответ
         (параллельно) ┘
```

**Пример из кода:**

```python
async def _generate_parallel(
    self, 
    prompt: str,
    response_format: Optional[Dict[str, Any]] = None
) -> ModelResponse:
    """Параллельная генерация через две модели с выбором лучшего ответа"""
    
    # Получаем две модели для параллельного использования
    model1, model2 = parallel_models[0], parallel_models[1]
    
    # Запускаем ОДНОВРЕМЕННО (не последовательно!)
    responses = await asyncio.gather(
        self._call_model(prompt, model1, response_format=response_format),
        self._call_model(prompt, model2, response_format=response_format),
        return_exceptions=True
    )
    
    # Фильтруем успешные ответы
    valid_responses = []
    for resp in responses:
        if resp.success:
            # Проверяем валидность JSON если нужно
            if response_format and response_format.get("type") == "json_object":
                if self._validate_json_response(resp.content):
                    valid_responses.append(resp)
            else:
                valid_responses.append(resp)
    
    if len(valid_responses) == 1:
        return valid_responses[0]  # Одна модель сработала
    
    if len(valid_responses) == 2:
        # Обе модели сработали - выбираем лучший
        return await self._select_best_response(valid_responses, prompt, parallel_config)
    
    # Обе упали - используем fallback
    return await self._generate_with_fallback(prompt, model1, response_format=response_format)
```

**Выбор лучшего ответа:**

```python
async def _select_best_response(
    self,
    responses: List[ModelResponse],
    prompt: str,
    parallel_config: Dict
) -> ModelResponse:
    """Выбор лучшего ответа через оценку моделью-оценщиком"""
    
    evaluator_model = self.models[parallel_config.get('evaluator_model')]
    
    # Оцениваем каждый ответ (0-10)
    for response in responses:
        score = await self._evaluate_response(
            prompt, response.content, evaluator_model
        )
        response.score = score
    
    # Выбираем ответ с максимальным score
    best_response = max(responses, key=lambda r: r.score or 0.0)
    
    return best_response
```

**Преимущества:**
- Повышение качества ответов (выбирается лучший)
- Повышение надежности (если одна упала, вторая работает)
- Время выполнения = время самой медленной модели (не сумма!)

## Конфигурация моделей

### Пример конфигурации (`config/llm_settings.yaml`)

```yaml
llm:
  default_provider: openrouter
  strategy: best_of_two  # Использовать параллельный режим по умолчанию
  
  model_roles:
    primary:
      - meta-llama/llama-3.2-1b-instruct      # Быстрая, надежная
      - microsoft/wizardlm-2-8x22b             # Альтернатива
    
    duplicate:
      - google/gemma-2-27b-it                  # Резервная копия primary
      - undi95/remm-slerp-l2-13b
    
    reserve:
      - mistralai/mistral-small-24b-instruct-2501  # На случай проблем
    
    fallback:
      - meta-llama/llama-3.2-3b-instruct       # Последний шанс
      - kwaipilot/kat-coder-pro:free
  
  parallel:
    enabled: true
    models:
      - meta-llama/llama-3.2-1b-instruct
      - microsoft/phi-3-mini-128k-instruct
    evaluator_model: meta-llama/llama-3.2-3b-instruct  # Модель для оценки ответов
```

## Статистика и мониторинг

LLMManager автоматически собирает статистику по каждой модели:

- `last_response_time` - время последнего ответа (для выбора самой быстрой)
- `error_count` - количество ошибок
- `success_count` - количество успешных запросов

Это позволяет:
- Автоматически выбирать самую быструю модель
- Отслеживать проблемные модели
- Оптимизировать производительность

## Резюме

**LLMManager решает следующие задачи:**

1. ✅ **Автоматический выбор модели** - выбирает самую быструю из доступных
2. ✅ **Обработка ошибок** - автоматически переключается на резервные модели
3. ✅ **JSON mode** - гарантирует валидные JSON ответы с fallback
4. ✅ **Параллельное выполнение** - использует две модели одновременно для лучшего качества
5. ✅ **Оценка ответов** - выбирает лучший ответ через модель-оценщик
6. ✅ **Статистика** - отслеживает производительность моделей

**Механизм дублирования:**

- **Последовательное (fallback)**: PRIMARY → DUPLICATE → RESERVE → FALLBACK
- **Параллельное (best_of_two)**: Две модели одновременно → выбор лучшего через оценщика

**Примеры использования в Code Agent:**

- Проверка полезности задач из TODO
- Проверка соответствия TODO пунктов плану
- Любые задачи требующие структурированных JSON ответов
