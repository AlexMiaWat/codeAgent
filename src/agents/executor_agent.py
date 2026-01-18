"""
Определение агента-исполнителя для CrewAI
"""

from pathlib import Path
from typing import Optional, List
from crewai import Agent
from crewai_tools import CodeInterpreterTool


def create_executor_agent(
    project_dir: Path,
    docs_dir: Optional[Path] = None,
    role: str = "Project Executor Agent",
    goal: str = "Execute todo items for the project, following documentation and best practices",
    backstory: Optional[str] = None,
    allow_code_execution: bool = True,
    verbose: bool = True
) -> Agent:
    """
    Создание агента-исполнителя для работы с проектом
    
    Args:
        project_dir: Директория проекта
        docs_dir: Директория с документацией (опционально)
        role: Роль агента
        goal: Цель агента
        backstory: История/контекст агента
        allow_code_execution: Разрешить выполнение кода
        verbose: Подробный вывод
    
    Returns:
        Настроенный агент CrewAI
    """
    if backstory is None:
        backstory = """You are an automated code agent working on software projects.
You read project documentation, understand requirements, and execute tasks
from the todo list systematically. You update project status and ensure
code quality and best practices are followed.
When working with the project, you have access to:
- Project documentation in the docs/ directory
- The ability to read and write files in the project
- The ability to execute Python code when necessary
"""
    
    # Список инструментов агента
    tools = []
    
    if allow_code_execution:
        tools.append(CodeInterpreterTool())
    
    # Можно добавить другие инструменты:
    # - FileReadTool для чтения файлов
    # - FileWriteTool для записи файлов
    # - CustomTool для специфических задач проекта
    
    agent = Agent(
        role=role,
        goal=goal,
        backstory=backstory,
        allow_code_execution=allow_code_execution,
        verbose=verbose,
        tools=tools,
        # max_iter - можно ограничить количество итераций агента
        # memory - можно включить память агента для запоминания контекста
    )
    
    return agent
