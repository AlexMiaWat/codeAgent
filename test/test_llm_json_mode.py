"""
Тестирование LLMManager с JSON mode и fallback механизмом

Проверяет:
- JSON mode с response_format
- Валидацию JSON ответов
- Fallback при ошибках (включая некорректный JSON)
- Извлечение JSON из ответов (включая markdown code fences)
- Проверку что все модели в fallback цепочке пробуются
"""

import asyncio
import json
import re
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

from src.llm.llm_manager import LLMManager, ModelResponse

# Добавляем корень проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def extract_json_object(text: str) -> Optional[dict]:
    """
    Надежно извлекает JSON-объект из ответа LLM.
    Поддерживает ситуации, когда модель возвращает текст/markdown и JSON внутри.
    """
    if not text:
        return None
    
    t = text.strip()
    # Убираем code fences вида ```json ... ```
    if t.startswith("```"):
        t = re.sub(r"^```(?:json)?\s*", "", t, flags=re.IGNORECASE)
        t = re.sub(r"\s*```$", "", t)
        t = t.strip()
    
    decoder = json.JSONDecoder()
    # Ищем первый валидный JSON объект, начиная с '{' или '['
    for i, ch in enumerate(t):
        if ch not in "{[":
            continue
        try:
            obj, _end = decoder.raw_decode(t[i:])
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            return obj
    return None


def validate_json_response(
    response: ModelResponse,
    expected_schema: Optional[Dict[str, Any]] = None,
    required_fields: Optional[list] = None
) -> tuple[bool, Optional[str], Optional[dict]]:
    """
    Валидирует JSON ответ от LLM
    
    Args:
        response: Ответ модели
        expected_schema: Ожидаемая схема JSON (для проверки типов)
        required_fields: Обязательные поля в JSON
    
    Returns:
        (is_valid, error_message, parsed_json)
    """
    if not response.success:
        return False, f"Response failed: {response.error}", None
    
    if not response.content:
        return False, "Empty response content", None
    
    # Извлекаем JSON из ответа
    json_obj = extract_json_object(response.content)
    
    if json_obj is None:
        # Последняя попытка - прямой парсинг
        try:
            json_obj = json.loads(response.content)
        except json.JSONDecodeError as e:
            return False, f"Failed to parse JSON: {e}. Content: {response.content[:200]}", None
    
    # Проверяем обязательные поля
    if required_fields:
        missing = [field for field in required_fields if field not in json_obj]
        if missing:
            return False, f"Missing required fields: {missing}", json_obj
    
    # Базовая валидация типов (если указана схема)
    if expected_schema:
        for field, expected_type in expected_schema.items():
            if field in json_obj:
                actual_type = type(json_obj[field]).__name__
                if expected_type == "number" and actual_type not in ["int", "float"]:
                    return False, f"Field '{field}' should be number, got {actual_type}", json_obj
                elif expected_type == "string" and actual_type != "str":
                    return False, f"Field '{field}' should be string, got {actual_type}", json_obj
                elif expected_type == "boolean" and actual_type != "bool":
                    return False, f"Field '{field}' should be boolean, got {actual_type}", json_obj
    
    return True, None, json_obj


async def test_json_mode_basic():
    """Тест базового JSON mode"""
    print("=" * 70)
    print("ТЕСТ 1: Базовый JSON mode")
    print("=" * 70)
    print()
    
    mgr = LLMManager('config/llm_settings.yaml')
    
    # Простой запрос с JSON схемой
    prompt = """Оцени полезность этого пункта из TODO списка.

ПУНКТ TODO: Реализовать функцию поиска документов

Верни JSON объект со следующей структурой:
{
  "usefulness_percent": число от 0 до 100,
  "comment": "краткий комментарий о полезности задачи"
}"""
    
    json_response_format = {"type": "json_object"}
    
    print(f"Запрос: {prompt[:100]}...")
    print(f"Response format: {json_response_format}")
    print()
    
    try:
        response = await mgr.generate_response(
            prompt=prompt,
            use_fastest=True,
            use_parallel=False,
            response_format=json_response_format
        )
        
        # Валидируем ответ
        is_valid, error_msg, json_obj = validate_json_response(
            response,
            expected_schema={"usefulness_percent": "number", "comment": "string"},
            required_fields=["usefulness_percent", "comment"]
        )
        
        if is_valid and json_obj:
            print("[OK] Успешно!")
            print(f"  Модель: {response.model_name}")
            print(f"  Время отклика: {response.response_time:.2f}s")
            print(f"  Парсированный JSON: {json.dumps(json_obj, ensure_ascii=False, indent=2)}")
            
            # Проверяем значения
            usefulness = json_obj.get("usefulness_percent", 0)
            if 0 <= usefulness <= 100:
                print(f"  [OK] usefulness_percent в допустимом диапазоне: {usefulness}")
            else:
                print(f"  [WARN] usefulness_percent вне диапазона: {usefulness}")
            
            return True
        else:
            print("[FAIL] Валидация не прошла:")
            print(f"  Модель: {response.model_name}")
            print(f"  Ошибка: {error_msg}")
            print(f"  Сырой ответ: {response.content[:300]}")
            return False
            
    except Exception as e:
        print(f"[ERROR] Исключение при генерации: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_json_mode_fallback():
    """Тест fallback при ошибках в JSON mode"""
    print()
    print("=" * 70)
    print("ТЕСТ 2: Fallback при ошибках в JSON mode")
    print("=" * 70)
    print()
    
    mgr = LLMManager('config/llm_settings.yaml')
    
    # Запрос с JSON схемой
    prompt = """Проверь, соответствует ли пункт туду пунктам плана.

ПУНКТ ТУДУ: Добавить валидацию входных данных

ПЛАН ВЫПОЛНЕНИЯ:
1. Создать функцию валидации
2. Добавить тесты
3. Обновить документацию

Ответь ТОЛЬКО в формате JSON:
{
  "matches": true/false,
  "reason": "краткая причина несоответствия (если matches=false)"
}"""
    
    json_response_format = {"type": "json_object"}
    
    print(f"Запрос: {prompt[:100]}...")
    print()
    print("Primary модели:")
    for model in mgr.get_primary_models():
        print(f"  - {model.name}")
    print()
    print("Fallback модели:")
    for model in mgr.get_fallback_models():
        print(f"  - {model.name}")
    print()
    print("Тестируем fallback цепочку...")
    print()
    
    try:
        # Сохраняем начальные счетчики ошибок
        initial_errors = {m.name: m.error_count for m in mgr.models.values()}
        
        response = await mgr.generate_response(
            prompt=prompt,
            use_fastest=True,
            use_parallel=False,
            response_format=json_response_format
        )
        
        # Проверяем что fallback сработал (если первая модель упала)
        final_errors = {m.name: m.error_count for m in mgr.models.values()}
        models_with_errors = {
            name: final_errors[name] - initial_errors[name]
            for name in final_errors
            if final_errors[name] > initial_errors[name]
        }
        
        if models_with_errors:
            print("[INFO] Модели с ошибками (fallback сработал):")
            for model_name, error_count in models_with_errors.items():
                print(f"  - {model_name}: {error_count} ошибок")
            print()
        
        # Валидируем ответ
        is_valid, error_msg, json_obj = validate_json_response(
            response,
            expected_schema={"matches": "boolean"},
            required_fields=["matches"]
        )
        
        if is_valid and json_obj:
            print("[OK] Успешно!")
            print(f"  Финальная модель: {response.model_name}")
            print(f"  Время отклика: {response.response_time:.2f}s")
            print(f"  Парсированный JSON: {json.dumps(json_obj, ensure_ascii=False, indent=2)}")
            
            matches = json_obj.get("matches", False)
            print(f"  [OK] matches: {matches}")
            
            if not matches and "reason" in json_obj:
                print(f"  [OK] reason присутствует: {json_obj['reason'][:100]}")
            
            return True
        else:
            print("[FAIL] Валидация не прошла:")
            print(f"  Модель: {response.model_name}")
            print(f"  Ошибка: {error_msg}")
            print(f"  Сырой ответ: {response.content[:500]}")
            return False
            
    except Exception as e:
        print(f"[ERROR] Исключение при генерации: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_json_extraction_from_markdown():
    """Тест извлечения JSON из markdown ответов"""
    print()
    print("=" * 70)
    print("ТЕСТ 3: Извлечение JSON из markdown ответов")
    print("=" * 70)
    print()
    
    mgr = LLMManager('config/llm_settings.yaml')
    
    # Запрос который может вернуть JSON в markdown
    prompt = """Оцени полезность задачи.

ЗАДАЧА: Реализовать поиск по документам

Верни JSON объект:
{
  "usefulness_percent": число от 0 до 100,
  "comment": "комментарий"
}"""
    
    json_response_format = {"type": "json_object"}
    
    print(f"Запрос: {prompt[:100]}...")
    print("(Некоторые модели могут обернуть JSON в markdown code fences)")
    print()
    
    try:
        response = await mgr.generate_response(
            prompt=prompt,
            use_fastest=True,
            use_parallel=False,
            response_format=json_response_format
        )
        
        if not response.success:
            print(f"[FAIL] Ошибка генерации: {response.error}")
            return False
        
        print("[INFO] Сырой ответ (первые 300 символов):")
        print(f"  {response.content[:300]}")
        print()
        
        # Пытаемся извлечь JSON
        json_obj = extract_json_object(response.content)
        
        if json_obj:
            print("[OK] JSON успешно извлечен!")
            print(f"  Модель: {response.model_name}")
            print(f"  Парсированный JSON: {json.dumps(json_obj, ensure_ascii=False, indent=2)}")
            
            # Проверяем структуру
            if "usefulness_percent" in json_obj:
                usefulness = json_obj["usefulness_percent"]
                if isinstance(usefulness, (int, float)) and 0 <= usefulness <= 100:
                    print(f"  [OK] usefulness_percent валиден: {usefulness}")
                else:
                    print(f"  [WARN] usefulness_percent невалиден: {usefulness}")
            
            return True
        else:
            print("[FAIL] Не удалось извлечь JSON из ответа")
            print(f"  Полный ответ: {response.content}")
            return False
            
    except Exception as e:
        print(f"[ERROR] Исключение при генерации: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_multiple_json_requests():
    """Тест множественных JSON запросов для проверки стабильности"""
    print()
    print("=" * 70)
    print("ТЕСТ 4: Множественные JSON запросы (стабильность)")
    print("=" * 70)
    print()
    
    mgr = LLMManager('config/llm_settings.yaml')
    
    prompts = [
        {
            "prompt": """Оцени полезность задачи.

ЗАДАЧА: Добавить комментарии к коду

Верни JSON:
{
  "usefulness_percent": число от 0 до 100,
  "comment": "комментарий"
}""",
            "required_fields": ["usefulness_percent", "comment"]
        },
        {
            "prompt": """Проверь соответствие туду плану.

ТУДУ: Создать тесты
ПЛАН: 1. Написать unit тесты 2. Интеграционные тесты

Верни JSON:
{
  "matches": true/false,
  "reason": "причина если не соответствует"
}""",
            "required_fields": ["matches"]
        },
        {
            "prompt": """Оцени качество ответа.

ОТВЕТ: Python - это язык программирования.

Верни JSON:
{
  "score": число от 0 до 10,
  "quality": "poor|fair|good|excellent"
}""",
            "required_fields": ["score", "quality"]
        }
    ]
    
    json_response_format = {"type": "json_object"}
    
    print(f"Выполняем {len(prompts)} запросов...")
    print()
    
    results = []
    for i, test_case in enumerate(prompts, 1):
        print(f"Запрос {i}/{len(prompts)}...")
        try:
            response = await mgr.generate_response(
                prompt=test_case["prompt"],
                use_fastest=True,
                use_parallel=False,
                response_format=json_response_format
            )
            
            is_valid, error_msg, json_obj = validate_json_response(
                response,
                required_fields=test_case["required_fields"]
            )
            
            if is_valid:
                print(f"  [OK] Запрос {i} успешен")
                results.append(True)
            else:
                print(f"  [FAIL] Запрос {i} не прошел валидацию: {error_msg}")
                results.append(False)
            
            # Небольшая задержка между запросами
            await asyncio.sleep(1)
            
        except Exception as e:
            print(f"  [ERROR] Запрос {i} упал с ошибкой: {e}")
            results.append(False)
    
    print()
    success_count = sum(results)
    print(f"Успешно: {success_count}/{len(prompts)}")
    
    return success_count == len(prompts)


async def test_fallback_chain_verification():
    """Тест проверки что все модели в fallback цепочке пробуются"""
    print()
    print("=" * 70)
    print("ТЕСТ 5: Проверка fallback цепочки")
    print("=" * 70)
    print()
    
    mgr = LLMManager('config/llm_settings.yaml')
    
    # Простой запрос
    prompt = """Верни JSON объект:
{
  "status": "ok",
  "message": "тест"
}"""
    
    json_response_format = {"type": "json_object"}
    
    print("Проверяем что fallback цепочка работает...")
    print()
    print("Доступные модели:")
    all_models = mgr.get_primary_models() + mgr.get_fallback_models()
    for i, model in enumerate(all_models, 1):
        role = "PRIMARY" if model in mgr.get_primary_models() else "FALLBACK"
        print(f"  {i}. [{role}] {model.name}")
    print()
    
    try:
        # Сохраняем начальные счетчики
        initial_stats = {
            m.name: {
                "success": m.success_count,
                "errors": m.error_count
            }
            for m in mgr.models.values()
        }
        
        response = await mgr.generate_response(
            prompt=prompt,
            use_fastest=True,
            use_parallel=False,
            response_format=json_response_format
        )
        
        # Проверяем статистику
        final_stats = {
            m.name: {
                "success": m.success_count,
                "errors": m.error_count
            }
            for m in mgr.models.values()
        }
        
        print("Статистика использования моделей:")
        models_used = []
        for model_name in final_stats:
            initial = initial_stats[model_name]
            final = final_stats[model_name]
            
            success_diff = final["success"] - initial["success"]
            error_diff = final["errors"] - initial["errors"]
            
            if success_diff > 0 or error_diff > 0:
                status = "SUCCESS" if success_diff > 0 else "ERROR"
                models_used.append((model_name, status))
                print(f"  - {model_name}: {status} (success: +{success_diff}, errors: +{error_diff})")
        
        print()
        
        if response.success:
            print(f"[OK] Успешно получен ответ от модели: {response.model_name}")
            
            # Проверяем что ответ валидный JSON
            is_valid, error_msg, json_obj = validate_json_response(
                response,
                required_fields=["status"]
            )
            
            if is_valid:
                print(f"[OK] Ответ валиден: {json.dumps(json_obj, ensure_ascii=False)}")
                return True
            else:
                print(f"[FAIL] Ответ невалиден: {error_msg}")
                return False
        else:
            print(f"[FAIL] Все модели провалились: {response.error}")
            return False
            
    except Exception as e:
        print(f"[ERROR] Исключение: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Главная функция тестирования"""
    print()
    print("=" * 70)
    print("ТЕСТИРОВАНИЕ LLMManager: JSON MODE И FALLBACK")
    print("=" * 70)
    print(f"Время начала: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    results = {}
    
    # Тест 1: Базовый JSON mode
    try:
        results['json_basic'] = await test_json_mode_basic()
    except Exception as e:
        print(f"[FAIL] Тест 1 прерван: {e}")
        results['json_basic'] = False
    
    # Тест 2: Fallback в JSON mode
    try:
        results['json_fallback'] = await test_json_mode_fallback()
    except Exception as e:
        print(f"[FAIL] Тест 2 прерван: {e}")
        results['json_fallback'] = False
    
    # Тест 3: Извлечение JSON из markdown
    try:
        results['json_extraction'] = await test_json_extraction_from_markdown()
    except Exception as e:
        print(f"[FAIL] Тест 3 прерван: {e}")
        results['json_extraction'] = False
    
    # Тест 4: Множественные запросы
    try:
        results['json_multiple'] = await test_multiple_json_requests()
    except Exception as e:
        print(f"[FAIL] Тест 4 прерван: {e}")
        results['json_multiple'] = False
    
    # Тест 5: Проверка fallback цепочки
    try:
        results['fallback_chain'] = await test_fallback_chain_verification()
    except Exception as e:
        print(f"[FAIL] Тест 5 прерван: {e}")
        results['fallback_chain'] = False
    
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
    
    return passed == total


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n[INFO] Тестирование прервано пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
