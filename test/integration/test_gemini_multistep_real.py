import logging
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

# Добавляем корень проекта в sys.path
sys.path.append(str(Path(__file__).parent.parent))

from src.agents.gemini_agent.gemini_cli_interface import create_gemini_cli_interface

# Настройка логирования
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("MultiStepTest")


def test_multistep_work():
    load_dotenv()

    # Параметры теста
    project_dir = os.getcwd()
    container_name = "gemini-agent"  # Имя контейнера из docker-compose.gemini.yml

    logger.info("Инициализация Gemini CLI Interface (Docker mode)...")
    interface = create_gemini_cli_interface(
        project_dir=project_dir,
        container_name=container_name,
        timeout=600,  # Увеличиваем таймаут для сложной задачи
    )

    if not interface.is_available():
        logger.error("Gemini CLI не доступен. Убедитесь, что Docker запущен и образ собран.")
        return

    # Список шагов для сложной задачи
    steps = [
        {
            "id": "step_1",
            "instruction": "Создай в корне проекта файл 'multistep_test_1.py', который содержит класс 'Calculator' с методом 'add(a, b)'.",
        },
        {
            "id": "step_2",
            "instruction": "Обнови файл 'multistep_test_1.py', добавив в класс 'Calculator' метод 'multiply(a, b)' и docstring к классу.",
        },
        {
            "id": "step_3",
            "instruction": "Создай файл 'multistep_test_2.py', который импортирует 'Calculator' из 'multistep_test_1' и выполняет вычисления 2+2 и 3*3, выводя результат на экран.",
        },
    ]

    stats = []
    session_id = f"test_session_{int(time.time())}"

    logger.info(f"Запуск многоэтапного теста. Session ID: {session_id}")

    for i, step in enumerate(steps):
        logger.info(f"\n--- ШАГ {i+1}: {step['id']} ---")
        start_time = time.time()

        result = interface.execute_instruction(
            instruction=step["instruction"],
            task_id=step["id"],
            session_id=session_id,  # Используем один и тот же session_id для поддержания контекста
        )

        duration = time.time() - start_time
        success = result.get("success", False)

        stats.append(
            {
                "step": i + 1,
                "id": step["id"],
                "duration": duration,
                "success": success,
                "error": result.get("error_message"),
            }
        )

        if success:
            logger.info(f"✅ Шаг {i+1} выполнен за {duration:.2f} сек")
        else:
            logger.error(f"❌ Шаг {i+1} провален: {result.get('error_message')}")
            # В реальном сценарии мы могли бы попробовать продолжить или остановиться

    # Вывод статистики
    logger.info("\n=== СТАТИСТИКА ТЕСТА ===")
    total_duration = 0
    successful_steps = 0

    for stat in stats:
        total_duration += stat["duration"]
        if stat["success"]:
            successful_steps += 1

        status = "OK" if stat["success"] else "FAIL"
        logger.info(f"Шаг {stat['step']} ({stat['id']}): {status} | Время: {stat['duration']:.2f}s")

    logger.info(f"\nВсего шагов: {len(steps)}")
    logger.info(f"Успешно: {successful_steps}")
    logger.info(f"Общее время: {total_duration:.2f} сек")

    # Очистка (необязательно)
    # logger.info("\nОчистка созданных файлов...")
    # for f in ["multistep_test_1.py", "multistep_test_2.py"]:
    #     if Path(f).exists():
    #         Path(f).unlink()


if __name__ == "__main__":
    test_multistep_work()
