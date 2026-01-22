#!/usr/bin/env python3
"""
Тест интеграции Smart Agent
Проверяет работоспособность LearningTool и ContextAnalyzerTool
"""

import sys
import os
from pathlib import Path

# Добавляем src в путь для импорта
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_learning_tool():
    """Тест LearningTool"""
    print("🧠 Тестирование LearningTool...")

    try:
        from src.tools import LearningTool

        # Создаем инструмент
        tool = LearningTool(experience_dir="test_smart_experience")

        # Тестируем сохранение опыта
        result = tool._run("save_experience", **{
            "task_id": "test_task_001",
            "task_description": "Тестовая задача для проверки обучения",
            "success": True,
            "execution_time": 5.5,
            "notes": "Тестовое выполнение",
            "patterns": ["test", "learning"]
        })

        print(f"✅ Сохранение опыта: {result}")

        # Тестируем поиск похожих задач
        result = tool._run("find_similar", **{
            "query": "тестовая задача",
            "limit": 3
        })

        print(f"✅ Поиск похожих задач: {result}")

        # Тестируем получение рекомендаций
        result = tool._run("get_recommendations", **{
            "current_task": "новая тестовая задача"
        })

        print(f"✅ Получение рекомендаций: {result}")

        # Тестируем получение статистики
        result = tool._run("get_statistics")

        print(f"✅ Получение статистики: {result}")

        return True

    except Exception as e:
        print(f"❌ Ошибка в LearningTool: {e}")
        return False

def test_context_analyzer_tool():
    """Тест ContextAnalyzerTool"""
    print("\n🔍 Тестирование ContextAnalyzerTool...")

    try:
        from src.tools import ContextAnalyzerTool

        # Создаем инструмент
        tool = ContextAnalyzerTool(
            project_dir=".",
            docs_dir="docs"
        )

        # Тестируем анализ структуры проекта
        result = tool._run("analyze_project")

        print(f"✅ Анализ структуры проекта: {result[:200]}...")

        # Тестируем получение контекста для задачи
        result = tool._run("get_context", **{
            "task_description": "интеграция smart agent"
        })

        print(f"✅ Получение контекста задачи: {result[:200]}...")

        # Тестируем поиск связанных файлов
        result = tool._run("find_related_files", **{
            "query": "smart agent"
        })

        print(f"✅ Поиск связанных файлов: {result[:200]}...")

        # Тестируем анализ компонента
        result = tool._run("analyze_component", **{
            "component_path": "src/tools"
        })

        print(f"✅ Анализ компонента: {result[:200]}...")

        return True

    except Exception as e:
        print(f"❌ Ошибка в ContextAnalyzerTool: {e}")
        return False

def test_smart_agent_creation():
    """Тест создания Smart Agent"""
    print("\n🤖 Тестирование создания Smart Agent...")

    try:
        from src.agents import create_smart_agent

        # Создаем агента
        agent = create_smart_agent(
            project_dir=Path("."),
            experience_dir="test_smart_experience"
        )

        # Проверяем основные свойства
        assert agent.role == "Smart Project Executor Agent"
        assert len(agent.tools) >= 2  # Должен иметь как минимум LearningTool и ContextAnalyzerTool

        # Проверяем наличие smart инструментов
        tool_names = [tool.name for tool in agent.tools]
        assert "LearningTool" in tool_names
        assert "ContextAnalyzerTool" in tool_names

        print("✅ Smart Agent создан успешно"        print(f"   Роль: {agent.role}")
        print(f"   Количество инструментов: {len(agent.tools)}")
        print(f"   Инструменты: {tool_names}")

        return True

    except Exception as e:
        print(f"❌ Ошибка создания Smart Agent: {e}")
        return False

def main():
    """Основная функция тестирования"""
    print("🚀 Начало тестирования Smart Agent интеграции\n")

    results = []

    # Тестируем компоненты
    results.append(("LearningTool", test_learning_tool()))
    results.append(("ContextAnalyzerTool", test_context_analyzer_tool()))
    results.append(("Smart Agent Creation", test_smart_agent_creation()))

    # Итоги тестирования
    print("\n" + "="*50)
    print("📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ")
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
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! Smart Agent интеграция работает корректно.")
        return 0
    else:
        print("⚠️  НЕКОТОРЫЕ ТЕСТЫ ПРОВАЛЕНЫ. Требуется дополнительная настройка.")
        return 1

if __name__ == "__main__":
    sys.exit(main())