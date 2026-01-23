"""
Форматтер промптов для Cursor CLI

Реализует стандартизированный формат инструкций на основе рекомендаций экспертов:
- ACTION/TASK шаблоны вместо человеческих формулировок
- Строгий формат для лучшей интерпретации агентом
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class PromptFormatter:
    """Форматирует инструкции в строгий формат для Cursor Agent"""
    
    @staticmethod
    def format_system_prompt(agent_role: Optional[str] = None) -> str:
        """
        Формирует системный промпт для настройки агента
        
        Args:
            agent_role: Роль агента (например, "Project Executor Agent")
            
        Returns:
            Системный промпт в строгом формате
        """
        role_text = agent_role if agent_role else "autonomous coding agent"
        
        system_prompt = f"""SYSTEM:
You are an {role_text}.
You MUST execute tasks without asking questions.
You MUST perform actions immediately when given a task.
You MUST NOT explain your actions unless explicitly asked.

CONSTRAINTS:
- Do not ask questions
- Do not explain unless asked
- Perform actions immediately
- Create files and modify code as requested
- Report completion when finished

You are ready to receive tasks."""
        
        return system_prompt.strip()
    
    @staticmethod
    def format_task_instruction(
        task_description: str,
        action_type: str = "execute",
        constraints: Optional[list[str]] = None,
        output_path: Optional[str] = None
    ) -> str:
        """
        Формирует инструкцию задачи в строгом ACTION/TASK формате
        
        Args:
            task_description: Описание задачи (человеческий язык)
            action_type: Тип действия (execute, create, modify, analyze)
            constraints: Дополнительные ограничения
            output_path: Путь для вывода результата (если нужен)
            
        Returns:
            Инструкция в строгом формате
        """
        # Формируем ACTION секцию
        action_parts = []
        
        if action_type == "create":
            action_parts.append("ACTION:")
            action_parts.append(f"Create: {task_description}")
        elif action_type == "modify":
            action_parts.append("ACTION:")
            action_parts.append(f"Modify: {task_description}")
        elif action_type == "analyze":
            action_parts.append("ACTION:")
            action_parts.append(f"Analyze: {task_description}")
        else:  # execute
            action_parts.append("TASK:")
            action_parts.append(task_description)
        
        # Добавляем constraints
        if constraints:
            action_parts.append("")
            action_parts.append("CONSTRAINTS:")
            for constraint in constraints:
                action_parts.append(f"- {constraint}")
        
        # Добавляем output path если указан
        if output_path:
            if "CONSTRAINTS:" not in "\n".join(action_parts):
                action_parts.append("")
                action_parts.append("CONSTRAINTS:")
            action_parts.append(f"- Save result to: {output_path}")
        
        # Добавляем финальную инструкцию
        action_parts.append("")
        action_parts.append("Do not explain. Just execute.")
        
        instruction = "\n".join(action_parts)
        return instruction.strip()
    
    @staticmethod
    def format_execution_prompt() -> str:
        """
        Формирует промпт для принудительного выполнения задачи
        
        Returns:
            Промпт для выполнения
        """
        return "Execute now. Perform the action immediately."
    
    @staticmethod
    def parse_instruction_to_action_format(
        instruction: str,
        output_path: Optional[str] = None
    ) -> str:
        """
        Преобразует человеческую инструкцию в строгий ACTION/TASK формат
        
        Args:
            instruction: Исходная инструкция (человеческий язык)
            output_path: Путь для сохранения результата
            
        Returns:
            Инструкция в строгом формате
        """
        # Определяем тип действия по ключевым словам
        instruction_lower = instruction.lower()
        
        if any(word in instruction_lower for word in ["создай", "create", "сделай", "make"]):
            action_type = "create"
        elif any(word in instruction_lower for word in ["измени", "modify", "обнови", "update"]):
            action_type = "modify"
        elif any(word in instruction_lower for word in ["проанализируй", "analyze", "изучи", "study"]):
            action_type = "analyze"
        else:
            action_type = "execute"
        
        return PromptFormatter.format_task_instruction(
            task_description=instruction,
            action_type=action_type,
            output_path=output_path
        )
    
    @staticmethod
    def format_task_with_execution_guarantee(
        task_name: str,
        task_description: str,
        output_file: Optional[str] = None,
        control_phrase: str = "Задача выполнена!",
        additional_constraints: Optional[list[str]] = None
    ) -> str:
        """
        Формирует инструкцию с явным указанием немедленного выполнения
        
        Этот формат добавляет дополнительные указания для гарантии выполнения задачи
        агентом в non-interactive режиме.
        
        Args:
            task_name: Название задачи
            task_description: Подробное описание задачи
            output_file: Файл для сохранения результата
            control_phrase: Контрольная фраза для подтверждения выполнения
            additional_constraints: Дополнительные ограничения
            
        Returns:
            Инструкция с явным указанием выполнения
        """
        instruction_parts = [
            "EXECUTE IMMEDIATELY - NO QUESTIONS:",
            "",
            "ACTION:",
            task_name,
            "",
            "DESCRIPTION:",
            task_description,
            "",
            "REQUIREMENTS:",
            "- Execute this task RIGHT NOW",
            "- Do NOT ask for confirmation",
            "- Do NOT explain unless explicitly requested",
            "- Perform all necessary actions (create files, modify code, etc.)",
            "- Save all changes immediately",
            "",
            "CONSTRAINTS:"
        ]
        
        # Добавляем output file если указан
        if output_file:
            instruction_parts.append(f"- Save result to: {output_file}")
        
        # Добавляем контрольную фразу
        instruction_parts.append(f'- Add control phrase at the end: "{control_phrase}"')
        
        # Добавляем дополнительные ограничения
        if additional_constraints:
            for constraint in additional_constraints:
                instruction_parts.append(f"- {constraint}")
        
        # Добавляем финальное напоминание
        instruction_parts.extend([
            "- Report completion when finished",
            "",
            "IMPORTANT: This is an automated task. Execute immediately without any questions or explanations."
        ])
        
        return "\n".join(instruction_parts)
