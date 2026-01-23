# Документация по тестированию

Документы, связанные с тестированием проекта Code Agent.

---

## 📄 Основные документы

### [TESTING_GUIDE.md](TESTING_GUIDE.md)
**Полное руководство по тестированию проекта.**

**Содержит:**
- Быстрый старт
- Единая точка входа
- **Запуск тестов по блокам (подробно)**
- Категории тестов
- Опции запуска
- Требования
- Устранение проблем
- Примеры использования

**Рекомендуется начать с этого документа!**

---

---


---

## 📋 Отчеты


---

## 🔗 Связанные документы

### В директории test/

- **[README_RUN_TESTS.md](../../test/README_RUN_TESTS.md)** - Подробная документация по `run_tests.py`
- **[QUICK_START.md](../../test/QUICK_START.md)** - Быстрый старт
- **[API_TESTS_README.md](../../test/API_TESTS_README.md)** - Документация по API тестам
- **[AUTO_SERVER_START.md](../../test/AUTO_SERVER_START.md)** - Автозапуск сервера

### В других директориях

- **Тесты проекта:** [../../test/](../../test/)
- **Решения и отчеты:** [../solutions/](../solutions/)
- **Главная документация:** [../README.md](../README.md)

---

## 🚀 Быстрый старт

### Просмотр всех тестов
```bash
python test/run_tests.py --list
```

### Запуск всех тестов
```bash
python test/run_tests.py
```

### Запуск по блокам
```bash
# OpenRouter тесты
python test/run_tests.py --openrouter

# API тесты
python test/run_tests.py --api

# Cursor тесты
python test/run_tests.py --cursor

# LLM тесты
python test/run_tests.py --llm

# Validation тесты
python test/run_tests.py --validation

# Checkpoint тесты
python test/run_tests.py --checkpoint

# Full Cycle тесты
python test/run_tests.py --full
```

### Через Makefile
```bash
make test-all          # Все тесты
make test-openrouter   # OpenRouter тесты
make test-api          # API тесты
make test-cursor       # Cursor тесты
make test-llm          # LLM тесты
make test-validation   # Validation тесты
make test-checkpoint   # Checkpoint тесты
make test-full         # Full Cycle тесты
```

---

## 📖 Рекомендуемый порядок чтения

1. **[QUICK_START.md](../../test/QUICK_START.md)** - Быстрый старт
2. **[TESTING_GUIDE.md](TESTING_GUIDE.md)** - Полное руководство
3. **[README_RUN_TESTS.md](../../test/README_RUN_TESTS.md)** - Детали по `run_tests.py`
4. **[API_TESTS_README.md](../../test/API_TESTS_README.md)** - Если работаете с API тестами

---

## 🔧 Утилиты

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

## 💡 Поддержка

При проблемах: см. [TESTING_GUIDE.md](TESTING_GUIDE.md) или логи в `logs/`
