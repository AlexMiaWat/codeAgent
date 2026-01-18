"""
Тест скрипт для проверки работы agent через Docker
"""

import subprocess
import sys
import os
from pathlib import Path

def test_docker_agent():
    """Тестирование agent через Docker"""
    
    print("=" * 70)
    print("Тестирование agent через Docker")
    print("=" * 70)
    print()
    
    # 1. Проверка .env файла
    print("1. Проверка .env файла:")
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        env_content = env_file.read_text(encoding='utf-8')
        if "CURSOR_API_KEY" in env_content:
            cursor_key = [line for line in env_content.split('\n') if 'CURSOR_API_KEY' in line][0]
            key_value = cursor_key.split('=')[1] if '=' in cursor_key else ""
            print(f"   [OK] CURSOR_API_KEY найден в .env")
            print(f"   [OK] CURSOR_API_KEY: {key_value[:20]}...")
        else:
            print("   [FAIL] CURSOR_API_KEY не найден в .env")
            return False
    else:
        print("   [FAIL] .env файл не найден")
        return False
    
    print()
    
    # 2. Проверка Docker образа
    print("2. Проверка Docker образа:")
    try:
        result = subprocess.run(
            ["docker", "images", "cursor-agent"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if "cursor-agent" in result.stdout:
            print("   [OK] Образ cursor-agent найден")
        else:
            print("   [FAIL] Образ cursor-agent не найден")
            return False
    except Exception as e:
        print(f"   [ERROR] Ошибка проверки образа: {e}")
        return False
    
    print()
    
    # 3. Проверка версии agent
    print("3. Проверка версии agent:")
    try:
        compose_file = Path(__file__).parent / "docker" / "docker-compose.agent.yml"
        result = subprocess.run(
            ["docker", "compose", "-f", str(compose_file), "run", "--rm", "agent", "--version"],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            version = result.stdout.strip().split('\n')[-1]
            print(f"   [OK] Agent версия: {version}")
        else:
            print(f"   [FAIL] Не удалось получить версию: {result.stderr}")
            return False
    except Exception as e:
        print(f"   [ERROR] Ошибка проверки версии: {e}")
        return False
    
    print()
    
    # 4. Тест выполнения команды
    print("4. Тест выполнения команды:")
    try:
        env = os.environ.copy()
        result = subprocess.run(
            ["docker", "compose", "-f", str(compose_file), "run", "--rm", 
             "-e", "CURSOR_API_KEY", "agent", "-p", "echo 'Test command'"],
            capture_output=True,
            text=True,
            timeout=60,
            env=env
        )
        if result.returncode == 0:
            print("   [OK] Команда выполнена успешно")
            output = result.stdout.strip().split('\n')[-3:]
            for line in output:
                if line.strip():
                    print(f"   Output: {line[:60]}")
        else:
            print(f"   [WARNING] Команда завершилась с кодом {result.returncode}")
            print(f"   Stderr: {result.stderr[:200]}")
    except Exception as e:
        print(f"   [ERROR] Ошибка выполнения команды: {e}")
    
    print()
    
    # 5. Тест создания файла
    print("5. Тест создания файла:")
    try:
        result = subprocess.run(
            ["docker", "compose", "-f", str(compose_file), "run", "--rm",
             "-e", "CURSOR_API_KEY", "agent", "-p", 
             "Create file docker_test4.txt with content 'Test from Python script'"],
            capture_output=True,
            text=True,
            timeout=60,
            env=env
        )
        if result.returncode == 0:
            print("   [OK] Команда создания файла выполнена")
            
            # Проверка файла
            test_file = Path(__file__).parent.parent / "life" / "docker_test4.txt"
            if test_file.exists():
                content = test_file.read_text(encoding='utf-8')
                print(f"   [OK] Файл создан: {test_file}")
                print(f"   [OK] Содержимое: {content[:50]}")
            else:
                print(f"   [WARNING] Файл не найден в {test_file}")
        else:
            print(f"   [WARNING] Команда завершилась с кодом {result.returncode}")
    except Exception as e:
        print(f"   [ERROR] Ошибка создания файла: {e}")
    
    print()
    print("=" * 70)
    print("Тестирование завершено")
    print("=" * 70)
    print()
    
    return True

if __name__ == "__main__":
    try:
        success = test_docker_agent()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n[ERROR] Ошибка тестирования: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
