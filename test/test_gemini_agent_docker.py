"""
Тест скрипт для проверки работы gemini-agent через Docker
"""

import subprocess
import sys
import os
from pathlib import Path
import pytest
import time

# Импорт вспомогательных функций
from .test_utils import get_project_dir

# Определение имени контейнера и файла docker-compose
GEMINI_CONTAINER_NAME = "gemini-agent"
GEMINI_COMPOSE_FILE = Path(__file__).parent.parent / "docker" / "docker-compose.gemini.yml"

# Вспомогательная функция для запуска docker compose команд
def run_docker_compose_command(command_args, timeout=60):
    cmd = ["docker", "compose", "-f", str(GEMINI_COMPOSE_FILE), "--env-file", "./.env"] + command_args
    print(f"Executing: {' '.join(cmd)}")
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False # Do not raise CalledProcessError for non-zero exit codes
    )
    if result.returncode != 0:
        print(f"Error Stdout: {result.stdout}")
        print(f"Error Stderr: {result.stderr}")
    return result

@pytest.fixture(scope="module", autouse=True)
def setup_and_teardown_gemini_agent():
    print("\nSetting up gemini-agent for testing...")
    
    # 1. Проверка .env файла
    print("1. Проверка .env файла:")
    env_file = Path(__file__).parent.parent / ".env"
    if not env_file.exists():
        pytest.fail(f"   [FAIL] .env файл не найден по пути: {env_file}. Создайте его из .env.example и настройте.")
    
    env_content = env_file.read_text(encoding='utf-8')
    target_project_path_set = False
    for line in env_content.split('\n'):
        if line.startswith("TARGET_PROJECT_PATH="):
            if line.split('=')[1].strip():
                target_project_path_set = True
            break
    
    if not target_project_path_set:
        pytest.fail("   [FAIL] TARGET_PROJECT_PATH не установлен в .env. Укажите абсолютный путь к целевому проекту.")
    else:
        print("   [OK] TARGET_PROJECT_PATH установлен в .env")

    # Убедимся, что контейнер не запущен от предыдущих сессий
    run_docker_compose_command(["down", "-v", "--remove-orphans"], timeout=120)
    
    # 2. Сборка образа gemini-agent
    print("\n2. Сборка образа gemini-agent:")
    build_result = run_docker_compose_command(["build"], timeout=300)
    if build_result.returncode != 0:
        pytest.fail(f"   [FAIL] Ошибка при сборке образа gemini-agent: {build_result.stderr}")
    print("   [OK] Образ gemini-agent успешно собран.")

    # 3. Запуск контейнера gemini-agent
    print("\n3. Запуск контейнера gemini-agent:")
    up_result = run_docker_compose_command(["up", "-d"])
    if up_result.returncode != 0:
        pytest.fail(f"   [FAIL] Ошибка при запуске контейнера gemini-agent: {up_result.stderr}")
    print("   [OK] Контейнер gemini-agent запущен.")

    # Даем контейнеру время на полную инициализацию
    time.sleep(10) 
    
    # Проверка, что контейнер действительно запущен
    ps_result = run_docker_compose_command(["ps", "-q", GEMINI_CONTAINER_NAME])
    if not ps_result.stdout.strip():
        pytest.fail(f"   [FAIL] Контейнер {GEMINI_CONTAINER_NAME} не запущен после 'up -d'. Логи:\n{run_docker_compose_command(['logs', GEMINI_CONTAINER_NAME]).stdout}")
    print(f"   [OK] Контейнер {GEMINI_CONTAINER_NAME} подтвержден как запущенный.")

    yield

    print("\nTeardown: Остановка и удаление контейнера gemini-agent...")
    down_result = run_docker_compose_command(["down", "-v", "--remove-orphans"])
    if down_result.returncode != 0:
        print(f"   [WARNING] Ошибка при остановке контейнера gemini-agent: {down_result.stderr}")
    print("   [OK] Контейнер gemini-agent остановлен и удален.")

def test_gemini_agent_version():
    """Тест: Проверка импортируемости google.generativeai внутри контейнера gemini-agent"""
    print("\nTest: Проверка импортируемости google.generativeai...")
    
    version_command = 'python -c "import google.generativeai as genai; print(\'google.generativeai installed\')"'
    result = run_docker_compose_command(["exec", GEMINI_CONTAINER_NAME, "/bin/bash", "-c", version_command])
    
    if result.returncode == 0 and "google.generativeai installed" in result.stdout:
        print(f"   [OK] google.generativeai успешно импортирован.")
    else:
        pytest.fail(f"   [FAIL] Не удалось импортировать google.generativeai. "
                    f"Stdout: {result.stdout}, Stderr: {result.stderr}")

@pytest.mark.skip(reason="No longer relevant after switching to API key authentication, which doesn't use GOOGLE_APPLICATION_CREDENTIALS for this API.")
def test_gemini_agent_google_credentials_env():
    """Тест: Проверка, что переменная окружения GOOGLE_APPLICATION_CREDENTIALS установлена внутри контейнера"""
    print("\nTest: Проверка GOOGLE_APPLICATION_CREDENTIALS...")
    
    env_check_command = 'printenv GOOGLE_APPLICATION_CREDENTIALS'
    result = run_docker_compose_command(["exec", GEMINI_CONTAINER_NAME, "/bin/bash", "-c", env_check_command])
    
    if result.returncode == 0 and "/root/.gemini/oauth_creds.json" in result.stdout.strip():
        print(f"   [OK] GOOGLE_APPLICATION_CREDENTIALS установлена: {result.stdout.strip()}")
    else:
        pytest.fail(f"   [FAIL] GOOGLE_APPLICATION_CREDENTIALS не установлена или имеет неверное значение. "
                    f"Stdout: {result.stdout}, Stderr: {result.stderr}")

def test_gemini_agent_file_creation():
    """Тест: Проверка создания файла в смонтированной директории проекта"""
    print("\nTest: Проверка создания файла в смонтированной директории...")
    
    project_dir = get_project_dir()
    if not project_dir:
        pytest.fail("TARGET_PROJECT_PATH (PROJECT_DIR) не установлен. Невозможно проверить создание файла.")

    test_filename = "gemini_test_file.txt"
    test_content = "This is a test file created by gemini-agent."
    
    # Команда для создания файла внутри контейнера
    create_file_command = f'echo "{test_content}" > /workspace/{test_filename}'
    result = run_docker_compose_command(["exec", GEMINI_CONTAINER_NAME, "/bin/bash", "-c", create_file_command])
    
    if result.returncode == 0:
        print(f"   [OK] Команда создания файла '{test_filename}' выполнена успешно внутри контейнера.")
        
        # Проверка файла на хост-системе
        host_test_file_path = Path(project_dir) / test_filename
        
        # Даем небольшую задержку для синхронизации файловых систем, если необходимо
        time.sleep(1) 

        if host_test_file_path.exists():
            content_on_host = host_test_file_path.read_text(encoding='utf-8').strip()
            if content_on_host == test_content:
                print(f"   [OK] Файл '{test_filename}' найден на хосте с правильным содержимым.")
            else:
                pytest.fail(f"   [FAIL] Содержимое файла '{test_filename}' на хосте не соответствует. "
                            f"Ожидалось: '{test_content}', Получено: '{content_on_host}'")
            # Удаляем тестовый файл
            host_test_file_path.unlink()
        else:
            pytest.fail(f"   [FAIL] Файл '{test_filename}' не найден на хосте по пути: {host_test_file_path}")
    else:
        pytest.fail(f"   [FAIL] Ошибка при выполнении команды создания файла внутри контейнера. "
                    f"Stdout: {result.stdout}, Stderr: {result.stderr}")

def test_gemini_agent_create_todo_file_via_instruction():
    """
    Тест: Проверка создания файла 'test_todo.md' в каталоге 'docs'
    внутри контейнера с проверкой контрольной фразы.
    """
    print("\nTest: Создание файла 'test_todo.md' в 'docs' с контрольной фразой...")
    
    project_dir_host = Path(get_project_dir())
    print(f"   Debug: project_dir_host: {project_dir_host}")
    
    # Ensure the docs directory exists on the host for cleanup purposes
    docs_dir_host = project_dir_host / "docs"
    print(f"   Debug: docs_dir_host (on host): {docs_dir_host}")
    docs_dir_host.mkdir(parents=True, exist_ok=True) # Create if not exists
    
    test_filename = "test_todo.md"
    control_phrase = "Файл todo успешно создан"
    
    # Instruction from the user, formatted to be passed to the mock script
    user_instruction = (
        "Создай в каталоге docs файл 'test_todo.md' зафиксируй в файле план развития проекта на ближайшие 2дня. "
        "тезичсно опиши пункты в конце файла напиши 'Файл todo успешно создан'"
    )
    # Command to be executed inside the container, invoking the real gemini_agent_cli.py
    create_command = (
        f'python /usr/local/bin/gemini_agent_cli.py '
        f'"{user_instruction}" '
        f'/workspace/docs/{test_filename} '
        f'"{control_phrase}" '
        f'--project_path /workspace' # Pass the mounted project path to the agent for context
    )
    print(f"   Debug: Command executed inside container: {create_command}")
    
    result = run_docker_compose_command(["exec", GEMINI_CONTAINER_NAME, "/bin/bash", "-c", create_command])
    
    if result.returncode == 0:
        print(f"   [OK] Команда создания файла '{test_filename}' выполнена успешно внутри контейнера.")
        
        host_test_file_path = docs_dir_host / test_filename
        print(f"   Debug: Expected file path on host: {host_test_file_path}")
        
        # Give a small delay for file system synchronization
        time.sleep(2) 

        if host_test_file_path.exists():
            content_on_host = host_test_file_path.read_text(encoding='utf-8').strip()
            print(f"   Debug: Content read from host file: '{content_on_host}'")
            if control_phrase in content_on_host:
                print(f"   [OK] Файл '{test_filename}' найден на хосте и содержит контрольную фразу.")
            else:
                pytest.fail(f"   [FAIL] Файл '{test_filename}' на хосте не содержит контрольную фразу. "
                            f"Содержимое: '{content_on_host}'")
            
            # Cleanup: Remove the test file
            # host_test_file_path.unlink()
            # If docs_dir_host is empty after deleting the file, remove it
            # if docs_dir_host.exists() and not any(docs_dir_host.iterdir()):
            #    docs_dir_host.rmdir()
        else:
            pytest.fail(f"   [FAIL] Файл '{test_filename}' не найден на хосте по пути: {host_test_file_path}. Directory exists: {docs_dir_host.exists()}")
    else:
        pytest.fail(f"   [FAIL] Ошибка при выполнении команды создания файла внутри контейнера. "
                    f"Stdout: {result.stdout}, Stderr: {result.stderr}")

def test_gemini_agent_api_key_env():
    """Тест: Проверка, что переменная окружения GOOGLE_API_KEY установлена внутри контейнера"""
    print("\nTest: Проверка GOOGLE_API_KEY...")
    
    env_check_command = 'printenv GOOGLE_API_KEY'
    result = run_docker_compose_command(["exec", GEMINI_CONTAINER_NAME, "/bin/bash", "-c", env_check_command])
    
    if result.returncode == 0 and result.stdout.strip():
        print(f"   [OK] GOOGLE_API_KEY установлена: {result.stdout.strip()[:5]}...") # Print first 5 chars for privacy
    else:
        pytest.fail(f"   [FAIL] GOOGLE_API_KEY не установлена или имеет неверное значение. "
                    f"Stdout: {result.stdout}, Stderr: {result.stderr}")

