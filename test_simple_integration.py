#!/usr/bin/env python3
"""
Простой интеграционный тест
"""

import asyncio
import sys
import os
sys.path.insert(0, 'src')

async def test_integration():
    try:
        from llm.manager import LLMManager

        print("Создание LLMManager...")
        manager = LLMManager()

        print("✓ LLMManager создан успешно")

        # Проверяем наличие компонентов
        assert hasattr(manager, 'intelligent_router'), "Нет intelligent_router"
        assert hasattr(manager, 'adaptive_strategy_manager'), "Нет adaptive_strategy_manager"
        assert hasattr(manager, 'intelligent_evaluator'), "Нет intelligent_evaluator"
        assert hasattr(manager, 'error_learning_system'), "Нет error_learning_system"

        print("✓ Все компоненты присутствуют")

        # Проверяем методы
        assert hasattr(manager, 'analyze_request'), "Нет метода analyze_request"
        assert hasattr(manager, 'generate_adaptive'), "Нет метода generate_adaptive"
        assert hasattr(manager, 'evaluate_response_intelligent'), "Нет метода evaluate_response_intelligent"
        assert hasattr(manager, 'get_error_learning_stats'), "Нет метода get_error_learning_stats"

        print("✓ Все методы присутствуют")

        # Проверяем статистику
        stats = manager.get_stats()
        assert 'intelligent_router' in stats, "Нет статистики intelligent_router"
        assert 'adaptive_strategy' in stats, "Нет статистики adaptive_strategy"
        assert 'intelligent_evaluator' in stats, "Нет статистики intelligent_evaluator"
        assert 'error_learning' in stats, "Нет статистики error_learning"

        print("✓ Статистика собирается корректно")

        print("\n🎉 Интеграционный тест пройден успешно!")
        return True

    except Exception as e:
        print(f"✗ Ошибка интеграции: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_integration())
    sys.exit(0 if result else 1)