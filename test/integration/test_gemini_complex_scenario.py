"""
Тест сложного многоэтапного сценария для Gemini CLI в Docker
"""

import subprocess
import time
from pathlib import Path

import pytest

from test.test_utils import get_project_dir

# Определение имени контейнера и файла docker-compose
GEMINI_CONTAINER_NAME = "gemini-agent"
GEMINI_COMPOSE_FILE = Path(__file__).parent.parent.parent / "docker" / "docker-compose.gemini.yml"


def run_docker_compose_command(command_args, timeout=600):  # Increased timeout for complex tasks
    cmd = [
        "docker",
        "compose",
        "-f",
        str(GEMINI_COMPOSE_FILE),
        "--env-file",
        "./.env",
    ] + command_args
    print(f"Executing: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
    if result.returncode != 0:
        print(f"Error Stdout: {result.stdout}")
        print(f"Error Stderr: {result.stderr}")
    return result


@pytest.fixture(scope="module", autouse=True)
def setup_gemini_agent():
    print("\nSetting up gemini-agent for complex test...")

    # Check .env
    env_file = Path(__file__).parent.parent.parent / ".env"
    if not env_file.exists():
        pytest.fail(".env file not found")

    # Ensure container is running (idempotent)
    run_docker_compose_command(["up", "-d"])

    # Wait for container
    time.sleep(5)

    # Check status
    ps_result = run_docker_compose_command(["ps", "-q", GEMINI_CONTAINER_NAME])
    if not ps_result.stdout.strip():
        pytest.fail(f"Container {GEMINI_CONTAINER_NAME} is not running")

    yield

    # Optional teardown or leave it running for inspection
    # run_docker_compose_command(["down"])


def test_complex_multi_stage_task():
    """
    Тест: Выполнение сложной многоэтапной задачи:
    1. Создать структуру директорий для новой фичи
    2. Создать файл реализации
    3. Создать файл теста
    4. Запустить тест
    """
    print("\nTest: Starting complex multi-stage task...")

    project_dir_host = Path(get_project_dir())

    # Define paths
    feature_dir = "src/features/complex_test"
    impl_file = f"{feature_dir}/calculator.py"
    test_file = f"{feature_dir}/test_calculator.py"
    report_file = "docs/results/complex_test_result.md"

    # Clean up before test
    feature_dir_host = project_dir_host / "src" / "features" / "complex_test"
    import shutil

    if feature_dir_host.exists():
        shutil.rmtree(feature_dir_host)

    # Complex instruction
    instruction = (
        f"Выполни многоэтапную задачу:\n"
        f"1. Создай директорию '{feature_dir}'.\n"
        f"2. В этой директории создай файл 'calculator.py' с классом Calculator, который имеет методы add, subtract, multiply, divide.\n"
        f"3. Создай файл 'test_calculator.py' в той же директории с тестами для этого класса (используй unittest).\n"
        f"4. Запусти этот тест используя python и сохрани вывод.\n"
        f"5. Создай отчет в '{report_file}' с результатами запуска тестов.\n"
        f"В конце отчета напиши 'Задача успешно выполнена!'"
    )

    control_phrase = "Задача успешно выполнена!"

    # Command execution
    # We use a long timeout because this involves multiple steps and delays
    start_time = time.time()

    create_command = (
        f"python /usr/local/bin/gemini_agent_cli.py "
        f'"{instruction}" '
        f"/workspace/{report_file} "
        f'"{control_phrase}" '
        f"--project_path /workspace"
    )

    print("Executing instruction in container...")
    # Using Popen to stream output
    process = subprocess.Popen(
        [
            "docker",
            "compose",
            "-f",
            str(GEMINI_COMPOSE_FILE),
            "--env-file",
            "./.env",
            "exec",
            GEMINI_CONTAINER_NAME,
            "/bin/bash",
            "-c",
            create_command,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",  # Force utf-8
    )

    stdout_lines = []
    stderr_lines = []

    # Simple streaming loop
    while True:
        output = process.stdout.readline()
        if output == "" and process.poll() is not None:
            break
        if output:
            print(output.strip())
            stdout_lines.append(output)

        err = process.stderr.readline()
        if err:
            print(f"STDERR: {err.strip()}")
            stderr_lines.append(err)

    return_code = process.poll()

    elapsed_time = time.time() - start_time
    print(f"Execution took {elapsed_time:.2f} seconds")

    stdout = "".join(stdout_lines)
    stderr = "".join(stderr_lines)

    if return_code != 0:
        pytest.fail(f"Agent execution failed with return code {return_code}")

    # Verify results on host
    report_path_host = project_dir_host / report_file

    if not report_path_host.exists():
        pytest.fail(f"Report file not found at {report_path_host}")

    content = report_path_host.read_text(encoding="utf-8")
    print(f"\nReport Content:\n{content}")

    if control_phrase not in content:
        pytest.fail("Control phrase not found in report")

    # Verify created files
    if not (project_dir_host / impl_file).exists():
        pytest.fail(f"Implementation file {impl_file} not found")

    if not (project_dir_host / test_file).exists():
        pytest.fail(f"Test file {test_file} not found")

    print("\n✅ Complex multi-stage test passed!")
