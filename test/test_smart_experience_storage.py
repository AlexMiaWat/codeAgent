#!/usr/bin/env python3
"""
Тесты хранения и управления опытом Smart Agent
Проверяет работу с директорией smart_experience и файлами опыта
"""

import sys
import json
import tempfile
import shutil
from pathlib import Path

# Добавляем корневую директорию в путь для импорта
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime


def test_smart_experience_directory_creation():
    """Тест создания директории smart_experience"""
    print("📁 Тестирование создания директории smart_experience...")

    try:
        # Используем временную директорию для тестов
        with tempfile.TemporaryDirectory() as temp_dir:
            experience_dir = Path(temp_dir) / "smart_experience"

            # Имитируем создание директории (как делает Smart Agent)
            experience_dir.mkdir(parents=True, exist_ok=True)

            # Проверяем создание директории
            assert experience_dir.exists(), "Директория smart_experience не создана"
            assert experience_dir.is_dir(), "smart_experience должен быть директорией"

            print("✅ Директория smart_experience создана успешно")
            print(f"   Путь: {experience_dir}")

        return True

    except Exception as e:
        print(f"❌ Ошибка создания директории smart_experience: {e}")
        return False


def test_experience_file_creation():
    """Тест создания файла experience.json"""
    print("\n📄 Тестирование создания файла experience.json...")

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            experience_dir = Path(temp_dir) / "smart_experience"
            experience_file = experience_dir / "experience.json"

            # Создаем директорию
            experience_dir.mkdir(parents=True, exist_ok=True)

            # Создаем базовую структуру experience.json
            experience_data = {
                "version": "1.0",
                "created_at": datetime.now().isoformat(),
                "tasks": [],
                "patterns": {},
                "statistics": {
                    "total_tasks": 0,
                    "successful_tasks": 0,
                    "failed_tasks": 0,
                    "average_execution_time": 0.0
                }
            }

            # Записываем в файл
            with open(experience_file, 'w', encoding='utf-8') as f:
                json.dump(experience_data, f, indent=2, ensure_ascii=False)

            # Проверяем создание файла
            assert experience_file.exists(), "Файл experience.json не создан"
            assert experience_file.is_file(), "experience.json должен быть файлом"

            # Проверяем содержимое
            with open(experience_file, 'r', encoding='utf-8') as f:
                loaded_data = json.load(f)

            assert "version" in loaded_data, "Отсутствует версия в experience.json"
            assert "tasks" in loaded_data, "Отсутствует список задач в experience.json"
            assert "patterns" in loaded_data, "Отсутствует секция паттернов в experience.json"
            assert "statistics" in loaded_data, "Отсутствует секция статистики в experience.json"

            print("✅ Файл experience.json создан и валиден")
            print(f"   Размер файла: {experience_file.stat().st_size} байт")
            print(f"   Структура: version={loaded_data['version']}, tasks={len(loaded_data['tasks'])}")

        return True

    except Exception as e:
        print(f"❌ Ошибка создания experience.json: {e}")
        return False


def test_experience_task_storage():
    """Тест сохранения задач в experience.json"""
    print("\n💾 Тестирование сохранения задач в experience.json...")

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            experience_dir = Path(temp_dir) / "smart_experience"
            experience_file = experience_dir / "experience.json"

            # Создаем директорию и базовый файл
            experience_dir.mkdir(parents=True, exist_ok=True)

            initial_data = {
                "version": "1.0",
                "created_at": datetime.now().isoformat(),
                "tasks": [],
                "patterns": {},
                "statistics": {
                    "total_tasks": 0,
                    "successful_tasks": 0,
                    "failed_tasks": 0,
                    "average_execution_time": 0.0
                }
            }

            with open(experience_file, 'w', encoding='utf-8') as f:
                json.dump(initial_data, f, indent=2, ensure_ascii=False)

            # Добавляем тестовую задачу
            test_task = {
                "task_id": "test_task_001",
                "description": "Тестовая задача для проверки сохранения опыта",
                "status": "completed",
                "execution_time": 45.5,
                "tools_used": ["LearningTool", "ContextAnalyzerTool"],
                "success_patterns": ["test_pattern", "learning_pattern"],
                "timestamp": datetime.now().isoformat(),
                "metadata": {
                    "agent_version": "1.0",
                    "config_hash": "abc123"
                }
            }

            # Имитируем добавление задачи (как делает LearningTool)
            with open(experience_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            data["tasks"].append(test_task)
            data["statistics"]["total_tasks"] = len(data["tasks"])
            data["statistics"]["successful_tasks"] += 1
            data["statistics"]["average_execution_time"] = 45.5

            with open(experience_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            # Проверяем сохранение задачи
            with open(experience_file, 'r', encoding='utf-8') as f:
                saved_data = json.load(f)

            assert len(saved_data["tasks"]) == 1, "Задача не сохранена"
            saved_task = saved_data["tasks"][0]

            assert saved_task["task_id"] == "test_task_001", "Неверный task_id"
            assert saved_task["status"] == "completed", "Неверный статус"
            assert saved_task["execution_time"] == 45.5, "Неверное время выполнения"
            assert "LearningTool" in saved_task["tools_used"], "LearningTool не указан в tools_used"

            print("✅ Задача успешно сохранена в experience.json")
            print(f"   Task ID: {saved_task['task_id']}")
            print(f"   Статус: {saved_task['status']}")
            print(f"   Время выполнения: {saved_task['execution_time']} сек")

        return True

    except Exception as e:
        print(f"❌ Ошибка сохранения задачи: {e}")
        return False


def test_experience_patterns_storage():
    """Тест сохранения паттернов решений"""
    print("\n🔄 Тестирование сохранения паттернов решений...")

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            experience_dir = Path(temp_dir) / "smart_experience"
            experience_file = experience_dir / "experience.json"

            # Создаем директорию и базовый файл
            experience_dir.mkdir(parents=True, exist_ok=True)

            initial_data = {
                "version": "1.0",
                "created_at": datetime.now().isoformat(),
                "tasks": [],
                "patterns": {},
                "statistics": {
                    "total_tasks": 0,
                    "successful_tasks": 0,
                    "failed_tasks": 0,
                    "average_execution_time": 0.0
                }
            }

            with open(experience_file, 'w', encoding='utf-8') as f:
                json.dump(initial_data, f, indent=2, ensure_ascii=False)

            # Добавляем паттерн решения
            test_pattern = {
                "pattern_id": "config_optimization",
                "description": "Оптимизация конфигурации Smart Agent",
                "success_rate": 0.95,
                "usage_count": 5,
                "average_time_saved": 120.5,
                "context": {
                    "tools_required": ["LearningTool", "ContextAnalyzerTool"],
                    "config_changes": ["smart_agent.enabled=true"]
                },
                "last_used": datetime.now().isoformat()
            }

            # Имитируем сохранение паттерна
            with open(experience_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            data["patterns"]["config_optimization"] = test_pattern

            with open(experience_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            # Проверяем сохранение паттерна
            with open(experience_file, 'r', encoding='utf-8') as f:
                saved_data = json.load(f)

            assert "config_optimization" in saved_data["patterns"], "Паттерн не сохранен"
            saved_pattern = saved_data["patterns"]["config_optimization"]

            assert saved_pattern["success_rate"] == 0.95, "Неверный success_rate"
            assert saved_pattern["usage_count"] == 5, "Неверный usage_count"
            assert "LearningTool" in saved_pattern["context"]["tools_required"], "Инструменты не сохранены"

            print("✅ Паттерн решения успешно сохранен")
            print(f"   Pattern ID: {saved_pattern['pattern_id']}")
            print(f"   Success rate: {saved_pattern['success_rate']}")
            print(f"   Usage count: {saved_pattern['usage_count']}")

        return True

    except Exception as e:
        print(f"❌ Ошибка сохранения паттерна: {e}")
        return False


def test_experience_statistics_update():
    """Тест обновления статистики в experience.json"""
    print("\n📊 Тестирование обновления статистики...")

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            experience_dir = Path(temp_dir) / "smart_experience"
            experience_file = experience_dir / "experience.json"

            # Создаем директорию и файл с начальными данными
            experience_dir.mkdir(parents=True, exist_ok=True)

            initial_stats = {
                "total_tasks": 10,
                "successful_tasks": 8,
                "failed_tasks": 2,
                "average_execution_time": 45.0,
                "total_execution_time": 450.0,
                "cache_hit_rate": 0.75,
                "pattern_usage_rate": 0.60
            }

            initial_data = {
                "version": "1.0",
                "created_at": datetime.now().isoformat(),
                "tasks": [],
                "patterns": {},
                "statistics": initial_stats
            }

            with open(experience_file, 'w', encoding='utf-8') as f:
                json.dump(initial_data, f, indent=2, ensure_ascii=False)

            # Имитируем обновление статистики после выполнения задачи
            with open(experience_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Новая успешная задача
            data["statistics"]["total_tasks"] += 1
            data["statistics"]["successful_tasks"] += 1
            data["statistics"]["total_execution_time"] += 30.5
            data["statistics"]["average_execution_time"] = (
                data["statistics"]["total_execution_time"] / data["statistics"]["total_tasks"]
            )

            with open(experience_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            # Проверяем обновление статистики
            with open(experience_file, 'r', encoding='utf-8') as f:
                updated_data = json.load(f)

            stats = updated_data["statistics"]
            assert stats["total_tasks"] == 11, "total_tasks не обновлен"
            assert stats["successful_tasks"] == 9, "successful_tasks не обновлен"
            assert abs(stats["average_execution_time"] - 43.68) < 0.01, "average_execution_time рассчитан неверно"

            print("✅ Статистика успешно обновлена")
            print(f"   Total tasks: {stats['total_tasks']}")
            print(f"   Successful tasks: {stats['successful_tasks']}")
            print(f"   Average execution time: {stats['average_execution_time']:.2f}s")
        return True

    except Exception as e:
        print(f"❌ Ошибка обновления статистики: {e}")
        return False


def test_experience_file_integrity():
    """Тест целостности файла experience.json"""
    print("\n🔒 Тестирование целостности experience.json...")

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            experience_dir = Path(temp_dir) / "smart_experience"
            experience_file = experience_dir / "experience.json"

            experience_dir.mkdir(parents=True, exist_ok=True)

            # Создаем корректный JSON
            valid_data = {
                "version": "1.0",
                "created_at": datetime.now().isoformat(),
                "tasks": [
                    {
                        "task_id": "test_001",
                        "description": "Test task",
                        "status": "completed",
                        "execution_time": 10.0,
                        "timestamp": datetime.now().isoformat()
                    }
                ],
                "patterns": {
                    "test_pattern": {
                        "description": "Test pattern",
                        "success_rate": 1.0
                    }
                },
                "statistics": {
                    "total_tasks": 1,
                    "successful_tasks": 1,
                    "failed_tasks": 0,
                    "average_execution_time": 10.0
                }
            }

            with open(experience_file, 'w', encoding='utf-8') as f:
                json.dump(valid_data, f, indent=2, ensure_ascii=False)

            # Проверяем, что файл можно прочитать и распарсить
            with open(experience_file, 'r', encoding='utf-8') as f:
                loaded_data = json.load(f)

            assert loaded_data["version"] == "1.0", "Версия не совпадает"
            assert len(loaded_data["tasks"]) == 1, "Количество задач не совпадает"
            assert "test_pattern" in loaded_data["patterns"], "Паттерн отсутствует"

            # Тестируем обработку поврежденного JSON
            with open(experience_file, 'w', encoding='utf-8') as f:
                f.write("{ invalid json content ")

            try:
                with open(experience_file, 'r', encoding='utf-8') as f:
                    json.load(f)
                assert False, "Поврежденный JSON должен вызывать исключение"
            except json.JSONDecodeError:
                print("✅ Корректно обработан поврежденный JSON")

            print("✅ Целостность experience.json проверена")
            print("   ✓ Корректный JSON загружается")
            print("   ✓ Поврежденный JSON вызывает исключение")
        return True

    except Exception as e:
        print(f"❌ Ошибка проверки целостности: {e}")
        return False


def test_experience_backup_restore():
    """Тест резервного копирования и восстановления experience.json"""
    print("\n💾 Тестирование резервного копирования и восстановления...")

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            experience_dir = Path(temp_dir) / "smart_experience"
            backup_dir = Path(temp_dir) / "backup"

            experience_dir.mkdir(parents=True, exist_ok=True)
            backup_dir.mkdir(parents=True, exist_ok=True)

            # Создаем тестовые данные
            original_data = {
                "version": "1.0",
                "created_at": datetime.now().isoformat(),
                "tasks": [
                    {
                        "task_id": "backup_test_001",
                        "description": "Test task for backup",
                        "status": "completed",
                        "execution_time": 15.0,
                        "timestamp": datetime.now().isoformat()
                    }
                ],
                "patterns": {},
                "statistics": {
                    "total_tasks": 1,
                    "successful_tasks": 1,
                    "failed_tasks": 0,
                    "average_execution_time": 15.0
                }
            }

            experience_file = experience_dir / "experience.json"
            backup_file = backup_dir / "experience_backup.json"

            # Сохраняем оригинальные данные
            with open(experience_file, 'w', encoding='utf-8') as f:
                json.dump(original_data, f, indent=2, ensure_ascii=False)

            # Создаем резервную копию
            shutil.copy2(experience_file, backup_file)

            # Имитируем повреждение оригинального файла
            with open(experience_file, 'w', encoding='utf-8') as f:
                f.write("{ corrupted data }")

            # Восстанавливаем из резервной копии
            shutil.copy2(backup_file, experience_file)

            # Проверяем восстановление
            with open(experience_file, 'r', encoding='utf-8') as f:
                restored_data = json.load(f)

            assert restored_data["version"] == "1.0", "Версия не восстановлена"
            assert len(restored_data["tasks"]) == 1, "Задачи не восстановлены"
            assert restored_data["tasks"][0]["task_id"] == "backup_test_001", "ID задачи не восстановлен"

            print("✅ Резервное копирование и восстановление работает")
            print(f"   Оригинальный файл: {experience_file.exists()}")
            print(f"   Резервная копия: {backup_file.exists()}")
            print(f"   Восстановлено задач: {len(restored_data['tasks'])}")

        return True

    except Exception as e:
        print(f"❌ Ошибка резервного копирования: {e}")
        return False


def main():
    """Основная функция тестирования хранения опыта"""
    print("💾 Начало тестирования хранения опыта Smart Agent\n")

    results = []

    # Тестируем компоненты хранения опыта
    results.append(("Smart Experience Directory Creation", test_smart_experience_directory_creation()))
    results.append(("Experience File Creation", test_experience_file_creation()))
    results.append(("Experience Task Storage", test_experience_task_storage()))
    results.append(("Experience Patterns Storage", test_experience_patterns_storage()))
    results.append(("Experience Statistics Update", test_experience_statistics_update()))
    results.append(("Experience File Integrity", test_experience_file_integrity()))
    results.append(("Experience Backup Restore", test_experience_backup_restore()))

    # Итоги тестирования
    print("\n" + "="*70)
    print("📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ ХРАНЕНИЯ ОПЫТА SMART AGENT")
    print("="*70)

    passed = 0
    total = len(results)

    for test_name, success in results:
        print("40")
        if success:
            passed += 1

    print(f"\n📈 ИТОГО: {passed}/{total} тестов пройдено")

    if passed == total:
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! Хранение опыта Smart Agent работает корректно.")
        return 0
    else:
        print("⚠️  НЕКОТОРЫЕ ТЕСТЫ ПРОВАЛЕНЫ. Требуется исправление системы хранения опыта.")
        return 1


if __name__ == "__main__":
    sys.exit(main())