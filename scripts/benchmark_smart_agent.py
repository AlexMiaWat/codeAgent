#!/usr/bin/env python3
"""
Простой скрипт для проверки baseline состояния Smart Agent конфигурации.

Проверяет:
- Загрузку конфигурации
- Наличие дублирования настроек
- Базовую валидность YAML файлов
- Структуру модели в llm_settings.yaml
"""

import os
import sys
import yaml
import json
from datetime import datetime
from pathlib import Path

def load_yaml_file(file_path):
    """Загрузка YAML файла с обработкой ошибок"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        return {"error": str(e), "file": str(file_path)}

def analyze_config_duplication():
    """Анализ дублирования настроек между config.yaml и agents.yaml"""
    config_path = Path("config/config.yaml")
    agents_path = Path("config/agents.yaml")

    config_data = load_yaml_file(config_path)
    agents_data = load_yaml_file(agents_path)

    issues = []

    # Проверяем дублирование smart_agent настроек
    config_smart = config_data.get("smart_agent", {})
    agents_smart = agents_data.get("smart_agent", {})

    duplicated_keys = set(config_smart.keys()) & set(agents_smart.keys())
    if duplicated_keys:
        issues.append({
            "type": "duplication",
            "description": f"Дублирование параметров smart_agent: {', '.join(duplicated_keys)}",
            "config_values": {k: config_smart[k] for k in duplicated_keys},
            "agents_values": {k: agents_smart[k] for k in duplicated_keys},
            "recommendation": "Убрать дублирование, оставить настройки только в одном месте"
        })

    return issues

def analyze_llm_settings():
    """Анализ настроек LLM"""
    llm_path = Path("config/llm_settings.yaml")
    llm_data = load_yaml_file(llm_path)

    issues = []

    if "error" in llm_data:
        return [{"type": "error", "description": f"Ошибка загрузки llm_settings.yaml: {llm_data['error']}"}]

    # Проверяем статистику
    stats = llm_data.get("_stats", {})
    if stats.get("working_count", 0) == 0:
        issues.append({
            "type": "warning",
            "description": "working_count = 0, возможно проблемы с моделями",
            "current_stats": stats
        })

    # Проверяем наличие дорогих моделей
    providers = llm_data.get("providers", {})
    expensive_models = []

    for provider_name, provider_data in providers.items():
        if "models" in provider_data:
            for model in provider_data["models"]:
                if isinstance(model, dict):
                    name = model.get("name", "")
                else:
                    name = str(model)
                if any(keyword in name.lower() for keyword in ["claude", "gpt-4o", "sonnet"]):
                    expensive_models.append(name)

    if expensive_models:
        issues.append({
            "type": "cost_warning",
            "description": f"Найдены потенциально дорогие модели: {', '.join(expensive_models)}",
            "recommendation": "Убедиться в необходимости использования дорогих моделей"
        })

    return issues

def check_todo_status():
    """Проверка статуса задачи в todo.md"""
    todo_path = Path("todo.md")

    try:
        with open(todo_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Ищем строку с задачей 1769114510
        lines = content.split('\n')
        for line in lines:
            if "1769114510" in line:
                if line.startswith("- [x]"):
                    return {"status": "completed", "line": line.strip()}
                elif line.startswith("- [ ]"):
                    return {"status": "pending", "line": line.strip()}
                else:
                    return {"status": "unknown", "line": line.strip()}

        return {"status": "not_found"}

    except Exception as e:
        return {"status": "error", "error": str(e)}

def main():
    """Основная функция анализа"""
    print("🔍 Анализ baseline состояния Smart Agent конфигурации")
    print("=" * 60)

    results = {
        "timestamp": datetime.now().isoformat(),
        "analysis_type": "baseline_check",
        "issues": []
    }

    # 1. Анализ дублирования настроек
    print("📋 Анализ дублирования настроек...")
    duplication_issues = analyze_config_duplication()
    results["issues"].extend(duplication_issues)
    print(f"   Найдено проблем дублирования: {len(duplication_issues)}")

    # 2. Анализ LLM настроек
    print("🤖 Анализ LLM настроек...")
    llm_issues = analyze_llm_settings()
    results["issues"].extend(llm_issues)
    print(f"   Найдено проблем LLM: {len(llm_issues)}")

    # 3. Проверка статуса задачи
    print("📝 Проверка статуса задачи...")
    todo_status = check_todo_status()
    results["todo_status"] = todo_status
    print(f"   Статус задачи: {todo_status.get('status', 'unknown')}")

    # Сохранение результатов
    output_file = f"docs/results/baseline_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print("=" * 60)
    print("✅ Анализ завершен!")
    print(f"📄 Результаты сохранены в: {output_file}")

    # Вывод кратких результатов
    print("\n📊 КРАТКИЕ РЕЗУЛЬТАТЫ:")

    if duplication_issues:
        print(f"⚠️  Дублирование настроек: {len(duplication_issues)} проблем")
        for issue in duplication_issues:
            print(f"   • {issue['description']}")

    if llm_issues:
        print(f"⚠️  Проблемы LLM: {len(llm_issues)} проблем")
        for issue in llm_issues:
            print(f"   • {issue['description']}")

    todo_status_desc = todo_status.get('status', 'unknown')
    if todo_status_desc == 'completed':
        print("✅ Задача отмечена как завершенная")
    elif todo_status_desc == 'pending':
        print("⏳ Задача все еще в работе")
    else:
        print(f"❓ Статус задачи: {todo_status_desc}")

    return results

if __name__ == "__main__":
    main()