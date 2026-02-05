from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

from ...todo_manager import TodoItem
from ...task_logger import TaskLogger


class ITaskProcessor(ABC):
    @abstractmethod
    async def process_task(
        self, todo_item: TodoItem, task_number: int, total_tasks: int
    ) -> bool:
        """
        Обрабатывает одну задачу.

        Args:
            todo_item: Элемент todo-листа для выполнения.
            task_number: Номер задачи в текущей итерации.
            total_tasks: Общее количество задач.

        Returns:
            True, если задача выполнена успешно, False в противном случае.
        """
        pass

    @abstractmethod
    async def check_task_usefulness(self, todo_item: TodoItem) -> Tuple[float, Optional[str]]:
        """
        Проверка полезности задачи - является ли она реальной задачей или мусором.

        Args:
            todo_item: Элемент todo-листа для проверки.

        Returns:
            Кортеж (процент полезности 0-100, комментарий если есть).
        """
        pass

    @abstractmethod
    async def check_todo_matches_plan(self, task_id: str, todo_item: TodoItem) -> Tuple[bool, Optional[str]]:
        """
        Проверка соответствия пункта туду пунктам плана через LLM агентов.

        Args:
            task_id: ID задачи.
            todo_item: Элемент todo-листа для проверки.

        Returns:
            Кортеж (соответствует ли туду плану, причина несоответствия если есть).
        """
        pass

    @abstractmethod
    def verify_real_work_done(self, task_id: str, todo_item: TodoItem, result_content: str) -> bool:
        """
        Проверка, что была выполнена реальная работа, а не только создан план.

        Args:
            task_id: ID задачи.
            todo_item: Элемент todo-листа.
            result_content: Содержимое файла результата.

        Returns:
            True если работа выполнена, False если только план.
        """
        pass

    @abstractmethod
    def determine_task_type(self, todo_item: TodoItem) -> str:
        """
        Определение типа задачи для выбора инструкции.
        """
        pass

    @abstractmethod
    def get_instruction_template(self, task_type: str, instruction_id: int = 1) -> Optional[Dict[str, Any]]:
        """
        Получить шаблон инструкции из конфигурации.
        """
        pass

    @abstractmethod
    def get_all_instruction_templates(self, task_type: str) -> List[Dict[str, Any]]:
        """
        Получить все шаблоны инструкций для типа задачи (последовательно 1-8).
        """
        pass

    @abstractmethod
    def format_instruction(self, template: Dict[str, Any], todo_item: TodoItem, task_id: str, instruction_num: int = 1) -> str:
        """
        Форматирование инструкции из шаблона.
        """
        pass

    @abstractmethod
    def wait_for_result_file(
        self,
        task_id: str,
        wait_for_file: Optional[str] = None,
        control_phrase: Optional[str] = None,
        timeout: int = 300
    ) -> Dict[str, Any]:
        """
        Ожидание файла результата от Cursor.
        """
        pass

    @abstractmethod
    async def execute_task_via_llm(self, todo_item: TodoItem, task_type: str, task_logger: TaskLogger) -> bool:
        """
        Выполнение задачи через интеллектуальную LLM систему.
        """
        pass

    @abstractmethod
    def _create_task_execution_prompt(self, todo_item: TodoItem, task_type: str) -> str:
        """
        Создать промпт для выполнения задачи через LLM
        """
        pass

    @abstractmethod
    def _process_llm_task_result(self, todo_item: TodoItem, result_content: str, task_logger: TaskLogger) -> bool:
        """
        Обработать результат выполнения задачи от LLM
        """
        pass

    @abstractmethod
    def _check_expected_files_from_result(self, result_content: str) -> bool:
        """
        Проверить создание ожидаемых файлов на основе результата LLM
        """
        pass

