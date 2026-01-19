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

### Только OpenRouter тесты
```bash
python test/run_tests.py --openrouter
# или
make test-openrouter
```

### Только HTTP API тесты
```bash
# Сначала запустите сервер в отдельной консоли:
python main.py

# Затем запустите тесты:
python test/run_tests.py --api
# или
make test-api
```

### Только Cursor тесты
```bash
python test/run_tests.py --cursor
# или
make test-cursor
```

## Комбинирование

```bash
# OpenRouter + API
python test/run_tests.py --openrouter --api

# OpenRouter + LLM
python test/run_tests.py --openrouter --llm

# Все кроме полного цикла
python test/run_tests.py --openrouter --api --cursor --llm --validation --checkpoint
```

## Режимы вывода

### Минимальный вывод (только итоги)
```bash
python test/run_tests.py --openrouter --quiet
```

### Без вывода тестов (только результаты)
```bash
python test/run_tests.py --openrouter --no-output
```

## Помощь

```bash
python test/run_tests.py --help
```
