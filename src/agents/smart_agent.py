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
    docker_error_msg = ""

    if allow_code_execution:
        try:
            if use_docker is None:  # Автоопределение
                docker_available = DockerChecker.is_docker_available()
                status_msg = 'available' if docker_available else 'not available'
                logger.info(f"Docker auto-detection: {status_msg}")

                if not docker_available:
                    docker_version = DockerChecker.get_docker_version()
                    if docker_version:
                        logger.info(f"Docker installed (version: {docker_version}) but daemon not accessible")
                    else:
                        logger.info("Docker not installed or not in PATH")

            elif use_docker:  # Принудительное использование
                docker_available = DockerChecker.is_docker_available()
                if not docker_available:
                    docker_error_msg = "Docker forced but not available - falling back to no code execution"
                    logger.warning(docker_error_msg)
                    # Проверяем права доступа
                    perms_ok, perms_msg = DockerChecker.check_docker_permissions()
                    if not perms_ok:
                        logger.warning(f"Docker permissions issue: {perms_msg}")
                else:
                    logger.info("Docker forced and available")
            else:  # Отключено
                docker_available = False
                logger.info("Docker disabled by configuration")

        except Exception as e:
            docker_available = False
            docker_error_msg = f"Docker check failed: {str(e)}"
            logger.error(docker_error_msg)

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
            fallback_reason = docker_error_msg or "Docker not available"
            logger.info(f"CodeInterpreterTool skipped - {fallback_reason} - operating in fallback mode")
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

    # Создаем агента с расширенными возможностями
    agent = Agent(
        role=role,
        goal=goal,
        backstory=backstory,
        allow_code_execution=allow_code_execution and docker_available,  # Обновляем на основе доступности Docker
        verbose=verbose,
        tools=tools,
        **llm_kwargs,
        # Для smart агента можно увеличить лимиты
        max_iter=50,  # Больше итераций для сложных задач
        memory=True,   # Включаем память для лучшего обучения
        # max_rpm=30,    # Можно настроить ограничения RPM
    )

    # Логируем итоговый статус
    tool_names = [tool.__class__.__name__ if hasattr(tool, '__class__') else str(type(tool)) for tool in tools]
    logger.info(f"SmartAgent created with {len(tools)} tools: {', '.join(tool_names)}")
    logger.info(f"Docker status: {'available' if docker_available else 'not available'}")
    logger.info(f"Code execution: {'enabled' if (allow_code_execution and docker_available) else 'disabled (fallback mode)'}")

    return agent