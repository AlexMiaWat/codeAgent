# Полное руководство по тестированию Code Agent

**Дата обновления:** 2026-01-19  
**Версия:** 2.0

---

## Содержание

1. [Быстрый старт](#быстрый-старт)
2. [Единая точка входа](#единая-точка-входа)
3. [Запуск тестов по блокам](#запуск-тестов-по-блокам)
4. [Категории тестов](#категории-тестов)
5. [Опции запуска](#опции-запуска)
6. [Требования](#требования)
7. [Устранение проблем](#устранение-проблем)
8. [Примеры использования](#примеры-использования)

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

### Запуск через Makefile

Все команды доступны через `make`:

```bash
make test-all          # Все тесты
make test-openrouter   # OpenRouter тесты
make test-api          # API тесты
make test-cursor       # Cursor тесты
make test-llm          # LLM тесты
make test-validation   # Валидация
make test-checkpoint   # Checkpoint тесты
make test-full         # Полный цикл
make test-smart        # Smart Agent тесты
```

---

## Единая точка входа

Все тесты запускаются через единый скрипт:

```bash
python test/run_tests.py [опции]
```

Этот скрипт:
- ✅ Управляет всеми тестами проекта
- ✅ Группирует тесты по категориям
- ✅ Предоставляет цветной вывод
- ✅ Генерирует итоговые отчеты
- ✅ Поддерживает различные режимы вывода

---

## Запуск тестов по блокам

### 1. OpenRouter API тесты

**Описание:** Тестирование OpenRouter API, обнаружение моделей через OpenRouter API, CrewAI сценарии.

**Запуск:**
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
- Валидный `OPENROUTER_API_KEY` в `.env` файле или переменных окружения

**Пример вывода:**
```
[OK] Тест пройден: test_openrouter_api.py (3.29s)
[OK] Тест пройден: test_openrouter_detailed.py (14.01s)
...
```

---

### 2. HTTP API Server тесты

**Описание:** Тестирование HTTP API сервера и endpoints.

**Запуск:**
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
- Доступ к порту 3456

**Запуск сервера:**
```bash
# В отдельной консоли
python main.py
```

**Пример вывода:**
```
[INFO] Сервер уже запущен, используем существующий
[OK] Тест пройден: test_server_api_only.py (2.15s)
[OK] Тест пройден: test_real_server_integration.py (5.42s)
```

---

### 3. Cursor Integration тесты

**Описание:** Тестирование интеграции с Cursor IDE.

**Запуск:**
```bash
python test/run_tests.py --cursor
# или
make test-cursor
```

**Включает (только автоматизированные тесты):**
- `test_real_cursor_cli.py` - Реальное выполнение через Cursor CLI (600s) - ✅ Полностью автоматизирован
- `test_hybrid_interface.py` - Гибридный интерфейс (CLI + файловый) (300s) - ✅ Полностью автоматизирован

**Исключены (требуют ручного участия):**
- `test_simple_cursor_task.py` - Требует ручного выполнения в Cursor IDE
- `test_cursor_integration_only.py` - Требует ручного выполнения в Cursor IDE

**Требования:**
- Docker Desktop (для тестов через Docker контейнер)
- Cursor CLI доступен через Docker контейнер `cursor-agent-life`

**Важно о Docker контейнере:**
- Тесты автоматически создают и запускают Docker контейнер `cursor-agent-life` при необходимости
- Контейнер остается активным после выполнения команд (это нормально и ожидаемо)
- Контейнер использует команду `while true; do sleep 3600; done` для постоянной работы
- Статус контейнера проверяется до и после каждого теста с подробным выводом
- При ошибках автоматически выводятся логи контейнера для диагностики

**Проверка статуса контейнера:**
```bash
# Проверка статуса
docker ps -a | grep cursor-agent-life

# Просмотр логов
docker logs cursor-agent-life --tail 50

# Остановка контейнера (если нужно)
docker stop cursor-agent-life
```

**Диагностика проблем:**
Если контейнер не активен после выполнения тестов:
1. Проверьте логи: `docker logs cursor-agent-life`
2. Проверьте статус: `docker inspect cursor-agent-life`
3. Перезапустите контейнер: `docker restart cursor-agent-life`

---

### 4. LLM Core тесты

**Описание:** Тестирование базовой функциональности LLM.

**Запуск:**
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

**Запуск:**
```bash
python test/run_tests.py --validation
# или
make test-validation
```

**Включает:**
- `test_comprehensive_validation.py` - Комплексная валидация конфигурации (120s)

**Проверяет:**
- Валидацию конфигурации при старте
- Обработку ошибок
- Безопасность (валидация путей, проверка прав доступа)
- Валидацию YAML схемы
- Определение формата TODO

---

### 6. Checkpoint тесты

**Описание:** Тестирование системы checkpoint.

**Запуск:**
```bash
python test/run_tests.py --checkpoint
# или
make test-checkpoint
```

**Включает:**
- `test_checkpoint_integration.py` - Интеграционное тестирование checkpoint (120s)
- `test_checkpoint_recovery.py` - Восстановление после сбоя (180s)

**Проверяет:**
- Сохранение состояния
- Восстановление после перезапуска
- Работу с чекпоинтами

---

### 7. Full Cycle тесты

**Описание:** Полный цикл работы агента.

**Запуск:**
```bash
python test/run_tests.py --full
# или
make test-full
```

**Включает:**
- `test_full_cycle.py` - Полный цикл выполнения задачи (600s)
- `test_full_cycle_with_server.py` - Полный цикл с сервером (600s)

**Проверяет:**
- Полный цикл выполнения задачи
- Интеграцию всех компонентов
- Работу с сервером

---

## Комбинирование блоков

Можно запускать несколько блоков одновременно:

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

### Полный список категорий

| Категория | Флаг | Описание | Тестов |
|-----------|------|----------|--------|
| OpenRouter API | `--openrouter` | Тестирование OpenRouter API, LLMManager | 5 |
| HTTP API Server | `--api` | Тестирование HTTP API сервера | 2 |
| Cursor Integration | `--cursor` | Тестирование интеграции с Cursor IDE | 4 |
| LLM Core | `--llm` | Тестирование базовой функциональности LLM | 2 |
| Validation | `--validation` | Валидация конфигурации и безопасности | 1 |
| Checkpoint | `--checkpoint` | Тестирование системы checkpoint | 2 |
| Full Cycle | `--full` | Полный цикл работы агента | 2 |
| Smart Agent | `--smart` | ✅ **НОВОЕ** - Тестирование Smart Agent с Docker поддержкой | 6 |

---

## Требования

### Обязательные

- **Python 3.10+**
- **Все зависимости** из `requirements-test.txt`
- **Настроенный `.env` файл** с необходимыми переменными

### Для конкретных блоков

**OpenRouter тесты:**
- Валидный `OPENROUTER_API_KEY` в `.env` или переменных окружения

**API тесты:**
- Запущенный сервер (`python main.py`) или автоматический запуск

**Cursor тесты:**
- Настроенный Cursor IDE
- Доступ к Cursor CLI

**Validation тесты:**
- Настроенный `PROJECT_DIR` в `.env`

**Smart Agent тесты:**
- ✅ **НОВОЕ** - Доступ к Docker (опционально, fallback режим при недоступности)
- Настроенная директория опыта `smart_experience/` (создается автоматически)
- Установленная библиотека `crewai[tools]` для CodeInterpreterTool

---

## Устранение проблем

### Тесты падают с ошибкой импорта

**Проблема:** `ModuleNotFoundError: No module named 'src'`

**Решение:**
```bash
# Убедитесь, что вы запускаете из корня проекта
cd /path/to/codeAgent
python test/run_tests.py
```

### OpenRouter тесты падают с 401

**Проблема:** `Error code: 401 - User not found`

**Решение:**
1. Проверьте API ключ:
```bash
python test/verify_api_key.py
```

2. Убедитесь, что ключ в `.env` файле:
```bash
# Проверка ключа
python -c "import os; from dotenv import load_dotenv; load_dotenv(override=True); print('Key:', bool(os.getenv('OPENROUTER_API_KEY')))"
```

3. Обновите ключ в `.env` файле и перезапустите тесты

### API тесты не могут подключиться

**Проблема:** `ConnectionError` или `Connection refused`

**Решение:**
1. Проверьте, запущен ли сервер:
```bash
python test/check_server.py
```

2. Запустите сервер:
```bash
# В отдельной консоли
python main.py
```

3. Или используйте тест с автозапуском:
```bash
python test/test_real_server_integration.py
```

### Проблемы с кодировкой в Windows

**Проблема:** Кракозябры в выводе

**Решение:**
Скрипт автоматически устанавливает UTF-8 кодировку для Windows. Если проблема сохраняется:
```bash
# Установите переменную окружения
set PYTHONIOENCODING=utf-8
python test/run_tests.py
```

### Тест провалился, но не понятно почему

**Решение:**
1. Запустите тест напрямую:
```bash
python test/test_openrouter_detailed.py
```

2. Используйте подробный вывод:
```bash
python test/run_tests.py --openrouter --verbose
```

3. Проверьте логи в `logs/` директории

---

## Примеры использования

### Быстрая проверка перед коммитом

```bash
# Только критичные тесты
python test/run_tests.py --openrouter --api --validation --quiet
```

### Полная проверка всех компонентов

```bash
# Все тесты
python test/run_tests.py
```

### Проверка только OpenRouter

```bash
# Только OpenRouter тесты
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
# OpenRouter + LLM тесты
python test/run_tests.py --openrouter --llm
```

### Проверка валидации и безопасности

```bash
# Validation тесты
python test/run_tests.py --validation
```

---

## Формат вывода

### Цветные метки

- ✅ `[OK]` - успешные тесты
- ❌ `[FAIL]` - проваленные тесты
- ⚠️ `[WARN]` - предупреждения
- ℹ️ `[INFO]` - информация

### Итоговый отчет

В конце выводится итоговый отчет с:
- Статистикой по категориям
- Общей статистикой
- Списком проваленных тестов
- Общим временем выполнения

**Пример:**
```
================================================================================
ИТОГОВЫЙ ОТЧЕТ
================================================================================

По категориям:

  OpenRouter API:
    Пройдено: 5/5
    Время: 131.84s

Общая статистика:
  Всего тестов: 5
  Пройдено: 5
  Общее время: 131.84s

[OK] ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!
```

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

### Сравнение ключей в тестах и сервере

```bash
python test/compare_keys.py
```

---

## Связанные документы

- [README_RUN_TESTS.md](../../test/README_RUN_TESTS.md) - Подробная документация по `run_tests.py`
- [QUICK_START.md](../../test/QUICK_START.md) - Быстрый старт
- [API_TESTS_README.md](../../test/API_TESTS_README.md) - Документация по API тестам
- [AUTO_SERVER_START.md](../../test/AUTO_SERVER_START.md) - Автозапуск сервера
- [API_KEY_STATUS.md](API_KEY_STATUS.md) - Статус API ключа

---

## Обновления

**2026-01-19:**
- ✅ Добавлена принудительная перезагрузка переменных окружения (`load_dotenv(override=True)`)
- ✅ Улучшена обработка ошибок в тестах
- ✅ Добавлены утилиты для проверки API ключа
- ✅ Обновлена документация по запуску тестов по блокам

---

## Поддержка

При возникновении проблем:
1. Проверьте настройки в `.env`
2. Убедитесь, что все зависимости установлены
3. Проверьте логи в `logs/` директории
4. Запустите тест напрямую для детальной диагностики
