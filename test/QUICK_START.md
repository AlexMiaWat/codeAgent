# Быстрый старт тестирования

## Самые частые команды

### Просмотр всех тестов
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

## Запуск по блокам

### OpenRouter тесты
```bash
python test/run_tests.py --openrouter
# или
make test-openrouter
```

### HTTP API тесты
```bash
# Сначала запустите сервер в отдельной консоли:
python main.py

# Затем запустите тесты:
python test/run_tests.py --api
# или
make test-api
```

### Cursor тесты
```bash
python test/run_tests.py --cursor
# или
make test-cursor
```

### LLM тесты
```bash
python test/run_tests.py --llm
# или
make test-llm
```

### Validation тесты
```bash
python test/run_tests.py --validation
# или
make test-validation
```

### Checkpoint тесты
```bash
python test/run_tests.py --checkpoint
# или
make test-checkpoint
```

### Full Cycle тесты
```bash
python test/run_tests.py --full
# или
make test-full
```

---

## Комбинирование

```bash
# OpenRouter + API
python test/run_tests.py --openrouter --api

# OpenRouter + LLM
python test/run_tests.py --openrouter --llm

# Все кроме полного цикла
python test/run_tests.py --openrouter --api --cursor --llm --validation --checkpoint
```

---

## Режимы вывода

### Минимальный вывод (только итоги)
```bash
python test/run_tests.py --openrouter --quiet
```

### Без вывода тестов (только результаты)
```bash
python test/run_tests.py --openrouter --no-output
```

---

## Помощь

```bash
python test/run_tests.py --help
```

---

## Все команды через Makefile

```bash
make test-all          # Все тесты
make test-list         # Список тестов
make test-openrouter   # OpenRouter тесты
make test-api          # API тесты
make test-cursor       # Cursor тесты
make test-llm          # LLM тесты
make test-validation   # Validation тесты
make test-checkpoint   # Checkpoint тесты
make test-full         # Full Cycle тесты
```

---

## Быстрая проверка перед коммитом

```bash
# Только критичные тесты
python test/run_tests.py --openrouter --api --validation --quiet
```

---

## Подробная документация

- [README_RUN_TESTS.md](README_RUN_TESTS.md) - Полная документация
- [../docs/testing/TESTING_GUIDE.md](../docs/testing/TESTING_GUIDE.md) - Полное руководство
