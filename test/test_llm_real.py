"""
Тестирование LLMManager с реальными API запросами

Проверяет:
- Базовую генерацию ответов
- Fallback механизм
- Параллельный режим (best_of_two)
- Работу разных моделей
- Время отклика
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

from src.llm.llm_manager import LLMManager
from src.llm.llm_test_runner import LLMTestRunner

# Добавляем корень проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


async def test_basic_generation():
    """Тест базовой генерации ответа"""
    print("=" * 70)
    print("ТЕСТ 1: Базовая генерация ответа")
    print("=" * 70)
    print()
    
    mgr = LLMManager('config/llm_settings.yaml')
    test_prompt = "Привет, это тестовое сообщение. Ответь кратко одной фразой."
    
    print(f"Запрос: {test_prompt}")
    print()
    
    try:
        response = await mgr.generate_response(
            prompt=test_prompt,
            use_fastest=True,
            use_parallel=False
        )
        
        if response.success:
            print("[OK] Успешно!")
            print(f"  Модель: {response.model_name}")
            print(f"  Время отклика: {response.response_time:.2f}s")
            print(f"  Длина ответа: {len(response.content)} символов")
            print(f"  Ответ: {response.content[:200]}")
            return True
        else:
            print("[FAIL] Ошибка генерации:")
            print(f"  Модель: {response.model_name}")
            print(f"  Ошибка: {response.error}")
            return False
            
    except Exception as e:
        print(f"[ERROR] Исключение при генерации: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_fallback_mechanism():
    """Тест fallback механизма"""
    print()
    print("=" * 70)
    print("ТЕСТ 2: Fallback механизм")
    print("=" * 70)
    print()
    
    mgr = LLMManager('config/llm_settings.yaml')
    test_prompt = "Ответь на русском: что такое Python?"
    
    print(f"Запрос: {test_prompt}")
    print()
    print("Primary модели:")
    for model in mgr.get_primary_models():
        print(f"  - {model.name}")
    print()
    print("Fallback модели:")
    for model in mgr.get_fallback_models():
        print(f"  - {model.name}")
    print()
    
    try:
        response = await mgr.generate_response(
            prompt=test_prompt,
            use_fastest=True,
            use_parallel=False
        )
        
        if response.success:
            print("[OK] Успешно!")
            print(f"  Модель: {response.model_name}")
            print(f"  Время отклика: {response.response_time:.2f}s")
            print(f"  Ответ: {response.content[:300]}")
            return True
        else:
            print("[FAIL] Ошибка генерации:")
            print(f"  Модель: {response.model_name}")
            print(f"  Ошибка: {response.error}")
            return False
            
    except Exception as e:
        print(f"[ERROR] Исключение при генерации: {e}")
        return False


async def test_parallel_mode():
    """Тест параллельного режима (best_of_two)"""
    print()
    print("=" * 70)
    print("ТЕСТ 3: Параллельный режим (best_of_two)")
    print("=" * 70)
    print()
    
    mgr = LLMManager('config/llm_settings.yaml')
    test_prompt = "Объясни кратко: что такое async/await в Python?"
    
    print(f"Запрос: {test_prompt}")
    print()
    print("Запускается параллельное выполнение двух моделей...")
    print()
    
    try:
        response = await mgr.generate_response(
            prompt=test_prompt,
            use_fastest=True,
            use_parallel=True
        )
        
        if response.success:
            print("[OK] Успешно!")
            print(f"  Выбранная модель: {response.model_name}")
            print(f"  Время отклика: {response.response_time:.2f}s")
            if hasattr(response, 'score') and response.score:
                print(f"  Оценка ответа: {response.score:.2f}")
            print(f"  Ответ: {response.content[:300]}")
            return True
        else:
            print("[FAIL] Ошибка генерации:")
            print(f"  Модель: {response.model_name}")
            print(f"  Ошибка: {response.error}")
            return False
            
    except Exception as e:
        print(f"[ERROR] Исключение при генерации: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_model_speed():
    """Тест скорости работы разных моделей"""
    print()
    print("=" * 70)
    print("ТЕСТ 4: Скорость работы моделей")
    print("=" * 70)
    print()
    
    mgr = LLMManager('config/llm_settings.yaml')
    test_prompt = "Скажи 'OK'"
    
    # Тестируем первые 3 primary модели
    primary_models = mgr.get_primary_models()[:3]
    
    print(f"Тестируем {len(primary_models)} моделей...")
    print(f"Запрос: {test_prompt}")
    print()
    
    results = []
    for model_config in primary_models:
        try:
            start_time = datetime.now()
            response = await mgr._call_model(test_prompt, model_config)
            end_time = datetime.now()
            
            if response.success:
                duration = (end_time - start_time).total_seconds()
                results.append({
                    'model': model_config.name,
                    'success': True,
                    'time': duration,
                    'response_length': len(response.content)
                })
                print(f"  {model_config.name}: {duration:.2f}s [OK]")
            else:
                results.append({
                    'model': model_config.name,
                    'success': False,
                    'error': response.error
                })
                print(f"  {model_config.name}: [FAILED] {response.error}")
        except Exception as e:
            results.append({
                'model': model_config.name,
                'success': False,
                'error': str(e)
            })
            print(f"  {model_config.name}: [ERROR] {e}")
        
        # Небольшая задержка между запросами
        await asyncio.sleep(1)
    
    print()
    if results:
        successful = [r for r in results if r.get('success')]
        if successful:
            fastest = min(successful, key=lambda x: x['time'])
            print(f"Самая быстрая модель: {fastest['model']} ({fastest['time']:.2f}s)")
        else:
            print("Ни одна модель не сработала успешно")
    
    return len([r for r in results if r.get('success')]) > 0


async def test_runner_full():
    """Тест полного функционала LLMTestRunner"""
    print()
    print("=" * 70)
    print("ТЕСТ 5: Полное тестирование через LLMTestRunner")
    print("=" * 70)
    print()
    
    mgr = LLMManager('config/llm_settings.yaml')
    runner = LLMTestRunner(mgr)
    
    print("Запуск тестирования всех моделей...")
    print("(Это может занять некоторое время)")
    print()
    
    try:
        # Тестируем только primary модели для быстроты
        primary_models = mgr.get_primary_models()[:2]  # Только первые 2
        
        print(f"Тестируем {len(primary_models)} primary моделей:")
        for model in primary_models:
            print(f"  - {model.name}")
        print()
        
        # Тестируем каждую модель
        for model_config in primary_models:
            print(f"Тестирование {model_config.name}...")
            available, msg = await runner.test_model_availability(model_config)
            status = "[OK]" if available else "[FAIL]"
            print(f"  {status} {msg}")
            
            if available:
                await asyncio.sleep(1)
                simple_response = await runner.test_model_simple(model_config)
                if simple_response.success:
                    print(f"  [OK] Простой тест: {simple_response.response_time:.2f}s, "
                          f"{len(simple_response.content)} символов")
                else:
                    print(f"  [FAIL] Простой тест: {simple_response.error}")
            
            await asyncio.sleep(1)
        
        print()
        print("[OK] Тестирование завершено")
        return True
        
    except Exception as e:
        print(f"[FAIL] Ошибка тестирования: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Главная функция тестирования"""
    print()
    print("=" * 70)
    print("ТЕСТИРОВАНИЕ LLMManager С РЕАЛЬНЫМИ API ЗАПРОСАМИ")
    print("=" * 70)
    print(f"Время начала: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    results = {}
    
    # Тест 1: Базовая генерация
    try:
        results['basic'] = await test_basic_generation()
    except Exception as e:
        print(f"[FAIL] Тест 1 прерван: {e}")
        results['basic'] = False
    
    # Тест 2: Fallback
    try:
        results['fallback'] = await test_fallback_mechanism()
    except Exception as e:
        print(f"[FAIL] Тест 2 прерван: {e}")
        results['fallback'] = False
    
    # Тест 3: Параллельный режим
    try:
        results['parallel'] = await test_parallel_mode()
    except Exception as e:
        print(f"[FAIL] Тест 3 прерван: {e}")
        results['parallel'] = False
    
    # Тест 4: Скорость моделей
    try:
        results['speed'] = await test_model_speed()
    except Exception as e:
        print(f"[FAIL] Тест 4 прерван: {e}")
        results['speed'] = False
    
    # Тест 5: Полное тестирование
    try:
        results['full'] = await test_runner_full()
    except Exception as e:
        print(f"[FAIL] Тест 5 прерван: {e}")
        results['full'] = False
    
    # Итоги
    print()
    print("=" * 70)
    print("ИТОГИ ТЕСТИРОВАНИЯ")
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
    print(f"Время завершения: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)


if __name__ == "__main__":
    try:
        # Добавляем timeout для предотвращения зависаний
        asyncio.run(asyncio.wait_for(main(), timeout=600))  # 10 минут таймаут
    except asyncio.TimeoutError:
        print("\n[ERROR] Тестирование превысило таймаут (10 минут)")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n[INFO] Тестирование прервано пользователем")
    except Exception as e:
        print(f"\n[ERROR] Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
