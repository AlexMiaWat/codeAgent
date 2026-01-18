# Тестирование Code Agent

Полное руководство по тестированию проекта Code Agent.

## Структура тестов

Все тесты находятся в директории `test/`:

```
test/
├── __init__.py                          # Инициализация пакета тестов
├── check_setup.py                       # Проверка корректности установки
├── cursor_commands/                     # Тестовые команды для Cursor
│   └── instruction_test_001_NEW_CHAT.txt
├── test_agent_installation.py           # Тесты установки агента
├── test_crewai_scenario.py              # Тесты сценариев CrewAI
├── test_cursor_agent_setup.py           # Тесты настройки Cursor агента
├── test_cursor_feedback.py              # Тесты обратной связи от Cursor
├── test_cursor_integration_only.py      # Тесты интеграции с Cursor
├── test_docker_agent.py                 # Тесты Docker-контейнера
├── test_full_cycle.py                   # Полный цикл выполнения задач
├── test_full_cycle_with_server.py       # Полный цикл с сервером
├── test_llm_real.py                     # Тесты реальных LLM
├── test_model_discovery_and_update.py   # Тесты обнаружения моделей
├── test_real_cursor_cli.py              # Тесты Cursor CLI
├── test_real_cursor_execution.py        # Тесты выполнения в Cursor
├── test_server_execution.py             # Тесты работы сервера
└── test_simple_cursor_task.py           # Простые тесты задач Cursor
```

## Категории тестов

### 1. Тесты установки и настройки

#### `check_setup.py`
Проверяет корректность установки и конфигурации проекта:
- Наличие всех необходимых зависимостей
- Корректность файлов конфигурации
- Доступность директорий проекта

**Запуск:**
```bash
python test/check_setup.py
```

#### `test_agent_installation.py`
Тестирует процесс установки агента:
- Установка зависимостей
- Создание необходимых файлов
- Инициализация компонентов

**Запуск:**
```bash
pytest test/test_agent_installation.py -v
```

#### `test_cursor_agent_setup.py`
Проверяет настройку интеграции с Cursor:
- Конфигурация Cursor CLI
- Настройка путей
- Проверка доступности команд

**Запуск:**
```bash
pytest test/test_cursor_agent_setup.py -v
```

### 2. Тесты интеграции с Cursor

#### `test_cursor_integration_only.py`
Изолированные тесты интеграции с Cursor:
- Отправка команд в Cursor
- Чтение результатов
- Обработка файлов-репортов

**Запуск:**
```bash
pytest test/test_cursor_integration_only.py -v
```

#### `test_cursor_feedback.py`
Тестирует механизм обратной связи от Cursor:
- Чтение файлов-репортов
- Парсинг результатов
- Обработка ошибок

**Запуск:**
```bash
pytest test/test_cursor_feedback.py -v
```

#### `test_real_cursor_cli.py`
Тесты реального Cursor CLI:
- Выполнение команд через CLI
- Проверка статусов выполнения
- Обработка таймаутов

**Запуск:**
```bash
pytest test/test_real_cursor_cli.py -v
```

#### `test_real_cursor_execution.py`
Тесты реального выполнения задач в Cursor:
- Создание инструкций
- Мониторинг выполнения
- Получение результатов

**Запуск:**
```bash
pytest test/test_real_cursor_execution.py -v
```

#### `test_simple_cursor_task.py`
Простые тесты выполнения задач:
- Базовые операции
- Простые инструкции
- Быстрые проверки

**Запуск:**
```bash
pytest test/test_simple_cursor_task.py -v
```

### 3. Тесты CrewAI

#### `test_crewai_scenario.py`
Тестирует сценарии работы CrewAI:
- Создание агентов
- Выполнение задач
- Координация между агентами

**Запуск:**
```bash
pytest test/test_crewai_scenario.py -v
```

### 4. Тесты LLM

#### `test_llm_real.py`
Тесты работы с реальными языковыми моделями:
- Подключение к LLM провайдерам
- Генерация ответов
- Обработка ошибок API

**Запуск:**
```bash
pytest test/test_llm_real.py -v
```

**Примечание:** Требуется наличие API ключей в `.env` файле.

#### `test_model_discovery_and_update.py`
Тесты обнаружения и обновления моделей:
- Автоматическое обнаружение доступных моделей
- Обновление конфигурации
- Валидация настроек

**Запуск:**
```bash
pytest test/test_model_discovery_and_update.py -v
```

### 5. Тесты сервера

#### `test_server_execution.py`
Тесты работы основного сервера:
- Запуск сервера
- Обработка задач
- Управление состоянием

**Запуск:**
```bash
pytest test/test_server_execution.py -v
```

### 6. Интеграционные тесты

#### `test_full_cycle.py`
Полный цикл выполнения задачи:
- Чтение задачи из todo
- Создание инструкций для Cursor
- Выполнение через Cursor
- Обновление статуса

**Запуск:**
```bash
pytest test/test_full_cycle.py -v
```

#### `test_full_cycle_with_server.py`
Полный цикл с запущенным сервером:
- Запуск сервера агента
- Выполнение задач
- Мониторинг процесса
- Проверка результатов

**Запуск:**
```bash
pytest test/test_full_cycle_with_server.py -v
```

### 7. Тесты Docker

#### `test_docker_agent.py`
Тесты Docker-контейнера агента:
- Сборка образа
- Запуск контейнера
- Выполнение задач в контейнере
- Проверка персистентности данных

**Запуск:**
```bash
pytest test/test_docker_agent.py -v
```

**Требования:**
- Установленный Docker
- Docker Compose (опционально)

## Запуск тестов

### Запуск всех тестов

```bash
# Запуск всех тестов
pytest test/ -v

# С покрытием кода
pytest test/ --cov=src --cov-report=html

# С подробным выводом
pytest test/ -vv -s
```

### Запуск по категориям

```bash
# Только тесты интеграции с Cursor
pytest test/test_cursor_*.py -v

# Только тесты полного цикла
pytest test/test_full_cycle*.py -v

# Только быстрые тесты (без LLM и Docker)
pytest test/ -v -m "not slow"
```

### Запуск с фильтрами

```bash
# Запуск конкретного теста
pytest test/test_simple_cursor_task.py::test_function_name -v

# Запуск тестов по паттерну
pytest test/ -k "cursor" -v

# Запуск с остановкой на первой ошибке
pytest test/ -x
```

## Настройка окружения для тестов

### Создание `.env.test`

Создайте файл `.env.test` для тестового окружения:

```env
# Тестовая директория проекта
PROJECT_DIR=D:\Space\test_project

# API ключи для тестов (опционально)
OPENAI_API_KEY=test_key_here
ANTHROPIC_API_KEY=test_key_here

# Настройки для тестов
TEST_MODE=true
LOG_LEVEL=DEBUG
```

### Использование тестовых фикстур

Тесты используют pytest фикстуры для подготовки окружения:

```python
# Пример использования фикстур
def test_example(tmp_path, mock_cursor_cli):
    # tmp_path - временная директория
    # mock_cursor_cli - мок Cursor CLI
    pass
```

## Мокирование

### Мокирование Cursor CLI

Для тестов без реального Cursor используйте моки:

```python
from unittest.mock import Mock, patch

@patch('src.cursor_cli_interface.CursorCLI')
def test_with_mock(mock_cli):
    mock_cli.execute.return_value = "Success"
    # Ваш тест
```

### Мокирование LLM

Для тестов без реальных API вызовов:

```python
@patch('src.llm.llm_manager.LLMManager.generate')
def test_with_mock_llm(mock_generate):
    mock_generate.return_value = "Mocked response"
    # Ваш тест
```

## Continuous Integration (CI)

### GitHub Actions

Пример конфигурации `.github/workflows/tests.yml`:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.10'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-cov
    
    - name: Run tests
      run: pytest test/ --cov=src --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v2
```

## Покрытие кода

### Генерация отчета о покрытии

```bash
# HTML отчет
pytest test/ --cov=src --cov-report=html

# Открыть отчет
open htmlcov/index.html  # macOS/Linux
start htmlcov/index.html  # Windows
```

### Минимальное покрытие

Проект стремится к покрытию не менее 80%:

```bash
pytest test/ --cov=src --cov-fail-under=80
```

## Отладка тестов

### Использование pdb

```bash
# Запуск с отладчиком
pytest test/test_example.py --pdb

# Остановка на первой ошибке с отладчиком
pytest test/ -x --pdb
```

### Вывод логов

```bash
# Показать все логи
pytest test/ -v -s --log-cli-level=DEBUG

# Сохранить логи в файл
pytest test/ --log-file=test_run.log
```

## Лучшие практики

### 1. Изоляция тестов
- Каждый тест должен быть независимым
- Используйте фикстуры для подготовки данных
- Очищайте временные файлы после тестов

### 2. Именование тестов
- Используйте префикс `test_` для всех тестовых функций
- Имена должны описывать проверяемое поведение
- Группируйте связанные тесты в классы

### 3. Параметризация
```python
@pytest.mark.parametrize("input,expected", [
    ("hello", "HELLO"),
    ("world", "WORLD"),
])
def test_upper(input, expected):
    assert input.upper() == expected
```

### 4. Маркеры
```python
@pytest.mark.slow
def test_long_running():
    # Долгий тест
    pass

@pytest.mark.integration
def test_full_system():
    # Интеграционный тест
    pass
```

### 5. Документирование тестов
```python
def test_example():
    """
    Проверяет, что функция корректно обрабатывает входные данные.
    
    Given: Входные данные в определенном формате
    When: Функция вызывается с этими данными
    Then: Результат соответствует ожидаемому
    """
    pass
```

## Troubleshooting

### Проблема: Тесты не находят модули

**Решение:**
```bash
# Установите проект в режиме разработки
pip install -e .

# Или добавьте путь в PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"  # Linux/macOS
set PYTHONPATH=%PYTHONPATH%;%CD%  # Windows
```

### Проблема: Тесты Cursor падают с таймаутом

**Решение:**
- Увеличьте таймаут в конфигурации
- Проверьте, что Cursor запущен
- Используйте моки для быстрых тестов

### Проблема: Тесты LLM требуют API ключи

**Решение:**
- Используйте `.env.test` с тестовыми ключами
- Мокируйте LLM вызовы для unit-тестов
- Пропускайте тесты без ключей: `@pytest.mark.skipif(not has_api_key, reason="No API key")`

## Дополнительные ресурсы

- [Pytest документация](https://docs.pytest.org/)
- [Coverage.py](https://coverage.readthedocs.io/)
- [Unittest.mock](https://docs.python.org/3/library/unittest.mock.html)
- [CrewAI Testing Guide](https://docs.crewai.com/testing/)

## Контрибьюция

При добавлении новых тестов:

1. Следуйте существующей структуре
2. Добавьте документацию к тесту
3. Убедитесь, что тест проходит локально
4. Проверьте покрытие кода
5. Обновите эту документацию при необходимости
