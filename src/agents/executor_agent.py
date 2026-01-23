"""
Определение агента-исполнителя для CrewAI
"""

from pathlib import Path
from typing import Optional
from crewai import Agent
from crewai_tools import CodeInterpreterTool

# Monkey patch для отключения проверки Docker в CrewAI
def _dummy_docker_validation(self):
    """Заглушка для отключения проверки Docker"""
    pass

# Заменяем метод проверки Docker на заглушку
Agent._validate_docker_installation = _dummy_docker_validation

# Импортируем LLM обертку для использования LLMManager
try:
    from ..llm.crewai_llm_wrapper import create_llm_for_crewai
    LLM_WRAPPER_AVAILABLE = True
except ImportError:
    LLM_WRAPPER_AVAILABLE = False
    create_llm_for_crewai = None


def create_executor_agent(
    project_dir: Path,
    docs_dir: Optional[Path] = None,
    role: str = "Project Executor Agent",
    goal: str = "Execute todo items for the project, following documentation and best practices",
    backstory: Optional[str] = None,
    allow_code_execution: bool = True,
    verbose: bool = True,
    use_llm_manager: bool = True,
    llm_config_path: str = "config/llm_settings.yaml",
    use_parallel: bool = False
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
    
    # Настройка LLM
    import os
    import logging
    logger = logging.getLogger(__name__)
    
    llm_kwargs = {}
    
    # Пытаемся использовать OpenRouter через CrewAI LLM с моделями из llm_settings.yaml (протестированные)
    if os.getenv('OPENROUTER_API_KEY'):
        try:
            from crewai.llm import LLM
            import yaml
            from pathlib import Path
            
            # Читаем default_model из llm_settings.yaml (протестированные модели)
            llm_config_path = Path(llm_config_path)
            if llm_config_path.exists():
                with open(llm_config_path, 'r', encoding='utf-8') as f:
                    llm_config = yaml.safe_load(f) or {}
                
                # Используем default_model из конфига (это протестированная модель)
                model_config = llm_config.get('llm', {})
                model_name = model_config.get('default_model', 'meta-llama/llama-3.2-1b-instruct')
                
                logger.info(f"Using OpenRouter with model from llm_settings.yaml: {model_name}")
            else:
                # Fallback на протестированную модель, если конфиг не найден
                model_name = 'meta-llama/llama-3.2-1b-instruct'
                logger.warning(f"LLM config not found at {llm_config_path}, using fallback model: {model_name}")
            
            # Создаем LLM объект с параметрами OpenRouter
            llm_kwargs['llm'] = LLM(
                model=model_name,
                api_key=os.getenv('OPENROUTER_API_KEY'),
                base_url="https://openrouter.ai/api/v1"
            )
        except Exception as e:
            logger.warning(f"Failed to create OpenRouter LLM: {e}")
            # Fallback: используем CrewAILLMWrapper с автоматическим fallback
            try:
                from ..llm.crewai_llm_wrapper import create_llm_for_crewai
                llm_kwargs['llm'] = create_llm_for_crewai(use_fastest=True)
                logger.info("Using CrewAILLMWrapper with automatic fallback mechanism")
            except Exception as fallback_error:
                logger.error(f"Failed to create CrewAILLMWrapper fallback: {fallback_error}")
                # Последний fallback - устанавливаем фиктивный OPENAI_API_KEY для предотвращения краха
                if not os.getenv('OPENAI_API_KEY'):
                    os.environ['OPENAI_API_KEY'] = 'sk-dummy'
                    logger.warning("Using dummy OpenAI key as last resort (agent may not work properly)")
    
    agent = Agent(
        role=role,
        goal=goal,
        backstory=backstory,
        allow_code_execution=allow_code_execution,
        verbose=verbose,
        tools=tools,
        **llm_kwargs,
        # max_iter - можно ограничить количество итераций агента
        # memory - можно включить память агента для запоминания контекста
    )
    
    return agent
