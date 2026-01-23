# Отчет об ошибках OpenRouter API
**Дата:** 2026-01-23 12:52:00
**Задача:** 1769170727
**Статус:** Критическая ошибка

## Описание проблемы

API ключ OpenRouter недействителен или истек. Все запросы к API возвращают ошибку 401:

```
Error code: 401 - {'error': {'message': 'User not found.', 'code': 401}}
```

## Затрагиваемые компоненты

1. **OpenRouter API тесты:**
   - `test_openrouter_api.py` - базовый тест API
   - `test_openrouter_detailed.py` - детальное тестирование
   - `test_model_discovery_and_update.py` - обнаружение моделей

2. **LLM тесты:**
   - `test_llm_real.py` - реальное тестирование LLMManager
   - `test_llm_json_mode.py` - тестирование JSON mode
   - `test_llm_json_mode_blacklist.py` - тестирование blacklist

3. **Интеграционные сценарии:**
   - `test_crewai_scenario.py` - CrewAI сценарии

## Детали ошибки

### Тест OpenRouter API
```
Тест 1: Проверка доступности API...
[FAIL] Ошибка при обращении к API:
  Error code: 401 - {'error': {'message': 'User not found.', 'code': 401}}
```

### Тесты моделей
Все модели возвращают одинаковую ошибку:
- `meta-llama/llama-3.2-1b-instruct`
- `microsoft/phi-3-mini-128k-instruct`
- `microsoft/wizardlm-2-8x22b`

```
[FAIL] Error code: 401 - {'error': {'message': 'User not found.', 'code': 401}}
```

## Возможные причины

1. **Недействительный API ключ:** Ключ истек или был отозван
2. **Проблемы с аккаунтом:** Аккаунт заблокирован или удален
3. **Отсутствие квот:** Закончились бесплатные кредиты или квоты
4. **Региональные ограничения:** API недоступен из текущего региона

## Текущее состояние

❌ **Критическая ошибка** - LLM функциональность недоступна

## Рекомендации по исправлению

1. **Проверка API ключа:**
   ```bash
   # Проверить переменную окружения
   echo $OPENROUTER_API_KEY

   # Или проверить через скрипт
   python test/verify_api_key.py
   ```

2. **Обновление API ключа:**
   - Зайти на https://openrouter.ai/keys
   - Создать новый API ключ
   - Обновить `.env` файл

3. **Проверка аккаунта:**
   - Убедиться, что аккаунт активен
   - Проверить баланс/квоты
   - Проверить статус подписки

4. **Альтернативные решения:**
   - Использовать mock/stub для тестов
   - Настроить локальную LLM (Ollama)
   - Использовать другие API провайдеров

## Влияние на тестирование

- **OpenRouter блок:** 4 теста полностью недоступны
- **LLM блок:** 3 теста недоступны
- **Общее тестирование:** ~50% функциональности недоступно

## Модели в конфигурации

Конфигурация содержит 7 моделей, но ни одна не работает из-за проблем с API ключом:

**Primary модели:**
- meta-llama/llama-3.2-1b-instruct
- meta-llama/llama-3.2-3b-instruct
- microsoft/wizardlm-2-8x22b
- microsoft/phi-3-mini-128k-instruct
- google/gemma-2-27b-it

**Fallback модели:**
- kwaipilot/kat-coder-pro:free
- undi95/remm-slerp-l2-13b