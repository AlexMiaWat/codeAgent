import abc
from typing import Dict, Any, List, Optional
from pathlib import Path

# --- Core Interfaces ---

class IConfigLoader(abc.ABC):
    @abc.abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        pass

    @abc.abstractmethod
    def get_project_dir(self) -> Path:
        pass

    @abc.abstractmethod
    def get_docs_dir(self) -> Path:
        pass

    @abc.abstractmethod
    def get_status_file(self) -> Path:
        pass

    @property
    @abc.abstractmethod
    def config(self) -> Dict[str, Any]:
        pass

class ITodoManager(abc.ABC):
    @abc.abstractmethod
    def get_next_todo_item(self) -> Optional[Any]: # Replace Any with actual TodoItem type
        pass

    @abc.abstractmethod
    def mark_todo_item_done(self, todo_id: str) -> None:
        pass

    @abc.abstractmethod
    def add_todo_item(self, description: str, priority: str = "medium") -> None:
        pass

    @abc.abstractmethod
    def get_all_todo_items(self) -> List[Any]: # Replace Any with actual TodoItem type
        pass

class IStatusManager(abc.ABC):
    @abc.abstractmethod
    def set_status(self, key: str, value: Any) -> None:
        pass

    @abc.abstractmethod
    def get_status(self, key: str, default: Any = None) -> Any:
        pass

    @abc.abstractmethod
    def save_status(self) -> None:
        pass

class ICheckpointManager(abc.ABC):
    @abc.abstractmethod
    def save_checkpoint(self, data: Dict[str, Any]) -> None:
        pass

    @abc.abstractmethod
    def load_checkpoint(self) -> Optional[Dict[str, Any]]:
        pass

    @abc.abstractmethod
    def clear_checkpoint(self) -> None:
        pass

class ILogger(abc.ABC):
    @abc.abstractmethod
    def log_initialization(self, info: Dict[str, Any]) -> None:
        pass

    @abc.abstractmethod
    def log_task_start(self, task_id: str, description: str) -> None:
        pass

    @abc.abstractmethod
    def log_task_end(self, task_id: str, success: bool, output: Optional[str] = None) -> None:
        pass

    @abc.abstractmethod
    def info(self, message: str, **kwargs) -> None:
        pass

    @abc.abstractmethod
    def debug(self, message: str, **kwargs) -> None:
        pass

    @abc.abstractmethod
    def warning(self, message: str, **kwargs) -> None:
        pass

    @abc.abstractmethod
    def error(self, message: str, **kwargs) -> None:
        pass

    @abc.abstractmethod
    def critical(self, message: str, **kwargs) -> None:
        pass

class IAgent(abc.ABC):
    @abc.abstractmethod
    def create_crew_for_task(self, task_description: str, tools: List[Any]) -> Any: # Replace Any with actual Crew type
        pass

    @abc.abstractmethod
    def execute_crew(self, crew: Any) -> str: # Replace Any with actual Crew type
        pass

class ITaskManager(abc.ABC):
    @abc.abstractmethod
    def execute_task(self, task_id: str, instruction: str) -> Dict[str, Any]:
        pass

    @abc.abstractmethod
    def process_result(self, task_id: str, result: Dict[str, Any]) -> None:
        pass

class IServer(abc.ABC):
    @abc.abstractmethod
    async def start(self) -> None:
        pass

    @abc.abstractmethod
    async def stop(self) -> None:
        pass

    @abc.abstractmethod
    def request_reload(self) -> None:
        pass

    @property
    @abc.abstractmethod
    def is_running(self) -> bool:
        pass

class IQualityGateManager(abc.ABC):
    @abc.abstractmethod
    def run_quality_gates(self, changes: str) -> bool:
        pass

class IMultiLevelVerificationManager(abc.ABC):
    @abc.abstractmethod
    async def verify_task_result(self, task_id: str, instructions: str, result: Dict[str, Any]) -> bool:
        pass

class ICursorExecutor(abc.ABC):
    @abc.abstractmethod
    def execute_instruction(self, instruction: str) -> Dict[str, Any]:
        pass

    @abc.abstractmethod
    def is_cursor_cli_available(self) -> bool:
        pass

class ISessionTracker(abc.ABC):
    @abc.abstractmethod
    def increment_session_count(self) -> int:
        pass

    @abc.abstractmethod
    def get_session_count(self) -> int:
        pass

    @abc.abstractmethod
    def reset_session_count(self) -> None:
        pass

    @abc.abstractmethod
    def can_generate_new_todo(self, max_generations: int) -> bool:
        pass

class ITodoCheckpointSynchronizer(abc.ABC):
    @abc.abstractmethod
    def check_recovery_needed(self) -> None:
        pass

    @abc.abstractmethod
    def sync_todos_with_checkpoint(self) -> None:
        pass

class IInstructionProcessor(abc.ABC):
    @abc.abstractmethod
    def determine_task_type(self, todo_item: Any) -> str: # Replace Any with actual TodoItem type
        pass

    @abc.abstractmethod
    def get_instruction_template(self, task_type: str, instruction_id: int = 1) -> Optional[Dict[str, Any]]:
        pass

    @abc.abstractmethod
    def get_all_instruction_templates(self, task_type: str) -> List[Dict[str, Any]]:
        pass

    @abc.abstractmethod
    def format_instruction(self, template: Dict[str, Any], todo_item: Any, task_id: str, instruction_num: int = 1) -> str: # Replace Any with actual TodoItem type
        pass
