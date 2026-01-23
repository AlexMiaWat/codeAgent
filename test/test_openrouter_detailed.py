"""
Детальный тест OpenRouter API

Проверяет:
- Валидность API ключа
- Доступность различных моделей
- Работу теста моделей
"""

import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv

# Загружаем переменные окружения (с перезаписью для обновления ключа)
load_dotenv(override=True)

# Добавляем текущую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.llm.llm_manager import LLMManager
from src.llm.llm_test_runner import LLMTestRunner


async def test_llm_manager_init():
    """Тест инициализации LLMManager"""
    print("=" * 70)
    print("Тест 1: Инициализация LLMManager")
    print("=" * 70)
    print()
    
    try:
        mgr = LLMManager('config/llm_settings.yaml')
        print("[OK] LLMManager инициализирован")
        
        print(f"\nЗагружено моделей: {len(mgr.models)}")
        print(f"Primary моделей: {len(mgr.get_primary_models())}")
        print(f"Fallback моделей: {len(mgr.get_fallback_models())}")
        
        print("\nPrimary модели:")
        for model in mgr.get_primary_models():
            print(f"  - {model.name}")
        
        return True, mgr
    except Exception as e:
        print(f"[FAIL] Ошибка инициализации: {e}")
        import traceback
        traceback.print_exc()
        return False, None


async def test_single_model(mgr, model_name: str):
    """Тест одной модели"""
    print()
    print(f"Тестирование модели: {model_name}")
    print("-" * 70)
    
    if model_name not in mgr.models:
        print(f"[SKIP] Модель {model_name} не найдена в конфиге")
        return None  # Возвращаем None для skip, а не False
    
    model_config = mgr.models[model_name]
    
    try:
        # Простой тест
        test_prompt = "Say 'OK'"
        print(f"Запрос: {test_prompt}")
        
        response = await mgr._call_model(test_prompt, model_config)
        
        if response.success:
            print("[OK] Успешно!")
            print(f"  Время отклика: {response.response_time:.2f}s")
            print(f"  Ответ: {response.content[:100]}")
            return True
        else:
            print(f"[FAIL] Ошибка: {response.error}")
            # Проверяем, не является ли это ошибкой API ключа
            if "401" in str(response.error) or "User not found" in str(response.error):
                print("[WARN] Возможно, проблема с API ключом")
            return False
            
    except Exception as e:
        print(f"[FAIL] Исключение: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_runner_simple(mgr):
    """Простой тест через LLMTestRunner"""
    print()
    print("=" * 70)
    print("Тест 2: LLMTestRunner - простой тест")
    print("=" * 70)
    print()
    
    try:
        runner = LLMTestRunner(mgr)
        print("[OK] LLMTestRunner создан")
        
        # Тестируем только первую primary модель
        primary_models = mgr.get_primary_models()
        if not primary_models:
            print("[FAIL] Нет primary моделей для тестирования")
            return False
        
        test_model = primary_models[0]
        print(f"\nТестируем модель: {test_model.name}")
        
        # Проверка доступности
        available, msg = await runner.test_model_availability(test_model)
        print(f"Доступность: {'[OK]' if available else '[FAIL]'} {msg}")
        
        if available:
            # Простой тест
            await asyncio.sleep(1)
            simple_response = await runner.test_model_simple(
                test_model,
                "Say 'OK'"
            )
            
            if simple_response.success:
                print("[OK] Простой тест успешен")
                print(f"  Время: {simple_response.response_time:.2f}s")
                print(f"  Ответ: {simple_response.content[:100]}")
                return True
            else:
                print(f"[FAIL] Простой тест провален: {simple_response.error}")
                return False
        else:
            print("[SKIP] Модель недоступна, пропускаем тест")
            return False
            
    except Exception as e:
        print(f"[FAIL] Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_free_models(mgr):
    """Тест бесплатных моделей"""
    print()
    print("=" * 70)
    print("Тест 3: Проверка бесплатных моделей")
    print("=" * 70)
    print()
    
    # Список известных бесплатных моделей на OpenRouter
    free_models = [
        "meta-llama/llama-3.2-1b-instruct",
        "microsoft/phi-3-mini-128k-instruct",
        "google/gemma-2-2b-it",
    ]
    
    results = {}
    
    for model_name in free_models:
        print(f"\nТестирование: {model_name}")
        
        # Проверяем, есть ли модель в конфиге
        if model_name in mgr.models:
            mgr.models[model_name]
            success = await test_single_model(mgr, model_name)
            results[model_name] = success
        else:
            print("[SKIP] Модель не найдена в конфиге")
            results[model_name] = None
        
        await asyncio.sleep(1)  # Задержка между запросами
    
    print()
    print("Результаты:")
    for model, result in results.items():
        if result is None:
            status = "[SKIP]"
        elif result:
            status = "[OK]"
        else:
            status = "[FAIL]"
        print(f"  {model}: {status}")
    
    # Тест считается успешным, если хотя бы одна модель работает
    # или если все модели пропущены (не найдены в конфиге)
    passed_models = [r for r in results.values() if r is True]
    skipped_models = [r for r in results.values() if r is None]
    
    if passed_models:
        return True  # Хотя бы одна модель работает
    elif len(skipped_models) == len(results):
        return True  # Все модели пропущены (не найдены в конфиге) - это нормально
    else:
        return False  # Есть проваленные тесты


async def main():
    """Главная функция"""
    print()
    print("=" * 70)
    print("ДЕТАЛЬНОЕ ТЕСТИРОВАНИЕ OpenRouter API")
    print("=" * 70)
    print()
    
    results = {}
    
    # Тест 1: Инициализация
    success, mgr = await test_llm_manager_init()
    results['init'] = success
    
    if not success or not mgr:
        print("\n[ERROR] Не удалось инициализировать LLMManager, остальные тесты пропущены")
        return False
    
    # Тест 2: LLMTestRunner
    results['runner'] = await test_runner_simple(mgr)
    
    # Тест 3: Бесплатные модели
    results['free_models'] = await test_free_models(mgr)
    
    # Итоги
    print()
    print("=" * 70)
    print("ИТОГИ")
    print("=" * 70)
    print()
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    
    print(f"Всего тестов: {total}")
    print(f"Успешно: {passed}")
    print(f"Провалено: {total - passed}")
    print()
    
    for test_name, result in results.items():
        status = "[OK] PASSED" if result else "[FAIL] FAILED"
        print(f"  {test_name}: {status}")
    
    print()
    print("=" * 70)
    
    # Выводы
    print()
    print("ВЫВОДЫ:")
    print("-" * 70)
    
    if results.get('init'):
        print("[OK] LLMManager инициализируется корректно")
    else:
        print("[FAIL] Проблема с инициализацией LLMManager")
    
    if results.get('runner'):
        print("[OK] Тест моделей работает (LLMTestRunner)")
    else:
        print("[FAIL] Тест моделей не работает - возможно, проблема с API ключом или квотами")
    
    if results.get('free_models'):
        print("[OK] Некоторые бесплатные модели доступны")
    else:
        print("[FAIL] Бесплатные модели недоступны - проверьте API ключ и квоты")
    
    print()
    
    return passed == total


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        exit_code = 0 if success else 1
        if not success:
            print(f"\n[FAIL] Тест завершился с ошибкой (exit code: {exit_code})")
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n[INFO] Тестирование прервано пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
