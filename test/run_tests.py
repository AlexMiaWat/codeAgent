#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Единая точка входа для всех тестов Code Agent

Использование:
    python test/run_tests.py                    # Все тесты
    python test/run_tests.py --openrouter       # Только OpenRouter тесты
    python test/run_tests.py --api              # Только HTTP API тесты
    python test/run_tests.py --cursor           # Только Cursor тесты
    python test/run_tests.py --llm               # Только LLM тесты
    python test/run_tests.py --openrouter --llm # Несколько категорий
    python test/run_tests.py --list             # Список всех тестов
"""

import sys
import os
import subprocess
import time
import argparse
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any
from datetime import datetime

# Устанавливаем UTF-8 кодировку для вывода
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

project_root = Path(__file__).parent.parent


# Цвета для вывода (если поддерживается)
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    
    @staticmethod
    def disable():
        Colors.HEADER = ''
        Colors.OKBLUE = ''
        Colors.OKCYAN = ''
        Colors.OKGREEN = ''
        Colors.WARNING = ''
        Colors.FAIL = ''
        Colors.ENDC = ''
        Colors.BOLD = ''
        Colors.UNDERLINE = ''


# Отключаем цвета если вывод не в терминал
if not sys.stdout.isatty():
    Colors.disable()


# Категории тестов
TEST_CATEGORIES = {
    'openrouter': {
        'name': 'OpenRouter API',
        'description': 'Тестирование OpenRouter API, LLMManager, генерация инструкций',
        'tests': [
            ('test_openrouter_api.py', 'Базовый тест OpenRouter API', 60),
            ('test_openrouter_detailed.py', 'Детальное тестирование LLMManager', 120),
            ('test_llm_real.py', 'Реальное тестирование LLM (генерация, fallback, параллельный режим)', 300),
            ('test_model_discovery_and_update.py', 'Обнаружение и обновление моделей', 600),
            ('test_crewai_scenario.py', 'CrewAI сценарий с параллельными моделями', 300),
        ]
    },
    'api': {
        'name': 'HTTP API Server',
        'description': 'Тестирование HTTP API сервера и endpoints',
        'tests': [
            ('test_server_api_only.py', 'Тестирование API endpoints (сервер должен быть запущен)', 60),
            ('test_real_server_integration.py', 'Интеграционное тестирование сервера (автозапуск сервера)', 120),
        ]
    },
    'cursor': {
        'name': 'Cursor Integration',
        'description': 'Тестирование интеграции с Cursor IDE',
        'tests': [
            ('test_simple_cursor_task.py', 'Простая задача через Cursor', 300),
            ('test_real_cursor_cli.py', 'Реальное выполнение через Cursor CLI', 600),
            ('test_cursor_integration_only.py', 'Интеграция с Cursor (только файловый интерфейс)', 300),
            ('test_hybrid_interface.py', 'Гибридный интерфейс (CLI + файловый)', 300),
        ]
    },
    'llm': {
        'name': 'LLM Core',
        'description': 'Тестирование базовой функциональности LLM',
        'tests': [
            ('test_llm_real.py', 'Реальное тестирование LLMManager', 300),
            ('test_model_discovery_and_update.py', 'Обнаружение и обновление моделей', 600),
        ]
    },
    'validation': {
        'name': 'Validation',
        'description': 'Тестирование валидации конфигурации и безопасности',
        'tests': [
            ('test_comprehensive_validation.py', 'Комплексная валидация конфигурации', 120),
        ]
    },
    'checkpoint': {
        'name': 'Checkpoint',
        'description': 'Тестирование системы checkpoint',
        'tests': [
            ('test_checkpoint_integration.py', 'Интеграционное тестирование checkpoint', 60),
            ('test_checkpoint_recovery.py', 'Восстановление после сбоя', 60),
        ]
    },
    'full': {
        'name': 'Full Cycle',
        'description': 'Полный цикл работы агента',
        'tests': [
            ('test_full_cycle.py', 'Полный цикл выполнения задачи', 300),
            ('test_full_cycle_with_server.py', 'Полный цикл с сервером', 600),
        ]
    },
}


class TestRunner:
    """Класс для запуска тестов"""
    
    def __init__(self, verbose: bool = True, show_output: bool = True):
        self.verbose = verbose
        self.show_output = show_output
        self.results: List[Tuple[str, str, bool, str, float]] = []  # (category, test, success, message, duration)
    
    def print_header(self, text: str, char: str = "="):
        """Печать заголовка"""
        width = 80
        print()
        print(char * width)
        print(f"{Colors.BOLD}{text}{Colors.ENDC}")
        print(char * width)
    
    def print_section(self, text: str):
        """Печать секции"""
        print()
        print(f"{Colors.OKCYAN}{'─' * 80}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.OKCYAN}{text}{Colors.ENDC}")
        print(f"{Colors.OKCYAN}{'─' * 80}{Colors.ENDC}")
    
    def print_success(self, text: str):
        """Печать успешного сообщения"""
        print(f"{Colors.OKGREEN}[OK]{Colors.ENDC} {text}")
    
    def print_fail(self, text: str):
        """Печать сообщения об ошибке"""
        print(f"{Colors.FAIL}[FAIL]{Colors.ENDC} {text}")
    
    def print_warning(self, text: str):
        """Печать предупреждения"""
        print(f"{Colors.WARNING}[WARN]{Colors.ENDC} {text}")
    
    def print_info(self, text: str):
        """Печать информации"""
        print(f"{Colors.OKBLUE}[INFO]{Colors.ENDC} {text}")
    
    def run_test(self, test_file: str, description: str, timeout: int, category: str, extra_args: Optional[List[str]] = None) -> Tuple[bool, str, float]:
        """Запуск одного теста"""
        test_path = project_root / "test" / test_file
        
        if not test_path.exists():
            return False, f"Файл не найден: {test_path}", 0.0
        
        self.print_section(f"Тест: {description}")
        self.print_info(f"Файл: {test_file}")
        self.print_info(f"Таймаут: {timeout}s")
        
        start_time = time.time()
        
        try:
            # Формируем команду запуска
            cmd = [sys.executable, str(test_path)]
            if extra_args:
                cmd.extend(extra_args)
            
            # Для test_real_server_integration.py не передаем --no-start, чтобы сервер запускался автоматически
            # если он не запущен
            if test_file == "test_real_server_integration.py" and "--no-start" not in (extra_args or []):
                # Не передаем --no-start, сервер запустится автоматически если нужно
                pass
            
            # Запускаем тест
            result = subprocess.run(
                cmd,
                cwd=str(project_root),
                capture_output=not self.show_output,
                text=True,
                timeout=timeout,
                encoding='utf-8',
                errors='replace'
            )
            
            duration = time.time() - start_time
            
            # Выводим результат
            if self.show_output and result.stdout:
                print(result.stdout)
            if result.stderr:
                if self.show_output:
                    print(f"{Colors.WARNING}STDERR:{Colors.ENDC}")
                    print(result.stderr)
                else:
                    # В режиме без вывода показываем только ошибки
                    if "ERROR" in result.stderr or "FAIL" in result.stderr or "Traceback" in result.stderr:
                        print(f"{Colors.FAIL}Ошибки:{Colors.ENDC}")
                        print(result.stderr[:500])  # Первые 500 символов
            
            success = result.returncode == 0
            
            if success:
                self.print_success(f"Тест пройден за {duration:.2f}s")
                message = "OK"
            else:
                self.print_fail(f"Тест провален (код: {result.returncode}) за {duration:.2f}s")
                message = f"Exit code: {result.returncode}"
            
            return success, message, duration
            
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            self.print_fail(f"Таймаут ({timeout}s)")
            return False, f"Timeout ({timeout}s)", duration
        except Exception as e:
            duration = time.time() - start_time
            self.print_fail(f"Ошибка: {str(e)}")
            return False, f"Ошибка: {str(e)}", duration
    
    def check_server_required(self, category: str) -> bool:
        """Проверка, требуется ли сервер для категории"""
        return category == 'api'
    
    def check_server_availability(self) -> bool:
        """Проверка доступности сервера"""
        try:
            import requests
            response = requests.get("http://127.0.0.1:3456/health", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def run_category(self, category: str) -> Dict[str, any]:
        """Запуск всех тестов категории"""
        if category not in TEST_CATEGORIES:
            self.print_fail(f"Неизвестная категория: {category}")
            return {'success': False, 'tests': 0, 'passed': 0, 'failed': 0}
        
        cat_info = TEST_CATEGORIES[category]
        self.print_header(f"КАТЕГОРИЯ: {cat_info['name']}")
        self.print_info(f"Описание: {cat_info['description']}")
        self.print_info(f"Тестов в категории: {len(cat_info['tests'])}")
        
        # Проверка сервера для API тестов
        # test_real_server_integration.py может запустить сервер автоматически, поэтому не пропускаем
        has_auto_start = any('test_real_server_integration' in test_file for test_file, _, _ in cat_info['tests'])
        
        if self.check_server_required(category) and not has_auto_start:
            if not self.check_server_availability():
                self.print_warning("Сервер не запущен!")
                self.print_info("Для тестов API требуется запущенный сервер")
                self.print_info("Запустите в отдельной консоли: python main.py")
                self.print_info("Или используйте: python test/check_server.py")
                self.print_warning("Пропускаем тесты API...")
                # Добавляем пропущенные тесты в результаты для отчетности
                for test_file, description, timeout in cat_info['tests']:
                    self.results.append((category, test_file, False, "Сервер не запущен", 0.0))
                return {'success': False, 'tests': len(cat_info['tests']), 'passed': 0, 'failed': len(cat_info['tests']), 'skipped': True}
        elif self.check_server_required(category) and has_auto_start:
            # Для test_real_server_integration.py сообщаем, что сервер будет запущен автоматически если нужно
            if not self.check_server_availability():
                self.print_info("Сервер не запущен, будет запущен автоматически тестом")
        
        passed = 0
        failed = 0
        
        for test_file, description, timeout in cat_info['tests']:
            # Для test_real_server_integration.py не передаем --no-start, чтобы сервер запускался автоматически
            extra_args = None
            if test_file == "test_real_server_integration.py":
                # Не передаем --no-start, сервер запустится автоматически если не запущен
                # start_server_flag по умолчанию True в main() функции теста
                extra_args = []
            
            success, message, duration = self.run_test(test_file, description, timeout, category, extra_args)
            self.results.append((category, test_file, success, message, duration))
            
            if success:
                passed += 1
            else:
                failed += 1
        
        return {
            'success': failed == 0,
            'tests': len(cat_info['tests']),
            'passed': passed,
            'failed': failed
        }
    
    def print_summary(self):
        """Печать итогового отчета"""
        self.print_header("ИТОГОВЫЙ ОТЧЕТ", "=")
        
        # Группируем по категориям
        categories = {}
        for category, test_file, success, message, duration in self.results:
            if category not in categories:
                categories[category] = {'passed': 0, 'failed': 0, 'total': 0, 'duration': 0.0}
            categories[category]['total'] += 1
            categories[category]['duration'] += duration
            if success:
                categories[category]['passed'] += 1
            else:
                categories[category]['failed'] += 1
        
        # Статистика по категориям
        print()
        print(f"{Colors.BOLD}По категориям:{Colors.ENDC}")
        print()
        for category, stats in categories.items():
            cat_name = TEST_CATEGORIES[category]['name']
            total = stats['total']
            passed = stats['passed']
            failed = stats['failed']
            duration = stats['duration']
            
            status_color = Colors.OKGREEN if failed == 0 else Colors.FAIL
            print(f"  {cat_name}:")
            print(f"    {status_color}Пройдено: {passed}/{total}{Colors.ENDC}")
            if failed > 0:
                print(f"    {Colors.FAIL}Провалено: {failed}{Colors.ENDC}")
            print(f"    Время: {duration:.2f}s")
        
        # Общая статистика
        total_tests = len(self.results)
        total_passed = sum(1 for _, _, success, _, _ in self.results if success)
        total_failed = total_tests - total_passed
        total_duration = sum(duration for _, _, _, _, duration in self.results)
        
        print()
        print(f"{Colors.BOLD}Общая статистика:{Colors.ENDC}")
        print(f"  Всего тестов: {total_tests}")
        print(f"  {Colors.OKGREEN}Пройдено: {total_passed}{Colors.ENDC}")
        if total_failed > 0:
            print(f"  {Colors.FAIL}Провалено: {total_failed}{Colors.ENDC}")
        print(f"  Общее время: {total_duration:.2f}s")
        
        # Детальный список проваленных тестов
        failed_tests = [(cat, test, msg) for cat, test, success, msg, _ in self.results if not success]
        if failed_tests:
            print()
            print(f"{Colors.FAIL}{Colors.BOLD}Проваленные тесты:{Colors.ENDC}")
            for category, test_file, message in failed_tests:
                cat_name = TEST_CATEGORIES[category]['name']
                print(f"  {Colors.FAIL}✗{Colors.ENDC} [{cat_name}] {test_file}: {message}")
        
        # Проверка пропущенных тестов (например, из-за отсутствия сервера)
        skipped_categories = [cat for cat, stats in categories.items() if stats.get('skipped', False)]
        if skipped_categories:
            print()
            print(f"{Colors.WARNING}{Colors.BOLD}Пропущенные категории (требуется сервер):{Colors.ENDC}")
            for category in skipped_categories:
                cat_name = TEST_CATEGORIES[category]['name']
                print(f"  {Colors.WARNING}⚠{Colors.ENDC} {cat_name}")
                print(f"     Запустите сервер: python main.py")
        
        # Финальный статус
        print()
        if total_failed == 0:
            self.print_success("ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
            return 0
        else:
            self.print_fail(f"НЕКОТОРЫЕ ТЕСТЫ ПРОВАЛЕНЫ ({total_failed}/{total_tests})")
            return 1


def list_tests():
    """Вывод списка всех доступных тестов"""
    print()
    print(f"{Colors.BOLD}{'=' * 80}{Colors.ENDC}")
    print(f"{Colors.BOLD}ДОСТУПНЫЕ КАТЕГОРИИ ТЕСТОВ{Colors.ENDC}")
    print(f"{Colors.BOLD}{'=' * 80}{Colors.ENDC}")
    print()
    
    for category, info in TEST_CATEGORIES.items():
        print(f"{Colors.OKCYAN}{Colors.BOLD}{category.upper()}{Colors.ENDC}: {info['name']}")
        print(f"  {info['description']}")
        print(f"  Тестов: {len(info['tests'])}")
        print()
        for test_file, description, timeout in info['tests']:
            print(f"    • {test_file}")
            print(f"      {description} (timeout: {timeout}s)")
        print()


def main():
    """Главная функция"""
    parser = argparse.ArgumentParser(
        description='Единая точка входа для всех тестов Code Agent',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python test/run_tests.py                    # Все тесты
  python test/run_tests.py --openrouter       # Только OpenRouter тесты
  python test/run_tests.py --api              # Только HTTP API тесты
  python test/run_tests.py --cursor           # Только Cursor тесты
  python test/run_tests.py --llm --openrouter  # Несколько категорий
  python test/run_tests.py --list             # Список всех тестов
        """
    )
    
    # Добавляем флаги для каждой категории
    for category in TEST_CATEGORIES.keys():
        parser.add_argument(
            f'--{category}',
            action='store_true',
            help=f"Запустить тесты категории '{TEST_CATEGORIES[category]['name']}'"
        )
    
    parser.add_argument(
        '--list',
        action='store_true',
        help='Показать список всех доступных тестов'
    )
    
    parser.add_argument(
        '--no-output',
        action='store_true',
        help='Не показывать вывод тестов (только результаты)'
    )
    
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Минимальный вывод (только итоги)'
    )
    
    args = parser.parse_args()
    
    # Список тестов
    if args.list:
        list_tests()
        return 0
    
    # Определяем какие категории запускать
    selected_categories = []
    for category in TEST_CATEGORIES.keys():
        if getattr(args, category, False):
            selected_categories.append(category)
    
    # Если ничего не выбрано, запускаем все
    if not selected_categories:
        selected_categories = list(TEST_CATEGORIES.keys())
    
    # Запускаем тесты
    runner = TestRunner(verbose=not args.quiet, show_output=not args.no_output)
    
    runner.print_header("ТЕСТИРОВАНИЕ CODE AGENT", "=")
    runner.print_info(f"Время начала: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    runner.print_info(f"Выбранные категории: {', '.join([TEST_CATEGORIES[c]['name'] for c in selected_categories])}")
    runner.print_info(f"Всего категорий: {len(selected_categories)}")
    
    # Запускаем каждую категорию
    for category in selected_categories:
        runner.run_category(category)
        time.sleep(1)  # Небольшая пауза между категориями
    
    # Итоговый отчет
    exit_code = runner.print_summary()
    
    runner.print_info(f"Время завершения: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return exit_code


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}[INFO] Тестирование прервано пользователем{Colors.ENDC}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.FAIL}[ERROR] Критическая ошибка: {e}{Colors.ENDC}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
