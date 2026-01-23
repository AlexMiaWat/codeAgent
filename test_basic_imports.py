#!/usr/bin/env python3
"""
Простой тест импортов
"""

import sys
sys.path.insert(0, 'src')

try:
    from llm.manager import LLMManager
    print("✓ Импорт LLMManager прошел успешно")

    from llm.intelligent_router import IntelligentRouter
    print("✓ Импорт IntelligentRouter прошел успешно")

    from llm.adaptive_strategy import AdaptiveStrategyManager
    print("✓ Импорт AdaptiveStrategyManager прошел успешно")

    from llm.intelligent_evaluator import IntelligentEvaluator
    print("✓ Импорт IntelligentEvaluator прошел успешно")

    from llm.error_learning_system import ErrorLearningSystem
    print("✓ Импорт ErrorLearningSystem прошел успешно")

    print("\n🎉 Все импорты прошли успешно!")

except ImportError as e:
    print(f"✗ Ошибка импорта: {e}")
    sys.exit(1)
except Exception as e:
    print(f"✗ Другая ошибка: {e}")
    sys.exit(1)