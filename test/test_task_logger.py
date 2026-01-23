"""
Тесты для системы логирования задач
"""

import pytest
import time
from src.task_logger import TaskLogger, ServerLogger, TaskPhase


def test_task_logger_creation(tmp_path):
    """Тест создания логгера задачи"""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    
    logger = TaskLogger("test_task_001", "Тестовая задача", log_dir)
    
    # Проверяем, что лог-файл создан
    assert logger.log_file.exists()
    assert logger.task_id == "test_task_001"
    assert logger.task_name == "Тестовая задача"
    
    logger.close()


def test_task_logger_phases(tmp_path):
    """Тест логирования фаз выполнения"""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    
    logger = TaskLogger("test_task_002", "Тестовая задача с фазами", log_dir)
    
    # Тестируем различные фазы
    logger.set_phase(TaskPhase.INITIALIZATION)
    logger.set_phase(TaskPhase.TASK_ANALYSIS)
    logger.set_phase(TaskPhase.INSTRUCTION_GENERATION, stage=1, instruction_num=1)
    logger.set_phase(TaskPhase.CURSOR_EXECUTION, stage=1, instruction_num=1)
    logger.set_phase(TaskPhase.COMPLETION)
    
    logger.close()
    
    # Проверяем содержимое лога
    log_content = logger.log_file.read_text(encoding='utf-8')
    assert "Инициализация" in log_content
    assert "Анализ задачи" in log_content
    assert "Генерация инструкции" in log_content
    assert "Выполнение через Cursor" in log_content
    assert "Завершение" in log_content


def test_task_logger_instruction(tmp_path):
    """Тест логирования инструкции"""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    
    logger = TaskLogger("test_task_003", "Задача с инструкцией", log_dir)
    
    instruction_text = "Выполни тестовую задачу: создай файл test.py"
    logger.log_instruction(1, instruction_text, "test")
    
    logger.close()
    
    # Проверяем содержимое лога
    log_content = logger.log_file.read_text(encoding='utf-8')
    assert "Инструкция 1" in log_content
    assert "test.py" in log_content


def test_task_logger_cursor_response(tmp_path):
    """Тест логирования ответа от Cursor"""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    
    logger = TaskLogger("test_task_004", "Задача с ответом", log_dir)
    
    # Успешный ответ
    response = {
        'success': True,
        'stdout': 'Created file test.py\nModified file utils.py\nTests passed',
        'stderr': '',
        'return_code': 0
    }
    logger.log_cursor_response(response, brief=True)
    
    logger.close()
    
    # Проверяем содержимое лога
    log_content = logger.log_file.read_text(encoding='utf-8')
    assert "УСПЕШНО" in log_content or "SUCCESS" in log_content


def test_task_logger_error(tmp_path):
    """Тест логирования ошибки"""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    
    logger = TaskLogger("test_task_005", "Задача с ошибкой", log_dir)
    
    try:
        raise ValueError("Тестовая ошибка")
    except ValueError as e:
        logger.log_error("Произошла ошибка", e)
    
    logger.close()
    
    # Проверяем содержимое лога
    log_content = logger.log_file.read_text(encoding='utf-8')
    assert "ОШИБКА" in log_content
    assert "Тестовая ошибка" in log_content


def test_task_logger_completion(tmp_path):
    """Тест логирования завершения задачи"""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    
    logger = TaskLogger("test_task_006", "Завершенная задача", log_dir)
    
    # Имитируем выполнение задачи
    time.sleep(0.1)
    logger.log_completion(success=True, summary="Все прошло успешно")
    
    logger.close()
    
    # Проверяем содержимое лога
    log_content = logger.log_file.read_text(encoding='utf-8')
    assert "УСПЕШНО ЗАВЕРШЕНА" in log_content
    assert "Время выполнения" in log_content


def test_task_logger_new_chat(tmp_path):
    """Тест логирования создания нового чата"""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    
    logger = TaskLogger("test_task_007", "Задача с чатом", log_dir)
    
    logger.log_new_chat(chat_id="chat_12345")
    
    logger.close()
    
    # Проверяем содержимое лога
    log_content = logger.log_file.read_text(encoding='utf-8')
    assert "Создан новый диалог" in log_content or "новый чат" in log_content.lower()


def test_server_logger_initialization(tmp_path):
    """Тест логирования инициализации сервера"""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    
    logger = ServerLogger(log_dir)
    
    config = {
        'project_dir': '/test/project',
        'docs_dir': '/test/docs',
        'cursor_cli_available': True
    }
    
    logger.log_initialization(config)
    
    # Проверяем, что логирование прошло без ошибок
    # (вывод идет в основной logger, который настроен в server.py)


def test_server_logger_iteration(tmp_path):
    """Тест логирования итерации"""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    
    logger = ServerLogger(log_dir)
    
    logger.log_iteration_start(iteration=1, pending_tasks=5)
    
    # Проверяем, что логирование прошло без ошибок


def test_server_logger_task_start(tmp_path):
    """Тест логирования начала задачи"""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    
    logger = ServerLogger(log_dir)
    
    logger.log_task_start(task_number=1, total_tasks=5, task_name="Тестовая задача")
    
    # Проверяем, что логирование прошло без ошибок


def test_server_logger_shutdown(tmp_path):
    """Тест логирования остановки сервера"""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    
    logger = ServerLogger(log_dir)
    
    logger.log_server_shutdown(reason="Тестовая остановка")
    
    # Проверяем, что логирование прошло без ошибок


def test_task_logger_file_extraction(tmp_path):
    """Тест извлечения упоминаний файлов из текста"""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    
    logger = TaskLogger("test_task_008", "Задача с файлами", log_dir)
    
    text = """
    Created file test.py
    Modified utils.py
    Created another_file.txt
    """
    
    files = logger._extract_file_mentions(text, ['created', 'modified'])
    
    assert len(files) > 0
    assert any('test.py' in f for f in files) or any('.py' in f for f in files)
    
    logger.close()


def test_task_logger_multiple_instructions(tmp_path):
    """Тест логирования нескольких инструкций"""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    
    logger = TaskLogger("test_task_009", "Задача с несколькими инструкциями", log_dir)
    
    # Логируем несколько инструкций
    for i in range(1, 4):
        logger.log_instruction(i, f"Инструкция {i}", "development")
    
    assert logger.instruction_count == 3
    
    logger.close()
    
    # Проверяем содержимое лога
    log_content = logger.log_file.read_text(encoding='utf-8')
    assert "Инструкция 1" in log_content
    assert "Инструкция 2" in log_content
    assert "Инструкция 3" in log_content


def test_task_logger_waiting_result(tmp_path):
    """Тест логирования ожидания результата"""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    
    logger = TaskLogger("test_task_010", "Задача с ожиданием", log_dir)
    
    logger.log_waiting_result("docs/results/test.md", timeout=300)
    
    logger.close()
    
    # Проверяем содержимое лога
    log_content = logger.log_file.read_text(encoding='utf-8')
    assert "Ожидание результата" in log_content or "ожидание" in log_content.lower()


def test_task_logger_result_received(tmp_path):
    """Тест логирования получения результата"""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    
    logger = TaskLogger("test_task_011", "Задача с результатом", log_dir)
    
    logger.log_result_received(
        "docs/results/test.md",
        wait_time=5.5,
        content_preview="Результат выполнения задачи..."
    )
    
    logger.close()
    
    # Проверяем содержимое лога
    log_content = logger.log_file.read_text(encoding='utf-8')
    assert "Результат получен" in log_content or "результат" in log_content.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
