"""
Модуль логирования задач с поддержкой отдельных файлов для каждой задачи
"""

import logging
import sys
import platform
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum

# Определяем, нужно ли использовать эмодзи (отключаем на Windows из-за проблем с кодировкой cp1251)
USE_EMOJI = platform.system() != 'Windows'


def emoji(emoji_char: str, fallback: str = '') -> str:
    """
    Возвращает эмодзи или текстовую альтернативу в зависимости от платформы
    
    Args:
        emoji_char: Символ эмодзи
        fallback: Текстовая альтернатива (если пустая, возвращается пустая строка)
    
    Returns:
        Эмодзи или альтернативный текст
    """
    return emoji_char if USE_EMOJI else fallback


# ANSI цветовые коды
class Colors:
    """ANSI цветовые коды для консоли"""
    RESET = '\033[0m'
    BOLD = '\033[1m'
    
    # Основные цвета
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # Яркие цвета
    BRIGHT_BLACK = '\033[90m'
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    BRIGHT_WHITE = '\033[97m'
    
    @staticmethod
    def colorize(text: str, color: str) -> str:
        """Раскрасить текст"""
        return f"{color}{text}{Colors.RESET}"


class TaskPhase(Enum):
    """Фазы выполнения задачи"""
    INITIALIZATION = "Инициализация"
    TASK_ANALYSIS = "Анализ задачи"
    INSTRUCTION_GENERATION = "Генерация инструкции"
    CURSOR_EXECUTION = "Выполнение через Cursor"
    WAITING_RESULT = "Ожидание результата"
    RESULT_PROCESSING = "Обработка результата"
    COMPLETION = "Завершение"
    ERROR = "Ошибка"


class TaskLogger:
    """
    Логгер для отдельной задачи
    
    Создает отдельный лог-файл для каждой задачи и выводит информацию в консоль
    """
    
    def __init__(self, task_id: str, task_name: str, log_dir: Path = Path("logs")):
        """
        Инициализация логгера задачи
        
        Args:
            task_id: Уникальный идентификатор задачи
            task_name: Название задачи
            log_dir: Директория для логов
        """
        self.task_id = task_id
        self.task_name = task_name
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Очищаем старые логи задач (оставляем только последние 20)
        self._cleanup_old_logs(max_logs=20)
        
        # Создаем имя файла лога на основе task_id и timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.log_file = self.log_dir / f"task_{task_id}_{timestamp}.log"
        
        # Создаем отдельный logger для этой задачи
        self.logger = logging.getLogger(f"task.{task_id}")
        self.logger.setLevel(logging.DEBUG)
        self.logger.propagate = False  # Не передаем в root logger
        
        # Удаляем существующие handlers если есть
        self.logger.handlers.clear()
        
        # File handler - детальное логирование
        file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)
        
        # Console handler - краткий вывод с временными метками
        # Используем UTF-8 для Windows консоли
        import io
        if sys.platform == 'win32':
            # Для Windows используем UTF-8 wrapper для stdout
            console_stream = io.TextIOWrapper(
                sys.stdout.buffer,
                encoding='utf-8',
                errors='replace',
                line_buffering=True
            )
        else:
            console_stream = sys.stdout
        
        console_handler = logging.StreamHandler(console_stream)
        console_handler.setLevel(logging.INFO)
        # Добавляем время в формат консоли
        console_formatter = logging.Formatter('%(asctime)s - %(message)s', datefmt='%H:%M:%S')
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        # Счетчики для статистики
        self.instruction_count = 0
        self.current_phase = None
        self.current_stage = None
        self.start_time = datetime.now()
        
        # Логируем начало
        self._log_header()
    
    def _cleanup_old_logs(self, max_logs: int = 20):
        """
        Очистка старых лог-файлов задач, оставляя только последние max_logs файлов
        
        Args:
            max_logs: Максимальное количество лог-файлов задач для хранения
        """
        try:
            # Получаем все лог-файлы задач
            log_files = sorted(
                self.log_dir.glob("task_*.log"),
                key=lambda p: p.stat().st_mtime,
                reverse=True  # Сортируем от новых к старым
            )
            
            # Удаляем старые логи, оставляя только max_logs последних
            if len(log_files) > max_logs:
                for old_log in log_files[max_logs:]:
                    try:
                        old_log.unlink()
                    except Exception as e:
                        # Игнорируем ошибки удаления отдельных файлов
                        pass
        except Exception as e:
            # Игнорируем ошибки очистки - это не критично
            pass
    
    def log_info(self, message: str):
        """Логировать информационное сообщение"""
        self.logger.info(Colors.colorize(f"ℹ️  {message}", Colors.BRIGHT_BLUE))

    def log_warning(self, message: str):
        """Логировать предупреждение"""
        self.logger.warning(Colors.colorize(f"⚠️  {message}", Colors.BRIGHT_YELLOW))

    def log_error(self, message: str, exception: Optional[Exception] = None):
        """Логировать ошибку"""
        self.logger.error(Colors.colorize(f"❌ {message}", Colors.BRIGHT_RED))
        if exception:
            self.logger.error(Colors.colorize(f"   Тип: {type(exception).__name__}", Colors.RED))
            self.logger.error(Colors.colorize(f"   Детали: {str(exception)}", Colors.RED))
    
    def _log_header(self):
        """Записать заголовок лога"""
        # Для файла - полный заголовок
        file_header = f"""
{'=' * 80}
ЗАДАЧА: {self.task_name}
ID: {self.task_id}
НАЧАЛО: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}
{'=' * 80}
"""
        # Записываем в файл через debug (чтобы не попало в консоль через info)
        for handler in self.logger.handlers:
            if isinstance(handler, logging.FileHandler):
                handler.stream.write(file_header)
                handler.flush()
        
        # В консоль - компактный заголовок с цветом
        task_name_short = self.task_name[:70] + "..." if len(self.task_name) > 70 else self.task_name
        console_header = Colors.colorize(
            f"📋 ЗАДАЧА: {task_name_short} | ID: {self.task_id}",
            Colors.BOLD + Colors.BRIGHT_YELLOW
        )
        self.logger.info(console_header)
        
        # В файл добавляем дополнительную информацию
        self.logger.debug(f"Лог файл: {self.log_file}")
    
    def set_phase(self, phase: TaskPhase, stage: Optional[int] = None, instruction_num: Optional[int] = None, task_text: Optional[str] = None):
        """
        Установить текущую фазу выполнения

        Args:
            phase: Фаза выполнения
            stage: Номер этапа (опционально)
            instruction_num: Номер инструкции (опционально)
            task_text: Текст задачи (опционально, для замены номера этапа)
        """
        self.current_phase = phase
        self.current_stage = stage

        # Формируем сообщение о фазе (без рамок, только цвет)
        if task_text and instruction_num:
            # Используем текст задачи вместо "ЭТАП"
            phase_text = f"📍 {task_text}, ИНСТРУКЦИЯ {instruction_num} - {phase.value}"
        elif stage and instruction_num:
            phase_text = f"📍 ЭТАП {stage}, ИНСТРУКЦИЯ {instruction_num} - {phase.value}"
        elif stage:
            phase_text = f"📍 ЭТАП {stage} - {phase.value}"
        elif task_text:
            phase_text = f"📍 {task_text} - {phase.value}"
        else:
            phase_text = f"📍 {phase.value}"
        
        # Цвет в зависимости от фазы
        if phase == TaskPhase.ERROR:
            color = Colors.BRIGHT_RED
        elif phase == TaskPhase.COMPLETION:
            color = Colors.BRIGHT_GREEN
        elif phase == TaskPhase.WAITING_RESULT:
            color = Colors.BRIGHT_YELLOW
        else:
            color = Colors.BRIGHT_BLUE
        
        # Используем только цветовое выделение, без разделителей
        phase_msg = Colors.colorize(phase_text, color)
        
        self.logger.info(phase_msg)
        self.logger.debug(f"Фаза изменена: {phase.value}")
    
    def log_instruction(self, instruction_num: int, instruction_text: str, task_type: str):
        """
        Логировать инструкцию
        
        Args:
            instruction_num: Номер инструкции
            instruction_text: Текст инструкции
            task_type: Тип задачи
        """
        self.instruction_count += 1
        
        # Вывод в консоль с цветом (запрос - желтый)
        instruction_header = Colors.colorize(f"📝 Инструкция {instruction_num} (тип: {task_type})", Colors.BRIGHT_MAGENTA)
        self.logger.info(instruction_header)
        
        # Показываем несколько строк инструкции (не сокращаем до 100 символов)
        # Разбиваем на строки и показываем первые 5 строк
        lines = instruction_text.split('\n')
        preview_lines = lines[:5]  # Первые 5 строк
        
        # Выделяем каждую строку инструкции желтым цветом (вопрос)
        for line in preview_lines:
            colored_line = Colors.colorize(f"   {line}", Colors.BRIGHT_YELLOW)
            self.logger.info(colored_line)
        
        # Если инструкция длиннее 5 строк, добавляем индикатор
        if len(lines) > 5:
            indicator = Colors.colorize(f"   ... (еще {len(lines) - 5} строк)", Colors.BRIGHT_BLACK)
            self.logger.info(indicator)
        
        # Полный вывод в файл
        self.logger.debug(f"\nИнструкция {instruction_num}:")
        self.logger.debug(f"Тип задачи: {task_type}")
        self.logger.debug(f"Полный текст:\n{instruction_text}")
    
    def log_cursor_response(self, response: Dict[str, Any], brief: bool = True):
        """
        Логировать Agent CLI ответ
        
        Args:
            response: Словарь с ответом от Cursor
            brief: Если True, выводить краткую информацию в консоль
        """
        success = response.get('success', False)
        
        # Вывод в консоль с цветом (ответ - зеленый для успеха)
        if brief:
            if success:
                status_icon = emoji("✅", "[OK]")
                status_text = "УСПЕШНО"
                color = Colors.BRIGHT_GREEN
            else:
                status_icon = emoji("❌", "[ERROR]")
                status_text = "ОШИБКА"
                color = Colors.BRIGHT_RED
            
            response_header = Colors.colorize(f"{status_icon} Agent CLI ответ: {status_text}", color)
            self.logger.info(response_header)
            
            # Извлекаем информацию из ответа
            stdout = response.get('stdout', '')
            stderr = response.get('stderr', '')
            
            if success:
                # Показываем первые несколько строк ответа (не сокращаем до минимума)
                if stdout:
                    # Разбиваем на строки и показываем первые 5 строк
                    stdout_lines = stdout.strip().split('\n')
                    preview_lines = stdout_lines[:5]  # Первые 5 строк
                    
                    # Выделяем каждую строку ответа зеленым цветом
                    for line in preview_lines:
                        colored_line = Colors.colorize(f"   {line}", Colors.BRIGHT_GREEN)
                        self.logger.info(colored_line)
                    
                    # Если ответ длиннее 5 строк, добавляем индикатор
                    if len(stdout_lines) > 5:
                        indicator = Colors.colorize(f"   ... (еще {len(stdout_lines) - 5} строк)", Colors.BRIGHT_BLACK)
                        self.logger.info(indicator)
                
                # Пытаемся найти информацию о созданных/измененных файлах
                created_files = self._extract_file_mentions(stdout, ['created', 'создан', 'создано'])
                modified_files = self._extract_file_mentions(stdout, ['modified', 'изменен', 'обновлен'])
                tested = 'test' in stdout.lower() or 'тест' in stdout.lower()
                
                if created_files:
                    self.logger.info(Colors.colorize(f"   📄 Создано файлов: {', '.join(created_files[:3])}", Colors.GREEN))
                if modified_files:
                    self.logger.info(Colors.colorize(f"   ✏️  Изменено файлов: {', '.join(modified_files[:3])}", Colors.YELLOW))
                if tested:
                    self.logger.info(Colors.colorize(f"   🧪 Выполнено тестирование", Colors.CYAN))
            else:
                # Для ошибок показываем больше информации
                error_msg = response.get('error_message', 'Неизвестная ошибка')
                self.logger.info(Colors.colorize(f"   Причина: {error_msg}", Colors.RED))
                
                # Показываем первые строки stderr если есть
                if stderr:
                    stderr_lines = stderr.strip().split('\n')
                    preview_lines = stderr_lines[:3]  # Первые 3 строки ошибки
                    
                    # Выделяем каждую строку ошибки красным цветом
                    for line in preview_lines:
                        colored_line = Colors.colorize(f"   {line}", Colors.RED)
                        self.logger.info(colored_line)
                    
                    if len(stderr_lines) > 3:
                        indicator = Colors.colorize(f"   ... (еще {len(stderr_lines) - 3} строк)", Colors.BRIGHT_BLACK)
                        self.logger.info(indicator)
        
        # Полный вывод в файл
        self.logger.debug("\n" + "=" * 40)
        self.logger.debug("Agent CLI ответ:")
        self.logger.debug("=" * 40)
        self.logger.debug(f"Успех: {success}")
        self.logger.debug(f"Код возврата: {response.get('return_code', 'N/A')}")
        
        if 'stdout' in response and response['stdout']:
            self.logger.debug(f"\nSTDOUT:\n{response['stdout']}")
        
        if 'stderr' in response and response['stderr']:
            self.logger.debug(f"\nSTDERR:\n{response['stderr']}")
        
        if 'error_message' in response and response['error_message']:
            self.logger.debug(f"\nОшибка: {response['error_message']}")
        
        self.logger.debug("=" * 40)
    
    def _extract_file_mentions(self, text: str, keywords: list) -> list:
        """
        Извлечь упоминания файлов из текста
        
        Args:
            text: Текст для анализа
            keywords: Ключевые слова для поиска
            
        Returns:
            Список найденных файлов
        """
        import re
        files = []
        
        # Простой паттерн для поиска путей к файлам
        # Ищем строки вида: "created file.py" или "создан test.txt"
        for keyword in keywords:
            pattern = rf'{keyword}\s+[\w\./\\-]+'
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                # Извлекаем имя файла
                parts = match.split()
                if len(parts) > 1:
                    files.append(parts[-1])
        
        return list(set(files))  # Убираем дубликаты
    
    def log_new_chat(self, chat_id: Optional[str] = None):
        """
        Логировать создание нового чата
        
        Args:
            chat_id: ID созданного чата (если доступен)
        """
        if chat_id:
            msg = Colors.colorize(f"💬 Создан новый диалог: {chat_id}", Colors.BRIGHT_CYAN)
            self.logger.info(msg)
            self.logger.debug(f"Chat ID: {chat_id}")
        else:
            msg = Colors.colorize(f"💬 Создан новый диалог", Colors.BRIGHT_CYAN)
            self.logger.info(msg)
            self.logger.debug("Chat ID не получен")
    
    def log_waiting_result(self, file_path: str, timeout: int):
        """
        Логировать ожидание результата
        
        Args:
            file_path: Путь к ожидаемому файлу
            timeout: Таймаут ожидания
        """
        # Ожидание - желтый цвет
        self.logger.info(Colors.colorize(f"{emoji('⏳', '[WAIT]')} Ожидание результата...", Colors.BRIGHT_YELLOW))
        self.logger.info(f"   Файл: {file_path}")
        self.logger.info(f"   Таймаут: {timeout}с")
        
        self.logger.debug(f"Ожидание файла результата: {file_path} (timeout: {timeout}s)")
    
    def log_result_received(self, file_path: str, wait_time: float, content_preview: str = "", execution_time: Optional[float] = None):
        """
        Логировать получение результата
        
        Args:
            file_path: Путь к полученному файлу
            wait_time: Время ожидания файла
            content_preview: Превью содержимого (опционально)
            execution_time: Время выполнения инструкции (если отличается от wait_time)
        """
        # Результат получен - зеленый цвет
        if execution_time and execution_time > wait_time:
            # Если время выполнения больше времени ожидания - показываем оба
            self.logger.info(
                Colors.colorize(
                    f"{emoji('✅', '[OK]')} Результат получен (выполнение: {execution_time:.1f}с, ожидание файла: {wait_time:.1f}с)",
                    Colors.BRIGHT_GREEN
                )
            )
        else:
            # Обычный случай - показываем только время ожидания
            self.logger.info(Colors.colorize(f"{emoji('✅', '[OK]')} Результат получен (за {wait_time:.1f}с)", Colors.BRIGHT_GREEN))
        self.logger.info(f"   Файл: {file_path}")
            
        if content_preview:
            preview = content_preview[:200] + "..." if len(content_preview) > 200 else content_preview
            self.logger.info(f"   Превью: {preview}")
        
        self.logger.debug(f"Файл результата получен: {file_path}")
        self.logger.debug(f"Время ожидания файла: {wait_time:.2f}s")
        if execution_time:
            self.logger.debug(f"Время выполнения инструкции: {execution_time:.2f}s")
        if content_preview:
            self.logger.debug(f"Содержимое:\n{content_preview}")
    
    def log_error(self, error_msg: str, exception: Optional[Exception] = None):
        """
        Логировать ошибку
        
        Args:
            error_msg: Сообщение об ошибке
            exception: Объект исключения (опционально)
        """
        # Ошибка - красный цвет
        self.logger.error(Colors.colorize(f"{emoji('❌', '[ERROR]')} ОШИБКА: {error_msg}", Colors.BRIGHT_RED))
        
        if exception:
            self.logger.error(Colors.colorize(f"   Тип: {type(exception).__name__}", Colors.RED))
            self.logger.error(Colors.colorize(f"   Детали: {str(exception)}", Colors.RED))
            self.logger.debug("Traceback:", exc_info=True)
    
    def log_completion(self, success: bool, summary: str = ""):
        """
        Логировать завершение задачи
        
        Args:
            success: Успешно ли выполнена задача
            summary: Краткое резюме
        """
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()
        
        status_icon = emoji("✅", "[OK]") if success else emoji("❌", "[ERROR]")
        status_text = "УСПЕШНО ЗАВЕРШЕНА" if success else "ЗАВЕРШЕНА С ОШИБКОЙ"
        color = Colors.BRIGHT_GREEN if success else Colors.BRIGHT_RED
        
        separator = '=' * 80
        footer_lines = [
            Colors.colorize(separator, Colors.BRIGHT_BLACK),
            Colors.colorize(f"{status_icon} ЗАДАЧА {status_text}", color),
            f"Время выполнения: {duration:.1f}с",
            f"Инструкций выполнено: {self.instruction_count}"
        ]
        
        if summary:
            footer_lines.append(f"Резюме: {summary}")
        
        footer_lines.append(Colors.colorize(separator, Colors.BRIGHT_BLACK))
        
        footer = '\n'.join(footer_lines)
        
        self.logger.info(footer)
        self.logger.debug(f"Задача завершена. Успех: {success}, Длительность: {duration:.2f}s")
    
    def log_info(self, message: str):
        """Логировать информационное сообщение"""
        self.logger.info(Colors.colorize(f"ℹ️  {message}", Colors.BRIGHT_BLUE))
        self.logger.debug(message)
    
    def log_warning(self, message: str):
        """Логировать предупреждение"""
        self.logger.warning(Colors.colorize(f"⚠️  {message}", Colors.BRIGHT_YELLOW))
        self.logger.debug(f"Предупреждение: {message}")
    
    def log_debug(self, message: str):
        """Логировать отладочное сообщение (только в файл)"""
        self.logger.debug(message)
    
    def close(self):
        """Закрыть логгер и освободить ресурсы"""
        for handler in self.logger.handlers:
            handler.close()
            self.logger.removeHandler(handler)


class ServerLogger:
    """
    Логгер для сервера (общие операции)
    """
    
    def __init__(self, log_dir: Path = Path("logs")):
        """
        Инициализация логгера сервера
        
        Args:
            log_dir: Директория для логов
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Используем существующий logger
        self.logger = logging.getLogger(__name__)
    
    def log_initialization(self, config: Dict[str, Any]):
        """
        Логировать инициализацию сервера
        
        Args:
            config: Конфигурация сервера
        """
        separator = '=' * 80
        cli_status = (emoji('✅', '[OK]') + ' Доступен') if config.get('cursor_cli_available') else (emoji('❌', '[X]') + ' Недоступен')
        
        header_lines = [
            Colors.colorize(separator, Colors.BRIGHT_BLACK),
            Colors.colorize("CODE AGENT SERVER", Colors.BOLD + Colors.BRIGHT_CYAN),
            Colors.colorize(separator, Colors.BRIGHT_BLACK),
            Colors.colorize(emoji("🚀", ">>>") + " ИНИЦИАЛИЗАЦИЯ", Colors.BRIGHT_GREEN),
            f"Проект: {config.get('project_dir', 'N/A')}",
            f"Документация: {config.get('docs_dir', 'N/A')}",
            f"Cursor CLI: {cli_status}",
            Colors.colorize(separator, Colors.BRIGHT_BLACK)
        ]
        
        header = '\n'.join(header_lines)
        self.logger.info(header)
    
    def log_iteration_start(self, iteration: int, pending_tasks: int):
        """
        Логировать начало итерации
        
        Args:
            iteration: Номер итерации
            pending_tasks: Количество ожидающих задач
        """
        separator = '-' * 80
        msg_lines = [
            Colors.colorize(separator, Colors.BRIGHT_BLACK),
            Colors.colorize(f"{emoji('🔄', '[ITER]')} ИТЕРАЦИЯ {iteration}", Colors.BRIGHT_CYAN),
            f"Ожидающих задач: {pending_tasks}",
            Colors.colorize(separator, Colors.BRIGHT_BLACK)
        ]
        
        msg = '\n'.join(msg_lines)
        self.logger.info(msg)
    
    def log_task_start(self, task_number: int, total_tasks: int, task_name: str):
        """
        Логировать начало выполнения задачи
        
        Args:
            task_number: Номер задачи
            total_tasks: Общее количество задач
            task_name: Название задачи
        """
        # Используем цветовое выделение вместо рамок
        task_text = f"ЗАДАЧА {task_number}/{total_tasks}: {task_name[:60]}"
        
        msg = Colors.colorize(task_text, Colors.BOLD + Colors.BRIGHT_YELLOW)
        self.logger.info(msg)
    
    def log_server_shutdown(self, reason: str = "Остановка пользователем"):
        """
        Логировать остановку сервера
        
        Args:
            reason: Причина остановки
        """
        separator = '=' * 80
        footer_lines = [
            Colors.colorize(separator, Colors.BRIGHT_BLACK),
            Colors.colorize("🛑 СЕРВЕР ОСТАНОВЛЕН", Colors.BRIGHT_RED),
            f"Причина: {reason}",
            Colors.colorize(separator, Colors.BRIGHT_BLACK)
        ]
        
        footer = '\n'.join(footer_lines)
        self.logger.info(footer)
    
    def log_info(self, message: str):
        """
        Логировать информационное сообщение

        Args:
            message: Текст сообщения
        """
        self.logger.info(Colors.colorize(f"ℹ️  {message}", Colors.BRIGHT_BLUE))
    
    def _cleanup_old_logs(self, max_logs: int = 20):
        """
        Очистка старых лог-файлов задач, оставляя только последние max_logs файлов
        
        Args:
            max_logs: Максимальное количество лог-файлов задач для хранения
        """
        try:
            # Получаем все лог-файлы задач
            log_files = sorted(
                self.log_dir.glob("task_*.log"),
                key=lambda p: p.stat().st_mtime,
                reverse=True  # Сортируем от новых к старым
            )
            
            # Удаляем старые логи, оставляя только max_logs последних
            if len(log_files) > max_logs:
                for old_log in log_files[max_logs:]:
                    try:
                        old_log.unlink()
                    except Exception as e:
                        # Игнорируем ошибки удаления отдельных файлов
                        pass
        except Exception as e:
            # Игнорируем ошибки очистки - это не критично
            pass
