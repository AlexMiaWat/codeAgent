#!/usr/bin/env python3
"""
Простые интеграционные тесты Smart Agent
Тестируют базовое взаимодействие инструментов без сложных сценариев
"""

import sys
import os
import tempfile
import shutil
from pathlib import Path

# Добавляем корневую директорию в путь для импорта
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from src.agents.smart_agent import create_smart_agent
from src.tools.learning_tool import LearningTool
from src.tools.context_analyzer_tool import ContextAnalyzerTool


class TestSmartAgentSimpleIntegration:
    """Простые интеграционные тесты Smart Agent"""

    def setup_method(self):
        """Настройка перед каждым тестом"""
        self.temp_dir = Path(tempfile.mkdtemp(prefix="smart_agent_simple_test_"))
        self.experience_dir = self.temp_dir / "experience"
        self.project_dir = self.temp_dir / "project"

        # Создаем тестовую структуру проекта
        self.project_dir.mkdir()
        (self.project_dir / "main.py").write_text("""
import os
from pathlib import Path

def main():
    print("Hello from test project")

if __name__ == "__main__":
    main()
""")

        (self.project_dir / "utils.py").write_text("""
def helper_function():
    return "helper result"
""")

    def teardown_method(self):
        """Очистка после каждого теста"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_learning_tool_context_analyzer_integration(self):
        """Тест интеграции LearningTool и ContextAnalyzerTool"""
        # Создаем инструменты
        learning_tool = LearningTool(experience_dir=str(self.experience_dir))
        context_tool = ContextAnalyzerTool(project_dir=str(self.project_dir))

        # Шаг 1: Анализируем проект
        project_analysis = context_tool.analyze_project_structure()
        assert ".py" in project_analysis  # Проверяем наличие Python файлов

        # Шаг 2: Сохраняем опыт анализа
        result = learning_tool.save_task_experience(
            task_id="integration_test_001",
            task_description="Анализ структуры тестового проекта",
            success=True,
            execution_time=1.5,
            patterns=["analysis", "integration_test"],
            notes="Проанализирована структура простого Python проекта"
        )
        assert "сохранен" in result

        # Шаг 3: Ищем сохраненный опыт
        similar = learning_tool.find_similar_tasks("анализ структуры")
        assert "Анализ структуры тестового проекта" in similar

        # Шаг 4: Получаем рекомендации
        recommendations = learning_tool.get_recommendations("анализ проекта")
        assert "рекомендации" in recommendations

    def test_tools_data_flow(self):
        """Тест потока данных между инструментами"""
        # Создаем инструменты
        learning_tool = LearningTool(experience_dir=str(self.experience_dir))
        context_tool = ContextAnalyzerTool(project_dir=str(self.project_dir))

        # Анализируем зависимости файла
        deps = context_tool.find_file_dependencies("main.py")
        assert isinstance(deps, str)

        # Сохраняем опыт работы с зависимостями
        learning_tool.save_task_experience(
            task_id="deps_test_001",
            task_description="Анализ зависимостей main.py",
            success=True,
            patterns=["dependencies", "imports"]
        )

        # Проверяем статистику
        stats = learning_tool.get_statistics()
        assert "1" in stats  # Одна задача
        assert "100.0%" in stats  # 100% успешности

    def test_unicode_handling_integration(self):
        """Тест обработки Unicode в интеграционном сценарии"""
        # Создаем инструменты
        learning_tool = LearningTool(experience_dir=str(self.experience_dir))
        context_tool = ContextAnalyzerTool(project_dir=str(self.project_dir))

        # Создаем файл с Unicode
        unicode_file = self.project_dir / "unicode_test.py"
        unicode_file.write_text("""
# Тестовый файл с Unicode
def функция_тест():
    return "тестовый результат"
""")

        # Анализируем компонент
        analysis = context_tool.analyze_component("unicode_test.py")
        assert "Анализ компонента" in analysis

        # Сохраняем опыт с Unicode
        learning_tool.save_task_experience(
            task_id="unicode_test_001",
            task_description="Анализ файла с Unicode символами",
            success=True,
            patterns=["unicode", "encoding"]
        )

        # Ищем опыт
        results = learning_tool.find_similar_tasks("unicode")
        assert "Анализ файла с Unicode символами" in results

    def test_error_recovery_integration(self):
        """Тест восстановления после ошибок"""
        # Создаем инструменты
        learning_tool = LearningTool(experience_dir=str(self.experience_dir))
        context_tool = ContextAnalyzerTool(project_dir=str(self.project_dir))

        # Тест 1: Анализ несуществующего файла
        result = context_tool.analyze_component("nonexistent.py")
        assert "не найден" in result

        # Тест 2: Поиск зависимостей несуществующего файла
        result = context_tool.find_file_dependencies("nonexistent.py")
        assert "не найден" in result or "Зависимости" in result

        # Несмотря на ошибки, инструменты должны продолжать работать
        # Сохраняем успешный опыт
        learning_tool.save_task_experience(
            task_id="error_recovery_test",
            task_description="Тест восстановления после ошибок",
            success=True
        )

        stats = learning_tool.get_statistics()
        assert "1" in stats

    def test_pattern_learning_integration(self):
        """Тест обучения паттернам в интеграционном сценарии"""
        learning_tool = LearningTool(experience_dir=str(self.experience_dir))
        context_tool = ContextAnalyzerTool(project_dir=str(self.project_dir))

        # Создаем несколько задач с похожими паттернами
        patterns_data = [
            ("pattern_test_001", "Создание структуры проекта", ["project_setup", "initialization"]),
            ("pattern_test_002", "Настройка конфигурации", ["configuration", "setup"]),
            ("pattern_test_003", "Создание основных модулей", ["project_setup", "modules"])
        ]

        for task_id, description, patterns in patterns_data:
            learning_tool.save_task_experience(
                task_id=task_id,
                task_description=description,
                success=True,
                patterns=patterns
            )

        # Ищем по паттерну "создание"
        results = learning_tool.find_similar_tasks("создание")
        assert "Создание структуры проекта" in results
        assert "Создание основных модулей" in results

        # Получаем рекомендации для похожей задачи
        recommendations = learning_tool.get_recommendations("инициализация нового проекта")
        assert "рекомендации" in recommendations
        assert "project_setup" in recommendations


def run_simple_integration_tests():
    """Запуск простых интеграционных тестов"""
    print("🚀 Запуск простых интеграционных тестов Smart Agent...")

    test_instance = TestSmartAgentSimpleIntegration()

    tests = [
        ("Learning-Context Integration", test_instance.test_learning_tool_context_analyzer_integration),
        ("Tools Data Flow", test_instance.test_tools_data_flow),
        ("Unicode Handling", test_instance.test_unicode_handling_integration),
        ("Error Recovery", test_instance.test_error_recovery_integration),
        ("Pattern Learning", test_instance.test_pattern_learning_integration),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            print(f"\n🔧 Запуск: {test_name}")
            test_instance.setup_method()
            test_func()
            test_instance.teardown_method()
            results.append((test_name, True))
            print(f"✅ {test_name}: ПРОЙДЕН")
        except Exception as e:
            test_instance.teardown_method()
            results.append((test_name, False))
            print(f"❌ {test_name}: ПРОВАЛЕН - {e}")

    # Итоги
    print("\n" + "="*70)
    print("📊 РЕЗУЛЬТАТЫ ПРОСТЫХ ИНТЕГРАЦИОННЫХ ТЕСТОВ SMART AGENT")
    print("="*70)

    passed = 0
    total = len(results)

    for test_name, success in results:
        status = "✅ ПРОЙДЕН" if success else "❌ ПРОВАЛЕН"
        print(f"{test_name:<40} {status}")

        if success:
            passed += 1

    print(f"\n📈 ИТОГО: {passed}/{total} тестов пройдено")

    if passed == total:
        print("🎉 ВСЕ ПРОСТЫЕ ИНТЕГРАЦИОННЫЕ ТЕСТЫ ПРОЙДЕНЫ!")
        return 0
    else:
        print("⚠️  НЕКОТОРЫЕ ТЕСТЫ ПРОВАЛЕНЫ.")
        return 1


if __name__ == "__main__":
    sys.exit(run_simple_integration_tests())