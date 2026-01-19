# Запуск тестов Code Agent

## Единая точка входа

Все тесты запускаются через единый скрипт:

```bash
python test/run_tests.py [опции]
```

## Быстрый старт

### Просмотр всех доступных тестов
```bash
python test/run_tests.py --list
```

### Запуск всех тестов
```bash
python test/run_tests.py
```

### Запуск конкретных категорий

**Только OpenRouter тесты:**
```bash
python test/run_tests.py --openrouter
```

**Только HTTP API тесты:**
```bash
python test/run_tests.py --api
```

**Только Cursor тесты:**
```bash
python test/run_tests.py --cursor
```

**Только LLM тесты:**
```bash
python test/run_tests.py --llm
```

**Валидация конфигурации:**
```bash
python test/run_tests.py --validation
```

**Тесты checkpoint:**
```bash
python test/run_tests.py --checkpoint
```

**Полный цикл:**
```bash
python test/run_tests.py --full
```

### Комбинирование категорий

**Несколько категорий одновременно:**
```bash
python test/run_tests.py --openrouter --api --cursor
```

**OpenRouter + LLM:**
```bash
python test/run_tests.py --openrouter --llm
```

## Опции запуска

### Минимальный вывод (только итоги)
```bash
python test/run_tests.py --openrouter --quiet
```

### Без вывода тестов (только результаты)
```bash
python test/run_tests.py --openrouter --no-output
```

## Категории тестов

### `--openrouter` - OpenRouter API
Тестирование OpenRouter API, LLMManager, генерация инструкций:
- Базовый тест OpenRouter API
- Детальное тестирование LLMManager
- Реальное тестирование LLM (генерация, fallback, параллельный режим)
- Обнаружение и обновление моделей
- CrewAI сценарий с параллельными моделями

### `--api` - HTTP API Server
Тестирование HTTP API сервера и endpoints:
- Тестирование API endpoints (сервер должен быть запущен)
- Интеграционное тестирование сервера

**Примечание:** Для тестов API сервер должен быть запущен:
```bash
# В отдельной консоли
python main.py
```

### `--cursor` - Cursor Integration
Тестирование интеграции с Cursor IDE:
- Простая задача через Cursor
- Реальное выполнение через Cursor CLI
- Интеграция с Cursor (только файловый интерфейс)
- Гибридный интерфейс (CLI + файловый)

### `--llm` - LLM Core
Тестирование базовой функциональности LLM:
- Реальное тестирование LLMManager
- Обнаружение и обновление моделей

### `--validation` - Validation
Тестирование валидации конфигурации и безопасности:
- Комплексная валидация конфигурации

### `--checkpoint` - Checkpoint
Тестирование системы checkpoint:
- Интеграционное тестирование checkpoint
- Восстановление после сбоя

### `--full` - Full Cycle
Полный цикл работы агента:
- Полный цикл выполнения задачи
- Полный цикл с сервером

## Примеры использования

### Быстрая проверка OpenRouter
```bash
python test/run_tests.py --openrouter
```

### Проверка API сервера (после запуска сервера)
```bash
# Терминал 1: Запуск сервера
python main.py

# Терминал 2: Запуск тестов
python test/run_tests.py --api
```

### Полная проверка перед коммитом
```bash
python test/run_tests.py --openrouter --api --validation
```

### Только критичные тесты
```bash
python test/run_tests.py --openrouter --api --quiet
```

## Формат вывода

Тесты выводят:
- ✅ `[OK]` - успешные тесты
- ❌ `[FAIL]` - проваленные тесты
- ⚠️ `[WARN]` - предупреждения
- ℹ️ `[INFO]` - информация

В конце выводится итоговый отчет с:
- Статистикой по категориям
- Общей статистикой
- Списком проваленных тестов
- Общим временем выполнения

## Требования

- Python 3.10+
- Все зависимости из `requirements-test.txt`
- Для тестов OpenRouter: валидный `OPENROUTER_API_KEY`
- Для тестов API: запущенный сервер (`python main.py`)
- Для тестов Cursor: настроенный Cursor IDE

## Устранение проблем

### Тесты падают с ошибкой импорта
Убедитесь, что вы запускаете из корня проекта:
```bash
cd /path/to/codeAgent
python test/run_tests.py
```

### OpenRouter тесты падают с 401
Проверьте API ключ:
```bash
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('Key:', bool(os.getenv('OPENROUTER_API_KEY')))"
```

### API тесты не могут подключиться
Убедитесь, что сервер запущен:
```bash
curl http://127.0.0.1:3456/health
```

### Проблемы с кодировкой в Windows
Скрипт автоматически устанавливает UTF-8 кодировку для Windows.
