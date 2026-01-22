"""
Smart Agent - расширенная версия агента с инструментами обучения и анализа контекста
"""

from pathlib import Path
from typing import Optional, List
from crewai import Agent

# Импортируем инструменты
from ..tools import LearningTool, ContextAnalyzerTool, is_docker_available

# Экспортируем функцию для тестирования
__all__ = ['create_smart_agent', 'is_docker_available']

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
    use_docker: bool = True,  # Simplified: True = use Docker if available, False = don't use
    verbose: bool = True,
    use_llm: bool = True,  # Simplified: True = use LLM if available, False = tool-only mode
    llm_config_path: str = "config/llm_settings.yaml",
    max_experience_tasks: int = 1000
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
        use_docker: Использовать Docker для code execution если доступен
        verbose: Подробный вывод
        use_llm: Использовать LLM если доступен
        llm_config_path: Путь к конфигурации LLM
        max_experience_tasks: Максимальное количество задач в опыте

    Returns:
        Настроенный smart агент CrewAI
    """

    # Настройка логирования
    import logging
    logger = logging.getLogger(__name__)

    # Создаем инструменты
    tools = []

    # Simplified Docker handling
    docker_available = False
    if allow_code_execution and use_docker:
        try:
            docker_available = is_docker_available()
            if docker_available:
                try:
                    from crewai_tools import CodeInterpreterTool
                    code_tool = CodeInterpreterTool()
                    tools.append(code_tool)
                    logger.info("CodeInterpreterTool added successfully")
                except Exception as e:
                    logger.warning(f"CodeInterpreterTool failed: {e}")
                    logger.info("⚠️  Operating in limited mode: code execution disabled")
                    docker_available = False
            else:
                logger.info("Docker not available - code execution disabled")
        except Exception as e:
            logger.warning(f"Docker check failed: {e}")
            docker_available = False

    # Добавляем smart инструменты (всегда доступны)
    try:
        # LearningTool для обучения на предыдущих задачах
        learning_tool = LearningTool(
            experience_dir=str(project_dir / experience_dir),
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
        logger.error(f"Failed to initialize smart tools: {e}")
        raise  # Smart tools are critical, fail if they can't be initialized

    # Настройка LLM
    import os

    llm_kwargs = {}
    llm_available = False

    if use_llm:
        # Try to use LLM if LLM_WRAPPER_AVAILABLE
        if LLM_WRAPPER_AVAILABLE:
            try:
                llm_kwargs['llm'] = create_llm_for_crewai(
                    config_path=llm_config_path,
                    use_fastest=True,
                    use_parallel=False
                )
                llm_available = True
                logger.info("LLM configured successfully")
            except Exception as e:
                logger.warning(f"LLM configuration failed: {e}")
                logger.info("💡 Tip: Check LLM configuration in config/llm_settings.yaml")

        # Fallback to OpenRouter if available and LLM wrapper failed
        if not llm_available and os.getenv('OPENROUTER_API_KEY'):
            try:
                from crewai.llm import LLM
                llm_kwargs['llm'] = LLM(
                    model="grok",
                    api_key=os.getenv('OPENROUTER_API_KEY'),
                    base_url="https://openrouter.ai/api/v1"
                )
                llm_available = True
                logger.info("Using OpenRouter fallback")
            except Exception as e:
                logger.warning(f"OpenRouter fallback failed: {e}")
                logger.info("💡 Tip: Verify OPENROUTER_API_KEY is set correctly")

    # If no LLM available, operate in tool-only mode
    if not llm_available:
        logger.info("Operating in tool-only mode (no LLM available)")
        llm_kwargs.clear()

    # Configure backstory if not provided
    if backstory is None:
        code_status = "with code execution" if (allow_code_execution and docker_available) else "without code execution"
        llm_status = "with LLM support" if llm_available else "in tool-only mode"

        backstory = f"""You are a smart agent that learns from task execution history and analyzes project context.
You use LearningTool and ContextAnalyzerTool to improve task execution quality.
You store experience data to provide better recommendations for similar tasks.
Operating {code_status} and {llm_status}.
"""

    # Создаем агента
    if llm_available:
        agent = Agent(
            role=role,
            goal=goal,
            backstory=backstory,
            allow_code_execution=allow_code_execution and docker_available,
            verbose=verbose,
            tools=tools,
            **llm_kwargs,
            max_iter=30,
            memory=True,
        )
    else:
        agent = Agent(
            role=role,
            goal=goal,
            backstory=backstory,
            allow_code_execution=allow_code_execution and docker_available,
            verbose=verbose,
            tools=tools,
            llm=None,  # Explicitly disable LLM
            max_iter=30,
            memory=False,
        )

    # Логируем итоговый статус
    tool_names = [tool.__class__.__name__ if hasattr(tool, '__class__') else str(type(tool)) for tool in tools]
    logger.info(f"SmartAgent created with {len(tools)} tools: {', '.join(tool_names)}")
    logger.info(f"Docker: {'available' if docker_available else 'not available'}")
    logger.info(f"LLM: {'available' if llm_available else 'not available'}")

    # User-visible status notification
    capabilities = []
    limitations = []

    if docker_available:
        capabilities.append("code execution")
    else:
        limitations.append("no code execution")

    if llm_available:
        capabilities.append("LLM support")
    else:
        limitations.append("tool-only mode")

    if capabilities:
        logger.info(f"✅ Smart Agent ready with: {', '.join(capabilities)}")
    if limitations:
        logger.warning(f"⚠️  Limited functionality: {', '.join(limitations)}")

    return agent