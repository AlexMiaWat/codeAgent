#!/usr/bin/env python3
"""
Реальные интеграционные тесты Smart Agent
Тестирует полную интеграцию компонентов: создание агента, выполнение задач, сохранение опыта
"""

import sys
import os
import tempfile
import json
from pathlib import Path

# Добавляем корневую директорию в путь для импорта
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_smart_agent_full_integration():
    """Полный интеграционный тест Smart Agent"""
    print("🚀 Начинаем полный интеграционный тест Smart Agent...")

    with tempfile.TemporaryDirectory() as tmp_dir:
        project_dir = Path(tmp_dir)
        experience_dir = f"test_integration_experience_{hash(tmp_dir)}"

        try:
            # 1. Создаем агента
            print("   1. Создание Smart Agent...")
            from src.agents.smart_agent import create_smart_agent

            # Устанавливаем dummy API ключ для тестирования
            os.environ['OPENAI_API_KEY'] = 'dummy-key-for-testing'

            agent = create_smart_agent(
                project_dir=project_dir,
                experience_dir=experience_dir,
                use_docker=False,  # Отключаем Docker для надежности
                use_llm=False,     # Отключаем LLM для тестирования tool-only режима
                verbose=False
            )

            assert agent is not None
            assert agent.role == "Smart Project Executor Agent"
            print("   ✅ Smart Agent создан успешно")

            # 2. Проверяем инструменты
            print("   2. Проверка инструментов...")
            tool_names = [tool.__class__.__name__ for tool in agent.tools]
            assert "LearningTool" in tool_names
            assert "ContextAnalyzerTool" in tool_names
            print(f"   ✅ Инструменты: {tool_names}")

            # 3. Создаем тестовую структуру проекта
            print("   3. Создание тестовой структуры проекта...")
            (project_dir / "src").mkdir()
            (project_dir / "docs").mkdir()
            (project_dir / "test").mkdir()

            # Создаем тестовые файлы
            (project_dir / "src" / "main.py").write_text("""
def hello_world():
    print("Hello, World!")

if __name__ == "__main__":
    hello_world()
""")

            (project_dir / "docs" / "README.md").write_text("""
# Test Project

This is a test project for Smart Agent integration testing.

## Features
- Hello World function
- Integration tests
""")

            (project_dir / "test" / "test_main.py").write_text("""
import sys
sys.path.insert(0, '../src')

def test_hello_world():
    from main import hello_world
    # This would normally print, but we can't capture stdout in this test
    assert hello_world is not None

if __name__ == "__main__":
    test_hello_world()
    print("All tests passed!")
""")

            print("   ✅ Тестовая структура проекта создана")

            # 4. Тестируем ContextAnalyzerTool
            print("   4. Тестирование ContextAnalyzerTool...")
            context_tool = None
            for tool in agent.tools:
                if tool.__class__.__name__ == "ContextAnalyzerTool":
                    context_tool = tool
                    break

            assert context_tool is not None

            # Анализируем структуру проекта
            result = context_tool._run("analyze_project")
            assert "src" in result
            assert "docs" in result
            assert "test" in result
            print("   ✅ Анализ структуры проекта работает")

            # Получаем контекст задачи
            result = context_tool._run("get_context", **{
                "task_description": "добавить функцию приветствия"
            })
            assert len(result) > 0
            print("   ✅ Получение контекста задачи работает")

            # 5. Тестируем LearningTool
            print("   5. Тестирование LearningTool...")
            learning_tool = None
            for tool in agent.tools:
                if tool.__class__.__name__ == "LearningTool":
                    learning_tool = tool
                    break

            assert learning_tool is not None

            # Сохраняем опыт выполнения задачи
            result = learning_tool._run("save_experience", **{
                "task_id": "integration_test_001",
                "task_description": "Создание тестовой структуры проекта",
                "success": True,
                "execution_time": 2.5,
                "notes": "Успешно создана структура с src/, docs/, test/",
                "patterns": ["project_setup", "structure_creation"]
            })
            assert "успешно" in result.lower()
            print("   ✅ Сохранение опыта работает")

            experience_file = learning_tool.experience_file

            # Ищем похожие задачи
            result = learning_tool._run("find_similar", **{
                "query": "создание структуры проекта",
                "limit": 5
            })
            assert len(result) > 0
            print("   ✅ Поиск похожих задач работает")

            # Получаем рекомендации
            result = learning_tool._run("get_recommendations", **{
                "current_task": "настроить тестовую среду"
            })
            assert len(result) > 0
            print("   ✅ Получение рекомендаций работает")

            # Получаем статистику
            result = learning_tool._run("get_statistics")
            assert "Всего задач:" in result
            print("   ✅ Получение статистики работает")

            # 6. Проверяем сохранение данных
            print("   6. Проверка сохранения данных...")
            print(f"   Путь к файлу опыта: {experience_file}")
            print(f"   Файл существует: {experience_file.exists()}")

            if experience_file.exists():
                with open(experience_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                print(f"   Данные в файле: {data}")
                assert "tasks" in data
                print(f"   Количество задач: {len(data['tasks'])}")
                assert len(data["tasks"]) == 1
                assert data["tasks"][0]["task_id"] == "integration_test_001"
                assert data["tasks"][0]["success"] == True
                print("   ✅ Данные опыта корректно сохранены")
            else:
                print("   ❌ Файл опыта не найден!")
                return False

            # 7. Тестируем несколько задач подряд
            print("   7. Тестирование последовательных задач...")
            for i in range(2, 5):
                result = learning_tool._run("save_experience", **{
                    "task_id": f"integration_test_{i:03d}",
                    "task_description": f"Тестовая задача #{i}",
                    "success": i % 2 == 0,  # Чередуем успех/неудачу
                    "execution_time": float(i),
                    "notes": f"Задача {i} выполнена",
                    "patterns": [f"test_task_{i}"]
                })
                print(f"   Результат сохранения задачи {i}: '{result}'")
                assert "сохранен" in result.lower() and ("успешно" in result.lower() or "неудачно" in result.lower())

            # Проверяем статистику после нескольких задач
            result = learning_tool._run("get_statistics")
            print(f"   Статистика: {result}")
            assert "Всего задач: 4" in result
            assert "Успешных задач: 3" in result  # Задачи 001, 002, 004
            assert "Неудачных задач: 1" in result  # Задача 003
            print("   ✅ Статистика корректна после нескольких задач")

            print("🎉 ПОЛНЫЙ ИНТЕГРАЦИОННЫЙ ТЕСТ ПРОЙДЕН УСПЕШНО!")
            return True

        except Exception as e:
            print(f"❌ ОШИБКА В ИНТЕГРАЦИОННОМ ТЕСТЕ: {e}")
            import traceback
            traceback.print_exc()
            return False

def test_smart_agent_error_handling():
    """Тест обработки ошибок в Smart Agent"""
    print("\n🛡️  Тестирование обработки ошибок...")

    try:
        # Тестируем graceful degradation без API ключей
        import os

        # Сохраняем оригинальные ключи
        original_keys = {}
        for key in ['OPENAI_API_KEY', 'OPENROUTER_API_KEY']:
            if key in os.environ:
                original_keys[key] = os.environ[key]
                del os.environ[key]

        # Устанавливаем dummy ключ
        os.environ['OPENAI_API_KEY'] = 'dummy-key-for-testing'

        try:
            from src.agents.smart_agent import create_smart_agent

            with tempfile.TemporaryDirectory() as tmp_dir:
                project_dir = Path(tmp_dir)

                # Создаем агента без реальных API ключей
                agent = create_smart_agent(
                    project_dir=project_dir,
                    use_docker=False,
                    use_llm=False,  # Явно отключаем LLM
                    verbose=False
                )

                assert agent is not None
                assert len(agent.tools) >= 2  # Должен иметь базовые инструменты

                # Проверяем что агент может работать без LLM
                tool_names = [tool.__class__.__name__ for tool in agent.tools]
                assert "LearningTool" in tool_names
                assert "ContextAnalyzerTool" in tool_names

                print("   ✅ Graceful degradation работает корректно")
                return True

        finally:
            # Восстанавливаем ключи
            for key, value in original_keys.items():
                os.environ[key] = value

    except Exception as e:
        print(f"❌ Ошибка в тесте обработки ошибок: {e}")
        return False

def main():
    """Основная функция тестирования"""
    print("🚀 НАЧАЛО РЕАЛЬНЫХ ИНТЕГРАЦИОННЫХ ТЕСТОВ SMART AGENT\n")

    results = []

    # Запускаем тесты
    results.append(("Полная интеграция Smart Agent", test_smart_agent_full_integration()))
    results.append(("Обработка ошибок", test_smart_agent_error_handling()))

    # Итоги
    print("\n" + "="*60)
    print("📊 РЕЗУЛЬТАТЫ РЕАЛЬНЫХ ИНТЕГРАЦИОННЫХ ТЕСТОВ")
    print("="*60)

    passed = 0
    total = len(results)

    for test_name, success in results:
        status = "✅ ПРОЙДЕН" if success else "❌ ПРОВАЛЕН"
        print("30")
        if success:
            passed += 1

    print(f"\n📈 ИТОГО: {passed}/{total} тестов пройдено")

    if passed == total:
        print("🎉 ВСЕ РЕАЛЬНЫЕ ИНТЕГРАЦИОННЫЕ ТЕСТЫ ПРОЙДЕНЫ!")
        print("Smart Agent готов к использованию в реальных сценариях.")
        return 0
    else:
        print("⚠️  НЕКОТОРЫЕ ТЕСТЫ ПРОВАЛЕНЫ. Требуется доработка.")
        return 1

if __name__ == "__main__":
    sys.exit(main())