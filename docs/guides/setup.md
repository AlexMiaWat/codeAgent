# Руководство по настройке Code Agent

## Быстрый старт

### 1. Установка зависимостей

```bash
# Использование pip
pip install crewai crewai-tools pyyaml python-dotenv

# Или с использованием uv (рекомендуется)
uv pip install crewai crewai-tools pyyaml python-dotenv
```

### 2. Настройка переменных окружения

Code Agent работает с двумя директориями:
1. **`codeAgent/`** - сам агент (код, конфигурация).
2. **`${PROJECT_DIR}`** - целевой проект, над которым работает агент.

**Создание `.env` файла:**
1. Скопируйте шаблон: `cp .env.example .env`
2. Отредактируйте `.env`:
   ```env
   PROJECT_DIR=D:\Space\your-project
   OPENROUTER_API_KEY=your_key_here
   ```

### 3. Настройка конфигурации

Отредактируйте `config/config.yaml`:
```yaml
project:
  base_dir: ${PROJECT_DIR}
  docs_dir: docs
  status_file: codeAgentProjectStatus.md
```

### 4. Подготовка целевого проекта

В `PROJECT_DIR` должен быть файл задач (`todo.md`, `todo.txt` или `todo.yaml`).

**Пример `todo.md`:**
```markdown
# Задачи
- [ ] Инициализировать проект
- [ ] Настроить окружение
```

### 5. Запуск агента

```bash
python main.py
```

HTTP API доступен по адресу: `http://127.0.0.1:3456`

## Использование различных провайдеров LLM

Code Agent поддерживает множество провайдеров через `LLMManager`. Подробное описание настройки моделей см. в [LLM Management](../core/llm_management.md).

**Основные провайдеры:**
- **OpenAI**: Укажите `OPENAI_API_KEY`.
- **Anthropic**: Укажите `ANTHROPIC_API_KEY`.
- **OpenRouter**: Укажите `OPENROUTER_API_KEY` (рекомендуется).
- **Google AI Studio**: Укажите `GOOGLE_API_KEY`.
- **Ollama**: Укажите `OLLAMA_API_URL` для локальных моделей.

## Устранение неполадок

### Ошибка: "Директория проекта не найдена"
Проверьте `PROJECT_DIR` в `.env` и существование пути.

### Ошибка: "Файл todo не найден"
Убедитесь, что в проекте есть `todo.md`, `todo.txt` или `todo.yaml`.

### Агент не выполняет задачи
Проверьте логи в `logs/code_agent.log` и файл статусов `codeAgentProjectStatus.md`.

## Дополнительные ресурсы
- [Архитектура](../core/architecture.md)
- [API Reference](../core/api.md)
- [Интеграция с Cursor](../integration/cursor_integration.md)
