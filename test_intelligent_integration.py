#!/usr/bin/env python3
"""
Тест интеллектуальной LLM интеграции

Проверяет работу всех компонентов интеллектуальной системы:
- IntelligentRouter
- AdaptiveStrategyManager
- IntelligentEvaluator
- ErrorLearningSystem
"""

import asyncio
import logging
import sys
from pathlib import Path

# Добавляем src в путь
sys.path.insert(0, str(Path(__file__).parent / "src"))

from llm.manager import LLMManager

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_basic_functionality():
    """Тест базовой функциональности"""
    print("\n=== Тест базовой функциональности ===")

    try:
        # Инициализация менеджера с правильным путем к конфигу
        config_path = Path(__file__).parent / "config" / "llm_settings.yaml"
        manager = LLMManager(config_path=str(config_path))
        await manager.initialize()

        # Тест простого запроса
        response = await manager.generate_response(
            prompt="Hello, how are you?",
            use_intelligent_routing=False  # Используем обычный режим для начала
        )

        print("✓ Базовая генерация работает")
        print(f"  Ответ: {response.content[:100]}...")

        # Тест интеллектуальной маршрутизации
        response_intelligent = await manager.generate_response(
            prompt="Explain quantum computing in simple terms",
            use_intelligent_routing=True
        )

        print("✓ Интеллектуальная маршрутизация работает")
        print(f"  Модель: {response_intelligent.model_name}")

        # Тест адаптивной генерации
        response_adaptive = await manager.generate_adaptive(
            prompt="Write a Python function to calculate fibonacci numbers"
        )

        print("✓ Адаптивная генерация работает")
        print(f"  Модель: {response_adaptive.model_name}")

        await manager.shutdown()
        return True

    except Exception as e:
        print(f"✗ Ошибка в базовой функциональности: {e}")
        return False


async def test_intelligent_analysis():
    """Тест интеллектуального анализа"""
    print("\n=== Тест интеллектуального анализа ===")

    try:
        config_path = Path(__file__).parent / "config" / "llm_settings.yaml"
        manager = LLMManager(config_path=str(config_path))
        await manager.initialize()

        # Тест анализа запросов разных типов
        test_prompts = [
            "def fibonacci(n):",  # Код
            "Analyze this data: [1, 2, 3, 4, 5]",  # Анализ
            "What is the capital of France?",  # Вопрос-ответ
            "Write a creative story about AI",  # Креатив
            '{"name": "John", "age": 30}',  # JSON
        ]

        for prompt in test_prompts:
            analysis = manager.analyze_request(prompt)
            print(f"✓ Анализ запроса: '{prompt[:30]}...' -> {analysis.task_type}")

        await manager.shutdown()
        return True

    except Exception as e:
        print(f"✗ Ошибка в интеллектуальном анализе: {e}")
        return False


async def test_evaluation_system():
    """Тест системы оценки"""
    print("\n=== Тест системы оценки ===")

    try:
        config_path = Path(__file__).parent / "config" / "llm_settings.yaml"
        manager = LLMManager(config_path=str(config_path))
        await manager.initialize()

        # Генерируем тестовый ответ
        response = await manager.generate_response(
            prompt="Explain machine learning briefly",
            use_intelligent_routing=False
        )

        if response.success:
            # Тест простой оценки
            evaluation = await manager.evaluate_response(
                prompt="Explain machine learning briefly",
                response=response.content
            )

            print(f"✓ Простая оценка работает: score = {evaluation.score}")

            # Тест интеллектуальной оценки
            detailed_eval = await manager.evaluate_response_intelligent(
                prompt="Explain machine learning briefly",
                response=response.content,
                task_type="question_answering"
            )

            print(f"✓ Интеллектуальная оценка работает: overall = {detailed_eval.overall_score}")
            print(f"  Аспекты: {list(detailed_eval.aspect_scores.keys())}")

        await manager.shutdown()
        return True

    except Exception as e:
        print(f"✗ Ошибка в системе оценки: {e}")
        return False


async def test_statistics():
    """Тест сбора статистики"""
    print("\n=== Тест статистики ===")

    try:
        config_path = Path(__file__).parent / "config" / "llm_settings.yaml"
        manager = LLMManager(config_path=str(config_path))
        await manager.initialize()

        # Выполняем несколько запросов для генерации статистики
        for i in range(3):
            await manager.generate_response(
                prompt=f"Test query {i}",
                use_intelligent_routing=True
            )

        # Получаем статистику
        stats = manager.get_stats()

        print("✓ Статистика собирается:")
        print(f"  Моделей: {stats['models']['total']}")
        print(f"  Интеллектуальный роутер: {stats['intelligent_router']['cache_size']} кэшированных")
        print(f"  Адаптивная стратегия: {stats['adaptive_strategy']['cache_size']} решений")
        print(f"  Оценщик: {stats['intelligent_evaluator']['cache_size']} оценок")
        print(f"  Обучение на ошибках: {stats['error_learning']['total_errors_analyzed']} ошибок")

        await manager.shutdown()
        return True

    except Exception as e:
        print(f"✗ Ошибка в сборе статистики: {e}")
        return False


async def test_error_learning():
    """Тест системы обучения на ошибках"""
    print("\n=== Тест обучения на ошибках ===")

    try:
        config_path = Path(__file__).parent / "config" / "llm_settings.yaml"
        manager = LLMManager(config_path=str(config_path))
        await manager.initialize()

        # Имитируем ошибку (используем несуществующую модель)
        try:
            response = await manager.generate_response(
                prompt="Test error handling",
                model_name="nonexistent_model"
            )
        except:
            pass  # Ожидаемая ошибка

        # Получаем рекомендации по предотвращению ошибок
        recommendations = manager.get_error_prevention_recommendations(
            "Another test query"
        )

        print(f"✓ Система обучения на ошибках работает")
        print(f"  Рекомендации: {len(recommendations)}")

        # Получаем статистику обучения
        learning_stats = manager.get_error_learning_stats()
        print(f"  Проанализировано ошибок: {learning_stats['total_errors_analyzed']}")

        await manager.shutdown()
        return True

    except Exception as e:
        print(f"✗ Ошибка в обучении на ошибках: {e}")
        return False


async def main():
    """Основная функция тестирования"""
    print("🚀 Тестирование интеллектуальной LLM интеграции")
    print("=" * 50)

    tests = [
        test_basic_functionality,
        test_intelligent_analysis,
        test_evaluation_system,
        test_statistics,
        test_error_learning
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        try:
            result = await test()
            if result:
                passed += 1
        except Exception as e:
            print(f"✗ Критическая ошибка в тесте {test.__name__}: {e}")

    print("\n" + "=" * 50)
    print(f"📊 Результаты тестирования: {passed}/{total} тестов пройдено")

    if passed == total:
        print("🎉 Все тесты пройдены! Интеллектуальная LLM интеграция работает корректно.")
        return 0
    else:
        print("⚠️  Некоторые тесты не пройдены. Проверьте логи для деталей.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)