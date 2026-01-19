# Исправление безопасности: API ключи

**Дата:** 2026-01-19  
**Статус:** ✅ Завершено

## Проблема

API ключи хранились в конфиг файлах (`config/llm_settings.yaml`), что является нарушением безопасности, так как эти файлы попадают в git репозиторий.

## Решение

### 1. Удален API ключ из конфиг файла

**Файл:** `config/llm_settings.yaml`

**Было:**
```yaml
providers:
  openrouter:
    base_url: https://openrouter.ai/api/v1
    api_key: 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
```

**Стало:**
```yaml
providers:
  openrouter:
    base_url: https://openrouter.ai/api/v1
    # api_key должен быть в переменной окружения OPENROUTER_API_KEY или в .env файле
    # api_key: ${OPENROUTER_API_KEY}
```

### 2. Обновлен код для чтения из переменных окружения

#### `src/llm/llm_manager.py`

- Добавлена проверка переменной окружения `OPENROUTER_API_KEY`
- Fallback на конфиг с предупреждением (для обратной совместимости)
- Выброс исключения, если ключ не найден

**Изменения:**
```python
# API ключ должен быть в переменной окружения, а не в конфиге
api_key = os.getenv('OPENROUTER_API_KEY')
if not api_key:
    # Fallback на конфиг (для обратной совместимости, но не рекомендуется)
    api_key = provider_config.get('api_key')
    if api_key:
        logger.warning("API key found in config file. Please move it to OPENROUTER_API_KEY environment variable or .env file for security.")

if not api_key:
    raise ValueError(
        f"API key not found for provider '{default_provider}'. "
        f"Please set OPENROUTER_API_KEY environment variable or add it to .env file."
    )
```

#### `src/llm/model_discovery.py`

- Аналогичные изменения для чтения API ключа из переменных окружения
- Предупреждение при использовании ключа из конфига

### 3. Обновлены тестовые файлы

#### `test/test_openrouter_api.py`
- Удалено чтение API ключа из конфига
- Используется только переменная окружения

#### `test/test_openrouter_detailed.py`
- Использует LLMManager, который теперь читает из переменных окружения

### 4. Создана документация

**Файл:** `docs/guides/API_KEYS_SETUP.md`

Содержит:
- Инструкции по настройке API ключей
- Примеры использования
- Troubleshooting
- Рекомендации по безопасности

## Проверка

✅ API ключи удалены из конфиг файлов  
✅ Код обновлен для чтения из переменных окружения  
✅ Тестовые файлы обновлены  
✅ Документация создана  
✅ `.env` файл в `.gitignore` (уже было)

## Как использовать

### Вариант 1: Переменная окружения

```bash
export OPENROUTER_API_KEY=sk-or-v1-your-key-here
```

### Вариант 2: .env файл

Создайте `.env` в корне проекта:
```env
OPENROUTER_API_KEY=sk-or-v1-your-key-here
```

## Обратная совместимость

Код поддерживает fallback на конфиг файл для обратной совместимости, но выдает предупреждение:

```
WARNING: API key found in config file. Please move it to OPENROUTER_API_KEY environment variable or .env file for security.
```

**Рекомендация:** Переместите все API ключи в `.env` файл или переменные окружения.

## Безопасность

- ✅ API ключи не хранятся в конфиг файлах
- ✅ `.env` файл в `.gitignore`
- ✅ Код требует явной установки ключа
- ✅ Предупреждения при использовании старого способа

## Следующие шаги

1. Убедитесь, что все API ключи перемещены в `.env` файл
2. Проверьте, что `.env` файл не попадает в git (уже в `.gitignore`)
3. Обновите документацию проекта, если необходимо
4. Уведомите команду о необходимости обновить их `.env` файлы
