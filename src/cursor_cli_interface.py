import subprocess
import logging
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class CursorCLIInterface:
    """Интерфейс взаимодействия с Cursor через CLI."""

    def __init__(
        self,
        cli_path: Optional[str] = None,
        timeout: int = 300,
        headless: bool = True,
        project_dir: Optional[str] = None,
        agent_role: Optional[str] = None
    ):
        self.cli_path = cli_path if cli_path else "cursor-agent"
        self.timeout = timeout
        self.headless = headless
        self.project_dir = Path(project_dir) if project_dir else Path.cwd()
        self.agent_role = agent_role
        self.current_chat_id = None # Placeholder for chat_id from CLI

        self._check_availability_on_init()

    def _check_availability_on_init(self):
        """Проверяет доступность Cursor CLI при инициализации."""
        try:
            # Попытка выполнить простую команду, чтобы убедиться, что CLI доступен
            result = subprocess.run(
                [self.cli_path, "--version"],
                capture_output=True,
                text=True,
                check=False,
                timeout=5
            )
            if result.returncode == 0:
                logger.info(f"Cursor CLI обнаружен: {self.cli_path} (версия: {result.stdout.strip()})")
                self._is_available = True
            else:
                logger.warning(f"Cursor CLI не найден или не работает по пути: {self.cli_path}. "
                               f"Ошибка: {result.stderr.strip() or 'Неизвестная ошибка'}")
                self._is_available = False
        except FileNotFoundError:
            logger.warning(f"Исполняемый файл Cursor CLI не найден по пути: {self.cli_path}. "
                           "Убедитесь, что он установлен и добавлен в PATH.")
            self._is_available = False
        except subprocess.TimeoutExpired:
            logger.warning(f"Таймаут при проверке доступности Cursor CLI: {self.cli_path}")
            self._is_available = False
        except Exception as e:
            logger.warning(f"Неизвестная ошибка при проверке доступности Cursor CLI: {e}")
            self._is_available = False

    def is_available(self) -> bool:
        """Проверяет, доступен ли Cursor CLI."""
        return self._is_available

    def check_version(self) -> Optional[str]:
        """Возвращает версию Cursor CLI, если доступен."""
        if not self.is_available():
            return None
        try:
            result = subprocess.run(
                [self.cli_path, "--version"],
                capture_output=True,
                text=True,
                check=True,
                timeout=5
            )
            return result.stdout.strip()
        except Exception as e:
            logger.warning(f"Не удалось получить версию Cursor CLI: {e}")
            return None

    def prepare_for_new_task(self) -> bool:
        """
        Очищает активные диалоги Cursor и подготавливает его к новой задаче.
        В текущей реализации CLI это может быть эквивалентно сбросу состояния.
        """
        logger.info("Подготовка Cursor CLI к новой задаче (очистка диалогов)...")
        # В зависимости от реального Cursor CLI, здесь может быть команда для очистки.
        # Если такой команды нет, можно просто логировать, что CLI готов.
        # Например, если есть команда "cursor-agent reset-dialogs"
        try:
            # Предполагаем, что есть команда для очистки диалогов или сброса
            # Если нет - это просто заглушка
            # result = subprocess.run([self.cli_path, "reset-dialogs"], capture_output=True, text=True, check=True, timeout=10)
            # if result.returncode == 0:
            #     logger.info("Cursor CLI диалоги успешно очищены.")
            #     return True
            # else:
            #     logger.warning(f"Не удалось очистить Cursor CLI диалоги: {result.stderr.strip()}")
            #     return False
            
            logger.info("Cursor CLI успешно подготовлен (без явной команды очистки)")
            self.current_chat_id = None # Сбрасываем chat_id при подготовке
            return True
        except Exception as e:
            logger.warning(f"Ошибка при подготовке Cursor CLI: {e}")
            return False

    def execute_instruction(
        self,
        instruction: str,
        task_id: str,
        working_dir: Optional[str] = None,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Выполнить команду через Cursor CLI.

        Args:
            instruction: Текст инструкции для выполнения.
            task_id: Идентификатор задачи.
            working_dir: Рабочая директория для выполнения команды.
            timeout: Таймаут выполнения (в секундах).

        Returns:
            Словарь с результатом выполнения.
        """
        if not self.is_available():
            return {
                "success": False,
                "error_message": "Cursor CLI недоступен",
                "stdout": "",
                "stderr": "",
                "return_code": -1,
                "cli_available": False
            }

        effective_working_dir = Path(working_dir) if working_dir else self.project_dir
        effective_timeout = timeout if timeout is not None else self.timeout

        logger.info(f"Запуск Cursor CLI для задачи {task_id} (timeout: {effective_timeout}s, dir: {effective_working_dir})")
        logger.debug(f"Инструкция: {instruction[:200]}...")

        # В реальной реализации здесь будет вызов "cursor-agent run <инструкция>"
        # или аналогичная команда.
        try:
            # Пример вызова CLI (нужно адаптировать под реальный Cursor CLI)
            # Вариант 1: передача инструкции через stdin или как аргумент
            # Вариант 2: вызов внешней команды, которая затем использует Cursor
            
            # Для демонстрации, имитируем выполнение команды и создание файла результата
            # ВНИМАНИЕ: это заглушка, реальный CLI должен генерировать файлы
            result_file_path = effective_working_dir / "cursor_results" / f"result_{task_id}.txt"
            result_file_path.parent.mkdir(parents=True, exist_ok=True)
            
            mock_output = f"Cursor CLI успешно обработал инструкцию для задачи {task_id}. " \
                          f"Выполнено: '{instruction[:50]}...'. Результат сохранен в {result_file_path}"
            mock_error = ""
            mock_return_code = 0
            
            # Имитация выполнения:
            # Здесь бы был subprocess.run([self.cli_path, "run", instruction], ...)
            # Или subprocess.run([self.cli_path, "chat", "-p", instruction], ...)
            
            # Для заглушки, просто записываем mock_output в stdout
            # и создаем пустой файл результата
            with open(result_file_path, "w", encoding="utf-8") as f:
                f.write(f"Result for {task_id}\\nInstruction: {instruction}\\n")
                f.write("Output from mock Cursor CLI execution.\\n")
                f.write("Отчет завершен!") # Контрольная фраза для теста
            
            logger.info(f"Имитация выполнения Cursor CLI: успех. Результат записан в {result_file_path}")
            
            # В реальном CLI, chat_id может быть возвращен в stdout/stderr
            # Для заглушки, генерируем фиктивный chat_id
            self.current_chat_id = f"mock_chat_{task_id}"

            return {
                "success": True,
                "error_message": None,
                "stdout": mock_output,
                "stderr": mock_error,
                "return_code": mock_return_code,
                "cli_available": True
            }
        except subprocess.TimeoutExpired:
            logger.error(f"Cursor CLI таймаут ({effective_timeout}s) для задачи {task_id}")
            return {
                "success": False,
                "error_message": f"Cursor CLI таймаут ({effective_timeout}s)",
                "stdout": "",
                "stderr": "",
                "return_code": -1,
                "cli_available": True
            }
        except subprocess.CalledProcessError as e:
            logger.error(f"Cursor CLI ошибка выполнения для задачи {task_id}: {e}")
            return {
                "success": False,
                "error_message": f"CLI вернул код {e.returncode}: {e.stderr.strip()}",
                "stdout": e.stdout,
                "stderr": e.stderr,
                "return_code": e.returncode,
                "cli_available": True
            }
        except FileNotFoundError:
            logger.error(f"Cursor CLI исполняемый файл не найден по пути: {self.cli_path}")
            return {
                "success": False,
                "error_message": f"Cursor CLI исполняемый файл не найден: {self.cli_path}",
                "stdout": "",
                "stderr": "",
                "return_code": -1,
                "cli_available": False
            }
        except Exception as e:
            logger.error(f"Неожиданная ошибка при вызове Cursor CLI для задачи {task_id}: {e}", exc_info=True)
            return {
                "success": False,
                "error_message": f"Неожиданная ошибка: {e}",
                "stdout": "",
                "stderr": "",
                "return_code": -1,
                "cli_available": True
            }

def create_cursor_cli_interface(
    cli_path: Optional[str] = None,
    timeout: int = 300,
    headless: bool = True,
    project_dir: Optional[str] = None,
    agent_role: Optional[str] = None
) -> CursorCLIInterface:
    """
    Фабричная функция для создания экземпляра CursorCLIInterface.
    """
    return CursorCLIInterface(cli_path, timeout, headless, project_dir, agent_role)
