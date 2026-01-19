# Запуск тестов Code Agent

## Единая точка входа

Все тесты запускаются через единый скрипт:

```bash
python test/run_tests.py [опции]
```

---

## Быстрый старт

### Просмотр всех доступных тестов
```bash
python test/run_tests.py --list
# или
make test-list
```

### Запуск всех тестов
```bash
python test/run_tests.py
# или
make test-all
```

---

## Запуск тестов по блокам

### 1. OpenRouter API тесты

**Описание:** Тестирование OpenRouter API, обнаружение моделей через OpenRouter API, CrewAI сценарии.

```bash
python test/run_tests.py --openrouter
# или
make test-openrouter
```

**Включает:**
- `test_openrouter_api.py` - Базовый тест OpenRouter API (60s)
- `test_openrouter_detailed.py` - Детальное тестирование LLMManager (120s)
- `test_model_discovery_and_update.py` - Обнаружение и обновление моделей через OpenRouter API (600s)
- `test_crewai_scenario.py` - CrewAI сценарий с параллельными моделями (300s)

**Требования:**
- Валидный `OPENROUTER_API_KEY` в `.env` файле

---

### 2. HTTP API Server тесты

**Описание:** Тестирование HTTP API сервера и endpoints.

```bash
python test/run_tests.py --api
# или
make test-api
```

**Включает:**
- `test_server_api_only.py` - Тестирование API endpoints (60s)
  - Требует запущенного сервера
- `test_real_server_integration.py` - Интеграционное тестирование сервера (120s)
  - Автоматически запускает сервер, если он не запущен

**Требования:**
- Сервер должен быть запущен (или будет запущен автоматически)

**Запуск сервера:**
```bash
# В отдельной консоли
python main.py
```

---

### 3. Cursor Integration тесты

**Описание:** Тестирование интеграции с Cursor IDE.

```bash
python test/run_tests.py --cursor
# или
make test-cursor
```

**Включает (только автоматизированные тесты):**
- `test_real_cursor_cli.py` - Реальное выполнение через Cursor CLI (600s) - ✅ Полностью автоматизирован
- `test_hybrid_interface.py` - Гибридный интерфейс (300s) - ✅ Полностью автоматизирован

**Исключены (требуют ручного участия):**
- `test_simple_cursor_task.py` - Требует ручного выполнения в Cursor IDE
- `test_cursor_integration_only.py` - Требует ручного выполнения в Cursor IDE

**Требования:**
- Docker Desktop (для тестов через Docker контейнер)
- Cursor CLI доступен через Docker контейнер `cursor-agent-life`
- Docker Desktop (для тестов через Docker контейнер)

**Важно о Docker контейнере:**
- Тесты автоматически создают и запускают Docker контейнер `cursor-agent-life` при необходимости
- Контейнер остается активным после выполнения команд (это нормально)
- Контейнер использует команду `while true; do sleep 3600; done` для постоянной работы
- Статус контейнера проверяется до и после каждого теста
- При ошибках автоматически выводятся логи контейнера для диагностики

**Проверка статуса контейнера вручную:**
```bash
# Проверка статуса
docker ps -a | grep cursor-agent-life

# Просмотр логов
docker logs cursor-agent-life --tail 50

# Остановка контейнера (если нужно)
docker stop cursor-agent-life

# Удаление контейнера (если нужно)
docker rm cursor-agent-life
```

---

### 4. LLM Core тесты

**Описание:** Тестирование базовой функциональности LLM.

```bash
python test/run_tests.py --llm
# или
make test-llm
```

**Включает:**
- `test_llm_real.py` - Реальное тестирование LLMManager (генерация, fallback, параллельный режим) (300s)

**Требования:**
- Валидный `OPENROUTER_API_KEY`

---

### 5. Validation тесты

**Описание:** Тестирование валидации конфигурации и безопасности.

```bash
python test/run_tests.py --validation
# или
make test-validation
```

**Включает:**
- `test_comprehensive_validation.py` - Комплексная валидация конфигурации (120s)

---

### 6. Checkpoint тесты

**Описание:** Тестирование системы checkpoint.

```bash
python test/run_tests.py --checkpoint
# или
make test-checkpoint
```

**Включает:**
- `test_checkpoint_integration.py` - Интеграционное тестирование checkpoint (120s)
- `test_checkpoint_recovery.py` - Восстановление после сбоя (180s)

---

### 7. Full Cycle тесты

**Описание:** Полный цикл работы агента.

```bash
python test/run_tests.py --full
# или
make test-full
```

**Включает:**
- `test_full_cycle.py` - Полный цикл выполнения задачи (600s)
- `test_full_cycle_with_server.py` - Полный цикл с сервером (600s)

---

## Комбинирование категорий

**Несколько категорий одновременно:**
```bash
# OpenRouter + API
python test/run_tests.py --openrouter --api

# OpenRouter + LLM
python test/run_tests.py --openrouter --llm

# API + Validation
python test/run_tests.py --api --validation

# Все кроме полного цикла
python test/run_tests.py --openrouter --api --cursor --llm --validation --checkpoint
```

---

## Опции запуска

### Режимы вывода

**Минимальный вывод (только итоги):**
```bash
python test/run_tests.py --openrouter --quiet
```

**Без вывода тестов (только результаты):**
```bash
python test/run_tests.py --openrouter --no-output
```

**Подробный вывод (по умолчанию):**
```bash
python test/run_tests.py --openrouter --verbose
```

### Справка

```bash
python test/run_tests.py --help
```

---

## Категории тестов

### Полный список

| Категория | Флаг | Описание | Тестов |
|-----------|------|----------|--------|
| OpenRouter API | `--openrouter` | Тестирование OpenRouter API, обнаружение моделей | 4 |
| HTTP API Server | `--api` | Тестирование HTTP API сервера | 2 |
| Cursor Integration | `--cursor` | Тестирование интеграции с Cursor IDE (автоматизированные) | 2 |
| LLM Core | `--llm` | Тестирование базовой функциональности LLM | 1 |
| Validation | `--validation` | Валидация конфигурации и безопасности | 1 |
| Checkpoint | `--checkpoint` | Тестирование системы checkpoint | 2 |
| Full Cycle | `--full` | Полный цикл работы агента | 2 |

---

## Примеры использования

### Быстрая проверка перед коммитом
```bash
python test/run_tests.py --openrouter --api --validation --quiet
```

### Полная проверка всех компонентов
```bash
python test/run_tests.py
```

### Проверка только OpenRouter
```bash
python test/run_tests.py --openrouter
```

### Проверка API сервера
```bash
# Терминал 1: Запуск сервера
python main.py

# Терминал 2: Запуск тестов
python test/run_tests.py --api
```

### Проверка после изменений в LLM
```bash
python test/run_tests.py --openrouter --llm
```

---

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

---

## Требования

- Python 3.10+
- Все зависимости из `requirements-test.txt`
- Для тестов OpenRouter: валидный `OPENROUTER_API_KEY`
- Для тестов API: запущенный сервер (`python main.py`)
- Для тестов Cursor: настроенный Cursor IDE

---

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
python test/verify_api_key.py
# или
python -c "import os; from dotenv import load_dotenv; load_dotenv(override=True); print('Key:', bool(os.getenv('OPENROUTER_API_KEY')))"
```

### API тесты не могут подключиться
Убедитесь, что сервер запущен:
```bash
python test/check_server.py
# или
curl http://127.0.0.1:3456/health
```

### Проблемы с кодировкой в Windows
Скрипт автоматически устанавливает UTF-8 кодировку для Windows.

---

## Дополнительные утилиты

### Проверка API ключа
```bash
python test/verify_api_key.py
```

### Проверка сервера
```bash
python test/check_server.py
```

### Сравнение ключей
```bash
python test/compare_keys.py
```

---

## Связанные документы

- [QUICK_START.md](QUICK_START.md) - Быстрый старт
- [API_TESTS_README.md](API_TESTS_README.md) - Документация по API тестам
- [AUTO_SERVER_START.md](AUTO_SERVER_START.md) - Автозапуск сервера
- [../docs/testing/TESTING_GUIDE.md](../docs/testing/TESTING_GUIDE.md) - Полное руководство по тестированию
