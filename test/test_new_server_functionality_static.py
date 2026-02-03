
import inspect
from typing import get_type_hints, Optional, Dict, Any
from pathlib import Path
import pytest
import os
import sys

# Мокируем импорты, которые могут вызвать проблемы или не нужны для статических тестов
sys.modules['flask'] = type('module', (object,), {'Flask': object, 'jsonify': lambda x: x})()
sys.modules['watchdog.observers'] = type('module', (object,), {'Observer': object})()
sys.modules['watchdog.events'] = type('module', (object,), {'FileSystemEventHandler': object})()
sys.modules['crewai'] = type('module', (object,), {'Task': object, 'Crew': object})()
sys.modules['src.mcp.server'] = type('module', (object,), {'MCPServer': object})()
sys.modules['src.llm.manager'] = type('module', (object,), {'LLMManager': object})()
sys.modules['src.llm.llm_manager'] = type('module', (object,), {'LLMManager': object})()
sys.modules['requests'] = type('module', (object,), {'get': object})()
sys.modules['src.tools.docker_utils'] = type('module', (object,), {'is_docker_available': lambda: True})()
sys.modules['src.tools.learning_tool'] = type('module', (object,), {'LearningTool': object, 'normalize_unicode_text': lambda x: x if x else ""})()
sys.modules['src.tools.context_analyzer_tool'] = type('module', (object,), {'ContextAnalyzerTool': object, 'normalize_unicode_text': lambda x: x if x else ""})()


# Импортируем тестируемые модули после моков
from src.server import CodeAgentServer, ServerReloadException, _setup_logging
from src.todo_manager import TodoItem, TodoManager
from src.core.types import TaskType, ExecutionState, ComponentState, ComponentStatus, ServerConfig, ComponentHealth
from src.task_logger import TaskLogger, TaskPhase, Colors
from src.config_loader import ConfigLoader
from src.checkpoint_manager import CheckpointManager
from src.status_manager import StatusManager
from src.session_tracker import SessionTracker

# Мок для ConfigLoader
class MockConfigLoader:
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config_path = Path(config_path)
        self.config = {
            'agent': {
                'role': 'test_role',
                'goal': 'test_goal',
                'backstory': 'test_backstory',
                'allow_code_execution': True,
                'verbose': True
            },
            'server': {
                'check_interval': 1,
                'task_delay': 0,
                'max_iterations': 2,
                'http_port': 3456,
                'http_enabled': False, # Disable HTTP for static tests
                'mcp_enabled': False, # Disable MCP for static tests
                'auto_reload': False, # Disable auto-reload for static tests
                'reload_on_py_changes': False,
                'auto_todo_generation': {'enabled': False}, # Disable auto-todo for static tests
            },
            'cursor': {
                'interface_type': 'cli',
                'cli': {
                    'cli_path': 'mock_cursor_cli',
                    'timeout': 10
                }
            },
            'docs': {
                'supported_extensions': ['.md', '.txt'],
                'max_file_size': 1000000
            },
            'git': {
                'smart_git': {
                    'allowed_branches': ['smart'],
                    'auto_push_timeout': 60
                }
            },
            'instructions': {
                'default': [{
                    'instruction_id': 1,
                    'template': 'Default instruction: {task_name}',
                    'wait_for_file': 'docs/results/result_{task_id}.md',
                    'control_phrase': 'Report complete!',
                    'timeout': 60
                }],
                'test': [
                    {'instruction_id': 1, 'template': 'Plan tests for {task_name}', 'wait_for_file': 'docs/results/plan_{task_id}.md', 'control_phrase': 'Plan generated!', 'timeout': 60},
                    {'instruction_id': 2, 'template': 'Write static tests for {task_name}', 'wait_for_file': 'docs/results/test_static_{task_id}.md', 'control_phrase': 'Static tests written!', 'timeout': 60},
                    {'instruction_id': 3, 'template': 'Write smoke tests for {task_name}', 'wait_for_file': 'docs/results/test_smoke_{task_id}.md', 'control_phrase': 'Smoke tests written!', 'timeout': 60},
                    {'instruction_id': 4, 'template': 'Write integration tests for {task_name}', 'wait_for_file': 'docs/results/test_integration_{task_id}.md', 'control_phrase': 'Integration tests written!', 'timeout': 120},
                    {'instruction_id': 5, 'template': 'Run all tests and capture results for {task_name}', 'wait_for_file': 'docs/results/test_results_{task_id}.md', 'control_phrase': 'Tests executed!', 'timeout': 120},
                    {'instruction_id': 6, 'template': 'Review test results and fix any issues for {task_name}', 'wait_for_file': 'docs/reviews/review_{task_id}.md', 'control_phrase': 'Review complete!', 'timeout': 90},
                    {'instruction_id': 7, 'template': 'Generate final report for {task_name}', 'wait_for_file': 'docs/results/final_report_{task_id}.md', 'control_phrase': 'Report generated!', 'timeout': 60},
                    {'instruction_id': 8, 'template': 'Commit changes and push for {task_name}', 'wait_for_file': 'docs/results/commit_status_{task_id}.md', 'control_phrase': 'Коммит выполнен!', 'timeout': 60}
                ]
            }
        }

    def get_project_dir(self):
        return Path('/tmp/test_project')

    def get_docs_dir(self):
        return Path('/tmp/test_project/docs')

    def get_status_file(self):
        return '/tmp/test_project/codeAgentProjectStatus.md'
    
    def get(self, key, default=None):
        keys = key.split('.')
        val = self.config
        for k in keys:
            if isinstance(val, dict) and k in val:
                val = val[k]
            else:
                return default
        return val


# Мок для ServerLogger
class MockServerLogger:
    def log_initialization(self, data: Dict[str, Any]): pass
    def log_server_shutdown(self, reason: str): pass
    def log_task_start(self, task_num: int, total_tasks: int, task_text: str): pass
    def log_error(self, message: str, exc: Exception = None): pass
    def log_warning(self, message: str): pass
    def log_info(self, message: str): pass

# Мок для CursorCLIInterface
class MockCursorCLI:
    def is_available(self): return True
    def check_version(self): return "1.0.0"
    def execute_instruction(self, instruction: str, task_id: str, working_dir: str, timeout: int) -> Dict[str, Any]:
        return {"success": True, "output": f"Executed: {instruction}", "return_code": 0}
    def prepare_for_new_task(self): return True
    def current_chat_id(self): return "mock_chat_id"

# Мок для TaskLogger
class MockTaskLogger:
    def __init__(self, task_id: str, task_name: str):
        self.task_id = task_id
        self.task_name = task_name
    def set_phase(self, phase: TaskPhase, stage: int = 1, instruction_num: int = 1): pass
    def log_debug(self, message: str): pass
    def log_info(self, message: str): pass
    def log_warning(self, message: str): pass
    def log_error(self, message: str, exc: Exception = None): pass
    def log_completion(self, success: bool, summary: str): pass
    def close(self): pass
    def log_instruction(self, instruction_num: int, instruction_text: str, task_type: str): pass
    def log_cursor_response(self, result: Dict[str, Any], brief: bool): pass
    def log_waiting_result(self, file_path: str, timeout: int): pass
    def log_new_chat(self, chat_id: Optional[str] = None): pass

# Мок для CheckpointManager
class MockCheckpointManager:
    def __init__(self):
        self.checkpoint_data = {'tasks': []}
        self._was_clean_shutdown = True
    def get_recovery_info(self): return {"was_clean_shutdown": self._was_clean_shutdown, "last_start_time": None, "last_stop_time": None, "session_id": "test_session", "iteration_count": 0, "incomplete_tasks_count": 0, "failed_tasks_count": 0}
    def get_statistics(self): return {'completed': 0, 'failed': 0, 'pending': 0, 'in_progress': 0, 'total_tasks': 0, 'iteration_count': 0}
    def is_task_completed(self, task_text: str): return False
    def mark_task_start(self, task_id: str): pass
    def add_task(self, task_id: str, task_text: str, metadata: Dict[str, Any]): pass
    def mark_task_completed(self, task_id: str): pass
    def mark_task_failed(self, task_id: str, error_message: str): pass
    def mark_server_start(self, session_id: str): pass
    def mark_server_stop(self, clean: bool): self._was_clean_shutdown = clean
    def get_iteration_count(self): return 0
    def clear_old_tasks(self, keep_last_n: int): pass
    def reset_interrupted_task(self): pass
    def _save_checkpoint(self, create_backup: bool = True): pass
    def _find_task(self, task_id: str): return None
    def get_instruction_progress(self, task_id: str): return None
    def update_instruction_progress(self, task_id: str, instruction_num: int, total_instructions: int): pass
    def get_current_task(self): return None
    def was_clean_shutdown(self): return self._was_clean_shutdown


# Мок для StatusManager
class MockStatusManager:
    def update_task_status(self, task_name: str, status: str, details: str): pass
    def append_status(self, status_text: str, level: int = 1): pass

# Мок для SessionTracker
class MockSessionTracker:
    def __init__(self):
        self.current_session_id = "mock_session_id"
    def can_generate_todo(self, max_generations: int): return False
    def record_generation(self, todo_file: str, task_count: int, metadata: Dict[str, Any]): pass

# Мок для DI Container
class MockDiContainer:
    def __init__(self, project_dir: Path, config: Dict[str, Any], status_file: str):
        self._instances = {}
        self.project_dir = project_dir
        self.config = config
        self.status_file = status_file
        self.register_instance(TodoManager, TodoManager(project_dir, config.get('todo_manager')))
        self.register_instance(CheckpointManager, MockCheckpointManager())
        self.register_instance(StatusManager, MockStatusManager())
        self.register_instance(MockServerLogger, MockServerLogger())
        self.register_instance(type('IAgent', (object,), {}), type('MockAgent', (object,), {'tools': []})())
        self.register_instance(type('ITaskManager', (object,), {}), type('MockTaskManager', (object,), {})())
        self.register_instance(type('IMultiLevelVerificationManager', (object,), {}), type('MockVerificationManager', (object,), {})())
        self.register_instance(type('IServer', (object,), {}), type('MockServer', (object,), {'_is_running': True})()) # Mock IServer


    def resolve(self, interface_type):
        if interface_type == TodoManager:
            # Возвращаем созданный экземпляр TodoManager
            return self._instances.get(TodoManager)
        elif interface_type.__name__ == 'ITodoManager':
            return self._instances.get(TodoManager)
        elif interface_type.__name__ == 'ICheckpointManager':
            return self._instances.get(CheckpointManager)
        elif interface_type.__name__ == 'IStatusManager':
            return self._instances.get(StatusManager)
        elif interface_type.__name__ == 'ILogger':
            return self._instances.get(MockServerLogger)
        elif interface_type.__name__ == 'IAgent':
            return self._instances.get(type('IAgent', (object,), {}))
        elif interface_type.__name__ == 'ITaskManager':
            return self._instances.get(type('ITaskManager', (object,), {}))
        elif interface_type.__name__ == 'IMultiLevelVerificationManager':
            return self._instances.get(type('IMultiLevelVerificationManager', (object,), {}))
        elif interface_type.__name__ == 'IServer':
            return self._instances.get(type('IServer', (object,), {}))
        else:
            raise ValueError(f"Unknown interface type: {interface_type}")

    def register_instance(self, interface_type, instance):
        self._instances[interface_type] = instance


@pytest.fixture
def mock_code_agent_server():
    # Создаем временную директорию проекта для тестов
    temp_dir = Path("/tmp/test_project")
    temp_dir.mkdir(exist_ok=True, parents=True)
    (temp_dir / "docs" / "results").mkdir(exist_ok=True, parents=True)
    (temp_dir / "docs" / "reviews").mkdir(exist_ok=True, parents=True)
    (temp_dir / "todo").mkdir(exist_ok=True, parents=True)

    # Создаем фиктивный todo.md для TodoManager
    todo_file = temp_dir / "todo" / "todo.md"
    todo_file.write_text("- [ ] Задача 1\n- [ ] Задача 2\n")

    # Создаем фиктивный config.yaml
    config_file = Path("config/config.yaml")
    config_file.parent.mkdir(exist_ok=True, parents=True)
    config_file.write_text("""
agent:
  role: Test Role
  goal: Test Goal
  backstory: Test Backstory
  allow_code_execution: true
  verbose: false
server:
  check_interval: 1
  task_delay: 0
  max_iterations: 2
  http_port: 3456
  http_enabled: false
  mcp_enabled: false
  auto_reload: false
  reload_on_py_changes: false
  auto_todo_generation:
    enabled: false
cursor:
  interface_type: cli
  cli:
    cli_path: mock_cursor_cli
    timeout: 10
docs:
  supported_extensions:
    - .md
    - .txt
  max_file_size: 1000000
git:
  smart_git:
    allowed_branches:
      - smart
    auto_push_timeout: 60
instructions:
  default:
    - instruction_id: 1
      template: Default instruction: {task_name}
      wait_for_file: docs/results/result_{task_id}.md
      control_phrase: Report complete!
      timeout: 60
  test:
    - instruction_id: 1
      template: Plan tests for {task_name}
      wait_for_file: docs/results/plan_{task_id}.md
      control_phrase: Plan generated!
      timeout: 60
    - instruction_id: 2
      template: Write static tests for {task_name}
      wait_for_file: docs/results/test_static_{task_id}.md
      control_phrase: Static tests written!
      timeout: 60
    - instruction_id: 3
      template: Write smoke tests for {task_name}
      wait_for_file: docs/results/test_smoke_{task_id}.md
      control_phrase: Smoke tests written!
      timeout: 60
    - instruction_id: 4
      template: Write integration tests for {task_name}
      wait_for_file: docs/results/test_integration_{task_id}.md
      control_phrase: Integration tests written!
      timeout: 120
    - instruction_id: 5
      template: Run all tests and capture results for {task_name}
      wait_for_file: docs/results/test_results_{task_id}.md
      control_phrase: Tests executed!
      timeout: 120
    - instruction_id: 6
      template: Review test results and fix any issues for {task_name}
      wait_for_file: docs/reviews/review_{task_id}.md
      control_phrase: Review complete!
      timeout: 90
    - instruction_id: 7
      template: Generate final report for {task_name}
      wait_for_file: docs/results/final_report_{task_id}.md
      control_phrase: Report generated!
      timeout: 60
    - instruction_id: 8
      template: Commit changes and push for {task_name}
      wait_for_file: docs/results/commit_status_{task_id}.md
      control_phrase: Коммит выполнен!
      timeout: 60
""")

    # Мокируем функции DI-контейнера в src.server
    original_create_default_container = CodeAgentServer.di_container
    original_create_executor_agent = CodeAgentServer.agent
    original_create_cursor_cli_interface = CodeAgentServer._init_cursor_cli


    # Заменяем их на моки
    def mock_create_default_container(project_dir, config, status_file):
        return MockDiContainer(project_dir, config, status_file)

    def mock_create_executor_agent(*args, **kwargs):
        return type('MockAgent', (object,), {'tools': []})() # Mock agent with empty tools

    def mock_init_cursor_cli(self):
        return MockCursorCLI()

    CodeAgentServer.di_container = mock_create_default_container
    CodeAgentServer.agent = mock_create_executor_agent
    CodeAgentServer._init_cursor_cli = mock_init_cursor_cli


    server = CodeAgentServer(project_dir=str(temp_dir))
    server.todo_manager = TodoManager(temp_dir, server.config.config.get('todo_manager'))
    server.checkpoint_manager = MockCheckpointManager()
    server.status_manager = MockStatusManager()
    server.server_logger = MockServerLogger()
    server.session_tracker = MockSessionTracker()
    server.cursor_cli = MockCursorCLI() # Ensure cursor_cli is mocked correctly

    # Устанавливаем мок LLMManager
    server.llm_manager = type('MockLLMManager', (object,), {
        'is_llm_available': lambda: True,
        'generate_adaptive': lambda prompt, response_format: type('MockLLMResponse', (object,), {'success': True, 'content': 'Mock LLM result'})()
    })()

    yield server

    # Очистка
    # Удаляем временные файлы
    if todo_file.exists():
        todo_file.unlink()
    if config_file.exists():
        config_file.unlink()
    if (temp_dir / "docs" / "results").exists():
        import shutil
        shutil.rmtree(temp_dir / "docs" / "results")
    if (temp_dir / "docs" / "reviews").exists():
        import shutil
        shutil.rmtree(temp_dir / "docs" / "reviews")
    if (temp_dir / "todo").exists():
        import shutil
        shutil.rmtree(temp_dir / "todo")
    if temp_dir.exists():
        temp_dir.rmdir()

    # Восстанавливаем оригинальные функции
    CodeAgentServer.di_container = original_create_default_container
    CodeAgentServer.agent = original_create_executor_agent
    CodeAgentServer._init_cursor_cli = original_create_cursor_cli_interface


class TestCodeAgentServerNewStatic:
    \"\"\"
    Статические тесты для новой функциональности в src/server.py:
    - Интеллектуальная LLM система выполнения задач
    - Проверка полезности задач через LLM
    - Проверка соответствия TODO плану через LLM
    - Улучшенная обработка ошибок Cursor/Docker
    - Логирование статуса системы
    \"\"\"

    def test_llm_execution_methods_exist(self, mock_code_agent_server):
        \"\"\"Проверяем наличие методов для выполнения задач через LLM\"\"\"
        server = mock_code_agent_server
        assert inspect.iscoroutinefunction(server._execute_task_via_llm)
        assert callable(server._create_task_execution_prompt)
        assert callable(server._process_llm_task_result)
        assert callable(server._check_expected_files_from_result)

    def test_task_usefulness_check_method_exists(self, mock_code_agent_server):
        \"\"\"Проверяем наличие метода для проверки полезности задачи через LLM\"\"\"
        server = mock_code_agent_server
        assert callable(server._check_task_usefulness)

    def test_todo_matches_plan_check_method_exists(self, mock_code_agent_server):
        \"\"\"Проверяем наличие метода для проверки соответствия TODO плану через LLM\"\"\"
        server = mock_code_agent_server
        assert callable(server._check_todo_matches_plan)

    def test_error_handling_methods_exist(self, mock_code_agent_server):
        \"\"\"Проверяем наличие методов для улучшенной обработки ошибок Cursor\"\"\"
        server = mock_code_agent_server
        assert callable(server._handle_cursor_error)
        assert callable(server._is_critical_cursor_error)
        assert callable(server._is_unexpected_cursor_error)
        assert callable(server._restart_cursor_environment)

    def test_llm_execution_method_signatures(self, mock_code_agent_server):
        \"\"\"Проверяем сигнатуры методов LLM выполнения задач\"\"\"\
        server = mock_code_agent_server

        # _execute_task_via_llm
        sig = inspect.signature(server._execute_task_via_llm)
        assert 'todo_item' in sig.parameters
        assert 'task_type' in sig.parameters
        assert 'task_logger' in sig.parameters
        assert sig.return_annotation == bool

        # _create_task_execution_prompt
        sig = inspect.signature(server._create_task_execution_prompt)
        assert 'todo_item' in sig.parameters
        assert 'task_type' in sig.parameters
        assert sig.return_annotation == str

        # _process_llm_task_result
        sig = inspect.signature(server._process_llm_task_result)
        assert 'todo_item' in sig.parameters
        assert 'result_content' in sig.parameters
        assert 'task_logger' in sig.parameters
        assert sig.return_annotation == bool

        # _check_expected_files_from_result
        sig = inspect.signature(server._check_expected_files_from_result)
        assert 'result_content' in sig.parameters
        assert sig.return_annotation == bool

    def test_task_usefulness_check_signature(self, mock_code_agent_server):
        \"\"\"Проверяем сигнатуру метода _check_task_usefulness\"\"\"\
        server = mock_code_agent_server
        sig = inspect.signature(server._check_task_usefulness)
        assert 'todo_item' in sig.parameters
        assert get_type_hints(server._check_task_usefulness)['return'] == tuple

    def test_todo_matches_plan_check_signature(self, mock_code_agent_server):
        \"\"\"Проверяем сигнатуру метода _check_todo_matches_plan\"\"\"\
        server = mock_code_agent_server
        sig = inspect.signature(server._check_todo_matches_plan)
        assert 'task_id' in sig.parameters
        assert 'todo_item' in sig.parameters
        assert get_type_hints(server._check_todo_matches_plan)['return'] == tuple

    def test_error_handling_method_signatures(self, mock_code_agent_server):
        \"\"\"Проверяем сигнатуры методов обработки ошибок\"\"\"\
        server = mock_code_agent_server

        # _handle_cursor_error
        sig = inspect.signature(server._handle_cursor_error)
        assert 'error_message' in sig.parameters
        assert 'task_logger' in sig.parameters
        assert sig.return_annotation == bool

        # _is_critical_cursor_error
        sig = inspect.signature(server._is_critical_cursor_error)
        assert 'error_message' in sig.parameters
        assert sig.return_annotation == bool

        # _is_unexpected_cursor_error
        sig = inspect.signature(server._is_unexpected_cursor_error)
        assert 'error_message' in sig.parameters
        assert sig.return_annotation == bool

        # _restart_cursor_environment
        sig = inspect.signature(server._restart_cursor_environment)
        assert sig.return_annotation == bool

    def test_llm_manager_integration(self, mock_code_agent_server):
        \"\"\"Проверяем, что LLMManager инициализируется и доступен в CodeAgentServer\"\"\"\
        server = mock_code_agent_server
        assert hasattr(server, 'llm_manager')
        assert server.llm_manager is not None
        assert callable(getattr(server.llm_manager, 'is_llm_available', None))
        assert callable(getattr(server.llm_manager, 'generate_adaptive', None))

    def test_system_status_logging_method_exists(self, mock_code_agent_server):
        \"\"\"Проверяем наличие метода для логирования статуса системы\"\"\"\
        server = mock_code_agent_server
        assert callable(server._log_system_status)

    def test_check_recovery_needed_signature(self, mock_code_agent_server):
        \"\"\"Проверяем сигнатуру метода _check_recovery_needed\"\"\"\
        server = mock_code_agent_server
        sig = inspect.signature(server._check_recovery_needed)
        assert len(sig.parameters) == 1 # self only

    def test_sync_todos_with_checkpoint_signature(self, mock_code_agent_server):
        \"\"\"Проверяем сигнатуру метода _sync_todos_with_checkpoint\"\"\"\
        server = mock_code_agent_server
        sig = inspect.signature(server._sync_todos_with_checkpoint)
        assert len(sig.parameters) == 1 # self only

    def test_filter_completed_tasks_signature(self, mock_code_agent_server):
        \"\"\"Проверяем сигнатуру метода _filter_completed_tasks\"\"\"\
        server = mock_code_agent_server
        sig = inspect.signature(server._filter_completed_tasks)
        assert 'tasks' in sig.parameters
        assert get_type_hints(server._filter_completed_tasks)['return'] == List[TodoItem]

    def test_server_core_creation_exists(self, mock_code_agent_server):
        \"\"\"Проверяем наличие метода _create_server_core\"\"\"\
        server = mock_code_agent_server
        assert callable(server._create_server_core)
        # Убедимся, что ServerCore был инициализирован во время создания сервера
        assert hasattr(server, 'server_core')
        assert server.server_core is not None

    def test_server_core_execution_delegation(self, mock_code_agent_server):
        \"\"\"Проверяем, что run_iteration делегирует вызов server_core.execute_full_iteration\"\"\"\
        server = mock_code_agent_server
        
        # Мокируем server_core.execute_full_iteration
        mock_execute_full_iteration_called = False
        async def mock_execute_full_iteration(*args, **kwargs):
            nonlocal mock_execute_full_iteration_called
            mock_execute_full_iteration_called = True
            return False, [] # Возвращаем False и пустой список задач
        
        server.server_core.execute_full_iteration = mock_execute_full_iteration
        
        import asyncio
        asyncio.run(server.run_iteration(1))
        
        assert mock_execute_full_iteration_called

    def test_error_learning_system_reference(self, mock_code_agent_server):
        \"\"\"Проверяем, что в _process_llm_task_result упоминается ErrorLearningSystem\"\"\"\
        server = mock_code_agent_server
        source = inspect.getsource(server._process_llm_task_result)
        assert 'ErrorLearningSystem' in source

    def test_llm_manager_shutdown_called(self, mock_code_agent_server):
        \"\"\"Проверяем, что метод shutdown LLMManager вызывается при остановке сервера\"\"\"\
        server = mock_code_agent_server
        mock_shutdown_called = False

        async def mock_shutdown():
            nonlocal mock_shutdown_called
            mock_shutdown_called = True

        server.llm_manager.shutdown = mock_shutdown

        import asyncio
        asyncio.run(server.start())
        asyncio.run(server.stop_server()) # Нужно явным образом вызвать остановку

        # Проверяем, что shutdown был вызван
        assert mock_shutdown_called
        
# Нужно добавить фикстуру для остановки сервера
@pytest.fixture
async def running_mock_code_agent_server(mock_code_agent_server):
    server = mock_code_agent_server
    # Для тестов нам не нужен запущенный HTTP-сервер, но _setup_http_server пытается его запустить.
    # Мы его мокнули, но если бы это был реальный Flask, он бы запустил.
    # В рамках статических тестов достаточно, что метод существует.
    # Для дымовых и интеграционных тестов придется более тонко мокать Flask.
    
    # Мокируем run_server_loop, чтобы он не запускал бесконечный цикл
    async def mock_run_server_loop():
        # Устанавливаем _is_running в True, чтобы _log_system_status мог работать
        server._is_running = True
        server._log_system_status()
        # Имитируем остановку
        server._is_running = False

    server._run_server_loop = mock_run_server_loop
    
    # Мокируем http_server.shutdown, чтобы избежать ошибок при остановке
    server.http_server = type('MockHTTPServer', (object,), {'shutdown': lambda: None})()

    # Запускаем сервер
    await server.start()
    yield server
    # Остановка сервера (если еще не остановлен)
    if server._is_running:
        with server._stop_lock:
            server._should_stop = True
        # Ждем, пока поток сервера остановится
        # Здесь это не совсем корректно, так как мы мокнули _run_server_loop
        # Но для завершения асинхронной функции этого достаточно
        # В реальной реализации тут должен быть await server._run_server_loop()
        pass

# Тест, который использует новую фикстуру
@pytest.mark.asyncio
async def test_log_system_status_execution(running_mock_code_agent_server, caplog):
    \"\"\"Проверяем, что _log_system_status вызывается и логирует информацию\"\"\"
    server = running_mock_code_agent_server
    
    # Проверяем, что в логах есть сообщения от _log_system_status
    assert "СТАТУС КОМПОНЕНТОВ СИСТЕМЫ" in caplog.text
    assert "Docker" in caplog.text
    assert "LLM" in caplog.text
    assert "Cursor CLI" in caplog.text
    assert "Smart Agent" in caplog.text

