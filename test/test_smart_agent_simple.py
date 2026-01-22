#!/usr/bin/env python3
"""
Простой тест импортов Smart Agent без зависимостей
"""

import sys
import os
from pathlib import Path

# Добавляем src в путь для импорта
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_imports():
    """Тест базовых импортов Smart Agent"""
    print("🧠 Тестирование импортов Smart Agent...")

    try:
        # Проверяем импорт из __init__.py
        from src.agents import create_smart_agent
        print("✅ Импорт create_smart_agent успешен")

        # Проверяем импорт инструментов
        from src.tools.learning_tool import LearningTool
        print("✅ Импорт LearningTool успешен")

        from src.tools.context_analyzer_tool import ContextAnalyzerTool
        print("✅ Импорт ContextAnalyzerTool успешен")

        # Проверяем импорт smart_agent модуля
        import src.agents.smart_agent as smart_agent_module
        print("✅ Импорт smart_agent модуля успешен")

        return True

    except Exception as e:
        print(f"❌ Ошибка импорта: {e}")
        return False

def test_learning_tool_basic():
    """Тест базовой функциональности LearningTool без зависимостей"""
    print("\n🧠 Тестирование базовой функциональности LearningTool...")

    try:
        from src.tools.learning_tool import LearningTool

        # Создаем инструмент
        tool = LearningTool(experience_dir="test_smart_experience")

        # Проверяем создание директории опыта
        assert tool.experience_dir.exists()
        print("✅ Директория опыта создана")

        # Проверяем создание файла опыта
        assert tool.experience_file.exists()
        print("✅ Файл опыта создан")

        # Проверяем базовые атрибуты
        assert tool.name == "LearningTool"
        assert "обучения" in tool.description.lower()
        print("✅ Базовые атрибуты корректны")

        return True

    except Exception as e:
        print(f"❌ Ошибка в LearningTool: {e}")
        return False

def test_context_analyzer_tool_basic():
    """Тест базовой функциональности ContextAnalyzerTool без зависимостей"""
    print("\n🔍 Тестирование базовой функциональности ContextAnalyzerTool...")

    try:
        from src.tools.context_analyzer_tool import ContextAnalyzerTool

        # Создаем инструмент
        tool = ContextAnalyzerTool(project_dir=".")

        # Проверяем базовые атрибуты
        assert tool.name == "ContextAnalyzerTool"
        assert "анализа контекста" in tool.description.lower()
        assert tool.project_dir == Path(".")
        print("✅ Базовые атрибуты корректны")

        # Проверяем поддерживаемые расширения
        assert ".py" in tool.supported_extensions
        assert ".md" in tool.supported_extensions
        print("✅ Поддерживаемые расширения корректны")

        return True

    except Exception as e:
        print(f"❌ Ошибка в ContextAnalyzerTool: {e}")
        return False

def main():
    """Основная функция тестирования"""
    print("🚀 Начало простого тестирования Smart Agent\n")

    results = []

    # Тестируем импорты
    results.append(("Импорты", test_imports()))
    results.append(("LearningTool базовый", test_learning_tool_basic()))
    results.append(("ContextAnalyzerTool базовый", test_context_analyzer_tool_basic()))

    # Итоги тестирования
    print("\n" + "="*50)
    print("📊 РЕЗУЛЬТАТЫ ПРОСТОГО ТЕСТИРОВАНИЯ")
    print("="*50)

    passed = 0
    total = len(results)

    for test_name, success in results:
        status = "✅ ПРОЙДЕН" if success else "❌ ПРОВАЛЕН"
        print("20")
        if success:
            passed += 1

    print(f"\n📈 ИТОГО: {passed}/{total} тестов пройдено")

    if passed == total:
        print("🎉 ВСЕ БАЗОВЫЕ ТЕСТЫ ПРОЙДЕНЫ! Структура Smart Agent корректна.")
        return 0
    else:
        print("⚠️  НЕКОТОРЫЕ ТЕСТЫ ПРОВАЛЕНЫ. Требуется дополнительная настройка.")
        return 1

if __name__ == "__main__":
    sys.exit(main())