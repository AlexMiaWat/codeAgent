"""
Pytest configuration and shared fixtures for Code Agent tests.
"""

import os
import sys
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add src to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))


@pytest.fixture
def project_root_path():
    """Return the project root directory path."""
    return Path(__file__).parent.parent


@pytest.fixture
def test_data_dir(project_root_path):
    """Return the test data directory path."""
    return project_root_path / "test" / "data"


@pytest.fixture
def temp_project_dir(tmp_path):
    """Create a temporary project directory for testing."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()
    
    # Create basic structure
    (project_dir / "docs").mkdir()
    (project_dir / "src").mkdir()
    
    # Create basic files (используем todo.md как формат по умолчанию)
    todo_content = """# Текущие задачи проекта

## Высокий приоритет
- [ ] Test task
- [ ] Another task
"""
    (project_dir / "todo.md").write_text(todo_content, encoding='utf-8')
    (project_dir / "docs" / "README.md").write_text("# Test Project\n", encoding='utf-8')
    
    return project_dir


@pytest.fixture
def ensure_project_dir_env(monkeypatch, tmp_path):
    """
    Фикстура для обеспечения наличия PROJECT_DIR в переменных окружения
    
    Читает PROJECT_DIR из .env файла, если он существует, или использует временную директорию.
    """
    project_root = Path(__file__).parent.parent
    env_file = project_root / '.env'
    
    project_dir = None
    
    # Пробуем прочитать из .env
    if env_file.exists():
        try:
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('PROJECT_DIR='):
                        project_dir = line.split('=', 1)[1].strip().strip('"').strip("'")
                        # Проверяем, что путь существует
                        if Path(project_dir).exists():
                            break
                        else:
                            project_dir = None
        except Exception:
            pass
    
    # Если не нашли в .env или путь не существует, используем временную директорию
    if not project_dir:
        project_dir = str(tmp_path / "test_project")
        Path(project_dir).mkdir(parents=True, exist_ok=True)
    
    monkeypatch.setenv("PROJECT_DIR", project_dir)
    return project_dir


@pytest.fixture
def mock_api_keys(monkeypatch):
    """
    Фикстура для установки mock API ключей для всех провайдеров

    Устанавливает dummy ключи для тестирования различных LLM провайдеров.
    """
    # Сохраняем оригинальные значения
    original_keys = {}
    api_keys_to_mock = [
        'OPENAI_API_KEY',
        'ANTHROPIC_API_KEY',
        'OPENROUTER_API_KEY',
        'GOOGLE_API_KEY',
        'GROQ_API_KEY',
        'TOGETHER_API_KEY'
    ]

    for key in api_keys_to_mock:
        original_keys[key] = os.environ.get(key)
        monkeypatch.setenv(key, f'dummy-{key.lower()}-for-testing')

    yield

    # Восстанавливаем оригинальные значения
    for key, original_value in original_keys.items():
        if original_value is not None:
            os.environ[key] = original_value
        elif key in os.environ:
            del os.environ[key]


@pytest.fixture
def mock_openai_api_key(monkeypatch):
    """
    Фикстура для установки mock OPENAI_API_KEY для тестов

    Это необходимо, потому что CrewAI автоматически пытается создать LLM из переменных окружения,
    даже когда LLM не используется в тесте.
    """
    original_key = os.environ.get('OPENAI_API_KEY')
    monkeypatch.setenv('OPENAI_API_KEY', 'dummy-key-for-testing')
    yield
    # Восстанавливаем оригинальное значение
    if original_key is not None:
        os.environ['OPENAI_API_KEY'] = original_key
    elif 'OPENAI_API_KEY' in os.environ:
        del os.environ['OPENAI_API_KEY']


@pytest.fixture
def project_env_with_env_file(monkeypatch):
    """
    Фикстура для создания словаря окружения с PROJECT_DIR из .env файла
    
    Используется для тестов, которые запускают процессы с subprocess.
    """
    env = os.environ.copy()
    project_root = Path(__file__).parent.parent
    env_file = project_root / '.env'
    
    if 'PROJECT_DIR' not in env:
        if env_file.exists():
            try:
                with open(env_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith('PROJECT_DIR='):
                            project_dir = line.split('=', 1)[1].strip().strip('"').strip("'")
                            # Проверяем, что путь существует
                            if Path(project_dir).exists():
                                env['PROJECT_DIR'] = project_dir
                                break
            except Exception:
                pass
    
    return env


@pytest.fixture
def test_config_path(project_root_path):
    """Return path to test configuration file."""
    test_config = project_root_path / "config" / "test_config.yaml"
    return test_config if test_config.exists() else None


@pytest.fixture
def mock_config():
    """Return a mock configuration object."""
    # Используем переменную окружения или путь к тестовому проекту
    test_project_dir = os.environ.get("TEST_PROJECT_DIR", "/tmp/test_project")
    config = {
        "project": {
            "base_dir": test_project_dir,
            "docs_dir": "docs",
            "status_file": "test_codeAgentProjectStatus.md",  # Используем test_ префикс
            "todo_format": "md",  # Формат по умолчанию
        },
        "agent": {
            "role": "Test Agent",
            "goal": "Execute test tasks",
            "backstory": "Test agent for testing",
            "allow_code_execution": False,  # Отключено для безопасности в тестах
            "verbose": False,
        },
        "server": {
            "check_interval": 5,  # Короткий интервал для тестов
            "max_iterations": 10,  # Ограничено для тестов
            "task_delay": 1,
            "http_enabled": False,  # Отключен в тестах
            "http_port": 3457,  # Другой порт
        },
    }
    return config


@pytest.fixture
def mock_cursor_cli():
    """Return a mock Cursor CLI interface."""
    mock = MagicMock()
    mock.execute.return_value = {"status": "success", "output": "Command executed"}
    mock.is_available.return_value = True
    mock.get_status.return_value = "ready"
    return mock


@pytest.fixture
def mock_llm_manager():
    """Return a mock LLM Manager."""
    mock = MagicMock()
    mock.generate.return_value = "Generated response from LLM"
    mock.is_available.return_value = True
    mock.get_model_info.return_value = {
        "provider": "test",
        "model": "test-model",
        "status": "available"
    }
    return mock


@pytest.fixture
def mock_status_manager():
    """Return a mock Status Manager."""
    mock = MagicMock()
    mock.update_status.return_value = True
    mock.get_current_status.return_value = "in_progress"
    mock.get_history.return_value = []
    return mock


@pytest.fixture
def mock_todo_manager():
    """Return a mock TODO Manager."""
    mock = MagicMock()
    mock.get_next_task.return_value = {
        "id": 1,
        "title": "Test task",
        "description": "Test task description",
        "status": "pending"
    }
    mock.mark_complete.return_value = True
    mock.get_all_tasks.return_value = [
        {"id": 1, "title": "Task 1", "status": "pending"},
        {"id": 2, "title": "Task 2", "status": "pending"},
    ]
    mock.get_pending_tasks.return_value = []
    mock.load_todos.return_value = None
    return mock


@pytest.fixture
def mock_checkpoint_manager():
    """Return a mock Checkpoint Manager."""
    mock = MagicMock()
    mock.increment_iteration.return_value = None
    mock.get_completed_tasks.return_value = []
    mock.save_checkpoint.return_value = True
    mock.load_checkpoint.return_value = {}
    return mock


@pytest.fixture
def mock_crewai_agent():
    """Return a mock CrewAI Agent."""
    mock = MagicMock()
    mock.execute.return_value = "Task executed successfully"
    mock.name = "TestAgent"
    mock.role = "Test Role"
    return mock


@pytest.fixture
def mock_crewai_llm():
    """Return a mock CrewAI LLM."""
    mock = MagicMock()
    mock.generate.return_value = "Generated response"
    return mock


@pytest.fixture
def sample_todo_content():
    """Return sample TODO content for testing."""
    return """
1. Инициализировать проект
2. Настроить окружение разработки
3. Создать базовую структуру
4. Написать документацию
5. Добавить тесты
"""


@pytest.fixture
def sample_status_content():
    """Return sample status file content for testing."""
    return """
# Code Agent Project Status

## [2025-01-18 10:00:00] Задача: 1. Инициализировать проект

### Инструкция 1: Создание плана
**Время:** 2025-01-18 10:00:15
**Действие:** Отправлена инструкция Cursor для создания плана
**Результат от Cursor:** Создан план в docs/results/current_plan_1.1.md
**Время завершения:** 2025-01-18 10:05:20

### Инструкция 2: Выполнение плана
**Время:** 2025-01-18 10:05:30
**Действие:** Отправлена инструкция Cursor для выполнения плана
**Результат от Cursor:** План выполнен успешно
**Время завершения:** 2025-01-18 10:15:45
"""


@pytest.fixture
def sample_cursor_report():
    """Return sample Cursor report content for testing."""
    return """
# Cursor Execution Report

## Task: Create project structure

### Status: Completed

### Actions Taken:
1. Created directory structure
2. Initialized git repository
3. Created README.md
4. Set up basic configuration

### Files Modified:
- README.md (created)
- .gitignore (created)
- config/config.yaml (created)

### Result: Success

All tasks completed successfully.
"""


@pytest.fixture(autouse=True)
def reset_environment():
    """Reset environment variables before each test."""
    # Store original environment
    original_env = os.environ.copy()
    
    yield
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set up mock environment variables for testing."""
    monkeypatch.setenv("PROJECT_DIR", "D:\\Space\\test_project")
    monkeypatch.setenv("TEST_MODE", "true")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")


# Markers for test categorization
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "unit: mark test as unit test")
    config.addinivalue_line("markers", "cursor: mark test as requiring Cursor IDE")
    config.addinivalue_line("markers", "llm: mark test as requiring LLM API")
    config.addinivalue_line("markers", "docker: mark test as requiring Docker")


@pytest.fixture(scope="session", autouse=False)
def auto_start_server(request):
    """
    Фикстура для автоматического запуска HTTP сервера перед интеграционными тестами.

    Запускает сервер автоматически для тестов, помеченных маркером 'requires_server'.
    """
    from test.test_real_server_integration import ServerTester

    # Проверяем, требует ли тест сервера
    requires_server = request.node.get_closest_marker("requires_server") is not None

    if not requires_server:
        yield
        return

    print(f"\n[INFO] Тест '{request.node.name}' требует сервера, запускаем автоматически...")

    # Создаем тестер сервера
    tester = ServerTester()

    # Проверяем, не запущен ли сервер уже
    try:
        import requests
        response = requests.get("http://127.0.0.1:3456/health", timeout=2)
        if response.status_code == 200:
            print("[INFO] Сервер уже запущен, используем существующий")
            server_started = False
        else:
            server_started = tester.start_server(timeout=30)
    except Exception:
        server_started = tester.start_server(timeout=30)

    if not server_started and requires_server:
        pytest.skip("Не удалось запустить HTTP сервер для интеграционного теста")

    yield

    # Останавливаем сервер только если мы его запускали
    if server_started:
        print(f"\n[INFO] Останавливаем сервер после теста '{request.node.name}'...")
        tester.stop_server()


@pytest.fixture(autouse=True)
def mock_external_dependencies():
    """
    Автоматический mock внешних зависимостей для всех тестов.

    Mock-ирует:
    - crewai: основной фреймворк для AI агентов
    - flask: веб-фреймворк для HTTP сервера
    - watchdog: мониторинг файловой системы
    """
    # Mock crewai
    with patch.dict('sys.modules', {
        'crewai': MagicMock(),
        'crewai.agents': MagicMock(),
        'crewai.tasks': MagicMock(),
        'crewai.crews': MagicMock(),
        'crewai.tools': MagicMock(),
        'crewai_tools': MagicMock(),
    }):
        # Mock flask
        flask_mock = MagicMock()
        flask_mock.Flask = MagicMock()
        flask_mock.jsonify = MagicMock()
        flask_mock.request = MagicMock()
        flask_mock.Response = MagicMock()

        # Mock watchdog
        watchdog_mock = MagicMock()
        watchdog_mock.observers = MagicMock()
        watchdog_mock.observers.Observer = MagicMock()
        watchdog_mock.events = MagicMock()
        watchdog_mock.events.FileSystemEventHandler = MagicMock()

        with patch.dict('sys.modules', {
            'flask': flask_mock,
            'watchdog': watchdog_mock,
        }):
            yield


@pytest.fixture
def mock_crewai():
    """Mock для CrewAI зависимостей."""
    crewai_mock = MagicMock()

    # Mock основных классов CrewAI
    crewai_mock.Agent = MagicMock()
    crewai_mock.Task = MagicMock()
    crewai_mock.Crew = MagicMock()
    crewai_mock.Process = MagicMock()
    crewai_mock.LLM = MagicMock()

    # Mock crewai_tools
    crewai_tools_mock = MagicMock()
    crewai_tools_mock.BaseTool = MagicMock()
    crewai_tools_mock.FileReadTool = MagicMock()
    crewai_tools_mock.DirectoryReadTool = MagicMock()

    with patch.dict('sys.modules', {
        'crewai': crewai_mock,
        'crewai_tools': crewai_tools_mock,
    }):
        yield crewai_mock


@pytest.fixture
def mock_flask():
    """Mock для Flask зависимостей."""
    flask_mock = MagicMock()

    # Mock основных компонентов Flask
    flask_mock.Flask = MagicMock()
    flask_mock.jsonify = MagicMock(return_value=MagicMock())
    flask_mock.request = MagicMock()
    flask_mock.Response = MagicMock()

    # Mock для blueprints и routing
    flask_mock.Blueprint = MagicMock()

    with patch.dict('sys.modules', {
        'flask': flask_mock,
    }):
        yield flask_mock


@pytest.fixture
def mock_watchdog():
    """Mock для Watchdog зависимостей."""
    watchdog_mock = MagicMock()

    # Mock наблюдателя файловой системы
    observer_mock = MagicMock()
    observer_mock.Observer = MagicMock()
    observer_mock.start = MagicMock()
    observer_mock.stop = MagicMock()
    observer_mock.join = MagicMock()

    # Mock обработчика событий
    events_mock = MagicMock()
    events_mock.FileSystemEventHandler = MagicMock()

    watchdog_mock.observers = observer_mock
    watchdog_mock.events = events_mock

    with patch.dict('sys.modules', {
        'watchdog': watchdog_mock,
    }):
        yield watchdog_mock


# Skip tests based on availability
def pytest_collection_modifyitems(config, items):
    """Modify test collection to skip tests based on markers."""
    skip_slow = pytest.mark.skip(reason="Slow test skipped (use -m slow to run)")
    pytest.mark.skip(reason="Cursor not available")
    skip_llm = pytest.mark.skip(reason="LLM API not configured")
    pytest.mark.skip(reason="Docker not available")

    for item in items:
        # Skip slow tests by default unless explicitly requested
        if "slow" in item.keywords and not config.getoption("-m") == "slow":
            item.add_marker(skip_slow)

        # Skip Cursor tests if not available
        if "cursor" in item.keywords:
            # Check if Cursor is available
            # This is a placeholder - implement actual check
            pass

        # Skip LLM tests if API keys not configured
        if "llm" in item.keywords:
            if not os.getenv("OPENAI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY") and not os.getenv("OPENROUTER_API_KEY"):
                item.add_marker(skip_llm)

        # Skip Docker tests if Docker not available
        if "docker" in item.keywords:
            # Check if Docker is available
            # This is a placeholder - implement actual check
            pass
