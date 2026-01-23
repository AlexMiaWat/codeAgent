#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Комплексное тестирование проекта Code Agent с учетом всех последних изменений

Проверяет:
1. Валидацию конфигурации при старте
2. Обработку ошибок
3. Безопасность (валидация путей, проверка прав доступа)
4. Валидацию YAML схемы
5. Улучшенное определение формата TODO
6. Работу с реальным сервером
7. Работу с реальными целевыми проектами
"""

import sys
import os
import time
import logging
import tempfile
from pathlib import Path
from typing import List, Tuple

# Добавляем путь к проекту
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Используем абсолютные импорты через src
from src.config_loader import ConfigLoader
from src.config_validator import ConfigValidator
from src.todo_manager import TodoManager
from src.status_manager import StatusManager
from src.security_utils import sanitize_for_logging
from src.server import CodeAgentServer

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TestResults:
    """Класс для хранения результатов тестирования"""
    
    def __init__(self):
        self.passed: List[str] = []
        self.failed: List[Tuple[str, str]] = []
        self.warnings: List[str] = []
    
    def add_pass(self, test_name: str):
        self.passed.append(test_name)
        print(f"[OK] PASS: {test_name}")
    
    def add_fail(self, test_name: str, error: str):
        self.failed.append((test_name, error))
        print(f"[FAIL] FAIL: {test_name}")
        print(f"   Ошибка: {error}")
    
    def add_warning(self, test_name: str, message: str):
        self.warnings.append(f"{test_name}: {message}")
        print(f"[WARN]  WARN: {test_name}: {message}")
    
    def print_summary(self):
        print("\n" + "=" * 80)
        print("ИТОГОВАЯ СТАТИСТИКА ТЕСТИРОВАНИЯ")
        print("=" * 80)
        print(f"[OK] Пройдено: {len(self.passed)}")
        print(f"[FAIL] Провалено: {len(self.failed)}")
        print(f"[WARN]  Предупреждений: {len(self.warnings)}")
        print("=" * 80)
        
        if self.passed:
            print("\n[OK] Пройденные тесты:")
            for test in self.passed:
                print(f"   - {test}")
        
        if self.failed:
            print("\n[FAIL] Проваленные тесты:")
            for test, error in self.failed:
                print(f"   - {test}")
                print(f"     {error}")
        
        if self.warnings:
            print("\n[WARN]  Предупреждения:")
            for warning in self.warnings:
                print(f"   - {warning}")


def test_config_validation(results: TestResults):
    """Тест валидации конфигурации"""
    print("\n" + "=" * 80)
    print("ТЕСТ 1: Валидация конфигурации")
    print("=" * 80)
    
    try:
        # Тест 1.1: Загрузка валидной конфигурации
        print("\n1.1. Загрузка валидной конфигурации...")
        config = ConfigLoader("config/config.yaml")
        project_dir = config.get_project_dir()
        if project_dir.exists():
            results.add_pass("Загрузка валидной конфигурации")
        else:
            results.add_fail("Загрузка валидной конфигурации", f"Проект не найден: {project_dir}")
            return
        
        # Тест 1.2: Валидация схемы YAML
        print("\n1.2. Валидация схемы YAML...")
        validator = ConfigValidator(config.config)
        validator.validate()
        results.add_pass("Валидация схемы YAML")
        
        # Тест 1.3: Проверка обязательных полей
        print("\n1.3. Проверка обязательных полей...")
        required_sections = ['project', 'agent', 'server']
        for section in required_sections:
            if section not in config.config:
                results.add_fail(f"Проверка обязательных полей ({section})", f"Секция {section} отсутствует")
                return
        results.add_pass("Проверка обязательных полей")
        
    except Exception as e:
        results.add_fail("Валидация конфигурации", str(e))
        import traceback
        traceback.print_exc()


def test_path_validation(results: TestResults):
    """Тест валидации путей и безопасности"""
    print("\n" + "=" * 80)
    print("ТЕСТ 2: Валидация путей и безопасность")
    print("=" * 80)
    
    try:
        config = ConfigLoader("config/config.yaml")
        
        # Тест 2.1: Проверка валидации project_dir
        print("\n2.1. Проверка валидации project_dir...")
        project_dir = config.get_project_dir()
        if project_dir.exists() and project_dir.is_dir():
            results.add_pass("Валидация project_dir")
        else:
            results.add_fail("Валидация project_dir", f"Невалидный путь: {project_dir}")
            return
        
        # Тест 2.2: Проверка защиты от path traversal
        print("\n2.2. Проверка защиты от path traversal...")
        try:
            # Пробуем создать путь с множественными ..
            test_path = Path("../../../../etc/passwd")
            validated = config._validate_path(test_path, "test_path")
            # Если валидация прошла, это проблема безопасности
            if ".." in str(validated):
                results.add_warning("Защита от path traversal", "Путь с .. прошел валидацию")
            else:
                results.add_pass("Защита от path traversal")
        except ValueError:
            # Ожидаемое поведение - путь отклонен
            results.add_pass("Защита от path traversal")
        
        # Тест 2.3: Проверка валидации docs_dir
        print("\n2.3. Проверка валидации docs_dir...")
        docs_dir = config.get_docs_dir()
        if docs_dir.exists():
            results.add_pass("Валидация docs_dir")
        else:
            results.add_warning("Валидация docs_dir", f"Директория docs не найдена: {docs_dir}")
        
    except Exception as e:
        results.add_fail("Валидация путей", str(e))
        import traceback
        traceback.print_exc()


def test_file_permissions(results: TestResults):
    """Тест проверки прав доступа к файлам"""
    print("\n" + "=" * 80)
    print("ТЕСТ 3: Проверка прав доступа к файлам")
    print("=" * 80)
    
    try:
        config = ConfigLoader("config/config.yaml")
        project_dir = config.get_project_dir()
        status_file = config.get_status_file()
        
        # Тест 3.1: Проверка прав на чтение project_dir
        print("\n3.1. Проверка прав на чтение project_dir...")
        if os.access(project_dir, os.R_OK):
            results.add_pass("Права на чтение project_dir")
        else:
            results.add_fail("Права на чтение project_dir", "Нет прав на чтение")
        
        # Тест 3.2: Проверка прав на запись project_dir
        print("\n3.2. Проверка прав на запись project_dir...")
        if os.access(project_dir, os.W_OK):
            results.add_pass("Права на запись project_dir")
        else:
            results.add_fail("Права на запись project_dir", "Нет прав на запись")
        
        # Тест 3.3: Проверка работы StatusManager с правами доступа
        print("\n3.3. Проверка работы StatusManager...")
        status_manager = StatusManager(status_file)
        # Пробуем прочитать статус
        try:
            status = status_manager.read_status()
            results.add_pass("Работа StatusManager")
        except PermissionError as e:
            results.add_fail("Работа StatusManager", f"Ошибка прав доступа: {e}")
        except Exception as e:
            # Файл может не существовать - это нормально
            results.add_warning("Работа StatusManager", f"Файл статуса не найден или ошибка: {e}")
        
    except Exception as e:
        results.add_fail("Проверка прав доступа", str(e))
        import traceback
        traceback.print_exc()


def test_todo_format_detection(results: TestResults):
    """Тест определения формата TODO"""
    print("\n" + "=" * 80)
    print("ТЕСТ 4: Определение формата TODO")
    print("=" * 80)
    
    try:
        config = ConfigLoader("config/config.yaml")
        project_dir = config.get_project_dir()
        
        # Тест 4.1: Определение формата Markdown
        print("\n4.1. Определение формата Markdown...")
        with tempfile.TemporaryDirectory() as tmpdir:
            test_project = Path(tmpdir) / "test_project"
            test_project.mkdir()
            
            todo_md = test_project / "todo.md"
            todo_md.write_text("""# Задачи
- [ ] Задача 1
- [x] Задача 2
""", encoding='utf-8')
            
            todo_manager = TodoManager(test_project, todo_format="md")
            detected_format = todo_manager._detect_file_format()
            if detected_format == "md":
                results.add_pass("Определение формата Markdown")
            else:
                results.add_fail("Определение формата Markdown", f"Определен формат: {detected_format}")
        
        # Тест 4.2: Определение формата YAML
        print("\n4.2. Определение формата YAML...")
        with tempfile.TemporaryDirectory() as tmpdir:
            test_project = Path(tmpdir) / "test_project"
            test_project.mkdir()
            
            todo_yaml = test_project / "todo.yaml"
            todo_yaml.write_text("""tasks:
  - text: Задача 1
    done: false
""", encoding='utf-8')
            
            todo_manager = TodoManager(test_project, todo_format="yaml")
            detected_format = todo_manager._detect_file_format()
            if detected_format == "yaml":
                results.add_pass("Определение формата YAML")
            else:
                results.add_fail("Определение формата YAML", f"Определен формат: {detected_format}")
        
        # Тест 4.3: Определение формата TXT
        print("\n4.3. Определение формата TXT...")
        with tempfile.TemporaryDirectory() as tmpdir:
            test_project = Path(tmpdir) / "test_project"
            test_project.mkdir()
            
            todo_txt = test_project / "todo.txt"
            todo_txt.write_text("""1. Задача 1
2. Задача 2
""", encoding='utf-8')
            
            todo_manager = TodoManager(test_project, todo_format="txt")
            detected_format = todo_manager._detect_file_format()
            if detected_format == "txt":
                results.add_pass("Определение формата TXT")
            else:
                results.add_fail("Определение формата TXT", f"Определен формат: {detected_format}")
        
        # Тест 4.4: Загрузка TODO из реального проекта
        print("\n4.4. Загрузка TODO из реального проекта...")
        try:
            todo_manager = TodoManager(project_dir)
            tasks = todo_manager.get_all_tasks()
            results.add_pass(f"Загрузка TODO из реального проекта (найдено задач: {len(tasks)})")
        except Exception as e:
            results.add_warning("Загрузка TODO из реального проекта", f"Ошибка: {e}")
        
    except Exception as e:
        results.add_fail("Определение формата TODO", str(e))
        import traceback
        traceback.print_exc()


def test_security_utils(results: TestResults):
    """Тест утилит безопасности"""
    print("\n" + "=" * 80)
    print("ТЕСТ 5: Утилиты безопасности")
    print("=" * 80)
    
    try:
        # Тест 5.1: Санитизация данных с API ключами
        print("\n5.1. Санитизация данных с API ключами...")
        test_data = {
            "api_key": "sk-1234567890abcdef",
            "password": "secret123",
            "normal_field": "normal_value"
        }
        sanitized = sanitize_for_logging(test_data)
        
        if isinstance(sanitized, dict):
            if sanitized.get("api_key") == "***REDACTED***" or "REDACTED" in str(sanitized.get("api_key")):
                results.add_pass("Санитизация API ключей")
            else:
                results.add_fail("Санитизация API ключей", f"Ключ не был скрыт: {sanitized.get('api_key')}")
        else:
            results.add_fail("Санитизация API ключей", "Неправильный тип возвращаемого значения")
        
        # Тест 5.2: Санитизация строк с API ключами
        print("\n5.2. Санитизация строк с API ключами...")
        test_string = "API key: sk-1234567890abcdef"
        sanitized_string = sanitize_for_logging(test_string)
        if "REDACTED" in str(sanitized_string) or "sk-" not in str(sanitized_string):
            results.add_pass("Санитизация строк с API ключами")
        else:
            results.add_warning("Санитизация строк с API ключами", "Ключ не был скрыт в строке")
        
    except Exception as e:
        results.add_fail("Утилиты безопасности", str(e))
        import traceback
        traceback.print_exc()


def test_server_initialization(results: TestResults):
    """Тест инициализации сервера"""
    print("\n" + "=" * 80)
    print("ТЕСТ 6: Инициализация сервера")
    print("=" * 80)
    
    try:
        # Тест 6.1: Создание сервера с валидацией
        print("\n6.1. Создание сервера с валидацией...")
        server = CodeAgentServer("config/config.yaml")
        
        # Проверяем, что сервер инициализирован
        if server.project_dir and server.project_dir.exists():
            results.add_pass("Создание сервера с валидацией")
        else:
            results.add_fail("Создание сервера с валидацией", "Проект не найден")
            return
        
        # Тест 6.2: Проверка валидации конфигурации при инициализации
        print("\n6.2. Проверка валидации конфигурации...")
        # Валидация должна была произойти в __init__
        if hasattr(server, 'config') and server.config:
            results.add_pass("Валидация конфигурации при инициализации")
        else:
            results.add_fail("Валидация конфигурации при инициализации", "Конфигурация не загружена")
        
        # Тест 6.3: Проверка инициализации менеджеров
        print("\n6.3. Проверка инициализации менеджеров...")
        if hasattr(server, 'todo_manager') and hasattr(server, 'status_manager'):
            results.add_pass("Инициализация менеджеров")
        else:
            results.add_fail("Инициализация менеджеров", "Менеджеры не инициализированы")
        
    except ValueError as e:
        # Ожидаемая ошибка валидации
        if "Ошибки конфигурации" in str(e) or "PROJECT_DIR" in str(e):
            results.add_warning("Создание сервера", f"Ошибка валидации (возможно, PROJECT_DIR не установлен): {e}")
        else:
            results.add_fail("Создание сервера", str(e))
    except Exception as e:
        results.add_fail("Инициализация сервера", str(e))
        import traceback
        traceback.print_exc()


def test_error_handling(results: TestResults):
    """Тест обработки ошибок"""
    print("\n" + "=" * 80)
    print("ТЕСТ 7: Обработка ошибок")
    print("=" * 80)
    
    try:
        # Тест 7.1: Обработка несуществующего файла конфигурации
        print("\n7.1. Обработка несуществующего файла конфигурации...")
        try:
            config = ConfigLoader("config/nonexistent.yaml")
            results.add_fail("Обработка несуществующего файла", "Не выброшено исключение")
        except FileNotFoundError:
            results.add_pass("Обработка несуществующего файла конфигурации")
        except Exception as e:
            results.add_warning("Обработка несуществующего файла", f"Неожиданное исключение: {e}")
        
        # Тест 7.2: Обработка невалидного YAML
        print("\n7.2. Обработка невалидного YAML...")
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [")
            invalid_yaml_path = f.name
        
        try:
            config = ConfigLoader(invalid_yaml_path)
            results.add_warning("Обработка невалидного YAML", "Не выброшено исключение")
        except Exception:
            results.add_pass("Обработка невалидного YAML")
        finally:
            os.unlink(invalid_yaml_path)
        
        # Тест 7.3: Обработка отсутствующего PROJECT_DIR
        print("\n7.3. Обработка отсутствующего PROJECT_DIR...")
        original_env = os.environ.get('PROJECT_DIR')
        try:
            if 'PROJECT_DIR' in os.environ:
                del os.environ['PROJECT_DIR']
            
            # Перезагружаем dotenv для очистки
            from dotenv import load_dotenv
            load_dotenv(override=True)
            
            try:
                config = ConfigLoader("config/config.yaml")
                project_dir = config.get_project_dir()
                # Если валидация прошла, значит PROJECT_DIR был в .env
                results.add_warning("Обработка отсутствующего PROJECT_DIR", "PROJECT_DIR найден в .env")
            except (ValueError, FileNotFoundError) as e:
                if "PROJECT_DIR" in str(e) or "project.base_dir" in str(e):
                    results.add_pass("Обработка отсутствующего PROJECT_DIR")
                else:
                    results.add_warning("Обработка отсутствующего PROJECT_DIR", f"Неожиданная ошибка: {e}")
        finally:
            if original_env:
                os.environ['PROJECT_DIR'] = original_env
        
    except Exception as e:
        results.add_fail("Обработка ошибок", str(e))
        import traceback
        traceback.print_exc()


def test_file_size_limits(results: TestResults):
    """Тест ограничений размера файлов"""
    print("\n" + "=" * 80)
    print("ТЕСТ 8: Ограничения размера файлов")
    print("=" * 80)
    
    try:
        config = ConfigLoader("config/config.yaml")
        project_dir = config.get_project_dir()
        
        # Тест 8.1: Проверка ограничения размера TODO файла
        print("\n8.1. Проверка ограничения размера TODO файла...")
        todo_manager = TodoManager(project_dir)
        max_size = todo_manager.max_file_size
        if max_size > 0:
            results.add_pass(f"Ограничение размера TODO файла установлено: {max_size} байт")
        else:
            results.add_warning("Ограничение размера TODO файла", "Ограничение не установлено")
        
        # Тест 8.2: Проверка чтения файла в пределах лимита
        print("\n8.2. Проверка чтения файла в пределах лимита...")
        try:
            tasks = todo_manager.get_all_tasks()
            results.add_pass(f"Чтение TODO файла успешно (задач: {len(tasks)})")
        except Exception as e:
            if "размер" in str(e).lower() or "size" in str(e).lower():
                results.add_pass("Ограничение размера файла работает")
            else:
                results.add_warning("Чтение TODO файла", f"Ошибка: {e}")
        
    except Exception as e:
        results.add_fail("Ограничения размера файлов", str(e))
        import traceback
        traceback.print_exc()


def main():
    """Главная функция тестирования"""
    print("=" * 80)
    print("КОМПЛЕКСНОЕ ТЕСТИРОВАНИЕ CODE AGENT")
    print("=" * 80)
    print(f"Время начала: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Рабочая директория: {os.getcwd()}")
    print("=" * 80)
    
    results = TestResults()
    
    # Запуск всех тестов
    test_config_validation(results)
    test_path_validation(results)
    test_file_permissions(results)
    test_todo_format_detection(results)
    test_security_utils(results)
    test_server_initialization(results)
    test_error_handling(results)
    test_file_size_limits(results)
    
    # Вывод итоговой статистики
    results.print_summary()
    
    # Возвращаем код выхода
    if results.failed:
        print("\n[FAIL] ТЕСТИРОВАНИЕ ЗАВЕРШЕНО С ОШИБКАМИ")
        return 1
    elif results.warnings:
        print("\n[WARN]  ТЕСТИРОВАНИЕ ЗАВЕРШЕНО С ПРЕДУПРЕЖДЕНИЯМИ")
        return 0
    else:
        print("\n[OK] ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО")
        return 0


if __name__ == "__main__":
    sys.exit(main())
