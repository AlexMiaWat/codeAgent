# Настройка API ключей

## Безопасность

**ВАЖНО:** API ключи никогда не должны храниться в конфиг файлах, которые попадают в git репозиторий!

API ключи должны храниться только в:
- Переменных окружения
- Файле `.env` (который в `.gitignore`)

## Настройка OpenRouter API

### 1. Получение API ключа

1. Зарегистрируйтесь на [OpenRouter](https://openrouter.ai/)
2. Перейдите в [Keys](https://openrouter.ai/keys)
3. Создайте новый API ключ
4. Скопируйте ключ (начинается с `sk-or-v1-...`)

### 2. Установка API ключа

#### Вариант A: Через переменную окружения (рекомендуется)

**Linux/macOS:**
```bash
export OPENROUTER_API_KEY=sk-or-v1-your-key-here
```

**Windows (PowerShell):**
```powershell
$env:OPENROUTER_API_KEY="sk-or-v1-your-key-here"
```

**Windows (CMD):**
```cmd
set OPENROUTER_API_KEY=sk-or-v1-your-key-here
```

#### Вариант B: Через .env файл (рекомендуется для разработки)

Создайте файл `.env` в корне проекта:

```env
OPENROUTER_API_KEY=sk-or-v1-your-key-here
```

Файл `.env` уже добавлен в `.gitignore`, поэтому он не попадет в git.

### 3. Проверка настройки

Запустите тест:

```bash
PYTHONPATH=. python test/test_openrouter_api.py
```

Если все настроено правильно, вы увидите:
```
[OK] API ключ найден в переменной окружения OPENROUTER_API_KEY
```

## Конфигурация

В файле `config/llm_settings.yaml` API ключ **не должен** быть указан:

```yaml
providers:
  openrouter:
    base_url: https://openrouter.ai/api/v1
    # api_key должен быть в переменной окружения OPENROUTER_API_KEY или в .env файле
    # api_key: ${OPENROUTER_API_KEY}  # НЕ ИСПОЛЬЗУЙТЕ ЭТО!
    models:
      ...
```

Код автоматически будет искать ключ в переменной окружения `OPENROUTER_API_KEY`.

## Как это работает

1. Код сначала проверяет переменную окружения `OPENROUTER_API_KEY`
2. Если ключ не найден, выводится ошибка с инструкцией
3. Для обратной совместимости код может проверить конфиг, но выдаст предупреждение

## Примеры использования

### В коде

```python
from src.llm.llm_manager import LLMManager

# LLMManager автоматически использует OPENROUTER_API_KEY из переменных окружения
mgr = LLMManager('config/llm_settings.yaml')

# Если ключ не найден, будет выброшено исключение:
# ValueError: API key not found for provider 'openrouter'. 
# Please set OPENROUTER_API_KEY environment variable or add it to .env file.
```

### В тестах

```python
import os
from dotenv import load_dotenv

load_dotenv()  # Загружает .env файл

# Ключ автоматически загружается из .env или переменных окружения
api_key = os.getenv('OPENROUTER_API_KEY')
```

## Troubleshooting

### Ошибка: "API key not found"

**Решение:**
1. Убедитесь, что переменная окружения установлена:
   ```bash
   echo $OPENROUTER_API_KEY  # Linux/macOS
   echo %OPENROUTER_API_KEY%  # Windows CMD
   ```
2. Проверьте наличие `.env` файла в корне проекта
3. Убедитесь, что `.env` файл содержит:
   ```
   OPENROUTER_API_KEY=sk-or-v1-your-key-here
   ```

### Ошибка: "User not found" (401)

Это означает, что API ключ недействителен:
1. Проверьте правильность ключа
2. Убедитесь, что ключ активен на OpenRouter
3. Проверьте наличие средств/квот на аккаунте

### Предупреждение: "API key found in config file"

Это означает, что в конфиг файле все еще есть API ключ (для обратной совместимости).

**Решение:**
1. Удалите `api_key` из `config/llm_settings.yaml`
2. Переместите ключ в `.env` файл или переменную окружения

## Безопасность

- ✅ **Правильно:** API ключ в `.env` файле (в `.gitignore`)
- ✅ **Правильно:** API ключ в переменных окружения
- ❌ **Неправильно:** API ключ в конфиг файлах (попадает в git)
- ❌ **Неправильно:** API ключ в коде

## Дополнительные провайдеры

Если вы добавляете поддержку других провайдеров, следуйте тому же принципу:

```yaml
providers:
  openai:
    base_url: https://api.openai.com/v1
    # api_key должен быть в OPENAI_API_KEY
  anthropic:
    base_url: https://api.anthropic.com
    # api_key должен быть в ANTHROPIC_API_KEY
```

И в коде:

```python
api_key = os.getenv('OPENAI_API_KEY')  # или ANTHROPIC_API_KEY
```
