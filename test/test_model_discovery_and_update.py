"""
Тестирование обнаружения моделей и автоматического обновления конфигурации

Тестирует:
1. Получение списка моделей через OpenRouter API
2. Определение самых быстрых моделей
3. Автоматическое обновление конфигурации
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

from src.llm.model_discovery import ModelDiscovery
from src.llm.config_updater import ConfigUpdater

# Добавляем корень проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


async def test_model_discovery():
    """Тест обнаружения моделей через API"""
    print("=" * 70)
    print("ТЕСТ 1: Обнаружение моделей через OpenRouter API")
    print("=" * 70)
    print()
    
    discovery = ModelDiscovery('config/llm_settings.yaml')
    
    print("Получение списка бесплатных моделей...")
    print()
    
    try:
        # Получаем все модели (включая платные для информации)
        all_models = await discovery.discover_openrouter_models(free_only=False)
        print(f"[INFO] Всего моделей в OpenRouter: {len(all_models)}")
        
        # Получаем только бесплатные
        free_models = await discovery.discover_openrouter_models(free_only=True)
        print(f"[OK] Бесплатных моделей: {len(free_models)}")
        print()
        
        if free_models:
            print("Первые 10 бесплатных моделей:")
            for i, model in enumerate(free_models[:10], 1):
                ctx_len = model.get('context_length', 0)
                print(f"  {i}. {model['id']} (context: {ctx_len})")
        
        return len(free_models) > 0
        
    except Exception as e:
        print(f"[ERROR] Ошибка обнаружения: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_config_update():
    """Тест автоматического обновления конфигурации"""
    print()
    print("=" * 70)
    print("ТЕСТ 2: Автоматическое обновление конфигурации")
    print("=" * 70)
    print()
    
    updater = ConfigUpdater('config/llm_settings.yaml', auto_backup=True)
    
    print("Запуск полного тестирования и обновления конфигурации...")
    print("(Это может занять несколько минут)")
    print()
    
    try:
        result = await updater.run_full_test_and_update(
            test_prompt="Привет, это тестовое сообщение. Ответь кратко.",
            update_config=True
        )
        
        print()
        print("[OK] Тестирование завершено")
        print()
        print("Результаты:")
        print(f"  Всего протестировано: {len(result['test_results'])}")
        print(f"  Работающих моделей: {len(result['working_models'])}")
        print(f"  Найдено быстрых моделей: {len(result['fastest_models'])}")
        print()
        
        if result['fastest_models']:
            print("Топ-3 самых быстрых модели:")
            for i, (model_name, response_time) in enumerate(result['fastest_models'][:3], 1):
                print(f"  {i}. {model_name}: {response_time:.2f}s")
        
        print()
        print("Работающие модели:")
        for model in result['working_models']:
            print(f"  - {model}")
        
        if result['config_updated']:
            print()
            print("[OK] Конфигурация обновлена!")
            print("  Резервная копия сохранена в: config/llm_settings.yaml.backup")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Ошибка обновления: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Главная функция тестирования"""
    print()
    print("=" * 70)
    print("ТЕСТИРОВАНИЕ ОБНАРУЖЕНИЯ И ОБНОВЛЕНИЯ МОДЕЛЕЙ")
    print("=" * 70)
    print(f"Время начала: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    results = {}
    
    # Тест 1: Обнаружение моделей
    try:
        results['discovery'] = await test_model_discovery()
    except Exception as e:
        print(f"[FAIL] Тест discovery прерван: {e}")
        results['discovery'] = False
    
    # Тест 2: Обновление конфигурации
    try:
        results['update'] = await test_config_update()
    except Exception as e:
        print(f"[FAIL] Тест update прерван: {e}")
        results['update'] = False
    
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
