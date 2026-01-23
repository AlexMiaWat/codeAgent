"""
Mock implementations for new interfaces.

These are temporary implementations used for testing DI container integration
and will be replaced with real implementations later.
"""

from typing import Dict, Any, Optional, List
from pathlib import Path
from .interfaces import IServer, IAgent, ITaskManager, TaskExecutionState
from ..todo_manager import TodoItem


class MockServer(IServer):
    """Mock implementation of IServer for testing DI integration."""

    def __init__(self, project_dir: Path, config: Optional[Dict[str, Any]] = None) -> None:
        self.project_dir = project_dir
        self.config = config or {}
        self._running = False

    def start(self) -> bool:
        self._running = True
        return True

    def stop(self) -> bool:
        self._running = False
        return True

    def restart(self) -> bool:
        self.stop()
        return self.start()

    def is_running(self) -> bool:
        return self._running

    def get_server_status(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "project_dir": str(self.project_dir),
            "config": self.config
        }

    def execute_task(self, task_id: str) -> bool:
        return True

    def get_pending_tasks(self) -> List[Dict[str, Any]]:
        return []

    def get_active_tasks(self) -> List[Dict[str, Any]]:
        return []

    def get_metrics(self) -> Dict[str, Any]:
        return {"mock": True}

    def reload_configuration(self) -> bool:
        return True

    def get_component_status(self, component_name: str) -> Dict[str, Any]:
        return {"component": component_name, "status": "mock"}

    def is_healthy(self) -> bool:
        return True

    def get_status(self) -> Dict[str, Any]:
        return self.get_server_status()

    def dispose(self) -> None:
        self._running = False


class MockAgentManager(IAgent):
    """Mock implementation of IAgent for testing DI integration."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.config = config or {}
        self._agents = {}

    def create_agent(self, agent_type: str, config: Optional[Dict[str, Any]] = None) -> Optional[str]:
        agent_id = f"mock_agent_{len(self._agents)}"
        self._agents[agent_id] = {
            "type": agent_type,
            "config": config or {},
            "status": "created"
        }
        return agent_id

    def get_agent(self, agent_id: str):
        return self._agents.get(agent_id)

    def remove_agent(self, agent_id: str) -> bool:
        if agent_id in self._agents:
            del self._agents[agent_id]
            return True
        return False

    def get_available_agents(self) -> List[str]:
        return ["executor", "smart", "custom"]

    def get_active_agents(self) -> List[str]:
        return list(self._agents.keys())

    def configure_agent(self, agent_id: str, config: Dict[str, Any]) -> bool:
        if agent_id in self._agents:
            self._agents[agent_id]["config"].update(config)
            return True
        return False

    def execute_with_agent(self, agent_id: str, task_description: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return {
            "agent_id": agent_id,
            "task": task_description,
            "status": "completed",
            "result": "mock execution result"
        }

    def get_agent_status(self, agent_id: str) -> Dict[str, Any]:
        if agent_id in self._agents:
            return self._agents[agent_id]
        return {"error": "agent not found"}

    def validate_agent_config(self, agent_type: str, config: Dict[str, Any]) -> bool:
        return True

    def get_agent_types_info(self) -> Dict[str, Dict[str, Any]]:
        return {
            "executor": {"description": "Basic executor agent"},
            "smart": {"description": "Advanced smart agent"},
            "custom": {"description": "Custom agent"}
        }

    def is_healthy(self) -> bool:
        return True

    def get_status(self) -> Dict[str, Any]:
        return {"agents_count": len(self._agents)}

    def dispose(self) -> None:
        self._agents.clear()


class MockTaskManager(ITaskManager):
    """Mock implementation of ITaskManager for testing DI integration."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.config = config or {}
        self._executions = {}

    def initialize_task_execution(self, task: TodoItem) -> str:
        execution_id = f"execution_{len(self._executions)}"
        self._executions[execution_id] = {
            "task": task,
            "state": TaskExecutionState.INITIALIZING,
            "progress": 0
        }
        return execution_id

    def execute_task_step(self, execution_id: str, step_data: Dict[str, Any]) -> Dict[str, Any]:
        if execution_id in self._executions:
            self._executions[execution_id]["state"] = TaskExecutionState.EXECUTING
            return {"status": "executing", "step": step_data}
        return {"error": "execution not found"}

    def monitor_task_progress(self, execution_id: str) -> Dict[str, Any]:
        if execution_id in self._executions:
            return self._executions[execution_id]
        return {"error": "execution not found"}

    def handle_task_failure(self, execution_id: str, error: Exception, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if execution_id in self._executions:
            self._executions[execution_id]["state"] = TaskExecutionState.FAILED
            self._executions[execution_id]["error"] = str(error)
            return {"status": "handled", "action": "logged"}
        return {"error": "execution not found"}

    def finalize_task_execution(self, execution_id: str) -> bool:
        if execution_id in self._executions:
            self._executions[execution_id]["state"] = TaskExecutionState.COMPLETED
            return True
        return False

    def cancel_task_execution(self, execution_id: str) -> bool:
        if execution_id in self._executions:
            self._executions[execution_id]["state"] = TaskExecutionState.CANCELLED
            return True
        return False

    def get_execution_status(self, execution_id: str) -> Dict[str, Any]:
        return self.monitor_task_progress(execution_id)

    def get_active_executions(self) -> List[str]:
        return [eid for eid, data in self._executions.items()
                if data["state"] in [TaskExecutionState.EXECUTING, TaskExecutionState.MONITORING]]

    def get_execution_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        history = list(self._executions.values())
        if limit:
            history = history[-limit:]
        return history

    def retry_execution(self, execution_id: str) -> str:
        if execution_id in self._executions:
            new_id = f"retry_{execution_id}"
            self._executions[new_id] = self._executions[execution_id].copy()
            self._executions[new_id]["state"] = TaskExecutionState.PENDING
            return new_id
        raise ValueError("execution not found")

    def get_execution_metrics(self) -> Dict[str, Any]:
        return {
            "total_executions": len(self._executions),
            "active": len(self.get_active_executions()),
            "completed": sum(1 for e in self._executions.values()
                           if e["state"] == TaskExecutionState.COMPLETED)
        }

    def validate_execution_requirements(self, execution_id: str) -> Dict[str, Any]:
        if execution_id in self._executions:
            return {"valid": True, "requirements": []}
        return {"valid": False, "error": "execution not found"}

    def is_healthy(self) -> bool:
        return True

    def get_status(self) -> Dict[str, Any]:
        return self.get_execution_metrics()

    def dispose(self) -> None:
        self._executions.clear()