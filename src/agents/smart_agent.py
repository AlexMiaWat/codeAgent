"""
Smart Agent - расширенная версия агента с инструментами обучения и анализа контекста
"""

from pathlib import Path
from typing import Optional, List
from crewai import Agent

# Импортируем инструменты
from ..tools import LearningTool, ContextAnalyzerTool, DockerChecker

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
    use_docker: Optional[bool] = None,  # None = auto-detect, True = force Docker, False = disable Docker
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
        use_docker: Использовать Docker для code execution (None=автоопределение, True=принудительно, False=отключить)
        verbose: Подробный вывод
        use_llm_manager: Использовать LLM Manager
        llm_config_path: Путь к конфигурации LLM
        max_experience_tasks: Максимальное количество задач в опыте
        use_parallel: Использовать параллельное выполнение

    Returns:
        Настроенный smart агент CrewAI
    """

    # Настройка логирования
    import logging
    logger = logging.getLogger(__name__)

    # Создаем инструменты
    tools = []

    # Определяем, использовать ли Docker для code execution
    docker_available = False

    if allow_code_execution:
        try:
            if use_docker is None:  # Автоопределение
                docker_available = DockerChecker.is_docker_available()
                logger.info(f"Docker auto-detection: {'available' if docker_available else 'not available'}")

            elif use_docker:  # Принудительное использование
                docker_available = DockerChecker.is_docker_available()
                if not docker_available:
                    logger.warning("Docker forced but not available - falling back to no code execution")
                else:
                    logger.info("Docker forced and available")

            # else: use_docker is False - Docker отключен, docker_available остается False

        except Exception as e:
            docker_available = False
            logger.error(f"Docker check failed: {str(e)}")

    else:
        logger.info("Code execution disabled - Docker check skipped")

    # Добавляем стандартные инструменты
    if allow_code_execution:
        if docker_available:
            try:
                from crewai_tools import CodeInterpreterTool
                code_tool = CodeInterpreterTool()
                tools.append(code_tool)
                logger.info("CodeInterpreterTool added successfully (Docker available)")
            except ImportError as e:
                logger.warning(f"CodeInterpreterTool import failed: {e}")
                logger.info("Falling back to no code execution mode")
            except Exception as e:
                logger.error(f"CodeInterpreterTool initialization failed: {e}")
                logger.info("Falling back to no code execution mode")
        else:
            logger.info("CodeInterpreterTool skipped - Docker not available - operating in fallback mode")
            # В fallback режиме полагаемся на LearningTool и ContextAnalyzerTool

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
        logger.warning(f"Failed to initialize smart tools: {e}")

    # Настройка LLM
    import os

    llm_kwargs = {}

    # Используем ранее определенный статус Docker для backstory
    docker_available_for_backstory = docker_available

    if backstory is None:
        if allow_code_execution and docker_available_for_backstory:
            code_execution_status = "with code execution capabilities"
            execution_note = "You can execute code safely in isolated Docker containers."
        else:
            code_execution_status = "without direct code execution (Docker not available)"
            execution_note = "You work with code analysis, recommendations, and documentation without direct execution. Focus on planning, analysis, and guidance."

        backstory = f"""You are a smart agent that learns from task execution history and analyzes project context.
You use LearningTool and ContextAnalyzerTool to improve task execution quality.
You store experience data to provide better recommendations for similar tasks.
You are operating {code_execution_status}.
{execution_note}
"""

    # Настройка LLM с многоуровневым fallback
    llm_available = False

    # Уровень 1: Продвинутые модели через OpenRouter (если есть API ключ)
    if os.getenv('OPENROUTER_API_KEY'):
        try:
            from crewai.llm import LLM
            import yaml
            from pathlib import Path

            # Читаем конфигурацию для выбора продвинутой модели
            llm_config_path_obj = Path(llm_config_path)
            model_name = "grok"  # По умолчанию используем grok для smart агента

            if llm_config_path_obj.exists():
                try:
                    with open(llm_config_path_obj, 'r', encoding='utf-8') as f:
                        llm_config = yaml.safe_load(f) or {}

                    # Для smart агента используем более продвинутые модели
                    smart_config = llm_config.get('smart_agent', {})
                    model_name = smart_config.get('model', 'grok')

                except Exception as e:
                    logger.warning(f"Failed to load smart agent model config: {e}")

            # Создаем LLM объект с продвинутой моделью
            llm_kwargs['llm'] = LLM(
                model=model_name,
                api_key=os.getenv('OPENROUTER_API_KEY'),
                base_url="https://openrouter.ai/api/v1"
            )
            llm_available = True
            logger.info(f"Using advanced model: {model_name} via OpenRouter")

        except Exception as e:
            logger.warning(f"Failed to create advanced LLM via OpenRouter: {e}")

    # Уровень 2: CrewAILLMWrapper с автоматическим fallback через LLMManager
    if not llm_available and use_llm_manager:
        try:
            from ..llm.crewai_llm_wrapper import create_llm_for_crewai
            llm_kwargs['llm'] = create_llm_for_crewai(
                config_path=llm_config_path,
                use_fastest=True,
                use_parallel=False
            )
            llm_available = True
            logger.info("Using LLMManager with multi-model fallback support")

        except Exception as e:
            logger.error(f"Failed to create LLMManager fallback: {e}")

    # Уровень 3: Graceful degradation - работа без LLM
    if not llm_available:
        logger.warning("No LLM available - Smart Agent will operate in tool-only mode")
        logger.info("Available capabilities: LearningTool, ContextAnalyzerTool, and Docker-based code execution (if available)")
        # Для graceful degradation не передаем llm параметр вообще
        llm_kwargs.clear()

    # Создаем агента с расширенными возможностями
    if llm_kwargs:
        # Создаем агента с LLM
        agent = Agent(
            role=role,
            goal=goal,
            backstory=backstory,
            allow_code_execution=allow_code_execution and docker_available,
            verbose=verbose,
            tools=tools,
            **llm_kwargs,
            # Для smart агента можно увеличить лимиты
            max_iter=50,  # Больше итераций для сложных задач
            memory=True,   # Включаем память для лучшего обучения
        )
    else:
        # Graceful degradation: создаем агента без LLM
        logger.warning("Creating Smart Agent in tool-only mode (no LLM available)")
        agent = Agent(
            role=role,
            goal=f"{goal} (Tool-only mode - enhanced intelligence through learning)",
            backstory=f"{backstory}\n\nOPERATING IN TOOL-ONLY MODE: No language model available. Using LearningTool and ContextAnalyzerTool for intelligent task execution based on experience and project analysis.",
            allow_code_execution=allow_code_execution and docker_available,
            verbose=verbose,
            tools=tools,
            # Для tool-only режима настраиваем параметры
            max_iter=30,  # Среднее количество итераций
            memory=False,  # Отключаем память CrewAI без LLM
        )

    # Логируем итоговый статус
    tool_names = [tool.__class__.__name__ if hasattr(tool, '__class__') else str(type(tool)) for tool in tools]
    logger.info(f"SmartAgent created with {len(tools)} tools: {', '.join(tool_names)}")
    logger.info(f"Docker status: {'available' if docker_available else 'not available'}")
    logger.info(f"Code execution: {'enabled' if (allow_code_execution and docker_available) else 'disabled (fallback mode)'}")

    return agent