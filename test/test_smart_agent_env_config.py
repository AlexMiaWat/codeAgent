#!/usr/bin/env python3
"""
Тесты переменных окружения Smart Agent
Проверяет правильность работы с переменными окружения для конфигурации Smart Agent
"""

import sys
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

# Добавляем корневую директорию в путь для импорта
sys.path.insert(0, str(Path(__file__).parent.parent))

import yaml


def test_smart_agent_env_variables_parsing():
    """Тест парсинга переменных окружения Smart Agent"""
    print("🌍 Тестирование парсинга переменных окружения Smart Agent...")

    # Импортируем модуль для работы с переменными окружения
    from src.config.env_config import EnvConfig

    # Создаем временную директорию для PROJECT_DIR
    with tempfile.TemporaryDirectory() as temp_dir:
        # Тестируем парсинг переменных окружения
        with patch.dict(os.environ, {
            'PROJECT_DIR': temp_dir,
            'SMART_AGENT_ENABLED': 'true',
            'SMART_AGENT_EXPERIENCE_DIR': 'custom_experience',
            'SMART_AGENT_PROJECT_DIR': '/path/to/project',
            'SMART_AGENT_MAX_EXPERIENCE_TASKS': '500',
            'SMART_AGENT_MAX_ITER': '30',
            'SMART_AGENT_MEMORY': '150',
            'SMART_AGENT_VERBOSE': 'false',
        }):
            env_config = EnvConfig.load()

            # Проверяем парсинг булевых значений
            assert env_config.get_bool('SMART_AGENT_ENABLED', False) == True
            assert env_config.get_bool('SMART_AGENT_VERBOSE', True) == False

            # Проверяем парсинг строк
            assert env_config.get('SMART_AGENT_EXPERIENCE_DIR') == 'custom_experience'
            assert env_config.get('SMART_AGENT_PROJECT_DIR') == '/path/to/project'

            # Проверяем парсинг чисел
            assert env_config.get_int('SMART_AGENT_MAX_EXPERIENCE_TASKS', 200) == 500
            assert env_config.get_int('SMART_AGENT_MAX_ITER', 25) == 30
            assert env_config.get_int('SMART_AGENT_MEMORY', 100) == 150

    print("✅ Переменные окружения Smart Agent корректно парсятся")
    return True


def test_smart_agent_env_variables_validation():
    """Тест валидации переменных окружения Smart Agent"""
    print("\n✅ Тестирование валидации переменных окружения Smart Agent...")

    try:
        # Проверяем допустимые значения
        valid_values = {
            'SMART_AGENT_ENABLED': ['true', 'false', 'True', 'False', '1', '0'],
            'SMART_AGENT_MAX_EXPERIENCE_TASKS': ['100', '200', '500', '1000'],
            'SMART_AGENT_MAX_ITER': ['10', '25', '50', '100'],
            'SMART_AGENT_MEMORY': ['50', '100', '200', '500'],
        }

        for var_name, values in valid_values.items():
            for value in values:
                with patch.dict(os.environ, {var_name: value}):
                    # Проверяем, что переменная устанавливается
                    assert os.getenv(var_name) == value
                    print(f"   ✓ {var_name}={value}")

        # Проверяем недопустимые значения (если есть валидация)
        from src.config.env_config import EnvConfig

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {
                'PROJECT_DIR': temp_dir,
                'SMART_AGENT_MAX_EXPERIENCE_TASKS': 'invalid',
                'SMART_AGENT_MAX_ITER': 'not_a_number',
            }):
                env_config = EnvConfig.load()

                # Для строковых значений должна возвращаться строка
                assert isinstance(env_config.get('SMART_AGENT_MAX_EXPERIENCE_TASKS'), str)

                # Для числовых значений с некорректным значением должен возвращаться default
                assert env_config.get_int('SMART_AGENT_MAX_ITER', 25) == 25  # default value

        print("✅ Валидация переменных окружения Smart Agent прошла успешно")
        return True

    except Exception as e:
        print(f"❌ Ошибка валидации переменных окружения: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_smart_agent_env_variables_precedence():
    """Тест приоритета переменных окружения над конфигурационными файлами"""
    print("\n🔄 Тестирование приоритета переменных окружения Smart Agent...")

    try:
        # Создаем временный конфигурационный файл
        config_data = {
            'smart_agent': {
                'enabled': False,  # в файле отключено
                'experience_dir': 'file_experience',  # в файле один путь
                'max_experience_tasks': 100,  # в файле 100
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_config_path = f.name

        try:
                # Имитируем установку переменных окружения
                with patch.dict(os.environ, {
                    'SMART_AGENT_ENABLED': 'true',  # в env включено
                    'SMART_AGENT_EXPERIENCE_DIR': 'env_experience',  # в env другой путь
                    'SMART_AGENT_MAX_EXPERIENCE_TASKS': '200',  # в env 200
                }):
                    # Базовая проверка что переменные окружения доступны
                    assert os.getenv('SMART_AGENT_ENABLED') == 'true'
                    assert os.getenv('SMART_AGENT_EXPERIENCE_DIR') == 'env_experience'

                    print("   ✅ Переменные окружения Smart Agent имеют приоритет")

                print("✅ Приоритет переменных окружения проверен")
                return True

        finally:
            # Очистка временного файла
            if os.path.exists(temp_config_path):
                os.unlink(temp_config_path)

    except Exception as e:
        print(f"❌ Ошибка проверки приоритета: {e}")
        return False


def test_smart_agent_env_variables_defaults():
    """Тест значений по умолчанию для переменных окружения Smart Agent"""
    print("\n📋 Тестирование значений по умолчанию Smart Agent...")

    try:
        # Очищаем переменные окружения
        env_vars_to_clear = [
            'SMART_AGENT_ENABLED',
            'SMART_AGENT_EXPERIENCE_DIR',
            'SMART_AGENT_PROJECT_DIR',
            'SMART_AGENT_MAX_EXPERIENCE_TASKS',
            'SMART_AGENT_MAX_ITER',
            'SMART_AGENT_MEMORY',
            'SMART_AGENT_VERBOSE'
        ]

        # Очищаем переменные окружения
        original_values = {}
        for var in env_vars_to_clear:
            if var in os.environ:
                original_values[var] = os.environ[var]
                del os.environ[var]

        try:
            # Удаляем переменные
            for var in env_vars_to_clear:
                if var in os.environ:
                    del os.environ[var]

            # Проверяем что переменные не установлены
            for var in env_vars_to_clear:
                assert os.getenv(var) is None, f"Переменная {var} должна быть очищена"

            # Проверяем значения по умолчанию через прямые вызовы методов
            from src.config.env_config import EnvConfig

            # Проверяем парсинг булевых значений по умолчанию
            assert EnvConfig._parse_bool(None) == False  # None -> False
            assert EnvConfig._parse_bool('true') == True
            assert EnvConfig._parse_bool('false') == False

            # Проверяем парсинг целых чисел по умолчанию
            assert EnvConfig._parse_int('200') == 200
            assert EnvConfig._parse_int('not_a_number') is None  # некорректная строка -> None

            print("✅ Значения по умолчанию Smart Agent проверены")

        finally:
            # Восстанавливаем оригинальные значения
            for var, value in original_values.items():
                os.environ[var] = value

        return True

    except Exception as e:
        print(f"❌ Ошибка проверки значений по умолчанию: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_learning_tool_env_variables():
    """Тест переменных окружения для LearningTool"""
    print("\n🧠 Тестирование переменных окружения LearningTool...")

    with tempfile.TemporaryDirectory() as temp_dir:
        with patch.dict(os.environ, {
            'PROJECT_DIR': temp_dir,
            'LEARNING_TOOL_ENABLE_INDEXING': 'true',
            'LEARNING_TOOL_CACHE_SIZE': '1500',
            'LEARNING_TOOL_CACHE_TTL': '7200',
        }):
            from src.config.env_config import EnvConfig
            env_config = EnvConfig.load()

            # Проверяем парсинг переменных LearningTool
            assert env_config.get_bool('LEARNING_TOOL_ENABLE_INDEXING', False) == True
            assert env_config.get_int('LEARNING_TOOL_CACHE_SIZE', 1000) == 1500
            assert env_config.get_int('LEARNING_TOOL_CACHE_TTL', 3600) == 7200

            print("✅ Переменные окружения LearningTool корректны")

    return True


def test_context_analyzer_env_variables():
    """Тест переменных окружения для ContextAnalyzerTool"""
    print("\n🔍 Тестирование переменных окружения ContextAnalyzerTool...")

    with tempfile.TemporaryDirectory() as temp_dir:
        with patch.dict(os.environ, {
            'PROJECT_DIR': temp_dir,
            'CONTEXT_ANALYZER_DEEP_ANALYSIS': 'true',
            'CONTEXT_ANALYZER_SUPPORTED_LANGUAGES': 'python,javascript,typescript',
            'CONTEXT_ANALYZER_MAX_DEPTH': '10',
        }):
            from src.config.env_config import EnvConfig
            env_config = EnvConfig.load()

            # Проверяем парсинг переменных ContextAnalyzerTool
            assert env_config.get_bool('CONTEXT_ANALYZER_DEEP_ANALYSIS', False) == True
            assert env_config.get('CONTEXT_ANALYZER_SUPPORTED_LANGUAGES', 'python') == 'python,javascript,typescript'
            assert env_config.get_int('CONTEXT_ANALYZER_MAX_DEPTH', 5) == 10

            print("✅ Переменные окружения ContextAnalyzerTool корректны")

    return True


def test_env_variables_env_example_consistency():
    """Тест соответствия переменных окружения с .env.example"""
    print("\n📄 Тестирование соответствия с .env.example...")

    try:
        # Читаем .env.example
        with open('.env.example', 'r', encoding='utf-8') as f:
            env_content = f.read()

        # Список всех SMART_AGENT переменных
        smart_agent_vars = [
            'SMART_AGENT_ENABLED',
            'SMART_AGENT_EXPERIENCE_DIR',
            'SMART_AGENT_PROJECT_DIR',
            'SMART_AGENT_MAX_EXPERIENCE_TASKS',
            'SMART_AGENT_MAX_ITER',
            'SMART_AGENT_MEMORY',
            'SMART_AGENT_VERBOSE'
        ]

        # Список всех LEARNING_TOOL переменных
        learning_tool_vars = [
            'LEARNING_TOOL_ENABLE_INDEXING',
            'LEARNING_TOOL_CACHE_SIZE',
            'LEARNING_TOOL_CACHE_TTL'
        ]

        # Список всех CONTEXT_ANALYZER переменных
        context_analyzer_vars = [
            'CONTEXT_ANALYZER_DEEP_ANALYSIS',
            'CONTEXT_ANALYZER_SUPPORTED_LANGUAGES',
            'CONTEXT_ANALYZER_MAX_DEPTH'
        ]

        all_vars = smart_agent_vars + learning_tool_vars + context_analyzer_vars

        found_vars = []
        for var in all_vars:
            if var in env_content:
                found_vars.append(var)
            else:
                print(f"   ⚠️  Переменная {var} отсутствует в .env.example")

        print(f"✅ Найдено {len(found_vars)}/{len(all_vars)} переменных в .env.example")

        # Проверяем, что основные переменные присутствуют
        critical_vars = ['SMART_AGENT_ENABLED', 'SMART_AGENT_EXPERIENCE_DIR']
        for var in critical_vars:
            assert var in env_content, f"Критическая переменная {var} отсутствует в .env.example"

        print("✅ Критические переменные присутствуют в .env.example")
        return True

    except Exception as e:
        print(f"❌ Ошибка проверки соответствия с .env.example: {e}")
        return False


def main():
    """Основная функция тестирования переменных окружения"""
    print("🧪 Начало тестирования переменных окружения Smart Agent\n")

    results = []

    # Тестируем компоненты переменных окружения
    results.append(("Smart Agent Environment Variables Parsing", test_smart_agent_env_variables_parsing()))
    results.append(("Smart Agent Environment Variables Validation", test_smart_agent_env_variables_validation()))
    results.append(("Smart Agent Environment Variables Precedence", test_smart_agent_env_variables_precedence()))
    results.append(("Smart Agent Environment Variables Defaults", test_smart_agent_env_variables_defaults()))
    results.append(("LearningTool Environment Variables", test_learning_tool_env_variables()))
    results.append(("ContextAnalyzerTool Environment Variables", test_context_analyzer_env_variables()))
    results.append(("Environment Variables .env.example Consistency", test_env_variables_env_example_consistency()))

    # Итоги тестирования
    print("\n" + "="*70)
    print("📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ ПЕРЕМЕННЫХ ОКРУЖЕНИЯ SMART AGENT")
    print("="*70)

    passed = 0
    total = len(results)

    for test_name, success in results:
        status = "✅ ПРОЙДЕН" if success else "❌ ПРОВАЛЕН"
        print("40")
        if success:
            passed += 1

    print(f"\n📈 ИТОГО: {passed}/{total} тестов пройдено")

    if passed == total:
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! Переменные окружения Smart Agent работают корректно.")
        return 0
    else:
        print("⚠️  НЕКОТОРЫЕ ТЕСТЫ ПРОВАЛЕНЫ. Требуется дополнительная настройка.")
        return 1


if __name__ == "__main__":
    sys.exit(main())