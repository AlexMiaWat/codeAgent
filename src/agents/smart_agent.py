"""
Smart Agent - расширенная версия агента с инструментами обучения и анализа контекста
"""

from pathlib import Path
from typing import Optional, List
from crewai import Agent

# Импортируем инструменты
from ..tools import LearningTool, ContextAnalyzerTool

# Импортируем LLM обертку для использования LLMManager
try:
    from ..llm.crewai_llm_wrapper import create_llm_for_crewai
    LLM_WRAPPER_AVAILABLE = True
except ImportError:
    LLM_WRAPPER_AVAILABLE = False
    create_llm_for_crewai = None


def create_smart_agent(
    project_dir: Path,
    docs_dir: Optional[Path] = None,
    experience_dir: str = "smart_experience",
    role: str = "Smart Project Executor Agent",
    goal: str = "Execute complex tasks with enhanced intelligence, learning from previous executions",
    backstory: Optional[str] = None,
    allow_code_execution: bool = True,
    verbose: bool = True,
    use_llm_manager: bool = True,
    llm_config_path: str = "config/llm_settings.yaml",
    max_experience_tasks: int = 1000,
    use_parallel: bool = False
) -> Agent:
    """
    Создание smart агента с расширенными возможностями

    Args:
        project_dir: Директория проекта
        docs_dir: Директория с документацией (опционально)
        experience_dir: Директория для хранения опыта
        role: Роль агента
        goal: Цель агента
        backstory: История/контекст агента
        allow_code_execution: Разрешить выполнение кода
        verbose: Подробный вывод
        use_llm_manager: Использовать LLM Manager
        llm_config_path: Путь к конфигурации LLM
        max_experience_tasks: Максимальное количество задач в опыте
        use_parallel: Использовать параллельное выполнение

    Returns:
        Настроенный smart агент CrewAI
    """
    if backstory is None:
        backstory = """You are a smart agent that learns from task execution history and analyzes project context.
You use LearningTool and ContextAnalyzerTool to improve task execution quality.
You store experience data to provide better recommendations for similar tasks.
"""

    # Создаем инструменты
    tools = []

    # Добавляем стандартные инструменты
    if allow_code_execution:
        try:
            from crewai_tools import CodeInterpreterTool
            tools.append(CodeInterpreterTool())
        except ImportError:
            pass  # Инструмент может быть недоступен

    # Добавляем smart инструменты
    try:
        # LearningTool для обучения на предыдущих задачах
        learning_tool = LearningTool(
            experience_dir=experience_dir,
            max_experience_tasks=max_experience_tasks
        )
        tools.append(learning_tool)

        # ContextAnalyzerTool для анализа контекста проекта
        context_tool = ContextAnalyzerTool(
            project_dir=str(project_dir),
            docs_dir=str(docs_dir) if docs_dir else "docs"
        )
        tools.append(context_tool)

    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to initialize smart tools: {e}")

    # Настройка LLM
    import os
    import logging
    logger = logging.getLogger(__name__)

    llm_kwargs = {}

    # Пытаемся использовать продвинутые модели через OpenRouter
    if os.getenv('OPENROUTER_API_KEY'):
        try:
            from crewai.llm import LLM
            import yaml
            from pathlib import Path

            # Читаем конфигурацию для выбора продвинутой модели
            llm_config_path = Path(llm_config_path)
            model_name = "grok"  # По умолчанию используем grok для smart агента

            if llm_config_path.exists():
                try:
                    with open(llm_config_path, 'r', encoding='utf-8') as f:
                        llm_config = yaml.safe_load(f) or {}

                    # Для smart агента используем более продвинутые модели
                    smart_config = llm_config.get('smart_agent', {})
                    model_name = smart_config.get('model', 'grok')

                    logger.info(f"Using advanced model for smart agent: {model_name}")
                except Exception as e:
                    logger.warning(f"Failed to load smart agent model config: {e}")

            # Создаем LLM объект с продвинутой моделью
            llm_kwargs['llm'] = LLM(
                model=model_name,
                api_key=os.getenv('OPENROUTER_API_KEY'),
                base_url="https://openrouter.ai/api/v1"
            )
        except Exception as e:
            logger.warning(f"Failed to create advanced LLM for smart agent: {e}")
            # Fallback: устанавливаем фиктивный OPENAI_API_KEY
            if not os.getenv('OPENAI_API_KEY'):
                os.environ['OPENAI_API_KEY'] = 'sk-dummy'
                logger.info("Using dummy OpenAI key (smart agent will not work without proper LLM)")

    # Создаем агента с расширенными возможностями
    agent = Agent(
        role=role,
        goal=goal,
        backstory=backstory,
        allow_code_execution=allow_code_execution,
        verbose=verbose,
        tools=tools,
        **llm_kwargs,
        # Для smart агента можно увеличить лимиты
        max_iter=50,  # Больше итераций для сложных задач
        memory=True,   # Включаем память для лучшего обучения
        # max_rpm=30,    # Можно настроить ограничения RPM
    )

    return agent