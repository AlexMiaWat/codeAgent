"""
Тестирование CrewAI сценария с проверкой параллельности и дублирования моделей

Имитирует активность по проекту с использованием LLMManager
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Добавляем корень проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.llm.llm_manager import LLMManager
from src.llm.crewai_llm_wrapper import create_llm_for_crewai


async def test_parallel_models():
    """Тест параллельного выполнения двух моделей"""
    print("=" * 70)
    print("ТЕСТ: Параллельное выполнение моделей (best_of_two)")
    print("=" * 70)
    print()
    
    mgr = LLMManager('config/llm_settings.yaml')
    
    # Запрос, который должен быть выполнен параллельно
    prompt = "Напиши краткий план для реализации todo-задачи: 'Создать API endpoint для пользователей'"
    
    print(f"Запрос: {prompt}")
    print()
    print("Запускается параллельное выполнение...")
    
    try:
        response = await mgr.generate_response(
            prompt=prompt,
            use_fastest=True,
            use_parallel=True  # Параллельный режим
        )
        
        if response.success:
            print("[OK] Успешно!")
            print(f"  Выбранная модель: {response.model_name}")
            print(f"  Время отклика: {response.response_time:.2f}s")
            if hasattr(response, 'score') and response.score:
                print(f"  Оценка ответа: {response.score:.2f}")
            print("  Ответ (первые 300 символов):")
            print(f"  {response.content[:300]}")
            return True
        else:
            print(f"[FAIL] Ошибка: {response.error}")
            return False
            
    except Exception as e:
        print(f"[ERROR] Исключение: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_duplicate_models():
    """Тест работы дублирующих моделей"""
    print()
    print("=" * 70)
    print("ТЕСТ: Работа дублирующих моделей")
    print("=" * 70)
    print()
    
    mgr = LLMManager('config/llm_settings.yaml')
    
    # Тестируем каждую duplicate модель отдельно
    duplicate_models = mgr.get_fallback_models()[:2]  # Берем первые 2
    
    print(f"Тестируем {len(duplicate_models)} duplicate моделей:")
    for model in duplicate_models:
        print(f"  - {model.name}")
    print()
    
    prompt = "Проанализируй задачу: 'Добавить валидацию входных данных' и предложи шаги выполнения"
    
    results = []
    for model_config in duplicate_models:
        try:
            print(f"Тестирование {model_config.name}...")
            response = await mgr._call_model(prompt, model_config)
            
            if response.success:
                results.append({
                    'model': model_config.name,
                    'success': True,
                    'time': response.response_time,
                    'content_length': len(response.content)
                })
                print(f"  [OK] {response.response_time:.2f}s, {len(response.content)} символов")
            else:
                results.append({
                    'model': model_config.name,
                    'success': False,
                    'error': response.error
                })
                print(f"  [FAIL] {response.error}")
        except Exception as e:
            print(f"  [ERROR] {e}")
        
        await asyncio.sleep(1)
    
    successful = [r for r in results if r.get('success')]
    print()
    print(f"Успешно протестировано: {len(successful)}/{len(duplicate_models)}")
    
    return len(successful) > 0


async def test_crewai_agent_simulation():
    """Тест имитации работы CrewAI агента с проектом"""
    print()
    print("=" * 70)
    print("ТЕСТ: Имитация CrewAI агента с проектом")
    print("=" * 70)
    print()
    
    try:
        # Создаем LLM wrapper
        custom_llm = create_llm_for_crewai(
            config_path="config/llm_settings.yaml",
            use_fastest=True,
            use_parallel=False  # Начинаем с обычного режима
        )
        
        print("[OK] LLM wrapper создан")
        print(f"  Моделей доступно: {len(custom_llm.llm_manager.models)}")
        print()
        
        # Имитация запроса к агенту
        print("Имитация запроса к агенту...")
        print("Запрос: 'Создай план выполнения todo-задачи: Разработать REST API'")
        print()
        
        # Используем async метод напрямую через текущий event loop
        response = await custom_llm.acall(
            "Создай краткий план выполнения todo-задачи: Разработать REST API для управления пользователями. "
            "План должен включать основные этапы разработки."
        )
        
        print("[OK] Ответ получен")
        print(f"  Длина ответа: {len(response)} символов")
        print("  Ответ (первые 400 символов):")
        print(f"  {response[:400]}")
        print()
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_fallback_chain():
    """Тест цепочки fallback при ошибках"""
    print()
    print("=" * 70)
    print("ТЕСТ: Цепочка fallback при ошибках")
    print("=" * 70)
    print()
    
    mgr = LLMManager('config/llm_settings.yaml')
    
    prompt = "Объясни кратко что такое REST API"
    
    print(f"Запрос: {prompt}")
    print()
    print("Тестируем fallback цепочку (Primary → Duplicate → Reserve → Fallback)...")
    print()
    
    try:
        # Используем метод с автоматическим fallback
        response = await mgr.generate_response(
            prompt=prompt,
            use_fastest=True,
            use_parallel=False
        )
        
        if response.success:
            print("[OK] Успешно!")
            print(f"  Финальная модель: {response.model_name}")
            print(f"  Время отклика: {response.response_time:.2f}s")
            print(f"  Ответ: {response.content[:300]}")
            
            # Проверяем статистику ошибок (если была)
            primary_models = mgr.get_primary_models()
            for model in primary_models:
                if model.error_count > 0:
                    print(f"  [INFO] Модель {model.name} имела {model.error_count} ошибок")
            
            return True
        else:
            print(f"[FAIL] Все модели провалились: {response.error}")
            return False
            
    except Exception as e:
        print(f"[ERROR] Исключение: {e}")
        return False


async def main():
    """Главная функция тестирования"""
    print()
    print("=" * 70)
    print("ТЕСТИРОВАНИЕ CREWAI СЦЕНАРИЯ С LLMMANAGER")
    print("=" * 70)
    print(f"Время начала: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    results = {}
    
    # Тест 1: Параллельное выполнение
    try:
        results['parallel'] = await test_parallel_models()
    except Exception as e:
        print(f"[FAIL] Тест parallel прерван: {e}")
        results['parallel'] = False
    
    # Тест 2: Дублирующие модели
    try:
        results['duplicate'] = await test_duplicate_models()
    except Exception as e:
        print(f"[FAIL] Тест duplicate прерван: {e}")
        results['duplicate'] = False
    
    # Тест 3: Имитация CrewAI агента
    try:
        results['crewai'] = await test_crewai_agent_simulation()
    except Exception as e:
        print(f"[FAIL] Тест crewai прерван: {e}")
        results['crewai'] = False
    
    # Тест 4: Fallback цепочка
    try:
        results['fallback'] = await test_fallback_chain()
    except Exception as e:
        print(f"[FAIL] Тест fallback прерван: {e}")
        results['fallback'] = False
    
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
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[INFO] Тестирование прервано пользователем")
    except Exception as e:
        print(f"\n[ERROR] Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
