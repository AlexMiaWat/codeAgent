#!/usr/bin/env python3
"""
Тестовый скрипт для проверки работы системы мониторинга стоимости API вызовов.
"""

import sys
import os
from pathlib import Path

# Добавляем src в путь
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cost_monitor import CostMonitor

def test_cost_monitor():
    """Тестирование основных функций мониторинга стоимости"""
    print("🧪 Тестирование системы мониторинга стоимости API вызовов")
    print("=" * 60)

    monitor = CostMonitor()

    # Тест 1: Получение информации о стоимости моделей
    print("1. Проверка информации о стоимости моделей...")
    models_to_test = [
        "meta-llama/llama-3.2-1b-instruct",
        "microsoft/wizardlm-2-8x22b",
        "auto",
        "nonexistent_model"
    ]

    for model in models_to_test:
        cost_info = monitor.get_model_cost_info(model)
        if cost_info:
            input_cost = cost_info.get('input_cost_per_1k', 0)
            output_cost = cost_info.get('output_cost_per_1k', 0)
            print(f"   ✅ {model}: вход ${input_cost:.6f}/1K, выход ${output_cost:.6f}/1K")
        else:
            print(f"   ❌ {model}: информация не найдена")

    # Тест 2: Расчет стоимости вызовов
    print("\n2. Тестирование расчета стоимости...")
    test_cases = [
        ("meta-llama/llama-3.2-1b-instruct", 1000, 500),  # 1500 токенов
        ("microsoft/wizardlm-2-8x22b", 2000, 1000),       # 3000 токенов
        ("auto", 1000, 500),                              # Неизвестная стоимость
    ]

    for model, input_tokens, output_tokens in test_cases:
        cost = monitor.calculate_cost(model, input_tokens, output_tokens)
        print(f"   💰 {model}: {input_tokens + output_tokens} токенов = ${cost:.6f}")
    # Тест 3: Запись API вызовов
    print("\n3. Тестирование записи API вызовов...")
    test_records = [
        ("meta-llama/llama-3.2-1b-instruct", 500, 250, "task_123"),
        ("microsoft/wizardlm-2-8x22b", 1000, 500, "task_124"),
        ("meta-llama/llama-3.2-1b-instruct", 300, 150, "task_125"),
    ]

    for model, input_tokens, output_tokens, task_id in test_records:
        monitor.record_api_call(
            model_name=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            task_id=task_id
        )
        print(f"   ✅ Записан вызов: {model}, токены: {input_tokens + output_tokens}")

    # Тест 4: Получение сводки стоимости
    print("\n4. Тестирование получения сводки стоимости...")
    summary = monitor.get_cost_summary('daily')
    print(f"   Общая стоимость: ${summary.total_cost:.6f}")
    print(f"   Всего токенов: {summary.total_tokens}")
    print(f"   Всего вызовов: {summary.total_calls}")

    if summary.model_breakdown:
        print("   Разбивка по моделям:")
        for model, stats in summary.model_breakdown.items():
            print(f"     {model}: ${stats['cost']:.6f}, {stats['tokens']} токенов, {stats['calls']} вызовов")
    # Тест 5: Отчет об эффективности
    print("\n5. Тестирование отчета об эффективности...")
    efficiency_report = monitor.get_model_efficiency_report()

    print(f"   Всего моделей: {efficiency_report['total_models_used']}")
    print(f"   Всего вызовов: {efficiency_report['total_api_calls']}")
    print(f"   Общая стоимость: ${efficiency_report['total_cost']:.6f}")

    if efficiency_report['model_ranking']:
        print("   Рейтинг моделей по стоимости:")
        for i, (model, stats) in enumerate(efficiency_report['model_ranking'][:3], 1):
            print(f"     {i}. {model}: ${stats['total_cost']:.6f}")
            print(f"        Вызовов: {stats['total_calls']}, средняя стоимость: ${stats['avg_cost_per_call']:.6f}")
    print("\n✅ Тестирование завершено!")
    print(f"📄 Данные сохранены в: {monitor.log_file}")

    return True

if __name__ == "__main__":
    try:
        test_cost_monitor()
    except Exception as e:
        print(f"❌ Ошибка тестирования: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)