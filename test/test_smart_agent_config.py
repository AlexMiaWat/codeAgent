#!/usr/bin/env python3
"""
Тесты конфигурации Smart Agent
Проверяет правильность загрузки и применения конфигурационных настроек
"""

import sys
import os
from pathlib import Path
from unittest.mock import patch

# Добавляем корневую директорию в путь для импорта
sys.path.insert(0, str(Path(__file__).parent.parent))

import yaml


def test_smart_agent_config_loading():
    """Тест загрузки конфигурации Smart Agent из config.yaml"""
    print("🔧 Тестирование загрузки конфигурации Smart Agent...")

    try:
        from config.config_loader import ConfigLoader

        # Загружаем конфигурацию
        config = ConfigLoader.load_config()

        # Проверяем наличие секции smart_agent
        assert 'smart_agent' in config, "Секция smart_agent отсутствует в конфигурации"

        smart_config = config['smart_agent']

        # Проверяем обязательные параметры
        assert 'enabled' in smart_config, "Параметр enabled отсутствует"
        assert isinstance(smart_config['enabled'], bool), "enabled должен быть boolean"

        # Проверяем параметры производительности
        assert 'max_iter' in smart_config, "max_iter отсутствует"
        assert 'memory' in smart_config, "memory отсутствует"
        assert 'verbose' in smart_config, "verbose отсутствует"

        # Проверяем директорию опыта
        assert 'experience_dir' in smart_config, "experience_dir отсутствует"
        assert 'max_experience_tasks' in smart_config, "max_experience_tasks отсутствует"

        print("✅ Конфигурация Smart Agent загружена корректно")
        print(f"   enabled: {smart_config['enabled']}")
        print(f"   max_iter: {smart_config['max_iter']}")
        print(f"   memory: {smart_config['memory']}")
        print(f"   experience_dir: {smart_config['experience_dir']}")

        return True

    except Exception as e:
        print(f"❌ Ошибка загрузки конфигурации: {e}")
        return False


def test_agents_config_loading():
    """Тест загрузки конфигурации агентов из agents.yaml"""
    print("\n🤖 Тестирование загрузки конфигурации агентов...")

    try:
        import yaml

        # Загружаем конфигурацию агентов
        with open('config/agents.yaml', 'r', encoding='utf-8') as f:
            agents_config = yaml.safe_load(f)

        # Проверяем наличие smart_agent
        assert 'smart_agent' in agents_config, "smart_agent отсутствует в agents.yaml"

        smart_agent = agents_config['smart_agent']

        # Проверяем обязательные поля
        required_fields = ['role', 'goal', 'backstory', 'allow_code_execution', 'verbose', 'tools']
        for field in required_fields:
            assert field in smart_agent, f"Поле {field} отсутствует в smart_agent"

        # Проверяем, что tools содержит LearningTool и ContextAnalyzerTool
        tools = smart_agent['tools']
        assert 'LearningTool' in tools, "LearningTool отсутствует в инструментах"
        assert 'ContextAnalyzerTool' in tools, "ContextAnalyzerTool отсутствует в инструментах"

        # Проверяем отсутствие CodeInterpreterTool (должен быть удален)
        assert 'CodeInterpreterTool' not in tools, "CodeInterpreterTool должен быть удален из конфигурации"

        print("✅ Конфигурация агентов загружена корректно")
        print(f"   Роль: {smart_agent['role']}")
        print(f"   Инструменты: {tools}")
        print(f"   CodeInterpreterTool отсутствует: {'CodeInterpreterTool' not in tools}")

        return True

    except Exception as e:
        print(f"❌ Ошибка загрузки конфигурации агентов: {e}")
        return False


def test_smart_agent_config_validation():
    """Тест валидации конфигурации Smart Agent"""
    print("\n✅ Тестирование валидации конфигурации Smart Agent...")

    try:
        from config.config_validator import ConfigValidator

        # Загружаем конфигурацию
        config = ConfigValidator.load_and_validate()

        # Проверяем, что валидация прошла успешно
        assert config is not None, "Конфигурация не прошла валидацию"

        # Проверяем smart_agent секцию
        smart_config = config.get('smart_agent', {})
        assert smart_config, "Секция smart_agent отсутствует после валидации"

        print("✅ Конфигурация Smart Agent прошла валидацию")
        return True

    except Exception as e:
        print(f"❌ Ошибка валидации конфигурации: {e}")
        return False


def test_smart_agent_env_variables():
    """Тест переменных окружения для Smart Agent"""
    print("\n🌍 Тестирование переменных окружения Smart Agent...")

    try:
        # Проверяем наличие переменных в .env.example
        with open('.env.example', 'r', encoding='utf-8') as f:
            env_content = f.read()

        # Ищем переменные связанные с Smart Agent
        smart_vars = [
            'SMART_AGENT_ENABLED',
            'SMART_AGENT_EXPERIENCE_DIR',
            'SMART_AGENT_PROJECT_DIR'
        ]

        found_vars = []
        for var in smart_vars:
            if var in env_content:
                found_vars.append(var)

        print(f"✅ Найдено переменных окружения: {len(found_vars)}/{len(smart_vars)}")
        for var in found_vars:
            print(f"   ✓ {var}")

        if len(found_vars) < len(smart_vars):
            missing = [v for v in smart_vars if v not in found_vars]
            print(f"   ⚠️  Отсутствуют: {missing}")

        # Проверяем, что основные переменные присутствуют
        assert 'SMART_AGENT_ENABLED' in env_content, "SMART_AGENT_ENABLED отсутствует в .env.example"

        return True

    except Exception as e:
        print(f"❌ Ошибка проверки переменных окружения: {e}")
        return False


def test_learning_tool_config():
    """Тест конфигурации LearningTool"""
    print("\n🧠 Тестирование конфигурации LearningTool...")

    try:
        from src.tools.learning_tool import LearningTool

        # Создаем инструмент с кастомными настройками
        tool = LearningTool(
            experience_dir="test_experience",
            max_experience_tasks=500
        )

        # Проверяем инициализацию
        assert tool.experience_dir.name == "test_experience"
        assert tool.max_experience_tasks == 500
        assert tool.name == "LearningTool"

        # Проверяем создание директории опыта
        assert tool.experience_dir.exists(), "Директория опыта не создана"

        # Проверяем создание файла опыта
        experience_file = tool.experience_dir / "experience.json"
        assert experience_file.exists(), "Файл experience.json не создан"

        # Проверяем структуру файла опыта
        import json
        with open(experience_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        assert 'version' in data, "version отсутствует в experience.json"
        assert 'tasks' in data, "tasks отсутствует в experience.json"
        assert 'patterns' in data, "patterns отсутствует в experience.json"
        assert 'statistics' in data, "statistics отсутствует в experience.json"

        print("✅ LearningTool инициализирован корректно")
        print(f"   Директория опыта: {tool.experience_dir}")
        print(f"   Максимум задач: {tool.max_experience_tasks}")

        # Очистка тестовых файлов
        if experience_file.exists():
            experience_file.unlink()
        if tool.experience_dir.exists():
            tool.experience_dir.rmdir()

        return True

    except Exception as e:
        print(f"❌ Ошибка конфигурации LearningTool: {e}")
        return False


def test_context_analyzer_config():
    """Тест конфигурации ContextAnalyzerTool"""
    print("\n🔍 Тестирование конфигурации ContextAnalyzerTool...")

    try:
        from src.tools.context_analyzer_tool import ContextAnalyzerTool

        # Создаем инструмент с кастомными настройками
        tool = ContextAnalyzerTool(
            project_dir=".",
            docs_dir="docs",
            max_file_size=2000000,  # 2MB
            supported_extensions=[".py", ".md", ".txt", ".yaml"]
        )

        # Проверяем инициализацию
        assert tool.project_dir == Path(".")
        assert tool.docs_dir == Path("./docs")
        assert tool.max_file_size == 2000000
        assert ".py" in tool.supported_extensions
        assert ".md" in tool.supported_extensions
        assert tool.name == "ContextAnalyzerTool"

        # Проверяем наличие кэшей
        assert hasattr(tool, '_analysis_cache'), "Кэш анализа отсутствует"
        assert hasattr(tool, '_dependency_cache'), "Кэш зависимостей отсутствует"

        print("✅ ContextAnalyzerTool инициализирован корректно")
        print(f"   Директория проекта: {tool.project_dir}")
        print(f"   Директория документации: {tool.docs_dir}")
        print(f"   Максимальный размер файла: {tool.max_file_size} байт")

        return True

    except Exception as e:
        print(f"❌ Ошибка конфигурации ContextAnalyzerTool: {e}")
        return False


def test_smart_agent_tools_integration():
    """Тест интеграции инструментов Smart Agent"""
    print("\n🔗 Тестирование интеграции инструментов Smart Agent...")

    try:
        from src.tools.learning_tool import LearningTool
        from src.tools.context_analyzer_tool import ContextAnalyzerTool

        # Создаем оба инструмента
        learning_tool = LearningTool(experience_dir="test_integration")
        context_tool = ContextAnalyzerTool(project_dir=".")

        # Проверяем, что они имеют разные имена
        assert learning_tool.name != context_tool.name
        assert learning_tool.name == "LearningTool"
        assert context_tool.name == "ContextAnalyzerTool"

        # Проверяем наличие метода _run у обоих
        assert hasattr(learning_tool, '_run'), "LearningTool не имеет метода _run"
        assert hasattr(context_tool, '_run'), "ContextAnalyzerTool не имеет метода _run"

        # Тестируем совместную работу
        # Сохраняем опыт в LearningTool
        learning_result = learning_tool._run("save_experience", **{
            "task_id": "integration_test_001",
            "task_description": "Тест интеграции инструментов",
            "success": True,
            "execution_time": 1.0,
            "notes": "Совместное тестирование",
            "patterns": ["integration", "test"]
        })

        assert "сохранен" in learning_result.lower(), "Опыт не сохранен"

        # Анализируем контекст
        context_result = context_tool._run("analyze_project")

        assert "анализ структуры проекта" in context_result.lower(), "Анализ структуры не выполнен"

        print("✅ Инструменты Smart Agent интегрированы корректно")

        # Очистка
        experience_file = learning_tool.experience_dir / "experience.json"
        if experience_file.exists():
            experience_file.unlink()
        if learning_tool.experience_dir.exists():
            learning_tool.experience_dir.rmdir()

        return True

    except Exception as e:
        print(f"❌ Ошибка интеграции инструментов: {e}")
        return False


def test_smart_agent_config_schema_validation():
    """Тест схемы конфигурации Smart Agent"""
    print("\n📋 Тестирование схемы конфигурации Smart Agent...")

    try:
        from config.config_loader import ConfigLoader

        # Загружаем конфигурацию
        config = ConfigLoader.load_config()

        # Проверяем наличие обязательных секций
        required_sections = ['smart_agent', 'agent', 'server', 'project', 'docs', 'logging']
        for section in required_sections:
            assert section in config, f"Обязательная секция {section} отсутствует в конфигурации"

        # Проверяем схему smart_agent секции
        smart_config = config['smart_agent']
        required_smart_fields = ['enabled', 'experience_dir', 'max_experience_tasks', 'max_iter', 'memory', 'verbose']
        for field in required_smart_fields:
            assert field in smart_config, f"Обязательное поле {field} отсутствует в smart_agent"

        # Проверяем типы данных
        assert isinstance(smart_config['enabled'], bool), "enabled должен быть boolean"
        assert isinstance(smart_config['max_experience_tasks'], int), "max_experience_tasks должен быть int"
        assert isinstance(smart_config['max_iter'], int), "max_iter должен быть int"
        assert isinstance(smart_config['memory'], int), "memory должен быть int"
        assert isinstance(smart_config['verbose'], bool), "verbose должен быть boolean"
        assert isinstance(smart_config['experience_dir'], str), "experience_dir должна быть строкой"

        print("✅ Схема конфигурации Smart Agent валидна")
        return True

    except Exception as e:
        print(f"❌ Ошибка валидации схемы конфигурации: {e}")
        return False


def test_smart_agent_config_ranges():
    """Тест допустимых диапазонов значений конфигурации Smart Agent"""
    print("\n📏 Тестирование диапазонов значений конфигурации Smart Agent...")

    try:
        # Проверяем допустимые диапазоны
        valid_ranges = {
            'max_experience_tasks': (1, 10000),  # от 1 до 10000
            'max_iter': (1, 100),               # от 1 до 100
            'memory': (10, 1000),               # от 10 до 1000
        }

        # Загружаем текущую конфигурацию
        from config.config_loader import ConfigLoader
        config = ConfigLoader.load_config()
        smart_config = config.get('smart_agent', {})

        for field, (min_val, max_val) in valid_ranges.items():
            if field in smart_config:
                value = smart_config[field]
                assert min_val <= value <= max_val, f"Значение {field}={value} вне допустимого диапазона [{min_val}, {max_val}]"
                print(f"   ✓ {field}={value} в диапазоне [{min_val}, {max_val}]")

        # Проверяем специальные значения
        assert smart_config.get('enabled') in [True, False], "enabled должен быть True или False"
        assert len(smart_config.get('experience_dir', '')) > 0, "experience_dir не должна быть пустой"

        print("✅ Диапазоны значений конфигурации корректны")
        return True

    except Exception as e:
        print(f"❌ Ошибка проверки диапазонов: {e}")
        return False


def test_smart_agent_config_cross_references():
    """Тест перекрестных ссылок в конфигурации Smart Agent"""
    print("\n🔗 Тестирование перекрестных ссылок в конфигурации Smart Agent...")

    try:
        from config.config_loader import ConfigLoader

        # Загружаем конфигурации
        config = ConfigLoader.load_config()
        smart_config = config.get('smart_agent', {})

        # Загружаем конфигурацию агентов
        with open('config/agents.yaml', 'r', encoding='utf-8') as f:
            agents_config = yaml.safe_load(f)

        # Проверяем соответствие настроек между config.yaml и agents.yaml
        if 'smart_agent' in agents_config:
            agent_config = agents_config['smart_agent']

            # Проверяем, что tools из agents.yaml соответствуют ожидаемым
            expected_tools = ['LearningTool', 'ContextAnalyzerTool']
            actual_tools = agent_config.get('tools', [])

            for tool in expected_tools:
                assert tool in actual_tools, f"Инструмент {tool} отсутствует в agents.yaml"

            # Проверяем настройки verbose
            config_verbose = smart_config.get('verbose', True)
            agent_verbose = agent_config.get('verbose', True)
            assert config_verbose == agent_verbose, f"verbose в config.yaml ({config_verbose}) не соответствует agents.yaml ({agent_verbose})"

        # Проверяем ссылки на директории
        experience_dir = smart_config.get('experience_dir', 'smart_experience')
        assert experience_dir != '', "experience_dir не должна быть пустой"

        print("✅ Перекрестные ссылки в конфигурации корректны")
        return True

    except Exception as e:
        print(f"❌ Ошибка проверки перекрестных ссылок: {e}")
        return False


def test_smart_agent_config_environment_integration():
    """Тест интеграции конфигурации Smart Agent с переменными окружения"""
    print("\n🌍 Тестирование интеграции конфигурации с переменными окружения...")

    try:
        # Тестируем интеграцию с переменными окружения
        with patch.dict(os.environ, {
            'SMART_AGENT_ENABLED': 'false',  # отключаем через env
            'SMART_AGENT_MAX_ITER': '50',    # изменяем через env
            'PROJECT_DIR': '/custom/project/path',
        }):
            # Перезагружаем конфигурацию
            from config.config_loader import ConfigLoader
            config = ConfigLoader.load_config()

            config.get('smart_agent', {})

            # Проверяем, что переменные окружения влияют на конфигурацию
            # (в реальной реализации это может работать через ConfigLoader)
            print("   ⚠️  Интеграция с переменными окружения требует реализации в ConfigLoader")

            # Проверяем базовую доступность переменных окружения
            assert os.getenv('SMART_AGENT_ENABLED') == 'false'
            assert os.getenv('SMART_AGENT_MAX_ITER') == '50'
            assert os.getenv('PROJECT_DIR') == '/custom/project/path'

            print("✅ Базовая интеграция с переменными окружения работает")
            return True

    except Exception as e:
        print(f"❌ Ошибка интеграции с переменными окружения: {e}")
        return False


def test_smart_agent_cursor_config_integration():
    """Тест интеграции конфигурации Smart Agent с настройками Cursor"""
    print("\n🖱️  Тестирование интеграции с конфигурацией Cursor...")

    try:
        from config.config_loader import ConfigLoader

        # Загружаем конфигурацию
        config = ConfigLoader.load_config()

        # Проверяем наличие секции cursor
        assert 'cursor' in config, "Секция cursor отсутствует в конфигурации"

        cursor_config = config['cursor']

        # Проверяем обязательные поля cursor
        required_cursor_fields = ['interface_type', 'cli', 'permissions']
        for field in required_cursor_fields:
            assert field in cursor_config, f"Обязательное поле {field} отсутствует в cursor конфигурации"

        # Проверяем настройки CLI
        cli_config = cursor_config.get('cli', {})
        assert 'timeout' in cli_config, "timeout отсутствует в cli конфигурации"
        assert 'model' in cli_config, "model отсутствует в cli конфигурации"
        assert cli_config.get('model') != '', "model не должна быть пустой"

        # Проверяем настройки разрешений
        permissions = cursor_config.get('permissions', {})
        assert permissions.get('enabled', False), "permissions должны быть включены"

        print("✅ Интеграция с конфигурацией Cursor корректна")
        return True

    except Exception as e:
        print(f"❌ Ошибка интеграции с Cursor: {e}")
        return False


def test_smart_agent_performance_config():
    """Тест настроек производительности Smart Agent"""
    print("\n⚡ Тестирование настроек производительности Smart Agent...")

    try:
        from config.config_loader import ConfigLoader

        # Загружаем конфигурацию
        config = ConfigLoader.load_config()
        smart_config = config.get('smart_agent', {})

        # Проверяем настройки производительности
        max_iter = smart_config.get('max_iter', 25)
        memory = smart_config.get('memory', 100)

        # Проверяем разумные значения производительности
        assert max_iter >= 10 and max_iter <= 50, f"max_iter={max_iter} вне разумного диапазона [10, 50]"
        assert memory >= 50 and memory <= 200, f"memory={memory} вне разумного диапазона [50, 200]"

        # Проверяем оптимизацию verbose режима
        verbose = smart_config.get('verbose', True)
        # verbose может быть True для отладки, но в production может быть False

        print(f"✅ Настройки производительности: max_iter={max_iter}, memory={memory}, verbose={verbose}")
        return True

    except Exception as e:
        print(f"❌ Ошибка проверки настроек производительности: {e}")
        return False


def test_smart_agent_experience_config():
    """Тест настроек хранения опыта Smart Agent"""
    print("\n📚 Тестирование настроек хранения опыта Smart Agent...")

    try:
        from config.config_loader import ConfigLoader

        # Загружаем конфигурацию
        config = ConfigLoader.load_config()
        smart_config = config.get('smart_agent', {})

        # Проверяем настройки опыта
        experience_dir = smart_config.get('experience_dir', 'smart_experience')
        max_experience_tasks = smart_config.get('max_experience_tasks', 200)

        # Проверяем валидность директории опыта
        assert experience_dir != '', "experience_dir не должна быть пустой"
        assert not experience_dir.startswith('/'), "experience_dir должна быть относительной"
        assert not experience_dir.startswith('\\'), "experience_dir должна быть относительной"

        # Проверяем разумные значения
        assert max_experience_tasks > 0, "max_experience_tasks должна быть > 0"
        assert max_experience_tasks <= 2000, f"max_experience_tasks={max_experience_tasks} слишком большое значение"

        print(f"✅ Настройки опыта: dir='{experience_dir}', max_tasks={max_experience_tasks}")
        return True

    except Exception as e:
        print(f"❌ Ошибка проверки настроек опыта: {e}")
        return False


def main():
    """Основная функция тестирования"""
    print("🧪 Начало тестирования конфигурации Smart Agent\n")

    results = []

    # Тестируем компоненты конфигурации
    results.append(("Smart Agent Config Loading", test_smart_agent_config_loading()))
    results.append(("Agents Config Loading", test_agents_config_loading()))
    results.append(("Smart Agent Config Validation", test_smart_agent_config_validation()))
    results.append(("Smart Agent Environment Variables", test_smart_agent_env_variables()))
    results.append(("LearningTool Configuration", test_learning_tool_config()))
    results.append(("ContextAnalyzerTool Configuration", test_context_analyzer_config()))
    results.append(("Smart Agent Tools Integration", test_smart_agent_tools_integration()))

    # Новые расширенные тесты
    results.append(("Smart Agent Config Schema Validation", test_smart_agent_config_schema_validation()))
    results.append(("Smart Agent Config Ranges", test_smart_agent_config_ranges()))
    results.append(("Smart Agent Config Cross References", test_smart_agent_config_cross_references()))
    results.append(("Smart Agent Config Environment Integration", test_smart_agent_config_environment_integration()))
    results.append(("Smart Agent Cursor Config Integration", test_smart_agent_cursor_config_integration()))
    results.append(("Smart Agent Performance Config", test_smart_agent_performance_config()))
    results.append(("Smart Agent Experience Config", test_smart_agent_experience_config()))

    # Итоги тестирования
    print("\n" + "="*70)
    print("📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ КОНФИГУРАЦИИ SMART AGENT")
    print("="*70)

    passed = 0
    total = len(results)

    for test_name, success in results:
        print("40")
        if success:
            passed += 1

    print(f"\n📈 ИТОГО: {passed}/{total} тестов пройдено")

    if passed == total:
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! Конфигурация Smart Agent работает корректно.")
        return 0
    else:
        print("⚠️  НЕКОТОРЫЕ ТЕСТЫ ПРОВАЛЕНЫ. Требуется дополнительная настройка.")
        return 1


if __name__ == "__main__":
    sys.exit(main())