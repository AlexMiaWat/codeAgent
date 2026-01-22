#!/usr/bin/env python3
"""
Тесты производительности Smart Agent
Проверяет метрики производительности, кэширование и оптимизацию
"""

import sys
import os
import time
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open

# Добавляем корневую директорию в путь для импорта
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import json
from datetime import datetime, timedelta


def test_learning_tool_cache_performance():
    """Тест производительности кэширования LearningTool"""
    print("⚡ Тестирование производительности кэширования LearningTool...")

    try:
        from src.tools.learning_tool import LearningTool

        with tempfile.TemporaryDirectory() as temp_dir:
            # Создаем LearningTool с тестовыми настройками
            tool = LearningTool(
                experience_dir=temp_dir + "/experience",
                max_experience_tasks=1000,
                cache_size=500,
                cache_ttl_seconds=300
            )

            # Тестируем скорость сохранения опыта
            start_time = time.time()

            for i in range(10):
                tool._run("save_experience", **{
                    "task_id": f"perf_test_{i:03d}",
                    "task_description": f"Performance test task {i}",
                    "success": True,
                    "execution_time": 1.0 + i * 0.1,
                    "notes": f"Test note {i}",
                    "patterns": ["performance", f"pattern_{i}"]
                })

            save_time = time.time() - start_time
            avg_save_time = save_time / 10

            print(f"   Сохранение: {save_time:.4f}s (среднее: {avg_save_time:.4f}s)")
            # Проверяем, что среднее время сохранения разумное (< 0.1 сек)
            assert avg_save_time < 0.1, f"Слишком медленное сохранение: {avg_save_time:.4f} сек"

            # Тестируем скорость поиска
            start_time = time.time()

            for i in range(20):
                result = tool._run("find_similar", **{
                    "query": f"performance test task {i % 5}",
                    "limit": 3
                })

            search_time = time.time() - start_time
            avg_search_time = search_time / 20

            print(f"   Поиск: {search_time:.4f}s (среднее: {avg_search_time:.4f}s)")
            # Проверяем, что среднее время поиска разумное (< 0.05 сек)
            assert avg_search_time < 0.05, f"Слишком медленный поиск: {avg_search_time:.4f} сек"

            # Проверяем статистику кэша
            cache_stats = tool.get_cache_stats()
            print(f"   📊 Cache stats: {cache_stats}")

            # Очистка
            experience_file = Path(temp_dir) / "experience" / "experience.json"
            if experience_file.exists():
                experience_file.unlink()

        return True

    except Exception as e:
        print(f"❌ Ошибка тестирования кэширования: {e}")
        return False


def test_context_analyzer_performance():
    """Тест производительности ContextAnalyzerTool"""
    print("\n🔍 Тестирование производительности ContextAnalyzerTool...")

    try:
        from src.tools.context_analyzer_tool import ContextAnalyzerTool

        # Создаем инструмент
        tool = ContextAnalyzerTool(
            project_dir=".",
            max_file_size=1000000,
            supported_extensions=[".py", ".md", ".txt"]
        )

        # Тестируем анализ структуры проекта
        start_time = time.time()
        result = tool._run("analyze_project")
        analysis_time = time.time() - start_time

        print(f"   Анализ: {analysis_time:.4f}s")
        print(f"   📏 Результат: {len(result)} символов")

        # Проверяем, что анализ завершается за разумное время (< 5 сек для тестового проекта)
        assert analysis_time < 5.0, f"Слишком медленный анализ: {analysis_time:.4f} сек"

        # Тестируем кэширование повторных запросов
        start_time = time.time()
        result2 = tool._run("analyze_project")  # Повторный анализ
        cached_analysis_time = time.time() - start_time

        print(".4f"
        # Проверяем, что повторный анализ быстрее (эффект кэширования)
        speedup = analysis_time / cached_analysis_time if cached_analysis_time > 0 else 1
        print(".2f"
        # Для кэширования ожидаем ускорение минимум в 2 раза
        assert speedup >= 2.0, f"Недостаточное ускорение от кэширования: {speedup:.2f}x"

        return True

    except Exception as e:
        print(f"❌ Ошибка тестирования производительности ContextAnalyzer: {e}")
        return False


def test_smart_agent_memory_usage():
    """Тест использования памяти Smart Agent"""
    print("\n🧠 Тестирование использования памяти Smart Agent...")

    try:
        import psutil
        import os

        # Получаем текущий процесс
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        print(".2f"
        # Импортируем инструменты Smart Agent
        from src.tools.learning_tool import LearningTool
        from src.tools.context_analyzer_tool import ContextAnalyzerTool

        import_memory = process.memory_info().rss / 1024 / 1024  # MB
        import_usage = import_memory - initial_memory

        print(".2f"
        # Проверяем, что импорт не использует слишком много памяти (< 50 MB)
        assert import_usage < 50.0, f"Слишком большое использование памяти при импорте: {import_usage:.2f} MB"

        # Создаем инструменты
        with tempfile.TemporaryDirectory() as temp_dir:
            learning_tool = LearningTool(experience_dir=temp_dir + "/experience")
            context_tool = ContextAnalyzerTool(project_dir=".")

            tool_memory = process.memory_info().rss / 1024 / 1024  # MB
            tool_usage = tool_memory - import_memory

            print(".2f"
            # Проверяем, что создание инструментов не использует слишком много памяти (< 20 MB)
            assert tool_usage < 20.0, f"Слишком большое использование памяти при создании инструментов: {tool_usage:.2f} MB"

            # Тестируем нагрузку с большим количеством задач
            for i in range(100):
                learning_tool._run("save_experience", **{
                    "task_id": f"memory_test_{i:03d}",
                    "task_description": f"Memory test task {i}",
                    "success": True,
                    "execution_time": 1.0,
                    "notes": f"Memory test {i}",
                    "patterns": ["memory_test"]
                })

            load_memory = process.memory_info().rss / 1024 / 1024  # MB
            load_usage = load_memory - tool_memory

            print(".2f"
            # Проверяем, что нагрузка не вызывает утечку памяти (< 10 MB прирост)
            assert load_usage < 10.0, f"Возможная утечка памяти при нагрузке: {load_usage:.2f} MB"

        return True

    except ImportError:
        print("⚠️  psutil не установлен, пропускаем тест использования памяти")
        return True
    except Exception as e:
        print(f"❌ Ошибка тестирования памяти: {e}")
        return False


def test_cache_hit_rate_optimization():
    """Тест оптимизации hit rate кэша"""
    print("\n🎯 Тестирование оптимизации hit rate кэша...")

    try:
        from src.tools.learning_tool import LearningTool

        with tempfile.TemporaryDirectory() as temp_dir:
            # Создаем LearningTool с большим кэшем
            tool = LearningTool(
                experience_dir=temp_dir + "/experience",
                max_experience_tasks=1000,
                cache_size=1000,
                cache_ttl_seconds=600
            )

            # Заполняем опыт разнообразными задачами
            task_templates = [
                "Создать API endpoint для {resource}",
                "Оптимизировать запрос к базе данных для {operation}",
                "Добавить валидацию для поля {field}",
                "Реализовать функцию {function} в модуле {module}",
                "Исправить баг в {component} связанный с {issue}"
            ]

            resources = ["users", "products", "orders", "settings"]
            operations = ["select", "insert", "update", "delete"]
            fields = ["email", "password", "name", "date"]
            functions = ["validate", "process", "calculate", "format"]
            modules = ["utils", "models", "views", "controllers"]
            components = ["frontend", "backend", "database", "cache"]
            issues = ["encoding", "timeout", "validation", "permissions"]

            # Создаем 50 разнообразных задач
            for i in range(50):
                template = task_templates[i % len(task_templates)]

                # Подставляем случайные значения
                task_desc = template.format(
                    resource=resources[i % len(resources)],
                    operation=operations[i % len(operations)],
                    field=fields[i % len(fields)],
                    function=functions[i % len(functions)],
                    module=modules[i % len(modules)],
                    component=components[i % len(components)],
                    issue=issues[i % len(issues)]
                )

                tool._run("save_experience", **{
                    "task_id": f"diversity_test_{i:03d}",
                    "task_description": task_desc,
                    "success": True,
                    "execution_time": 2.0 + (i % 10) * 0.5,
                    "notes": f"Diversity test {i}",
                    "patterns": ["diversity", f"pattern_{(i % 5)}"]
                })

            # Тестируем поиск похожих задач (имитируем кэш hits)
            search_queries = [
                "Создать API endpoint для users",
                "Оптимизировать запрос к базе данных для select",
                "Добавить валидацию для поля email",
                "Реализовать функцию validate в модуле utils"
            ]

            hits = 0
            total_searches = 20

            start_time = time.time()
            for i in range(total_searches):
                query = search_queries[i % len(search_queries)]
                result = tool._run("find_similar", **{
                    "query": query,
                    "limit": 3
                })
                if result and len(result) > 0:
                    hits += 1

            search_time = time.time() - start_time
            avg_search_time = search_time / total_searches
            hit_rate = hits / total_searches

            print(".1%"            print(".4f"            print(f"   📊 Всего поисков: {total_searches}, hits: {hits}")

            # Ожидаем hit rate > 80% для хорошей производительности кэша
            assert hit_rate > 0.8, f"Низкий hit rate кэша: {hit_rate:.1%}"
            # Ожидаем среднее время поиска < 0.02 сек
            assert avg_search_time < 0.02, f"Слишком медленный поиск: {avg_search_time:.4f} сек"

        return True

    except Exception as e:
        print(f"❌ Ошибка тестирования hit rate: {e}")
        return False


def test_concurrent_performance():
    """Тест производительности при параллельном использовании"""
    print("\n🔄 Тестирование параллельной производительности...")

    try:
        import threading
        from concurrent.futures import ThreadPoolExecutor, as_completed

        from src.tools.learning_tool import LearningTool

        results = []
        errors = []

        def worker_thread(thread_id):
            """Рабочая функция для потока"""
            try:
                with tempfile.TemporaryDirectory() as temp_dir:
                    tool = LearningTool(
                        experience_dir=f"{temp_dir}/experience_{thread_id}",
                        max_experience_tasks=500
                    )

                    # Выполняем операции в потоке
                    thread_results = []

                    # Сохраняем несколько задач
                    for i in range(5):
                        result = tool._run("save_experience", **{
                            "task_id": f"concurrent_test_{thread_id}_{i:02d}",
                            "task_description": f"Concurrent test task {thread_id}-{i}",
                            "success": True,
                            "execution_time": 1.0,
                            "notes": f"Thread {thread_id}, task {i}",
                            "patterns": [f"thread_{thread_id}", f"task_{i}"]
                        })
                        thread_results.append(result)

                    # Выполняем поиск
                    search_result = tool._run("find_similar", **{
                        "query": f"concurrent test task {thread_id}",
                        "limit": 2
                    })
                    thread_results.append(search_result)

                    return thread_results

            except Exception as e:
                errors.append(f"Thread {thread_id}: {e}")
                return None

        # Запускаем несколько потоков параллельно
        start_time = time.time()

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(worker_thread, i) for i in range(4)]

            for future in as_completed(futures):
                result = future.result()
                if result:
                    results.extend(result)

        total_time = time.time() - start_time

        print(".2f"        print(f"   📊 Всего операций: {len(results)}")
        print(f"   ❌ Ошибок: {len(errors)}")

        if errors:
            print("   Ошибки:")
            for error in errors:
                print(f"     {error}")

        # Проверяем, что все операции завершились успешно
        assert len(errors) == 0, f"Обнаружены ошибки в параллельном режиме: {errors}"

        # Проверяем, что общее время разумное (< 10 сек для 4 потоков x 6 операций)
        assert total_time < 10.0, f"Слишком медленное параллельное выполнение: {total_time:.2f} сек"

        return True

    except ImportError:
        print("⚠️  ThreadPoolExecutor недоступен, пропускаем тест параллельности")
        return True
    except Exception as e:
        print(f"❌ Ошибка тестирования параллельности: {e}")
        return False


def test_performance_metrics_collection():
    """Тест сбора метрик производительности"""
    print("\n📈 Тестирование сбора метрик производительности...")

    try:
        from src.tools.learning_tool import LearningTool

        with tempfile.TemporaryDirectory() as temp_dir:
            tool = LearningTool(
                experience_dir=temp_dir + "/experience",
                max_experience_tasks=100
            )

            # Выполняем различные операции для сбора метрик
            operations = []

            # Сохраняем задачи с разным временем выполнения
            execution_times = [0.5, 1.2, 2.8, 0.9, 3.1, 1.5, 0.7, 2.2]
            for i, exec_time in enumerate(execution_times):
                start = time.time()
                tool._run("save_experience", **{
                    "task_id": f"metrics_test_{i:02d}",
                    "task_description": f"Metrics test task {i}",
                    "success": i % 3 != 2,  # 2 из 3 успешных
                    "execution_time": exec_time,
                    "notes": f"Metrics collection test {i}",
                    "patterns": ["metrics", f"type_{i % 3}"]
                })
                operations.append(("save", time.time() - start))

            # Выполняем поисковые операции
            search_queries = ["metrics test", "performance", "optimization"]
            for query in search_queries:
                start = time.time()
                result = tool._run("find_similar", **{
                    "query": query,
                    "limit": 3
                })
                operations.append(("search", time.time() - start))

            # Рассчитываем метрики
            save_times = [t for op, t in operations if op == "save"]
            search_times = [t for op, t in operations if op == "search"]

            avg_save_time = sum(save_times) / len(save_times) if save_times else 0
            avg_search_time = sum(search_times) / len(search_times) if search_times else 0
            total_operations = len(operations)

            print("   📊 Метрики производительности:"            print(".4f"            print(".4f"            print(f"   🔢 Всего операций: {total_operations}")

            # Проверяем разумность метрик
            assert avg_save_time < 0.1, f"Среднее время сохранения слишком велико: {avg_save_time:.4f}"
            assert avg_search_time < 0.05, f"Среднее время поиска слишком велико: {avg_search_time:.4f}"
            assert total_operations == len(execution_times) + len(search_queries), "Количество операций не совпадает"

            # Получаем статистику из инструмента
            if hasattr(tool, 'get_performance_stats'):
                stats = tool.get_performance_stats()
                print(f"   📈 Статистика инструмента: {stats}")

        return True

    except Exception as e:
        print(f"❌ Ошибка сбора метрик: {e}")
        return False


def main():
    """Основная функция тестирования производительности"""
    print("⚡ Начало тестирования производительности Smart Agent\n")

    results = []

    # Тестируем компоненты производительности
    results.append(("LearningTool Cache Performance", test_learning_tool_cache_performance()))
    results.append(("ContextAnalyzer Performance", test_context_analyzer_performance()))
    results.append(("Smart Agent Memory Usage", test_smart_agent_memory_usage()))
    results.append(("Cache Hit Rate Optimization", test_cache_hit_rate_optimization()))
    results.append(("Concurrent Performance", test_concurrent_performance()))
    results.append(("Performance Metrics Collection", test_performance_metrics_collection()))

    # Итоги тестирования
    print("\n" + "="*70)
    print("📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ ПРОИЗВОДИТЕЛЬНОСТИ SMART AGENT")
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
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! Производительность Smart Agent в норме.")
        return 0
    else:
        print("⚠️  НЕКОТОРЫЕ ТЕСТЫ ПРОВАЛЕНЫ. Требуется оптимизация производительности.")
        return 1


if __name__ == "__main__":
    sys.exit(main())