from typing import List, Optional
from .types import TaskType

class TodoItem:
    """Элемент todo-листа"""
    
    def __init__(self, text: str, level: int = 0, done: bool = False, parent: Optional['TodoItem'] = None, comment: Optional[str] = None, category: Optional[str] = None, id: Optional[str] = None, task_type: Optional[TaskType] = None):
        """
        Инициализация элемента todo

        Args:
            text: Текст задачи
            level: Уровень вложенности (0 - корень)
            done: Выполнена ли задача
            parent: Родительский элемент
            comment: Комментарий к задаче (например, причина пропуска или краткое описание выполнения)
            category: Категория задачи
            id: Уникальный идентификатор задачи
            task_type: Тип задачи (опционально, будет определен автоматически если не указан)
        """
        self.text = text.strip()
        self.level = level
        self.done = done
        self.parent = parent
        self.children: List['TodoItem'] = []
        self.comment = comment
        self.category = category
        self.id = id
        self.task_type = task_type or TaskType.auto_detect(text)

    @property
    def effective_task_type(self) -> Optional[TaskType]:
        """
        Get the effective task type, using auto-detection if not explicitly set.

        Returns:
            TaskType for this todo item
        """
        return self.task_type or TaskType.auto_detect(self.text)

    def set_task_type(self, task_type: Optional[TaskType]) -> None:
        """
        Explicitly set the task type for this todo item.

        Args:
            task_type: TaskType to set, or None to enable auto-detection
        """
        self.task_type = task_type

    def __repr__(self) -> str:
        status = "✓" if self.done else "○"
        indent = "  " * self.level
        task_type_str = f"[{self.effective_task_type.value}]" if self.effective_task_type else ""
        return f"{indent}{status} {task_type_str} {self.text}"