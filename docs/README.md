# Документация Code Agent

**Дата обновления:** 2026-01-26  
**Версия:** 2.3

---

## 📚 Быстрый доступ

- **[../README.md](../README.md)** - Главная страница проекта
- **[guides/setup.md](guides/setup.md)** - Установка и настройка
- **[testing/TESTING_GUIDE.md](testing/TESTING_GUIDE.md)** - Тестирование
- **[changelog/CHANGELOG.md](changelog/CHANGELOG.md)** - История изменений

---

## 📚 Структура документации

### 📂 core/ - Основная документация
- **[api.md](core/api.md)** - API документация
- **[api_endpoints.md](core/api_endpoints.md)** - HTTP API Endpoints
- **[architecture.md](core/architecture.md)** - Архитектура системы
- **[project_structure.md](core/project_structure.md)** - Структура проекта
- **[workflow_detailed.md](core/workflow_detailed.md)** - Детальный workflow

### 📂 guides/ - Руководства
- **[setup.md](guides/setup.md)** - Установка и настройка
- **[api_keys_setup.md](guides/api_keys_setup.md)** - Настройка API ключей
- **[GIT_AUTHENTICATION_SETUP.md](guides/GIT_AUTHENTICATION_SETUP.md)** - Настройка Git
- **[SERVER_MONITORING_GUIDE.md](guides/SERVER_MONITORING_GUIDE.md)** - Мониторинг сервера
- **[docker_integration_guide.md](guides/docker_integration_guide.md)** - Docker интеграция
- **[cursor_cli_fallback.md](guides/cursor_cli_fallback.md)** - Fallback для Cursor CLI
- **[cursor_results_mechanism.md](guides/cursor_results_mechanism.md)** - Механизм результатов Cursor
- **[cursor_setup_recommendations.md](guides/cursor_setup_recommendations.md)** - Рекомендации по настройке Cursor
- **[docker_persistent_container.md](guides/docker_persistent_container.md)** - Постоянные Docker контейнеры
- **[START_HERE.md](guides/START_HERE.md)** - С чего начать
- **[testing.md](guides/testing.md)** - Руководство по тестированию

### 📂 integration/ - Интеграции
- **[cursor_integration.md](integration/cursor_integration.md)** - Интеграция с Cursor
- **[full_access_setup.md](integration/full_access_setup.md)** - Полный доступ Cursor
- **[QUICK_START_FULL_ACCESS.md](integration/QUICK_START_FULL_ACCESS.md)** - Быстрый старт полного доступа
- **[FULL_ACCESS_CHEATSHEET.md](integration/FULL_ACCESS_CHEATSHEET.md)** - Шпаргалка полного доступа
- **[FULL_ACCESS_INTEGRATION_REPORT.md](integration/FULL_ACCESS_INTEGRATION_REPORT.md)** - Отчет об интеграции
- **[llm_integration.md](integration/llm_integration.md)** - Интеграция с LLM
- **[llm_limitations.md](integration/llm_limitations.md)** - Ограничения LLM

### 📂 testing/ - Тестирование
- **[TESTING_GUIDE.md](testing/TESTING_GUIDE.md)** - Полное руководство по тестированию
- **[README.md](testing/README.md)** - Обзор тестирования
- **[COMPREHENSIVE_TEST_REPORT.md](testing/COMPREHENSIVE_TEST_REPORT.md)** - Комплексный отчет
- **[CURSOR_TESTS_DOCKER.md](testing/CURSOR_TESTS_DOCKER.md)** - Тесты Cursor в Docker

### 📂 features/ - Функции
- **[auto_todo_generation.md](features/auto_todo_generation.md)** - Автогенерация TODO
- **[auto_push_after_commit.md](features/auto_push_after_commit.md)** - Auto-push после коммита
- **[checkpoint_checklist.md](features/checkpoint_checklist.md)** - Система контрольных точек

### 📂 configuration/ - Конфигурация
- **[cursor_instructions.md](configuration/cursor_instructions.md)** - Инструкции для Cursor
- **[server_config.md](configuration/server_config.md)** - Конфигурация сервера

### 📂 planning/ - Планирование
- **[ROADMAP_2026.md](planning/ROADMAP_2026.md)** - Дорожная карта 2026
- **[DEBT.md](planning/DEBT.md)** - Архитектурный долг
- **[implementation_roadmap.md](planning/implementation_roadmap.md)** - План реализации
- **[todo_format_requirements.md](planning/todo_format_requirements.md)** - Формат TODO
- **[improvements_summary.md](planning/improvements_summary.md)** - Сводка улучшений
- **[conceptual_improvements.md](planning/conceptual_improvements.md)** - Концептуальные улучшения

### 📂 solutions/ - Решения проблем
- **[CURSOR_INTEGRATION_SOLUTIONS.md](solutions/CURSOR_INTEGRATION_SOLUTIONS.md)** - Решения проблем Cursor
- **[HYBRID_INTERFACE_TEST_RESULTS.md](solutions/HYBRID_INTERFACE_TEST_RESULTS.md)** - Результаты тестов гибридного интерфейса
- **[IMPROVEMENT_PLAN.md](solutions/IMPROVEMENT_PLAN.md)** - План улучшений
- **[IMPROVEMENT_PROCESS.md](solutions/IMPROVEMENT_PROCESS.md)** - Процесс улучшений
- **[INTEGRATION_FIX_SUMMARY.md](solutions/INTEGRATION_FIX_SUMMARY.md)** - Сводка исправлений интеграции
- **[MINI_DOCS_CREATION_REPORT.md](solutions/MINI_DOCS_CREATION_REPORT.md)** - Отчет о создании мини-документации
- **[SKEPTIC_ANALYSIS_REPORT.md](solutions/SKEPTIC_ANALYSIS_REPORT.md)** - Анализ скептика

### 📂 changelog/ - История изменений
- **[CHANGELOG.md](changelog/CHANGELOG.md)** - Основной changelog
- **[CHANGELOG_CURSOR_CLI.md](changelog/CHANGELOG_CURSOR_CLI.md)** - Изменения Cursor CLI
- **[README.md](changelog/README.md)** - Описание changelog

### 📂 archive/ - Архив
- **[reports/](archive/reports/)** - Исторические отчеты (15 файлов)
- **[research/](archive/research/)** - Исследовательские материалы (14 файлов)

### 📂 root/ - Корневые документы
- **[PROJECT_STRUCTURE.md](root/PROJECT_STRUCTURE.md)** - Структура проекта
- **[QUICK_START_HYBRID.md](root/QUICK_START_HYBRID.md)** - Быстрый старт гибридного режима
- **[README.md](root/README.md)** - Корневой README

### 🔧 Специализированные документы
- **[checkpoint_recovery.md](checkpoint_recovery.md)** - Восстановление после сбоев
- **[quick_recovery_guide.md](quick_recovery_guide.md)** - Быстрое восстановление
- **[logging_system.md](logging_system.md)** - Система логирования
- **[LLM_MANAGER_EXPLAINED.md](LLM_MANAGER_EXPLAINED.md)** - Объяснение LLM Manager
- **[cursor-logging-instruction.md](cursor-logging-instruction.md)** - Инструкции по логированию Cursor
- **[logging_colors.md](logging_colors.md)** - Цвета логирования

---

## 🚀 Быстрые старты

### Для новых пользователей
1. **[../README.md](../README.md)** - Основная информация о проекте
2. **[guides/START_HERE.md](guides/START_HERE.md)** - С чего начать
3. **[guides/setup.md](guides/setup.md)** - Установка и настройка
4. **[integration/QUICK_START_FULL_ACCESS.md](integration/QUICK_START_FULL_ACCESS.md)** - Быстрый старт Cursor интеграции

### Для разработчиков
1. **[testing/TESTING_GUIDE.md](testing/TESTING_GUIDE.md)** - Руководство по тестированию
2. **[core/architecture.md](core/architecture.md)** - Архитектура системы
3. **[core/api_endpoints.md](core/api_endpoints.md)** - HTTP API

### Специализированные руководства
- **[quick_start_logging.md](quick_start_logging.md)** - Быстрый старт логирования
- **[quick_start_auto_todo.md](quick_start_auto_todo.md)** - Автогенерация TODO
- **[quick_recovery_guide.md](quick_recovery_guide.md)** - Восстановление после сбоев
- **[root/QUICK_START_HYBRID.md](root/QUICK_START_HYBRID.md)** - Гибридный режим

---

## 🔍 Поиск по темам

**Установка и настройка:**
- [guides/setup.md](guides/setup.md) - Основная установка
- [guides/api_keys_setup.md](guides/api_keys_setup.md) - Настройка API ключей
- [guides/GIT_AUTHENTICATION_SETUP.md](guides/GIT_AUTHENTICATION_SETUP.md) - Git аутентификация
- [configuration/server_config.md](configuration/server_config.md) - Конфигурация сервера

**Интеграция:**
- [integration/cursor_integration.md](integration/cursor_integration.md) - Cursor IDE
- [integration/llm_integration.md](integration/llm_integration.md) - Языковые модели
- [guides/docker_integration_guide.md](guides/docker_integration_guide.md) - Docker

**Тестирование:**
- [testing/TESTING_GUIDE.md](testing/TESTING_GUIDE.md) - Полное руководство
- [testing/README.md](testing/README.md) - Обзор тестирования

**Разработка:**
- [core/architecture.md](core/architecture.md) - Архитектура
- [core/api.md](core/api.md) - API документация
- [core/workflow_detailed.md](core/workflow_detailed.md) - Рабочий процесс

**Функции:**
- [features/auto_todo_generation.md](features/auto_todo_generation.md) - Авто-TODO
- [features/auto_push_after_commit.md](features/auto_push_after_commit.md) - Auto-push
- [checkpoint_recovery.md](checkpoint_recovery.md) - Контрольные точки

---

**Всего документов:** 75+ файлов
**Последнее обновление:** 2026-01-26
**Версия проекта:** 2.3
