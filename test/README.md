# Тесты Code Agent

Эта директория содержит все тесты для проекта Code Agent.

## Быстрый старт

```bash
# Запуск всех тестов
pytest test/ -v

# Запуск с покрытием
pytest test/ --cov=src --cov-report=html
```

## Структура тестов

### Тесты установки
- `check_setup.py` - Проверка корректности установки
- `test_agent_installation.py` - Тесты установки агента
- `test_cursor_agent_setup.py` - Тесты настройки Cursor

### Тесты интеграции с Cursor
- `test_cursor_integration_only.py` - Изолированные тесты интеграции
- `test_cursor_feedback.py` - Тесты обратной связи
- `test_real_cursor_cli.py` - Тесты Cursor CLI
- `test_real_cursor_execution.py` - Тесты выполнения в Cursor
- `test_simple_cursor_task.py` - Простые тесты задач

### Тесты CrewAI
- `test_crewai_scenario.py` - Тесты сценариев CrewAI

### Тесты LLM
- `test_llm_real.py` - Тесты реальных LLM
- `test_model_discovery_and_update.py` - Тесты обнаружения моделей

### Тесты сервера
- `test_server_execution.py` - Тесты работы сервера

### Интеграционные тесты
- `test_full_cycle.py` - Полный цикл выполнения
- `test_full_cycle_with_server.py` - Полный цикл с сервером

### Тесты Docker
- `test_docker_agent.py` - Тесты Docker-контейнера

## Запуск по категориям

```bash
# Только быстрые тесты
pytest test/ -m "not slow" -v

# Только unit-тесты
pytest test/ -m unit -v

# Только интеграционные тесты
pytest test/ -m integration -v

# Тесты Cursor
pytest test/ -m cursor -v

# Тесты LLM
pytest test/ -m llm -v
```

## Подробная документация

Полная документация по тестированию: [../docs/testing/TESTING.md](../docs/testing/TESTING.md)

## Требования

```bash
# Установка зависимостей для тестов
pip install pytest pytest-cov pytest-mock pytest-asyncio
```

## Маркеры тестов

Используйте маркеры для категоризации тестов:

```python
import pytest

@pytest.mark.slow
def test_long_operation():
    pass

@pytest.mark.integration
@pytest.mark.cursor
def test_cursor_integration():
    pass
```

## CI/CD

Тесты автоматически запускаются в CI/CD pipeline при каждом коммите.

Минимальное требование к покрытию кода: **80%**
