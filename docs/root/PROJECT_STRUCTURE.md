# Структура проекта Code Agent

**Дата обновления:** 2026-01-18  
**Версия:** 2.0 (После реорганизации)

---

## 📁 Иерархия проекта

```
codeAgent/
├── 📄 README.md                          # Основная документация проекта
│
├── 📂 src/                              # Исходный код
│   ├── server.py                        # Основной сервер Code Agent
│   ├── config_loader.py                 # Загрузчик конфигурации
│   ├── todo_manager.py                  # Менеджер TODO задач
│   ├── cursor_cli_interface.py          # CLI интерфейс для Cursor
│   ├── cursor_file_interface.py         # Файловый интерфейс для Cursor
│   ├── hybrid_cursor_interface.py       # Гибридный интерфейс (CLI + файловый)
│   ├── prompt_formatter.py              # Форматирование промптов
│   ├── agents/                          # Агенты CrewAI
│   │   ├── executor_agent.py
│   │   └── ...
│   └── llm/                             # LLM интеграция
│       ├── llm_interface.py
│       └── ...
│
├── 📂 config/                           # Конфигурация
│   ├── config.yaml                      # Основная конфигурация
│   ├── llm_settings.yaml                # Настройки LLM
│   └── logging.yaml                     # Конфигурация логирования
│
├── 📂 test/                             # Тесты
│   ├── README.md                        # Документация тестов
│   ├── conftest.py                      # Конфигурация pytest
│   ├── __init__.py
│   │
│   ├── 📂 unit/                         # Юнит-тесты
│   │   └── (будущие тесты)
│   │
│   ├── 📂 integration/                  # Интеграционные тесты
│   │   ├── test_hybrid_quick.py         # Быстрый тест гибридного интерфейса
│   │   ├── test_hybrid_real.py          # Реальный тест гибридного интерфейса
│   │   └── test_mini_docs_hybrid.py     # Тест создания документации
│   │
│   ├── test_cursor_cli_full_scenarios.py  # Полные сценарии Cursor CLI
│   ├── test_expert_recommendations.py     # Тесты рекомендаций экспертов
│   ├── test_mini_docs_scenario.py         # Сценарий mini_docs
│   ├── test_real_cursor_cli.py            # Реальное тестирование Cursor CLI
│   ├── test_hybrid_interface.py           # Тесты гибридного интерфейса
│   ├── test_server_execution.py           # Тесты выполнения сервера
│   └── ...                                # Другие тесты
│
├── 📂 docs/                             # Документация
│   ├── README.md                        # Обзор документации
│   │
│   ├── 📂 root/                         # Документы из корня проекта
│   │   ├── QUICK_START_HYBRID.md        # Быстрый старт
│   │   ├── PROJECT_STRUCTURE.md         # Этот файл
│   │   └── REORGANIZATION_REPORT.md     # Отчет о реорганизации
│   │
│   ├── 📂 testing/                      # Документация тестирования
│   │   ├── TESTING.md                   # Руководство по тестированию
│   │   └── TEST_SUMMARY.md              # Сводка тестирования
│   │
│   ├── 📂 changelog/                    # История изменений
│   │   ├── CHANGELOG.md                 # История изменений проекта
│   │   └── CHANGELOG_CURSOR_CLI.md      # История Cursor CLI
│   │
│   ├── 📂 core/                         # Основная документация
│   │   ├── api.md                       # API документация
│   │   ├── architecture.md              # Архитектура системы
│   │   ├── project_structure.md         # Структура проекта (старая версия)
│   │   └── workflow_detailed.md         # Детальный workflow
│   │
│   ├── 📂 guides/                       # Руководства
│   │   ├── setup.md                     # Руководство по установке
│   │   ├── cursor_setup_recommendations.md  # Рекомендации по настройке Cursor
│   │   ├── docker_integration_guide.md  # Руководство по Docker интеграции
│   │   ├── docker_persistent_container.md  # Постоянный Docker контейнер
│   │   └── testing.md                   # Руководство по тестированию
│   │
│   ├── 📂 integration/                  # Документация интеграций
│   │   ├── cursor_integration.md        # Интеграция с Cursor
│   │   ├── llm_integration.md           # Интеграция с LLM
│   │   └── llm_limitations.md           # Ограничения LLM
│   │
│   ├── 📂 solutions/                    # Решения проблем
│   │   ├── CURSOR_INTEGRATION_SOLUTIONS.md  # Решения интеграции с Cursor
│   │   ├── INTEGRATION_FIX_SUMMARY.md   # Резюме исправлений
│   │   ├── HYBRID_INTERFACE_TEST_RESULTS.md  # Результаты тестов гибридного интерфейса
│   │   └── MINI_DOCS_CREATION_REPORT.md  # Отчет о создании mini_docs
│   │
│   ├── 📂 planning/                     # Планирование
│   │   ├── implementation_roadmap.md    # Дорожная карта реализации
│   │   ├── improvements_summary.md      # Резюме улучшений
│   │   ├── conceptual_improvements.md   # Концептуальные улучшения
│   │   └── todo_format_requirements.md  # Требования к формату TODO
│   │
│   └── 📂 archive/                      # Архив старых документов
│       ├── 📂 reports/                  # Отчеты и статусы
│       │   ├── COMPLEX_SCENARIOS_TEST_RESULTS.md
│       │   ├── COMPREHENSIVE_TEST_REPORT.md
│       │   ├── EXPERT_RECOMMENDATIONS_*.md
│       │   ├── FINAL_*.md
│       │   ├── TEST_*.md
│       │   └── ...
│       │
│       ├── 📂 research/                 # Исследования
│       │   ├── cursor_cli_*.md
│       │   ├── cursor_feedback_*.md
│       │   └── ...
│       │
│       ├── INSTALL_CURSOR_AGENT.md
│       ├── INSTALL_CURSOR_AGENT_DOCKER.md
│       └── MIGRATION_COMPLETE.md
│
├── 📂 logs/                             # Логи (создаются автоматически)
│   ├── codeagent.log                    # Основной лог
│   ├── errors.log                       # Лог ошибок
│   ├── tests.log                        # Лог тестов
│   └── 📂 archive/                      # Архив старых логов
│       ├── test_*.log
│       └── ...
│
├── 📂 docker/                           # Docker конфигурация
│   ├── Dockerfile.agent                 # Dockerfile для Cursor agent
│   └── docker-compose.agent.yml         # Docker Compose для agent
│
├── 📂 scripts/                          # Вспомогательные скрипты
│   └── (будущие скрипты)
│
├── 📂 .github/                          # GitHub конфигурация
│   └── workflows/                       # GitHub Actions
│
├── 📄 pyproject.toml                    # Конфигурация проекта Python
├── 📄 pytest.ini                        # Конфигурация pytest
├── 📄 Makefile                          # Makefile для команд
├── 📄 requirements-test.txt             # Зависимости для тестирования
└── 📄 .gitignore                        # Git ignore правила
```

---

## 📋 Описание директорий

### `/src` - Исходный код
Весь исполняемый код проекта. Основные модули:
- **server.py** - главный сервер
- **cursor_*_interface.py** - интерфейсы для работы с Cursor
- **hybrid_cursor_interface.py** - гибридный интерфейс (рекомендуется)
- **agents/** - агенты CrewAI
- **llm/** - интеграция с LLM

### `/config` - Конфигурация
Все конфигурационные файлы:
- **config.yaml** - основная конфигурация
- **llm_settings.yaml** - настройки LLM моделей
- **logging.yaml** - конфигурация логирования

### `/test` - Тесты
Все тесты проекта, организованные по типам:
- **unit/** - юнит-тесты (изолированные тесты модулей)
- **integration/** - интеграционные тесты (тесты взаимодействия)
- Корень test/ - функциональные и сценарные тесты

**Правило:** Все новые тесты создавать в `/test`, не в корне проекта!

### `/docs` - Документация
Структурированная документация:
- **core/** - основная документация (API, архитектура)
- **guides/** - руководства пользователя
- **integration/** - документация интеграций
- **solutions/** - решения проблем и отчеты
- **planning/** - планирование и roadmap
- **archive/** - архив старых документов

### `/logs` - Логи
Все логи приложения (создаются автоматически):
- **codeagent.log** - основной лог работы
- **errors.log** - только ошибки
- **tests.log** - логи тестов
- **archive/** - архив старых логов

**Правило:** Все логи должны создаваться в `/logs`, не в корне!

### `/docker` - Docker
Docker конфигурация для контейнеризации

### `/scripts` - Скрипты
Вспомогательные скрипты для автоматизации

---

## 🎯 Правила организации

### 1. Тесты
- ✅ Все тесты в `/test`
- ✅ Интеграционные тесты в `/test/integration`
- ✅ Юнит-тесты в `/test/unit`
- ❌ Никаких тестов в корне проекта

### 2. Логи
- ✅ Все логи в `/logs`
- ✅ Конфигурация в `/config/logging.yaml`
- ✅ Ротация логов (10MB, 5 файлов)
- ❌ Никаких логов в корне проекта

### 3. Документация
- ✅ Актуальная документация в `/docs`
- ✅ Промежуточные отчеты в `/docs/archive`
- ✅ Структурирована по категориям
- ❌ Никаких дублирующих документов

### 4. Конфигурация
- ✅ Все конфиги в `/config`
- ✅ YAML формат для читаемости
- ✅ Комментарии в конфигах

---

## 📊 Статистика проекта

### Исходный код
- **Модулей:** ~15
- **Строк кода:** ~5000+
- **Тестов:** 20+
- **Покрытие:** В разработке

### Документация
- **Активных документов:** ~20
- **Архивных документов:** ~40
- **Руководств:** 5+
- **Отчетов:** 10+ (в архиве)

### Структура
- **Основных директорий:** 8
- **Поддиректорий:** 15+
- **Конфигурационных файлов:** 3

---

## 🚀 Быстрый старт

### Установка
```bash
pip install -r requirements-test.txt
```

### Запуск тестов
```bash
pytest test/
```

### Запуск сервера
```bash
python src/server.py
```

### Использование гибридного интерфейса
```python
from src.hybrid_cursor_interface import create_hybrid_cursor_interface

hybrid = create_hybrid_cursor_interface(
    cli_path="docker-compose-agent",
    project_dir="d:/Space/life"
)

result = hybrid.execute_task(
    instruction="Создай файл test.txt",
    task_id="task_001"
)
```

---

## 📚 Дополнительная информация

- **Основная документация:** [README.md](README.md)
- **Быстрый старт:** [QUICK_START_HYBRID.md](QUICK_START_HYBRID.md)
- **Руководство по тестированию:** [TESTING.md](TESTING.md)
- **Документация API:** [docs/core/api.md](docs/core/api.md)
- **Архитектура:** [docs/core/architecture.md](docs/core/architecture.md)

---

**Обновлено:** 2026-01-18  
**Версия структуры:** 2.0
