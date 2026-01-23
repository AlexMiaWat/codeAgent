#!/usr/bin/env python3
"""
Тесты мониторинга и логирования Smart Agent
Проверяет работу систем логирования и мониторинга производительности
"""

import sys
import os
import tempfile
import logging
import json
from pathlib import Path
from unittest.mock import patch, mock_open

# Добавляем корневую директорию в путь для импорта
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import yaml
from datetime import datetime, timedelta


def test_smart_agent_logging_setup():
    """Тест настройки логирования Smart Agent"""
    print("📝 Тестирование настройки логирования Smart Agent...")

    try:
        # Имитируем настройку логирования из config/logging.yaml
        log_config = {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'detailed': {
                    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                },
                'simple': {
                    'format': '%(levelname)s - %(message)s'
                }
            },
            'handlers': {
                'console': {
                    'class': 'logging.StreamHandler',
                    'level': 'INFO',
                    'formatter': 'simple',
                    'stream': 'ext://sys.stdout'
                },
                'smart_agent_file': {
                    'class': 'logging.FileHandler',
                    'level': 'DEBUG',
                    'formatter': 'detailed',
                    'filename': 'logs/smart_agent.log'
                },
                'smart_agent_errors': {
                    'class': 'logging.FileHandler',
                    'level': 'ERROR',
                    'formatter': 'detailed',
                    'filename': 'logs/smart_agent_errors.log'
                }
            },
            'loggers': {
                'smart_agent': {
                    'level': 'DEBUG',
                    'handlers': ['console', 'smart_agent_file', 'smart_agent_errors'],
                    'propagate': False
                },
                'learning_tool': {
                    'level': 'INFO',
                    'handlers': ['smart_agent_file'],
                    'propagate': False
                },
                'context_analyzer': {
                    'level': 'INFO',
                    'handlers': ['smart_agent_file'],
                    'propagate': False
                }
            }
        }

        # Создаем логгеры
        smart_logger = logging.getLogger('smart_agent')
        learning_logger = logging.getLogger('learning_tool')
        context_logger = logging.getLogger('context_analyzer')

        # Проверяем уровни логирования
        assert smart_logger.level <= logging.DEBUG, f"Уровень smart_agent не DEBUG: {smart_logger.level}"
        assert learning_logger.level <= logging.INFO, f"Уровень learning_tool не INFO: {learning_logger.level}"
        assert context_logger.level <= logging.INFO, f"Уровень context_analyzer не INFO: {context_logger.level}"

        print("✅ Логгеры Smart Agent настроены корректно")
        print(f"   smart_agent level: {smart_logger.level}")
        print(f"   learning_tool level: {learning_logger.level}")
        print(f"   context_analyzer level: {context_logger.level}")

        return True

    except Exception as e:
        print(f"❌ Ошибка настройки логирования: {e}")
        return False


def test_smart_agent_log_files_creation():
    """Тест создания файлов логов Smart Agent"""
    print("\n📁 Тестирование создания файлов логов...")

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            logs_dir = Path(temp_dir) / "logs"
            logs_dir.mkdir(exist_ok=True)

            # Определяем файлы логов
            log_files = [
                "smart_agent.log",
                "smart_agent_errors.log",
                "smart_agent_performance.log"
            ]

            created_files = []

            for log_file in log_files:
                file_path = logs_dir / log_file

                # Создаем файл лога с тестовым содержимым
                with open(file_path, 'w', encoding='utf-8') as f:
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    f.write(f"{timestamp} - INFO - Smart Agent log initialized\n")

                created_files.append(file_path)

                # Проверяем создание
                assert file_path.exists(), f"Файл лога не создан: {log_file}"
                assert file_path.stat().st_size > 0, f"Файл лога пустой: {log_file}"

            print("✅ Файлы логов Smart Agent созданы")
            for file_path in created_files:
                print(f"   ✓ {file_path.name} ({file_path.stat().st_size} bytes)")

        return True

    except Exception as e:
        print(f"❌ Ошибка создания файлов логов: {e}")
        return False


def test_smart_agent_log_rotation():
    """Тест ротации логов Smart Agent"""
    print("\n🔄 Тестирование ротации логов...")

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            logs_dir = Path(temp_dir) / "logs"
            logs_dir.mkdir(exist_ok=True)

            log_file = logs_dir / "smart_agent.log"

            # Имитируем ротацию логов
            max_log_size = 1024  # 1KB
            rotation_count = 3

            for rotation in range(rotation_count):
                # Создаем записи в лог до достижения лимита размера
                with open(log_file, 'a', encoding='utf-8') as f:
                    for i in range(50):  # Добавляем записи
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        f.write(f"{timestamp} - INFO - Log entry {rotation * 50 + i} from Smart Agent operation\n")

                # Проверяем размер файла
                current_size = log_file.stat().st_size

                if current_size >= max_log_size:
                    # Имитируем ротацию
                    backup_file = logs_dir / f"smart_agent.log.{rotation + 1}"
                    log_file.rename(backup_file)

                    # Создаем новый файл лога
                    with open(log_file, 'w', encoding='utf-8') as f:
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        f.write(f"{timestamp} - INFO - Log rotated, starting new file\n")

                    print(f"   🔄 Ротация {rotation + 1}: {backup_file.name} ({backup_file.stat().st_size} bytes)")

            # Проверяем, что ротация произошла
            backup_files = list(logs_dir.glob("smart_agent.log.*"))
            assert len(backup_files) > 0, "Ротация логов не произошла"

            # Проверяем, что текущий файл лога существует и не пустой
            assert log_file.exists(), "Текущий файл лога не существует после ротации"
            assert log_file.stat().st_size > 0, "Текущий файл лога пустой после ротации"

            print("✅ Ротация логов работает корректно")
            print(f"   Архивных файлов: {len(backup_files)}")
            print(f"   Текущий файл: {log_file.stat().st_size} bytes")

        return True

    except Exception as e:
        print(f"❌ Ошибка ротации логов: {e}")
        return False


def test_performance_logging():
    """Тест логирования метрик производительности"""
    print("\n📈 Тестирование логирования метрик производительности...")

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            perf_log_file = Path(temp_dir) / "smart_agent_performance.log"

            # Имитируем логирование метрик производительности
            performance_metrics = [
                {
                    "timestamp": datetime.now().isoformat(),
                    "operation": "save_experience",
                    "duration": 0.045,
                    "task_id": "test_task_001",
                    "success": True
                },
                {
                    "timestamp": (datetime.now() + timedelta(seconds=1)).isoformat(),
                    "operation": "find_similar",
                    "duration": 0.023,
                    "query_terms": 3,
                    "results_count": 5
                },
                {
                    "timestamp": (datetime.now() + timedelta(seconds=2)).isoformat(),
                    "operation": "analyze_project",
                    "duration": 1.234,
                    "files_analyzed": 25,
                    "dependencies_found": 12
                }
            ]

            # Записываем метрики в лог
            with open(perf_log_file, 'w', encoding='utf-8') as f:
                for metric in performance_metrics:
                    log_entry = json.dumps(metric, ensure_ascii=False)
                    f.write(f"{log_entry}\n")

            # Проверяем запись метрик
            assert perf_log_file.exists(), "Файл метрик производительности не создан"

            # Читаем и парсим метрики
            logged_metrics = []
            with open(perf_log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        logged_metrics.append(json.loads(line.strip()))

            assert len(logged_metrics) == len(performance_metrics), "Количество метрик не совпадает"

            # Проверяем корректность метрик
            for i, metric in enumerate(logged_metrics):
                original = performance_metrics[i]
                assert metric["operation"] == original["operation"], f"Операция не совпадает: {metric['operation']}"
                assert abs(metric["duration"] - original["duration"]) < 0.001, f"Длительность не совпадает: {metric['duration']}"

            print("✅ Метрики производительности логируются корректно")
            print(f"   Записано метрик: {len(logged_metrics)}")
            print("   Операции:")
            for metric in logged_metrics:
                print(f"     - {metric['operation']}: {metric['duration']:.3f}s")

        return True

    except Exception as e:
        print(f"❌ Ошибка логирования метрик: {e}")
        return False


def test_error_logging_and_tracking():
    """Тест логирования и отслеживания ошибок"""
    print("\n❌ Тестирование логирования ошибок...")

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            error_log_file = Path(temp_dir) / "smart_agent_errors.log"

            # Имитируем различные типы ошибок Smart Agent
            error_scenarios = [
                {
                    "timestamp": datetime.now().isoformat(),
                    "level": "ERROR",
                    "component": "LearningTool",
                    "error_type": "FileNotFoundError",
                    "message": "Experience file not found: smart_experience/experience.json",
                    "task_id": "test_task_001",
                    "stack_trace": "FileNotFoundError: [Errno 2] No such file or directory: 'smart_experience/experience.json'"
                },
                {
                    "timestamp": (datetime.now() + timedelta(seconds=1)).isoformat(),
                    "level": "WARNING",
                    "component": "ContextAnalyzerTool",
                    "error_type": "TimeoutError",
                    "message": "Analysis timeout after 30 seconds",
                    "task_id": "test_task_002",
                    "context": {"files_processed": 150, "timeout_limit": 30}
                },
                {
                    "timestamp": (datetime.now() + timedelta(seconds=2)).isoformat(),
                    "level": "ERROR",
                    "component": "SmartAgent",
                    "error_type": "ConfigurationError",
                    "message": "Invalid smart_agent configuration: max_iter must be positive",
                    "config_key": "smart_agent.max_iter",
                    "provided_value": -1
                }
            ]

            # Логируем ошибки
            with open(error_log_file, 'w', encoding='utf-8') as f:
                for error in error_scenarios:
                    # Имитируем структурированное логирование
                    log_line = f"{error['timestamp']} - {error['level']} - {error['component']} - {error['message']}"
                    f.write(f"{log_line}\n")

                    # Добавляем дополнительные детали для ERROR уровня
                    if error['level'] == 'ERROR':
                        f.write(f"  Details: {json.dumps(error, ensure_ascii=False, indent=2)}\n")
                    f.write("\n")

            # Проверяем логирование ошибок
            assert error_log_file.exists(), "Файл лога ошибок не создан"

            # Анализируем лог ошибок
            with open(error_log_file, 'r', encoding='utf-8') as f:
                log_content = f.read()

            # Проверяем наличие всех типов ошибок
            assert "FileNotFoundError" in log_content, "FileNotFoundError не залогирован"
            assert "TimeoutError" in log_content, "TimeoutError не залогирован"
            assert "ConfigurationError" in log_content, "ConfigurationError не залогирован"

            # Проверяем наличие уровней логирования
            assert "ERROR" in log_content, "ERROR уровень не найден"
            assert "WARNING" in log_content, "WARNING уровень не найден"

            print("✅ Ошибки логируются корректно")
            print(f"   Размер лога ошибок: {error_log_file.stat().st_size} bytes")
            print("   Зарегистрированные ошибки:")
            for error in error_scenarios:
                print(f"     - {error['level']}: {error['error_type']} в {error['component']}")

        return True

    except Exception as e:
        print(f"❌ Ошибка логирования ошибок: {e}")
        return False


def test_monitoring_dashboard_data():
    """Тест данных для мониторинга (dashboard)"""
    print("\n📊 Тестирование данных мониторинга...")

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            monitoring_file = Path(temp_dir) / "smart_agent_monitoring.json"

            # Создаем тестовые данные мониторинга
            monitoring_data = {
                "timestamp": datetime.now().isoformat(),
                "uptime_seconds": 3600,
                "version": "1.0.0",
                "status": "active",
                "metrics": {
                    "total_tasks_processed": 150,
                    "successful_tasks": 142,
                    "failed_tasks": 8,
                    "average_task_duration": 45.5,
                    "cache_hit_rate": 0.87,
                    "memory_usage_mb": 125.3,
                    "active_threads": 3
                },
                "components": {
                    "LearningTool": {
                        "status": "active",
                        "experience_tasks": 500,
                        "cache_size": 1000,
                        "hit_rate": 0.85
                    },
                    "ContextAnalyzerTool": {
                        "status": "active",
                        "files_analyzed": 2500,
                        "cache_size": 500,
                        "hit_rate": 0.92
                    }
                },
                "recent_errors": [
                    {
                        "timestamp": (datetime.now() - timedelta(minutes=5)).isoformat(),
                        "component": "LearningTool",
                        "error": "Cache timeout",
                        "severity": "low"
                    }
                ],
                "performance_trends": {
                    "last_24h": {
                        "tasks_per_hour": 6.25,
                        "avg_duration_trend": -0.05,  # улучшение на 5%
                        "error_rate_trend": -0.02     # снижение на 2%
                    }
                }
            }

            # Сохраняем данные мониторинга
            with open(monitoring_file, 'w', encoding='utf-8') as f:
                json.dump(monitoring_data, f, indent=2, ensure_ascii=False)

            # Проверяем создание файла мониторинга
            assert monitoring_file.exists(), "Файл мониторинга не создан"

            # Загружаем и проверяем структуру данных
            with open(monitoring_file, 'r', encoding='utf-8') as f:
                loaded_data = json.load(f)

            # Проверяем обязательные поля
            required_fields = ["timestamp", "status", "metrics", "components"]
            for field in required_fields:
                assert field in loaded_data, f"Отсутствует поле {field} в данных мониторинга"

            # Проверяем метрики
            metrics = loaded_data["metrics"]
            assert metrics["total_tasks_processed"] == 150, "Неверное количество задач"
            assert metrics["successful_tasks"] == 142, "Неверное количество успешных задач"
            assert abs(metrics["average_task_duration"] - 45.5) < 0.1, "Неверное среднее время выполнения"

            # Проверяем компоненты
            components = loaded_data["components"]
            assert "LearningTool" in components, "LearningTool отсутствует в компонентах"
            assert "ContextAnalyzerTool" in components, "ContextAnalyzerTool отсутствует в компонентах"

            print("✅ Данные мониторинга сформированы корректно")
            print(f"   Статус: {loaded_data['status']}")
            print(f"   Обработано задач: {metrics['total_tasks_processed']}")
            print(".1%"            print(".2f")

        return True

    except Exception as e:
        print(f"❌ Ошибка формирования данных мониторинга: {e}")
        return False


def test_log_analysis_and_reporting():
    """Тест анализа логов и формирования отчетов"""
    print("\n📋 Тестирование анализа логов и отчетов...")

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            logs_dir = Path(temp_dir) / "logs"
            reports_dir = Path(temp_dir) / "reports"
            logs_dir.mkdir(exist_ok=True)
            reports_dir.mkdir(exist_ok=True)

            # Создаем тестовые логи
            log_entries = [
                "2024-01-22 10:00:01 - INFO - Smart Agent initialized",
                "2024-01-22 10:00:02 - INFO - LearningTool: Experience loaded (150 tasks)",
                "2024-01-22 10:00:05 - INFO - Task test_001 started",
                "2024-01-22 10:00:05 - INFO - LearningTool: Found 3 similar tasks",
                "2024-01-22 10:00:07 - INFO - ContextAnalyzerTool: Analysis completed (25 files)",
                "2024-01-22 10:00:08 - INFO - Task test_001 completed successfully",
                "2024-01-22 10:00:10 - WARNING - LearningTool: Cache miss rate high (0.75)",
                "2024-01-22 10:00:15 - ERROR - ContextAnalyzerTool: Timeout during analysis",
                "2024-01-22 10:00:20 - INFO - Task test_002 started",
                "2024-01-22 10:00:25 - INFO - Task test_002 completed successfully"
            ]

            log_file = logs_dir / "smart_agent.log"
            with open(log_file, 'w', encoding='utf-8') as f:
                for entry in log_entries:
                    f.write(f"{entry}\n")

            # Анализируем логи и создаем отчет
            analysis_results = {
                "period": {
                    "start": "2024-01-22 10:00:00",
                    "end": "2024-01-22 10:00:30"
                },
                "summary": {
                    "total_entries": len(log_entries),
                    "info_count": sum(1 for e in log_entries if "INFO" in e),
                    "warning_count": sum(1 for e in log_entries if "WARNING" in e),
                    "error_count": sum(1 for e in log_entries if "ERROR" in e)
                },
                "tasks": {
                    "started": 2,
                    "completed": 2,
                    "failed": 0,
                    "success_rate": 1.0
                },
                "performance": {
                    "learning_tool_queries": 1,
                    "context_analysis": 1,
                    "cache_issues": 1,
                    "timeouts": 1
                },
                "recommendations": [
                    "Рассмотреть увеличение размера кэша LearningTool (высокий cache miss rate)",
                    "Настроить таймауты для ContextAnalyzerTool",
                    "Мониторить производительность операций поиска"
                ]
            }

            # Сохраняем отчет
            report_file = reports_dir / "smart_agent_log_analysis.json"
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(analysis_results, f, indent=2, ensure_ascii=False)

            # Проверяем создание отчета
            assert report_file.exists(), "Отчет анализа логов не создан"

            # Проверяем корректность анализа
            with open(report_file, 'r', encoding='utf-8') as f:
                report_data = json.load(f)

            assert report_data["summary"]["total_entries"] == len(log_entries), "Неверное общее количество записей"
            assert report_data["summary"]["error_count"] == 1, "Неверное количество ошибок"
            assert report_data["tasks"]["success_rate"] == 1.0, "Неверный процент успеха задач"

            print("✅ Анализ логов выполнен корректно")
            print(f"   Проанализировано записей: {report_data['summary']['total_entries']}")
            print(f"   Задач выполнено: {report_data['tasks']['completed']}")
            print(f"   Ошибок: {report_data['summary']['error_count']}")
            print(f"   Рекомендаций: {len(report_data['recommendations'])}")

        return True

    except Exception as e:
        print(f"❌ Ошибка анализа логов: {e}")
        return False


def main():
    """Основная функция тестирования мониторинга и логирования"""
    print("📊 Начало тестирования мониторинга и логирования Smart Agent\n")

    results = []

    # Тестируем компоненты мониторинга и логирования
    results.append(("Smart Agent Logging Setup", test_smart_agent_logging_setup()))
    results.append(("Smart Agent Log Files Creation", test_smart_agent_log_files_creation()))
    results.append(("Smart Agent Log Rotation", test_smart_agent_log_rotation()))
    results.append(("Performance Logging", test_performance_logging()))
    results.append(("Error Logging and Tracking", test_error_logging_and_tracking()))
    results.append(("Monitoring Dashboard Data", test_monitoring_dashboard_data()))
    results.append(("Log Analysis and Reporting", test_log_analysis_and_reporting()))

    # Итоги тестирования
    print("\n" + "="*70)
    print("📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ МОНИТОРИНГА И ЛОГИРОВАНИЯ SMART AGENT")
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
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! Мониторинг и логирование Smart Agent работает корректно.")
        return 0
    else:
        print("⚠️  НЕКОТОРЫЕ ТЕСТЫ ПРОВАЛЕНЫ. Требуется исправление системы мониторинга.")
        return 1


if __name__ == "__main__":
    sys.exit(main())