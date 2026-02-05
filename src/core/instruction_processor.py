
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..config_loader import ConfigLoader
from ..todo_manager import TodoItem

logger = logging.getLogger(__name__)

class InstructionProcessor:
    """
    Обработчик инструкций и промптов для Code Agent.
    Отвечает за определение типа задачи, получение шаблонов инструкций
    и форматирование финального промпта для агента/LLM.
    """

    def __init__(self, config: Dict[str, Any], project_dir: Path):
        self.config = config
        self.project_dir = project_dir

    def _determine_task_type(self, todo_item: TodoItem) -> str:
        """
        Определение типа задачи для выбора инструкции

        Args:
            todo_item: Элемент todo-листа

        Returns:
            Тип задачи (default, frontend-task, backend-task, etc.)
        """
        task_text = todo_item.text.lower()

        # Определяем тип задачи по ключевым словам
        if any(word in task_text for word in ['тест', 'test', 'тестирование']):
            return 'test'
        elif any(word in task_text for word in ['документация', 'docs', 'readme']):
            return 'documentation'
        elif any(word in task_text for word in ['рефакторинг', 'refactor']):
            return 'refactoring'
        elif any(word in task_text for word in ['разработка', 'реализация', 'implement']):
            return 'development'
        else:
            return 'default'

    def _get_instruction_template(self, task_type: str, instruction_id: int = 1) -> Optional[Dict[str, Any]]:
        """
        Получить шаблон инструкции из конфигурации

        Args:
            task_type: Тип задачи
            instruction_id: ID инструкции (1-8 для последовательного выполнения)

        Returns:
            Словарь с шаблоном инструкции или None
        """
        instructions = self.config.get('instructions', {})
        task_instructions = instructions.get(task_type, instructions.get('default', []))

        # Ищем инструкцию с нужным ID
        for instruction in task_instructions:
            if isinstance(instruction, dict) and instruction.get('instruction_id') == instruction_id:
                return instruction

        # Если не найдена, берем первую доступную (только для backward compatibility)
        if task_instructions and isinstance(task_instructions[0], dict):
            return task_instructions[0]

        return None

    def _get_all_instruction_templates(self, task_type: str) -> List[Dict[str, Any]]:
        """
        Получить все шаблоны инструкций для типа задачи (последовательно 1-8)

        Args:
            task_type: Тип задачи

        Returns:
            Список шаблонов инструкций, отсортированный по instruction_id
        """
        instructions = self.config.get('instructions', {})
        task_instructions = instructions.get(task_type, instructions.get('default', []))

        # Фильтруем только словари с instruction_id и сортируем по ID
        valid_instructions = [
            instr for instr in task_instructions
            if isinstance(instr, dict) and 'instruction_id' in instr
        ]

        # Сортируем по instruction_id (1, 2, 3, ...)
        valid_instructions.sort(key=lambda x: x.get('instruction_id', 999))

        return valid_instructions

    def _format_instruction(self, template: Dict[str, Any], todo_item: TodoItem, task_id: str, instruction_num: int = 1) -> str:
        """
        Форматирование инструкции из шаблона

        Args:
            template: Шаблон инструкции
            todo_item: Элемент todo-листа
            task_id: Идентификатор задачи
            instruction_num: Номер инструкции в последовательности

        Returns:
            Отформатированная инструкция
        """
        instruction_text = template.get('template', '')

        # Подстановка значений
        replacements = {
            'task_name': todo_item.text,
            'task_id': task_id,
            'task_description': todo_item.text,
            'date': datetime.now().strftime('%Y%m%d'),
            'plan_item_number': str(instruction_num),  # Номер инструкции
            'plan_item_text': todo_item.text
        }

        for key, value in replacements.items():
            instruction_text = instruction_text.replace(f'{{{key}}}', str(value))

        return instruction_text

    def _load_documentation(self) -> str:
        """
        Загрузка документации проекта из папки docs

        Returns:
            Контент документации в виде строки
        """
        if not self.project_dir.exists():
            logger.warning(f"Project directory not found: {self.project_dir}")
            return ""

        docs_dir = self.project_dir / "docs"
        if not docs_dir.exists():
            logger.warning(f"Documentation directory not found: {docs_dir}")
            return ""

        docs_content = []
        # Assuming config.get is available or passed. For now, using direct access.
        # It's better to pass a ConfigLoader instance or the relevant config dict.
        supported_extensions = self.config.get('docs.supported_extensions', ['.md', '.txt'])
        max_file_size = self.config.get('docs.max_file_size', 1_000_000) # Default 1 MB

        for file_path in docs_dir.rglob('*'):
            if file_path.is_file() and file_path.suffix in supported_extensions:
                try:
                    file_size = file_path.stat().st_size
                    if file_size > max_file_size:
                        logger.warning(f"File too large, skipped: {file_path}")
                        continue

                    content = file_path.read_text(encoding='utf-8')
                    docs_content.append(f"\n## {file_path.name}\n\n{content}\n")
                except Exception as e:
                    logger.error(f"Error reading file {file_path}: {e}")

        return "\n".join(docs_content)

    def _create_task_execution_prompt(self, todo_item: TodoItem, task_type: str) -> str:
        """
        Создать промпт для выполнения задачи через LLM

        Args:
            todo_item: Задача для выполнения
            task_type: Тип задачи

        Returns:
            Промпт для LLM
        """
        documentation = self._load_documentation()
        context = f"""
Ты - опытный разработчик ПО, выполняющий задачи в проекте Code Agent.

КОНТЕКСТ ПРОЕКТА:
{documentation[:2000]}... (сокращено для краткости)

ТИП ЗАДАЧИ: {task_type}
ОПИСАНИЕ ЗАДАЧИ: {todo_item.text}

ТРЕБОВАНИЯ К ВЫПОЛНЕНИЮ:
1. Проанализируй задачу и ее контекст
2. Предоставь детальное решение
3. Создай необходимые файлы или модифицируй существующие
4. Обеспечь высокое качество кода/документации
5. Следуй лучшим практикам разработки

ФОРМАТ ОТВЕТА:
- Опиши анализ проблемы
- Предоставь решение с кодом/изменениями
- Укажи файлы, которые нужно создать/изменить
- Создай отчет в соответствующем формате

Задача должна быть выполнена качественно и полностью.
"""
        return context
