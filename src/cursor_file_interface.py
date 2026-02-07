from pathlib import Path
import time
from typing import List

class CursorFileInterface:
    """Интерфейс взаимодействия с Cursor через файлы."""

    def __init__(self, commands_dir: Path, results_dir: Path):
        self.commands_dir = commands_dir
        self.results_dir = results_dir
        self.commands_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def send_instruction(self, instruction: str, task_id: str) -> Path:
        """Отправить инструкцию через файл."""
        file_path = self.commands_dir / f"instruction_{task_id}.txt"
        file_path.write_text(instruction, encoding="utf-8")
        return file_path

    def wait_for_result(self, task_id: str, timeout: int = 300) -> str:
        """Дождаться результата от Cursor."""
        result_path = self.results_dir / f"result_{task_id}.txt"
        start_time = time.time()
        while not result_path.exists():
            if time.time() - start_time > timeout:
                raise TimeoutError(f"Таймаут ожидания файла результата для задачи {task_id}")
            time.sleep(1)  # Проверяем каждую секунду
        
        # Once the file exists, read its content.
        # ReportWatcher will handle control phrases.
        return result_path.read_text(encoding="utf-8")
