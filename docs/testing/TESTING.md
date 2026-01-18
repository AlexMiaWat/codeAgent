# Тестирование Code Agent - Краткое руководство

## Быстрый старт

### Установка зависимостей для тестов

```bash
# Установка всех тестовых зависимостей
pip install -e ".[test]"

# Или через Makefile
make install-test
```

### Запуск тестов

```bash
# Все тесты
pytest test/ -v

# Или через Makefile
make test
```

## Основные команды

### Запуск по категориям

```bash
# Unit-тесты (быстрые)
pytest test/ -m unit -v
make test-unit

# Интеграционные тесты
pytest test/ -m integration -v
make test-integration

# Без медленных тестов (по умолчанию)
pytest test/ -m "not slow" -v

# Только медленные тесты
pytest test/ -m slow -v
make test-slow
```

### Запуск с покрытием

```bash
# С HTML отчетом
pytest test/ --cov=src --cov-report=html
make test-coverage

# Открыть отчет
start htmlcov/index.html  # Windows
open htmlcov/index.html   # macOS
xdg-open htmlcov/index.html  # Linux
```

### Параллельный запуск

```bash
# Автоматическое определение количества процессов
pytest test/ -n auto
make test-parallel

# Указать количество процессов
pytest test/ -n 4
```

### Запуск конкретных тестов

```bash
# Один файл
pytest test/test_example.py -v

# Один тест
pytest test/test_example.py::test_project_root_exists -v

# По паттерну
pytest test/ -k "cursor" -v

# По маркеру
pytest test/ -m cursor -v
```

## Структура тестов

```
test/
├── __init__.py                    # Инициализация пакета
├── conftest.py                    # Общие фикстуры
├── test_example.py                # Пример тестов
├── test_*_installation.py         # Тесты установки
├── test_*_cursor_*.py             # Тесты Cursor
├── test_*_llm_*.py                # Тесты LLM
├── test_*_full_cycle*.py          # Интеграционные тесты
└── cursor_commands/               # Тестовые команды
```

## Маркеры тестов

- `@pytest.mark.unit` - Unit-тесты
- `@pytest.mark.integration` - Интеграционные тесты
- `@pytest.mark.slow` - Медленные тесты
- `@pytest.mark.cursor` - Требуют Cursor IDE
- `@pytest.mark.llm` - Требуют LLM API
- `@pytest.mark.docker` - Требуют Docker

## Фикстуры

Доступные фикстуры (см. `test/conftest.py`):

- `project_root_path` - Путь к корню проекта
- `temp_project_dir` - Временная директория проекта
- `mock_config` - Мок конфигурации
- `mock_cursor_cli` - Мок Cursor CLI
- `mock_llm_manager` - Мок LLM менеджера
- `mock_todo_manager` - Мок TODO менеджера
- `sample_todo_content` - Пример TODO контента
- `sample_status_content` - Пример статуса
- `sample_cursor_report` - Пример отчета Cursor

## Отладка

```bash
# С отладчиком
pytest test/ --pdb

# С логами
pytest test/ -v -s --log-cli-level=DEBUG

# Остановка на первой ошибке
pytest test/ -x

# Показать самые медленные тесты
pytest test/ --durations=10
```

## CI/CD

Тесты автоматически запускаются в GitHub Actions при:
- Push в ветки `main` и `develop`
- Создании Pull Request

См. `.github/workflows/tests.yml`

## Покрытие кода

Минимальное требование: **80%**

Проверка:
```bash
pytest test/ --cov=src --cov-fail-under=80
```

## Дополнительная информация

Полная документация: [docs/testing.md](docs/testing.md)

## Troubleshooting

### Проблема: Модули не найдены

```bash
# Установите проект в режиме разработки
pip install -e .
```

### Проблема: Тесты падают с таймаутом

```bash
# Используйте маркер slow или увеличьте таймаут
pytest test/ --timeout=300
```

### Проблема: Нет API ключей для LLM

```bash
# Пропустите LLM тесты
pytest test/ -m "not llm"

# Или создайте .env.test с ключами
```

## Контрибьюция

При добавлении новых тестов:

1. ✅ Следуйте структуре существующих тестов
2. ✅ Используйте фикстуры из `conftest.py`
3. ✅ Добавьте соответствующие маркеры
4. ✅ Документируйте сложные тесты
5. ✅ Проверьте покрытие кода
6. ✅ Запустите `make pre-commit` перед коммитом
