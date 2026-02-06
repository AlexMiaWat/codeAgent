# Структура проекта Code Agent

**Дата обновления:** 2026-02-05
**Версия:** 3.1 (Актуализация структуры)

---

## 📁 Иерархия проекта

```
codeAgent/
├── 📄 README.md                          # Основная документация проекта
├── 📄 main.py                            # Точка входа в приложение
├── 📄 Makefile                           # Команды для сборки и тестирования
├── 📄 pyproject.toml                     # Конфигурация Python проекта
├── 📄 requirements.txt                   # Зависимости Python
├── 📄 runtime.txt                        # Указание версии Python для PaaS
├── 📄 pytest.ini                         # Конфигурация pytest
├── 📄 pyrightconfig.json                 # Конфигурация Pyright (типизация)
├── 📄 smoke_check.py                     # Скрипт проверки окружения
├── 📄 .env.example                       # Пример переменных окружения
├── 📄 .gitignore                         # Исключения Git
├── 📄 .pre-commit-config.yaml            # Конфигурация pre-commit хуков
│
├── 📂 src/                              # Исходный код
│   ├── __init__.py
│   ├── server.py                        # Основной сервер Code Agent
│   ├── config_loader.py                 # Загрузчик конфигурации
│   ├── config_validator.py              # Валидатор конфигурации
│   ├── todo_manager.py                  # Менеджер TODO задач
│   ├── cursor_cli_interface.py          # CLI интерфейс для Cursor
│   ├── cursor_file_interface.py         # Файловый интерфейс для Cursor
│   ├── hybrid_cursor_interface.py       # Гибридный интерфейс
│   ├── checkpoint_manager.py            # Менеджер контрольных точек
│   ├── fallback_state_manager.py        # Менеджер состояния fallback
│   ├── git_utils.py                     # Утилиты Git
│   ├── prompt_formatter.py              # Форматирование промптов
│   ├── security_utils.py                # Утилиты безопасности
│   ├── session_tracker.py               # Трекер сессий
│   ├── status_manager.py                # Менеджер статусов проекта
│   ├── task_logger.py                   # Логирование задач
│   ├── 📂 agents/                       # Агенты CrewAI
│   │   ├── __init__.py
│   │   ├── executor_agent.py            # Агент-исполнитель
│   │   └── gemini_agent/                # Агент для Gemini API
│   │       ├── gemini_agent_cli.py
│   │       ├── gemini_cli_interface.py
│   │       └── hybrid_gemini_interface.py
│   ├── 📂 llm/                          # Менеджеры и обертки LLM
│   │   ├── __init__.py
│   │   ├── config_updater.py            # Обновление конфигурации LLM
│   │   ├── crewai_llm_wrapper.py        # Обертка CrewAI для LLM
│   │   ├── llm_manager.py               # Менеджер LLM
│   │   ├── llm_test_runner.py           # Тестовый раннер LLM
│   │   └── model_discovery.py           # Обнаружение моделей
│   └── 📂 tools/                        # Пользовательские инструменты
│       └── __init__.py
│
├── 📂 config/                           # Конфигурация
│   ├── config.yaml                      # Основная конфигурация
│   ├── agents.yaml                      # Конфигурация агентов
│   ├── llm_settings.yaml                # Настройки LLM
│   ├── logging.yaml                     # Конфигурация логирования
│   ├── test_config.yaml                 # Конфигурация тестов
│   └── mcp_config.example.json          # Пример конфигурации MCP серверов
│
├── 📂 test/                             # Тесты (функциональные и интеграционные)
│   ├── __init__.py                      # Пакет тестов
│   ├── conftest.py                      # Конфигурация pytest
│   ├── fix_encoding.py                  # Исправление кодировки
│   ├── fix_imports.py                   # Исправление импортов
│   ├── README.md                        # Описание тестов
│   ├── run_comprehensive_tests.py       # Скрипт комплексного тестирования
│   ├── run_full_testing.py              # Полный цикл тестирования
│   ├── run_tests.py                     # Единая точка входа для тестов
│   ├── test_utils.py                    # Утилиты для тестов
│   ├── 📂 cursor_cli/                   # Тесты CLI Cursor
│   ├── 📂 cursor_commands/              # Тестовые команды Cursor
│   ├── 📂 e2e/                          # End-to-end тесты
│   ├── 📂 integration/                  # Интеграционные тесты
│   └── 📂 unit/                         # Модульные тесты
│
├── 📂 docs/                             # Документация
│   ├── README.md                        # Обзор всей документации
│   ├── core/                            # Ядро: архитектура, API, LLM
│   ├── guides/                          # Руководства: установка, Docker, Git
│   ├── planning/                        # Планы, ROADMAP, технический долг
│   ├── testing/                         # Инструкции по тестированию
│   ├── changelog/                       # История изменений
│   ├── archive/                         # Архив старых отчетов и исследований
│   ├── integration/                     # Интеграции
│   ├── results/                         # Результаты тестирования
│   └── reviews/                         # Обзоры
│
├── 📂 scripts/                          # Вспомогательные скрипты
│   ├── check_doc_links.py               # Проверка ссылок документации
│   ├── check_gemini_availability.py     # Проверка доступности Gemini
│   ├── classify_and_move_tests.py       # Классификация тестов
│   ├── clean.py                         # Очистка временных файлов
│   ├── mark_task_done.py                # Отметка задачи выполненной
│   ├── monitor_server.py                # Мониторинг сервера
│   ├── run_quality_checks.py            # Запуск проверок качества
│   ├── setup_git_ssh.sh                 # Настройка SSH для Git
│   └── test_openai_keys.py              # Тест ключей OpenAI
│
├── 📂 examples/                         # Примеры использования API и агента
│   ├── gemini_api_example.py            # Пример использования Gemini API
│   ├── gemini_cli_example.py            # Пример CLI Gemini
│   └── gemini_example.py                # Общий пример Gemini
│
├── 📂 docker/                           # Dockerfile и docker-compose
│   ├── docker-compose.agent.yml         # Docker Compose для агента
│   ├── docker-compose.gemini.yml        # Docker Compose для Gemini
│   ├── Dockerfile.agent                 # Dockerfile агента
│   ├── Dockerfile.gemini                # Dockerfile Gemini
│   ├── README.md                        # Документация Docker
│   └── test_docker_agent.sh             # Скрипт тестирования Docker
│
├── 📂 .github/                          # CI/CD (GitHub Actions)
│   └── workflows/                       # Определения workflow
│
├── 📂 logs/                             # Логи (создаются автоматически)
├── 📂 results/                          # Результаты тестов (создаются автоматически)
└── 📂 .cursor/                          # Конфигурация Cursor (локальная)
```

---

## 📋 Описание директорий

### `/src` - Исходный код
Весь исполняемый код. Включает логику сервера, менеджеров задач и статусов, интеграции с LLM и Cursor, а также агентов CrewAI. Поддиректории:
- **agents/** - Определения агентов для выполнения задач.
- **llm/** - Менеджеры LLM, обертки, тестирование моделей.
- **tools/** - Пользовательские инструменты.

### `/config` - Конфигурация
Централизованное хранилище настроек в формате YAML и JSON. Включает основную конфигурацию, настройки агентов, LLM, логирования и тестов.

### `/test` - Тесты
Все тесты проекта. Организованы по категориям в поддиректориях:
- **cursor_cli/** - Тесты CLI Cursor.
- **cursor_commands/** - Тестовые команды Cursor.
- **e2e/** - End-to-end тесты.
- **integration/** - Интеграционные тесты.
- **unit/** - Модульные тесты.

### `/docs` - Документация
Разбита на логические блоки:
- **core/** - Архитектура, API и управление моделями.
- **guides/** - Пошаговые инструкции по развертыванию и Docker.
- **planning/** - Активные задачи и планы (todo.md).
- **archive/** - Архив старых планов, отчетов и исследований.
- **integration/** - Документация по интеграциям.
- **testing/** - Инструкции по тестированию.

### `/scripts` - Вспомогательные скрипты
Скрипты для автоматизации задач: проверка документации, мониторинг, очистка, настройка Git.

### `/examples` - Примеры использования
Примеры кода для работы с API и агентами.

### `/docker` - Docker конфигурация
Файлы для развертывания в контейнерах.

### `/logs` - Логи
Создаются автоматически при работе сервера. Не должны попадать в Git.

### `/results` - Результаты тестов
Создаются автоматически при запуске тестов.

---

## 📚 Дополнительная информация

- [README.md](../../README.md) - Главный файл проекта.
- [docs/README.md](../README.md) - Навигация по документации.
- [docs/core/architecture.md](architecture.md) - Подробное описание архитектуры.
- [docs/testing/TESTING_GUIDE.md](../testing/TESTING_GUIDE.md) - Руководство по тестированию.
