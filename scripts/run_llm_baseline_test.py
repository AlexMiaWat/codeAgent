#!/usr/bin/env python3
"""
Скрипт для проведения baseline тестирования LLM моделей

Измеряет метрики производительности и стоимости для всех моделей.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Добавляем корневую директорию в PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.llm.llm_manager import LLMManager
from src.llm.llm_test_runner import LLMTestRunner
from src.config_loader import ConfigLoader

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

async def run_baseline_tests():
    """Запуск baseline тестирования всех моделей"""

    logger.info("Starting LLM baseline performance and cost measurements...")

    try:
        # Создаем LLM менеджер с конфигурацией по умолчанию
        llm_manager = LLMManager()

        # Создаем тестер
        test_runner = LLMTestRunner(llm_manager)

        # Запускаем тестирование всех моделей
        logger.info("Running comprehensive model tests...")
        results = await test_runner.test_all_models(
            simple_prompt="Привет, это тестовое сообщение для измерения baseline производительности. Ответь кратко, в одном предложении.",
            delay=2.0,  # Задержка между тестами
            use_usefulness_test=True,  # Используем реальный тест с JSON mode
            test_todo_text="Добавить обработку ошибок в API для улучшения надежности",
            project_docs="Проект Code Agent - система автоматизации задач через LLM. Основные компоненты: сервер агента, smart agent, система инструментов, LLM менеджер."
        )

        # Экспортируем результаты в Markdown
        output_path = Path("docs/results/llm_baseline_metrics_20260122.md")
        exported_path = test_runner.export_results_markdown(output_path)

        logger.info(f"Baseline test completed. Results saved to: {exported_path}")

        # Выводим краткую сводку
        working_models = test_runner.get_working_models()
        fastest_models = test_runner.get_fastest_models()

        print("\n" + "="*80)
        print("BASELINE LLM METRICS SUMMARY")
        print("="*80)
        print(f"Total models tested: {len(results)}")
        print(f"Working models: {len(working_models)}")
        print(f"Working model names: {', '.join(working_models)}")

        if fastest_models:
            print("\nTop 5 fastest models:")
            for i, (model, time) in enumerate(fastest_models[:5], 1):
                print(f"  {i}. {model}: {time:.2f}s")

        print(f"\nDetailed results: {exported_path}")
        print("="*80)

        return results, exported_path

    except Exception as e:
        logger.error(f"Error during baseline testing: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(run_baseline_tests())