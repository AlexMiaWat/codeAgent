"""
Простой тест для проверки OpenRouter API

Проверяет:
- Доступность API
- Валидность API ключа
- Работу простого запроса
"""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from openai import AsyncOpenAI
import yaml

# Загружаем переменные окружения
load_dotenv()

# Добавляем текущую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))


async def test_openrouter_api():
    """Тест OpenRouter API"""
    print("=" * 70)
    print("ТЕСТ OpenRouter API")
    print("=" * 70)
    print()
    
    # API ключ должен быть только в переменной окружения или .env файле
    api_key = os.getenv('OPENROUTER_API_KEY')
    
    if api_key:
        print("[OK] API ключ найден в переменной окружения OPENROUTER_API_KEY")
    else:
        print("[ERROR] API ключ не найден!")
        print("Установите OPENROUTER_API_KEY в переменных окружения или в .env файле")
        print("API ключи не должны храниться в конфиг файлах по соображениям безопасности")
    
    if not api_key:
        print()
        print("[ERROR] API ключ не найден ни в одном источнике!")
        print("Установите OPENROUTER_API_KEY в переменных окружения или в config/llm_settings.yaml")
        return False
    
    print(f"API ключ: {api_key[:20]}...{api_key[-10:]}")
    print()
    
    # Создаем клиент
    base_url = "https://openrouter.ai/api/v1"
    client = AsyncOpenAI(base_url=base_url, api_key=api_key, timeout=30)
    
    # Тест 1: Проверка доступности API через список моделей
    print("Тест 1: Проверка доступности API...")
    try:
        # Используем простой запрос для проверки
        response = await client.chat.completions.create(
            model="meta-llama/llama-3.2-1b-instruct",
            messages=[{"role": "user", "content": "Say 'OK'"}],
            max_tokens=10
        )
        
        if response and response.choices:
            content = response.choices[0].message.content
            print(f"[OK] API доступен!")
            print(f"  Ответ модели: {content}")
            return True
        else:
            print("[FAIL] API вернул пустой ответ")
            return False
            
    except Exception as e:
        error_msg = str(e)
        print(f"[FAIL] Ошибка при обращении к API:")
        print(f"  {error_msg}")
        
        if "401" in error_msg or "User not found" in error_msg:
            print()
            print("[INFO] Ошибка 401 означает, что API ключ недействителен или истек.")
            print("Проверьте:")
            print("  1. Правильность API ключа")
            print("  2. Активность аккаунта на OpenRouter")
            print("  3. Наличие средств/квот на аккаунте")
        
        return False


async def test_model_list():
    """Тест получения списка моделей"""
    print()
    print("=" * 70)
    print("Тест 2: Получение списка моделей")
    print("=" * 70)
    print()
    
    # API ключ должен быть только в переменной окружения или .env файле
    api_key = os.getenv('OPENROUTER_API_KEY')
    
    if not api_key:
        print("[SKIP] API ключ не найден")
        print("Установите OPENROUTER_API_KEY в переменных окружения или в .env файле")
        return False
    
    try:
        import requests
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        response = requests.get("https://openrouter.ai/api/v1/models", headers=headers, timeout=10)
        
        if response.status_code == 200:
            models = response.json().get('data', [])
            print(f"[OK] Получено {len(models)} моделей")
            
            # Показываем первые 5 бесплатных моделей
            free_models = [m for m in models if m.get('pricing', {}).get('prompt') == '0' or m.get('pricing', {}).get('completion') == '0']
            print(f"\nНайдено {len(free_models)} бесплатных моделей")
            print("\nПервые 5 бесплатных моделей:")
            for i, model in enumerate(free_models[:5], 1):
                name = model.get('id', 'unknown')
                print(f"  {i}. {name}")
            
            return True
        else:
            print(f"[FAIL] Ошибка при получении списка моделей: {response.status_code}")
            print(f"  Ответ: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"[FAIL] Ошибка: {e}")
        return False


async def main():
    """Главная функция"""
    print()
    print("=" * 70)
    print("ТЕСТИРОВАНИЕ OpenRouter API")
    print("=" * 70)
    print()
    
    results = {}
    
    # Тест 1: Проверка API
    try:
        results['api'] = await test_openrouter_api()
    except Exception as e:
        print(f"[ERROR] Тест 1 прерван: {e}")
        results['api'] = False
    
    # Тест 2: Список моделей
    try:
        results['models'] = await test_model_list()
    except Exception as e:
        print(f"[ERROR] Тест 2 прерван: {e}")
        results['models'] = False
    
    # Итоги
    print()
    print("=" * 70)
    print("ИТОГИ")
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
