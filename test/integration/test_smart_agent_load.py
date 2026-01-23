#!/usr/bin/env python3
"""
Нагрузочные тесты Smart Agent
Тестирует производительность и стабильность под высокой нагрузкой
"""

import sys
import tempfile
import shutil
import time
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from statistics import mean, median, stdev
import psutil
import gc

# Добавляем корневую директорию в путь для импорта
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class LoadTestMetrics:
    """Метрики нагрузочного тестирования"""

    def __init__(self):
        self.response_times = []
        self.memory_usage = []
        self.cpu_usage = []
        self.errors = 0
        self.start_time = time.time()

    def record_response_time(self, duration):
        self.response_times.append(duration)

    def record_memory_usage(self):
        process = psutil.Process()
        self.memory_usage.append(process.memory_info().rss / 1024 / 1024)  # MB

    def record_cpu_usage(self):
        self.cpu_usage.append(psutil.cpu_percent(interval=0.1))

    def record_error(self):
        self.errors += 1

    def get_summary(self):
        total_time = time.time() - self.start_time
        return {
            'total_time': total_time,
            'total_requests': len(self.response_times),
            'errors': self.errors,
            'success_rate': (len(self.response_times) - self.errors) / len(self.response_times) if self.response_times else 0,
            'avg_response_time': mean(self.response_times) if self.response_times else 0,
            'median_response_time': median(self.response_times) if self.response_times else 0,
            'min_response_time': min(self.response_times) if self.response_times else 0,
            'max_response_time': max(self.response_times) if self.response_times else 0,
            'response_time_stdev': stdev(self.response_times) if len(self.response_times) > 1 else 0,
            'avg_memory_usage': mean(self.memory_usage) if self.memory_usage else 0,
            'avg_cpu_usage': mean(self.cpu_usage) if self.cpu_usage else 0,
            'requests_per_second': len(self.response_times) / total_time if total_time > 0 else 0
        }


class SmartAgentLoadTester:
    """Нагрузочный тестер Smart Agent"""

    def __init__(self, temp_dir=None):
        self.temp_dir = Path(temp_dir or tempfile.mkdtemp(prefix="smart_agent_load_test_"))
        self.experience_dir = self.temp_dir / "experience"
        self.project_dir = self.temp_dir / "project"
        self.metrics = LoadTestMetrics()

        # Создаем тестовую структуру проекта
        self._setup_test_project()

    def _setup_test_project(self):
        """Создание тестовой структуры проекта"""
        self.project_dir.mkdir(parents=True, exist_ok=True)

        # Создаем несколько Python файлов
        for i in range(10):
            file_path = self.project_dir / f"module_{i}.py"
            content = f'''
"""Module {i} for load testing"""

import sys
import os
from pathlib import Path

class Class{i}:
    """Test class {i}"""

    def __init__(self, value):
        self.value = value

    def method_{i}(self):
        """Test method"""
        return f"result_{i}: {{self.value}}"

def function_{i}(param):
    """Test function {i}"""
    return param * {i}

CONSTANT_{i} = {i * 100}

# Some imports to test dependency analysis
import json
import datetime
'''
            file_path.write_text(content)

        # Создаем requirements.txt
        (self.project_dir / "requirements.txt").write_text('''
pytest>=7.0.0
requests>=2.28.0
fastapi>=0.68.0
uvicorn>=0.15.0
''')

        # Создаем README
        (self.project_dir / "README.md").write_text('''
# Load Test Project

This is a test project for Smart Agent load testing.

## Features

- Multiple Python modules
- Dependencies management
- Documentation
''')

    def cleanup(self):
        """Очистка тестовых данных"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def load_test_learning_tool(self, num_tasks=1000, num_threads=10):
        """Нагрузочное тестирование LearningTool"""
        print(f"🔧 Тестирование LearningTool: {num_tasks} задач, {num_threads} потоков")

        from src.tools.learning_tool import LearningTool

        tool = LearningTool(experience_dir=str(self.experience_dir))

        def save_task_worker(task_range):
            """Рабочий поток для сохранения задач"""
            for i in task_range:
                start_time = time.time()

                try:
                    tool._run("save_experience",
                                     task_id=f"load_task_{i:06d}",
                                     task_description=f"Load test task #{i} for performance testing",
                                     success=i % 10 != 0,  # 90% success rate
                                     execution_time=0.1 + (i % 100) * 0.01,
                                     patterns=[f"pattern_{(i % 5)}", "load_test", f"batch_{(i // 100)}"],
                                     notes=f"Detailed notes for task {i} with some additional context")

                    duration = time.time() - start_time
                    self.metrics.record_response_time(duration)
                    self.metrics.record_memory_usage()

                except Exception as e:
                    self.metrics.record_error()
                    print(f"❌ Error in task {i}: {e}")

        # Разделяем задачи между потоками
        tasks_per_thread = num_tasks // num_threads
        task_ranges = []
        for t in range(num_threads):
            start = t * tasks_per_thread
            end = start + tasks_per_thread if t < num_threads - 1 else num_tasks
            task_ranges.append(range(start, end))

        # Запускаем нагрузочное тестирование
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(save_task_worker, task_range) for task_range in task_ranges]
            for future in as_completed(futures):
                future.result()

        # Тестируем поиск после загрузки данных
        print("🔍 Тестирование поиска после загрузки данных...")

        search_queries = [
            "performance testing",
            "load test",
            "pattern_0",
            "batch_5",
            "несуществующий запрос"
        ]

        for query in search_queries:
            start_time = time.time()
            try:
                tool._run("find_similar_tasks", query=query)
                duration = time.time() - start_time
                self.metrics.record_response_time(duration)
                self.metrics.record_memory_usage()
            except Exception as e:
                self.metrics.record_error()
                print(f"❌ Search error for '{query}': {e}")

    def load_test_context_analyzer(self, num_iterations=100, num_threads=5):
        """Нагрузочное тестирование ContextAnalyzerTool"""
        print(f"🔧 Тестирование ContextAnalyzerTool: {num_iterations} итераций, {num_threads} потоков")

        from src.tools.context_analyzer_tool import ContextAnalyzerTool

        tool = ContextAnalyzerTool(
            project_dir=str(self.project_dir),
            max_file_size=1024*1024  # 1MB
        )

        def analysis_worker(iterations):
            """Рабочий поток для анализа"""
            for i in iterations:
                self.metrics.record_memory_usage()

                # Анализ структуры проекта
                start_time = time.time()
                try:
                    tool._run("analyze_project")
                    duration = time.time() - start_time
                    self.metrics.record_response_time(duration)
                except Exception as e:
                    self.metrics.record_error()
                    print(f"❌ Project analysis error {i}: {e}")

                # Анализ зависимостей случайного файла
                file_path = f"module_{(i % 10)}.py"
                start_time = time.time()
                try:
                    tool._run("analyze_dependencies", file_path=file_path)
                    duration = time.time() - start_time
                    self.metrics.record_response_time(duration)
                except Exception as e:
                    self.metrics.record_error()
                    print(f"❌ Dependency analysis error {i}: {e}")

                # Анализ конкретного файла
                start_time = time.time()
                try:
                    tool._run("analyze_file", file_path=file_path)
                    duration = time.time() - start_time
                    self.metrics.record_response_time(duration)
                except Exception as e:
                    self.metrics.record_error()
                    print(f"❌ File analysis error {i}: {e}")

        # Разделяем итерации между потоками
        iterations_per_thread = num_iterations // num_threads
        iteration_ranges = []
        for t in range(num_threads):
            start = t * iterations_per_thread
            end = start + iterations_per_thread if t < num_threads - 1 else num_iterations
            iteration_ranges.append(range(start, end))

        # Запускаем нагрузочное тестирование
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(analysis_worker, it_range) for it_range in iteration_ranges]
            for future in as_completed(futures):
                future.result()

    def load_test_combined_workflow(self, num_workflows=50, num_threads=5):
        """Нагрузочное тестирование комбинированного рабочего процесса"""
        print(f"🔧 Тестирование комбинированного workflow: {num_workflows} workflows, {num_threads} потоков")

        from src.tools.learning_tool import LearningTool
        from src.tools.context_analyzer_tool import ContextAnalyzerTool

        learning_tool = LearningTool(experience_dir=str(self.experience_dir))
        context_tool = ContextAnalyzerTool(project_dir=str(self.project_dir))

        def workflow_worker(workflow_range):
            """Рабочий поток для комбинированного workflow"""
            for i in workflow_range:
                workflow_start = time.time()

                try:
                    # Шаг 1: Анализ проекта
                    context_tool._run("analyze_project")

                    # Шаг 2: Сохранение опыта анализа
                    learning_tool._run("save_experience",
                                     task_id=f"workflow_analysis_{i:04d}",
                                     task_description=f"Analysis workflow #{i}",
                                     success=True,
                                     execution_time=time.time() - workflow_start,
                                     patterns=["analysis", "workflow", f"thread_{threading.current_thread().ident % 5}"],
                                     notes="Combined workflow analysis")

                    # Шаг 3: Поиск похожих задач
                    learning_tool._run("find_similar_tasks",
                                                     query="analysis workflow")

                    # Шаг 4: Анализ зависимостей
                    context_tool._run("analyze_dependencies",
                                                 file_path="module_0.py")

                    # Шаг 5: Сохранение финального опыта
                    total_time = time.time() - workflow_start
                    learning_tool._run("save_experience",
                                     task_id=f"workflow_complete_{i:04d}",
                                     task_description=f"Complete workflow #{i}",
                                     success=True,
                                     execution_time=total_time,
                                     patterns=["complete", "workflow", "integration"],
                                     notes=f"Full workflow completed in {total_time:.2f}s")

                    self.metrics.record_response_time(total_time)
                    self.metrics.record_memory_usage()

                except Exception as e:
                    self.metrics.record_error()
                    print(f"❌ Workflow {i} error: {e}")

        # Разделяем workflows между потоками
        workflows_per_thread = num_workflows // num_threads
        workflow_ranges = []
        for t in range(num_threads):
            start = t * workflows_per_thread
            end = start + workflows_per_thread if t < num_threads - 1 else num_workflows
            workflow_ranges.append(range(start, end))

        # Запускаем нагрузочное тестирование
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(workflow_worker, wf_range) for wf_range in workflow_ranges]
            for future in as_completed(futures):
                future.result()

    def run_full_load_test(self):
        """Запуск полного набора нагрузочных тестов"""
        print("🚀 НАЧАЛО НАГРУЗОЧНОГО ТЕСТИРОВАНИЯ SMART AGENT")
        print("="*70)

        test_configs = [
            ("LearningTool Load Test", lambda: self.load_test_learning_tool(500, 5)),
            ("ContextAnalyzer Load Test", lambda: self.load_test_context_analyzer(50, 3)),
            ("Combined Workflow Load Test", lambda: self.load_test_combined_workflow(25, 3)),
        ]

        all_summaries = []

        for test_name, test_func in test_configs:
            print(f"\n🔥 ЗАПУСК: {test_name}")
            print("-" * 50)

            # Сброс метрик для каждого теста
            self.metrics = LoadTestMetrics()

            try:
                test_func()
                summary = self.metrics.get_summary()
                all_summaries.append((test_name, summary))

                print(f"✅ {test_name} завершен")
                self._print_test_summary(summary)

            except Exception as e:
                print(f"❌ {test_name} провален: {e}")
                all_summaries.append((test_name, {'error': str(e)}))

            # Очистка памяти между тестами
            gc.collect()
            time.sleep(1)

        # Финальный отчет
        print("\n" + "="*70)
        print("📊 ФИНАЛЬНЫЙ ОТЧЕТ НАГРУЗОЧНОГО ТЕСТИРОВАНИЯ")
        print("="*70)

        for test_name, summary in all_summaries:
            print(f"\n🔍 {test_name}:")
            if 'error' in summary:
                print(f"  ❌ ОШИБКА: {summary['error']}")
            else:
                print(".2f")
                print(".2f")
                print(".1f")
                print(".1f")

        return all_summaries

    def _print_test_summary(self, summary):
        """Вывод краткого отчета по тесту"""
        print("\n📈 РЕЗУЛЬТАТЫ:")
        print(f"  ⏱️  Общее время: {summary['total_time']:.2f}с")
        print(f"  📊 Запросов: {summary['total_requests']}")
        print(f"  🎯 Успешность: {summary['success_rate']:.1f}%")
        print(f"  ⚡ Среднее время ответа: {summary['avg_response_time']:.2f}с")
        print(f"  💾 Среднее использование памяти: {summary['avg_memory_usage']:.1f}MB")
        print(f"  🔄 Запросов в секунду: {summary['requests_per_second']:.3f}")
        if summary['errors'] > 0:
            print(f"  ❌ Ошибок: {summary['errors']}")
            print(".1f")


def main():
    """Основная функция нагрузочного тестирования"""
    print("⚡ SMART AGENT LOAD TESTING")
    print("Тестирование производительности и стабильности под нагрузкой\n")

    # Проверяем наличие psutil
    try:
        import psutil
    except ImportError:
        print("❌ Требуется установка psutil: pip install psutil")
        return 1

    tester = None
    try:
        tester = SmartAgentLoadTester()

        # Запуск тестов
        results = tester.run_full_load_test()

        # Анализ результатов
        total_errors = sum(1 for _, summary in results if 'error' in summary or summary.get('errors', 0) > 0)

        if total_errors == 0:
            print("\n🎉 ВСЕ НАГРУЗОЧНЫЕ ТЕСТЫ ПРОЙДЕНЫ!")
            print("Smart Agent готов к высокой нагрузке.")
            return 0
        else:
            print(f"\n⚠️  ОБНАРУЖЕНЫ ПРОБЛЕМЫ В {total_errors} ТЕСТАХ")
            print("Требуется оптимизация производительности.")
            return 1

    except KeyboardInterrupt:
        print("\n⏹️  Тестирование прервано пользователем")
        return 130
    except Exception as e:
        print(f"\n❌ Критическая ошибка тестирования: {e}")
        return 1
    finally:
        if tester:
            tester.cleanup()


if __name__ == "__main__":
    sys.exit(main())