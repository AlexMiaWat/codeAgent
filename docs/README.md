# Документация Code Agent

**Дата обновления:** 2026-01-26  
**Версия:** 2.2 (после ревизии проекта)

---

## 📚 Быстрый доступ

### Основные документы (из корня проекта)
- **[../README.md](../README.md)** - Главная страница проекта
- **[root/QUICK_START_HYBRID.md](root/QUICK_START_HYBRID.md)** - Быстрый старт с гибридным интерфейсом
- **[root/PROJECT_STRUCTURE.md](root/PROJECT_STRUCTURE.md)** - Полная структура проекта
- **[root/REORGANIZATION_REPORT.md](root/REORGANIZATION_REPORT.md)** - Отчет о реорганизации

### Тестирование
- **[testing/TESTING.md](testing/TESTING.md)** - Руководство по тестированию
- **[testing/TEST_SUMMARY.md](testing/TEST_SUMMARY.md)** - Сводка тестирования

### История изменений
- **[changelog/CHANGELOG.md](changelog/CHANGELOG.md)** - История изменений проекта
- **[changelog/CHANGELOG_CURSOR_CLI.md](changelog/CHANGELOG_CURSOR_CLI.md)** - История изменений Cursor CLI

---

## 📚 Структура документации

### 📂 core/ - Основная документация
Ключевые технические документы:
- **[api.md](core/api.md)** - API документация (программный интерфейс)
- **[api_endpoints.md](core/api_endpoints.md)** - HTTP API Endpoints (мониторинг и управление)
- **[architecture.md](core/architecture.md)** - Архитектура системы
- **[project_structure.md](core/project_structure.md)** - Структура проекта
- **[workflow_detailed.md](core/workflow_detailed.md)** - Детальный workflow

### 📂 guides/ - Руководства
Практические руководства для пользователей:
- **[setup.md](guides/setup.md)** - Руководство по установке и настройке
- **[cursor_setup_recommendations.md](guides/cursor_setup_recommendations.md)** - Рекомендации по настройке Cursor
- **[docker_integration_guide.md](guides/docker_integration_guide.md)** - Руководство по Docker интеграции
- **[docker_persistent_container.md](guides/docker_persistent_container.md)** - Настройка постоянного Docker контейнера
- **[testing.md](guides/testing.md)** - Руководство по тестированию

### 📂 integration/ - Интеграции
Документация по интеграциям с внешними системами:
- **[cursor_integration.md](integration/cursor_integration.md)** - Интеграция с Cursor IDE
- **[llm_integration.md](integration/llm_integration.md)** - Интеграция с LLM моделями
- **[llm_limitations.md](integration/llm_limitations.md)** - Ограничения и особенности LLM

### 📂 solutions/ - Решения и отчеты
Решения проблем и результаты тестирования:
- **[CURSOR_INTEGRATION_SOLUTIONS.md](solutions/CURSOR_INTEGRATION_SOLUTIONS.md)** - Решения проблем интеграции с Cursor
- **[INTEGRATION_FIX_SUMMARY.md](solutions/INTEGRATION_FIX_SUMMARY.md)** - Резюме исправлений интеграции
- **[HYBRID_INTERFACE_TEST_RESULTS.md](solutions/HYBRID_INTERFACE_TEST_RESULTS.md)** - Результаты тестирования гибридного интерфейса
- **[MINI_DOCS_CREATION_REPORT.md](solutions/MINI_DOCS_CREATION_REPORT.md)** - Отчет о создании mini_docs

### 📂 planning/ - Планирование
Дорожные карты и планы развития:
- **[implementation_roadmap.md](planning/implementation_roadmap.md)** - Дорожная карта реализации
- **[improvements_summary.md](planning/improvements_summary.md)** - Резюме улучшений
- **[conceptual_improvements.md](planning/conceptual_improvements.md)** - Концептуальные улучшения
- **[todo_format_requirements.md](planning/todo_format_requirements.md)** - Требования к формату TODO

### 📂 archive/ - Архив
Старые документы, отчеты и исследования:
- **[archive/reports/](archive/reports/)** - Промежуточные отчеты и статусы
- **[archive/research/](archive/research/)** - Исследования и эксперименты
- **[archive/](archive/)** - Устаревшие руководства по установке

---

## 🚀 Быстрый старт

### Новым пользователям
1. Начните с **[../README.md](../README.md)** - основная информация о проекте
2. Прочитайте **[guides/setup.md](guides/setup.md)** - установка и настройка
3. Изучите **[../QUICK_START_HYBRID.md](../QUICK_START_HYBRID.md)** - быстрый старт с гибридным интерфейсом

### Разработчикам
1. **[core/architecture.md](core/architecture.md)** - понимание архитектуры
2. **[core/api.md](core/api.md)** - API документация
3. **[guides/testing.md](guides/testing.md)** - запуск и написание тестов

### Интеграция с Cursor
1. **[integration/cursor_integration.md](integration/cursor_integration.md)** - обзор интеграции
2. **[solutions/CURSOR_INTEGRATION_SOLUTIONS.md](solutions/CURSOR_INTEGRATION_SOLUTIONS.md)** - решения проблем
3. **[guides/cursor_setup_recommendations.md](guides/cursor_setup_recommendations.md)** - рекомендации

---

## 📖 Рекомендуемый порядок чтения

### Уровень 1: Основы
1. [../README.md](../README.md) - Что такое Code Agent
2. [guides/setup.md](guides/setup.md) - Как установить
3. [../QUICK_START_HYBRID.md](../QUICK_START_HYBRID.md) - Как начать работать

### Уровень 2: Использование
1. [core/architecture.md](core/architecture.md) - Как устроен проект
2. [integration/cursor_integration.md](integration/cursor_integration.md) - Работа с Cursor
3. [guides/testing.md](guides/testing.md) - Тестирование

### Уровень 3: Продвинутое
1. [core/api.md](core/api.md) - Детали API
2. [solutions/HYBRID_INTERFACE_TEST_RESULTS.md](solutions/HYBRID_INTERFACE_TEST_RESULTS.md) - Результаты тестов
3. [planning/implementation_roadmap.md](planning/implementation_roadmap.md) - Планы развития

---

## 🔍 Поиск информации

### По темам

**Установка и настройка:**
- [guides/setup.md](guides/setup.md)
- [guides/cursor_setup_recommendations.md](guides/cursor_setup_recommendations.md)
- [guides/docker_integration_guide.md](guides/docker_integration_guide.md)

**Интеграция с Cursor:**
- [integration/cursor_integration.md](integration/cursor_integration.md)
- [solutions/CURSOR_INTEGRATION_SOLUTIONS.md](solutions/CURSOR_INTEGRATION_SOLUTIONS.md)
- [solutions/INTEGRATION_FIX_SUMMARY.md](solutions/INTEGRATION_FIX_SUMMARY.md)

**Тестирование:**
- [guides/testing.md](guides/testing.md)
- [solutions/HYBRID_INTERFACE_TEST_RESULTS.md](solutions/HYBRID_INTERFACE_TEST_RESULTS.md)
- [../TESTING.md](../TESTING.md)

**Разработка:**
- [core/architecture.md](core/architecture.md)
- [core/api.md](core/api.md)
- [core/api_endpoints.md](core/api_endpoints.md) - HTTP API для мониторинга и управления
- [planning/implementation_roadmap.md](planning/implementation_roadmap.md)

**Мониторинг и управление:**
- [core/api_endpoints.md](core/api_endpoints.md) - Полная документация HTTP API
- [guides/SERVER_MONITORING_GUIDE.md](guides/SERVER_MONITORING_GUIDE.md) - Руководство по мониторингу

---

## 📝 Обновление документации

### Правила
1. Актуальная документация - в основных папках (core, guides, integration, solutions, planning)
2. Промежуточные отчеты - в archive/reports/
3. Исследования и эксперименты - в archive/research/
4. Устаревшие документы - в archive/

### Создание новых документов
- **Руководства** → `guides/`
- **Технические детали** → `core/`
- **Интеграции** → `integration/`
- **Решения проблем** → `solutions/`
- **Планирование** → `planning/`

---

## 📊 Статистика документации

- **Активных документов:** ~20
- **Руководств:** 5
- **Технических документов:** 4
- **Решений и отчетов:** 4
- **Планов:** 4
- **Архивных документов:** ~40

---

## 🆘 Помощь

Если не можете найти нужную информацию:
1. Проверьте [../README.md](../README.md) - основной обзор
2. Посмотрите в [../PROJECT_STRUCTURE.md](../PROJECT_STRUCTURE.md) - полная структура проекта
3. Изучите [solutions/](solutions/) - возможно, проблема уже решена

---

**Обновлено:** 2026-01-19  
**Версия:** 2.1
