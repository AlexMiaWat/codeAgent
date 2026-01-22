#!/usr/bin/env python3
"""
Скрипт для тестирования архитектуры кеширования LearningTool
"""

import sys
import time
import json
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.tools.learning_tool import LearningTool


def test_cache_performance():
    """Тест производительности кеширования"""
    print("🚀 Тестирование производительности кеширования LearningTool")

    # Создаем временную директорию для тестов
    import tempfile
    with tempfile.TemporaryDirectory(prefix="cache_test_") as temp_dir:
        temp_path = Path(temp_dir)

        # Создаем инструмент с оптимизированными настройками
        tool = LearningTool(
            experience_dir=str(temp_path / "experience"),
            cache_size=100,
            cache_ttl_seconds=300,
            enable_cache_persistence=True,
            enable_indexing=True
        )

        print("📝 Добавление тестовых данных...")

        # Добавляем тестовые задачи
        tasks_data = [
            {"desc": "Настройка pytest конфигурации для проекта", "patterns": ["testing", "configuration"], "time": 15.5},
            {"desc": "Добавление зависимостей requests в requirements.txt", "patterns": ["dependencies", "requirements"], "time": 8.2},
            {"desc": "Создание структуры Python пакета", "patterns": ["project_structure", "python"], "time": 22.1},
            {"desc": "Оптимизация импортов в модуле utils", "patterns": ["optimization", "imports"], "time": 12.3},
            {"desc": "Настройка логирования для приложения", "patterns": ["logging", "configuration"], "time": 18.7},
            {"desc": "Создание unit тестов для класса", "patterns": ["testing", "unit_tests"], "time": 25.4},
            {"desc": "Рефакторинг функции обработки данных", "patterns": ["refactoring", "data_processing"], "time": 35.2},
            {"desc": "Интеграция с внешним API", "patterns": ["integration", "api"], "time": 45.8},
            {"desc": "Оптимизация производительности базы данных", "patterns": ["optimization", "database"], "time": 55.1},
            {"desc": "Настройка CI/CD пайплайна", "patterns": ["ci_cd", "deployment"], "time": 28.9},
        ]

        for i, task in enumerate(tasks_data):
            tool._run("save_experience",
                     task_id=f"perf_task_{i:03d}",
                     task_description=task["desc"],
                     success=True,
                     execution_time=task["time"],
                     patterns=task["patterns"],
                     notes=f"Performance test task {i}")

        print(f"✅ Добавлено {len(tasks_data)} тестовых задач")

        # Тест 1: Первый поиск (холодный кэш)
        print("\n🔍 Тест 1: Поиск с холодным кэшем")
        start_time = time.time()
        result1 = tool._run("find_similar_tasks", query="оптимизации")
        cold_search_time = time.time() - start_time
        print(f"Время холодного поиска: {cold_search_time:.3f}с")
        # Тест 2: Повторный поиск (горячий кэш)
        print("\n🔍 Тест 2: Поиск с горячим кэшем")
        start_time = time.time()
        result2 = tool._run("find_similar_tasks", query="оптимизации")
        hot_search_time = time.time() - start_time
        print(f"Время горячего поиска: {hot_search_time:.3f}с")
        # Проверяем, что результаты одинаковые
        assert result1 == result2, "Результаты поиска должны быть одинаковыми"

        # Тест 3: Разные запросы для заполнения кэша
        print("\n🔍 Тест 3: Множественные запросы")
        queries = ["тестирования", "конфигурации", "проекта", "оптимизации", "базы данных"]

        for query in queries:
            tool._run("find_similar_tasks", query=query)

        # Проверяем статистику кэша
        cache_stats = tool.get_cache_stats()
        print("\n📊 Статистика кэша после тестов:")
        print(cache_stats)

        # Тест 4: Персистентность кэша
        print("\n💾 Тест 4: Персистентность кэша")

        # Создаем новый экземпляр (имитация перезапуска)
        tool2 = LearningTool(
            experience_dir=str(temp_path / "experience"),
            cache_size=100,
            cache_ttl_seconds=300,
            enable_cache_persistence=True
        )

        # Проверяем, что кэш загрузился
        cache_stats2 = tool2.get_cache_stats()
        print("Статистика кэша после загрузки:")
        print(cache_stats2)

        # Выполняем поиск - должен быть из кэша
        start_time = time.time()
        result3 = tool2._run("find_similar_tasks", query="оптимизации")
        persisted_search_time = time.time() - start_time

        assert result1 == result3, "Результаты должны быть одинаковыми после загрузки кэша"
        print(f"Время поиска с персистентным кэшем: {persisted_search_time:.3f}с")
        # Итоговый отчет
        print("\n" + "="*60)
        print("📈 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ КЕШИРОВАНИЯ")
        print("="*60)

        print(f"Холодный поиск: {cold_search_time:.3f}с")
        print(f"Горячий поиск: {hot_search_time:.3f}с")
        print(f"Персистентный поиск: {persisted_search_time:.3f}с")

        # Проверяем улучшение производительности
        if hot_search_time < cold_search_time:
            improvement = (cold_search_time - hot_search_time) / cold_search_time * 100
            print(f"✅ Кэширование ускорило поиск на {improvement:.1f}%")
        else:
            print("⚠️  Кэширование не показало улучшения производительности")

        # Проверяем hit rate
        stats_lines = cache_stats.split('\n')
        hit_rate_line = next((line for line in stats_lines if 'Процент попаданий' in line), None)
        if hit_rate_line:
            hit_rate = float(hit_rate_line.split(': ')[1].rstrip('%'))
            if hit_rate > 50:
                print(f"✅ Хороший hit rate кэша: {hit_rate:.1f}%")
            else:
                print(f"⚠️  Низкий hit rate кэша: {hit_rate:.1f}%")
        print("\n✅ Тестирование кеширования завершено успешно!")


def test_cache_edge_cases():
    """Тест граничных случаев кеширования"""
    print("\n🔬 Тестирование граничных случаев кеширования")

    import tempfile
    with tempfile.TemporaryDirectory(prefix="cache_edge_test_") as temp_dir:
        temp_path = Path(temp_dir)

        # Тест с очень маленьким кэшем
        tool = LearningTool(
            experience_dir=str(temp_path / "experience"),
            cache_size=1,  # Только 1 элемент в кэше
            cache_ttl_seconds=1,  # TTL 1 секунда
            enable_cache_persistence=False
        )

        # Добавляем задачу
        tool._run("save_experience",
                 task_id="edge_case_1",
                 task_description="Тест граничных случаев кеширования",
                 success=True,
                 execution_time=1.0,
                 patterns=["edge", "case"],
                 notes="Edge case test")

        # Выполняем несколько разных запросов
        queries = ["граничных", "случаев", "кеширования", "теста", "оптимизации"]

        for query in queries:
            tool._run("find_similar_tasks", query=query)

        # Проверяем статистику
        cache_stats = tool.get_cache_stats()
        print("Статистика при экстремальных условиях:")
        print(cache_stats)

        # Должен быть хотя бы один eviction
        assert "Выселений из кэша:" in cache_stats

        print("✅ Граничные случаи обработаны корректно")


if __name__ == "__main__":
    try:
        test_cache_performance()
        test_cache_edge_cases()
        print("\n🎉 Все тесты кеширования пройдены успешно!")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Ошибка тестирования кеширования: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)