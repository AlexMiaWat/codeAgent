"""
Module for handling Cursor CLI interactions and error recovery.
"""

import logging
import time
import subprocess
import sys
import re
import threading
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from src.cursor_cli_interface import CursorCLIInterface, create_cursor_cli_interface
from src.task_logger import TaskLogger, Colors
from src.exceptions import ServerReloadException 

logger = logging.getLogger(__name__)

# Constants for Cursor error handling
MAX_CURSOR_ERRORS = 3  # Max consecutive errors before restart
CURSOR_ERROR_DELAY_INITIAL = 30  # Initial delay on error (seconds)
CURSOR_ERROR_DELAY_INCREMENT = 30  # Delay increment per new error (seconds)

# Default timeouts
DEFAULT_CURSOR_CLI_TIMEOUT = 300  # Default timeout for Cursor CLI (seconds)

class CursorExecutor:
    def __init__(self, config: Dict[str, Any], project_dir: Path, mcp_server=None, mcp_enabled: bool = False, stop_lock: threading.Lock = None, reload_lock: threading.Lock = None, task_in_progress_lock: threading.Lock = None, server_logger=None, status_manager=None, checkpoint_manager=None):
        self.config = config
        self.project_dir = project_dir
        self.mcp_server = mcp_server
        self.mcp_enabled = mcp_enabled
        self._stop_lock = stop_lock or threading.Lock()
        self._reload_lock = reload_lock or threading.Lock()
        self._task_in_progress_lock = task_in_progress_lock or threading.Lock()
        self.server_logger = server_logger
        self.status_manager = status_manager
        self.checkpoint_manager = checkpoint_manager

        self._cursor_error_count = 0
        self._cursor_error_lock = threading.Lock()
        self._last_cursor_error = None
        self._cursor_error_delay = 0
        self._max_cursor_errors = MAX_CURSOR_ERRORS
        self._should_stop = False 
        self._should_reload = False
        self._reload_after_instruction = False 

        self.cursor_cli = self._init_cursor_cli()

        cursor_config = self.config.get('cursor', {})
        interface_type = cursor_config.get('interface_type', 'cli')
        self.use_cursor_cli = (
            interface_type == 'cli' and
            self.cursor_cli and
            self.cursor_cli.is_available()
        )

    def _init_cursor_cli(self) -> Optional[CursorCLIInterface]:
        """
        Initializes the Cursor CLI interface.

        Returns:
            CursorCLIInterface instance or None if unavailable.
        """
        try:
            cursor_config = self.config.get('cursor', {})
            cli_config = cursor_config.get('cli', {})

            cli_path = cli_config.get('cli_path')
            timeout = cli_config.get('timeout', DEFAULT_CURSOR_CLI_TIMEOUT)
            headless = cli_config.get('headless', True)

            logger.debug(f"Initializing Cursor CLI: timeout={timeout} seconds (from config: {cli_config.get('timeout', 'not specified')}, default: {DEFAULT_CURSOR_CLI_TIMEOUT})")

            agent_config = self.config.get('agent', {})
            cli_interface = create_cursor_cli_interface(
                cli_path=cli_path,
                timeout=timeout,
                headless=headless,
                project_dir=str(self.project_dir),
                agent_role=agent_config.get('role')
            )

            if cli_interface and cli_interface.is_available():
                version = cli_interface.check_version()
                if version:
                    logger.info(f"Cursor CLI version: {version}")
                return cli_interface
            else:
                logger.info("Cursor CLI not found on system")
                return cli_interface

        except Exception as e:
            logger.warning(f"Error initializing Cursor CLI: {e}")
            return None

    def execute_cursor_instruction(
        self,
        instruction: str,
        task_id: str,
        timeout: Optional[int] = None,
    ) -> dict:
        """
        Executes an instruction via Cursor CLI (if available).

        Args:
            instruction: The instruction text to execute.
            task_id: Task identifier.
            timeout: Execution timeout (if None, uses config value).

        Returns:
            Dictionary with execution result.
        """
        if not self.cursor_cli or not self.cursor_cli.is_available():
            logger.warning("Cursor CLI is unavailable, instruction cannot be executed")
            return {
                "task_id": task_id,
                "success": False,
                "error": "Cursor CLI is unavailable",
                "cli_available": False
            }

        # Update MCP context
        if self.mcp_server and self.mcp_enabled:
            try:
                self.mcp_server.update_task_context(task_id, {
                    "instruction": instruction,
                    "status": "executing",
                    "type": "cursor_instruction",
                    "start_time": datetime.utcnow().isoformat()
                })
            except Exception as e:
                logger.warning(f"Failed to update MCP task context before execution: {e}")


        logger.info(f"Executing instruction for task {task_id} via Cursor CLI")

        result = self.cursor_cli.execute_instruction(
            instruction=instruction,
            task_id=task_id,
            working_dir=str(self.project_dir),
            timeout=timeout
        )

        # Update MCP result
        if self.mcp_server and self.mcp_enabled:
            task_result = {
                "task_id": task_id,
                "success": result["success"],
                "type": "cursor_instruction",
                "completed_at": datetime.utcnow().isoformat()
            }

            if result["success"]:
                logger.info(f"Instruction for task {task_id} executed successfully")
                task_result["status"] = "completed"
            else:
                logger.warning(f"Instruction for task {task_id} failed with error: {result.get('error_message')}")
                task_result["status"] = "failed"
                task_result["error"] = result.get('error_message')

            try:
                self.mcp_server.update_task_result(task_id, task_result)
            except Exception as e:
                logger.warning(f"Failed to update MCP task result after execution: {e}")

        return result

    def execute_instruction_with_retry(
        self,
        instruction: str,
        task_id: str,
        timeout: Optional[int],
        task_logger: TaskLogger,
        instruction_num: int,
    ) -> dict:
        """
        Executes an instruction via Cursor with retry handling for repeated errors.
        
        Args:
            instruction: Instruction text.
            task_id: Task ID.
            timeout: Execution timeout.
            task_logger: Task logger.
            instruction_num: Instruction number.
            
        Returns:
            Dictionary with execution result.
        """
        return self.execute_cursor_instruction(
            instruction=instruction,
            task_id=task_id,
            timeout=timeout,
        )

    def _is_critical_cursor_error(self, error_message: str) -> bool:
        """
        Checks if an error is critical (cannot be fixed by restart).
        
        Args:
            error_message: Error message.
            
        Returns:
            True if the error is critical.
        """
        error_lower = error_message.lower()
        critical_keywords = [
            "неоплаченный счет", "unpaid", "billing", "payment required",
            "subscription", "account suspended", "аккаунт заблокирован",
            "доступ запрещен", "access denied", "authentication failed",
            "invalid api key", "api key expired"
        ]
        return any(keyword in error_lower for keyword in critical_keywords)

    def _is_unexpected_cursor_error(self, error_message: str) -> bool:
        """
        Checks if an error is unexpected (might be fixed by Docker restart).
        
        Unexpected errors are those that can be resolved by restarting Docker,
        e.g., when Cursor CLI is unavailable or returns an unknown error.
        
        Args:
            error_message: Error message.
            
        Returns:
            True if the error is unexpected and might be fixed by Docker restart.
        """
        if not error_message:
            return False

        error_lower = error_message.lower()
        unexpected_keywords = [
            "неизвестная ошибка", "unknown error", "cursor cli недоступен",
            "cursor cli unavailable", "cli недоступен", "cli unavailable"
        ]

        if any(keyword in error_lower for keyword in unexpected_keywords):
            return True

        cli_code_pattern = r"cli вернул код (\d+)"
        match = re.search(cli_code_pattern, error_lower)
        if match:
            return_code = int(match.group(1))
            logger.debug(f"Found error 'CLI returned code {return_code}' in message: {error_message}")
            if return_code not in [137, 143]:
                logger.debug(f"Return code {return_code} is not special, considering error unexpected")
                return True
            else:
                logger.debug(f"Return code {return_code} is special (SIGKILL/SIGTERM), not considering unexpected")
        return False

    def handle_cursor_error(self, error_message: str, task_logger: TaskLogger) -> bool:
        """
        Handles Cursor errors, including repeated errors.
        
        Args:
            error_message: Error message.
            task_logger: Task logger.
            
        Returns:
            True if work can continue, False if server needs to stop.
        """
        is_critical = self._is_critical_cursor_error(error_message)
        is_unexpected = self._is_unexpected_cursor_error(error_message)
        logger.info(f"Handling Cursor error: error_message='{error_message}', is_critical={is_critical}, is_unexpected={is_unexpected}")

        with self._cursor_error_lock:
            error_key = error_message[:100] if error_message else ""
            if self._last_cursor_error == error_key:
                self._cursor_error_count += 1
            else:
                self._cursor_error_count = 1
                self._last_cursor_error = error_key
                self._cursor_error_delay = CURSOR_ERROR_DELAY_INITIAL

            if is_critical:
                logger.error("=" * 80)
                logger.error(f"CRITICAL CURSOR ERROR: {error_message}")
                logger.error("Critical error will not be fixed by restart - stopping server immediately")
                logger.error("=" * 80)
                task_logger.log_error(f"Critical Cursor error (unfixable): {error_message}", Exception(error_message))
                self.stop_server_due_to_cursor_errors(error_message)
                return False

            logger.info(f"Checking unexpected error: is_unexpected={is_unexpected}, count={self._cursor_error_count}")
            if is_unexpected and self._cursor_error_count <= 2:
                logger.info(f"Unexpected error detected (count: {self._cursor_error_count}), checking Docker usage...")
                if self.cursor_cli and hasattr(self.cursor_cli, 'cli_command'):
                    logger.debug(f"Cursor CLI available, cli_command: {self.cursor_cli.cli_command}")
                    if self.cursor_cli.cli_command == "docker-compose-agent":
                        logger.warning("=" * 80)
                        logger.warning(f"UNEXPECTED CURSOR ERROR (#{self._cursor_error_count}): {error_message}")
                        logger.warning("Restarting Docker container due to unexpected error...")
                        logger.warning("=" * 80)
                        task_logger.log_warning(f"Unexpected Cursor error - restarting Docker: {error_message}")
                        
                        container_name = "cursor-agent-life"
                        logger.info(f"Checking Cursor Agent installation in container {container_name}...")
                        
                        try:
                            agent_check = subprocess.run(
                                ["docker", "exec", container_name, "/root/.local/bin/agent", "--version"],
                                capture_output=True,
                                text=True,
                                timeout=10
                            )
                        
                            if agent_check.returncode != 0:
                                logger.warning("Cursor Agent not found in container, attempting to reinstall...")
                                self._safe_print("Reinstalling Cursor Agent in container...")
                                reinstall_result = subprocess.run(
                                    ["docker", "exec", container_name, "bash", "-c", "curl https://cursor.com/install -fsS | bash"],
                                    capture_output=True,
                                    text=True,
                                    timeout=60
                                )
                                if reinstall_result.returncode == 0:
                                    logger.info("✓ Cursor Agent reinstalled")
                                    self._safe_print("✓ Cursor Agent reinstalled")
                                else:
                                    logger.warning(f"Failed to reinstall agent: {reinstall_result.stderr[:200]}")
                            
                            self._safe_print("Attempting to restart Docker container due to unexpected error...")
                            if self._restart_cursor_environment():
                                success_msg = "Docker container restarted after unexpected error. Resetting error count."
                                self._safe_print(success_msg)
                                logger.info(success_msg)
                                task_logger.log_info("Docker container restarted after unexpected error")
                                self._cursor_error_count = 0
                                self._cursor_error_delay = 0
                                self._last_cursor_error = None
                                return True
                            else:
                                logger.warning("Docker restart failed, continuing with normal error handling")
                        except Exception as e:
                            logger.error(f"Error during Docker agent check/reinstall: {e}", exc_info=True)
                            logger.warning("Proceeding with normal error handling as Docker agent check failed.")
                    else:
                        logger.warning(f"Docker not used (cli_command='{self.cursor_cli.cli_command}'), skipping restart for unexpected error")
                else:
                    logger.warning("Cursor CLI unavailable or has no cli_command, skipping restart for unexpected error")
            elif is_unexpected:
                logger.debug(f"Unexpected error detected, but error count ({self._cursor_error_count}) > 2, skipping restart")
            else:
                logger.debug("Error is not unexpected (is_unexpected=False), normal handling")
            
            if self._cursor_error_count > 1:
                self._cursor_error_delay += CURSOR_ERROR_DELAY_INCREMENT
            
            logger.warning(f"Cursor Error #{self._cursor_error_count}: {error_message}")
            logger.warning(f"Additional delay before next request: {self._cursor_error_delay} seconds")
            task_logger.log_warning(f"Cursor Error #{self._cursor_error_count}, delay before next request: {self._cursor_error_delay}s")
            
            if self._cursor_error_count >= self._max_cursor_errors:
                critical_msg = "=" * 80 + "\n"
                critical_msg += f"CRITICAL SITUATION: Cursor error repeated {self._cursor_error_count} times\n"
                critical_msg += f"Last error: {error_message}\n"
                critical_msg += "=" * 80
                
                self._safe_print("\n" + critical_msg + "\n")
                logger.error(critical_msg)
                
                task_logger.log_error(f"Critical error: repeated {self._cursor_error_count} times", Exception(error_message))
                
                self._safe_print("Attempting to restart Docker container and clear dialogues...")
                if self._restart_cursor_environment():
                    success_msg = "Docker container and dialogues restarted. Resetting error count."
                    self._safe_print(success_msg)
                    logger.info(success_msg)
                    task_logger.log_info("Docker container restarted after critical error")
                    self._cursor_error_count = 0
                    self._cursor_error_delay = 0
                    self._last_cursor_error = None
                    return True
                else:
                    self._safe_print("Restart failed. Stopping server...")
                    task_logger.log_error("Critical error: restart failed, server stopped", Exception(error_message))
                    self.stop_server_due_to_cursor_errors(error_message)
                    return False
            
            return True

    def _restart_cursor_environment(self) -> bool:
        """
        Restarts the Docker container and clears open Cursor dialogues.
        
        Returns:
            True if restart is successful, False otherwise.
        """
        logger.info("=" * 80)
        logger.info("RESTARTING CURSOR ENVIRONMENT")
        logger.info("=" * 80)
        
        try:
            logger.info("Step 1: Clearing open Cursor dialogues...")
            if self.cursor_cli:
                cleanup_result = self.cursor_cli.prepare_for_new_task()
                if cleanup_result:
                    logger.info("  ✓ Dialogues cleared")
                else:
                    logger.warning("  ⚠ Failed to fully clear dialogues")

            logger.info("Step 2: Restarting Docker container...")
            if self.cursor_cli and hasattr(self.cursor_cli, 'cli_command'):
                if self.cursor_cli.cli_command == "docker-compose-agent":
                    compose_file = Path(__file__).parent.parent.parent / "docker" / "docker-compose.agent.yml"
                    container_name = "cursor-agent-life"

                    try:
                        import subprocess
                        logger.info(f"  Stopping container {container_name}...")
                        stop_result = subprocess.run(
                            ["docker", "stop", container_name],
                            capture_output=True,
                            text=True,
                            timeout=15
                        )
                        if stop_result.returncode == 0:
                            logger.info(f"  ✓ Container {container_name} stopped")
                        else:
                            logger.warning(f"  ⚠ Failed to stop container: {stop_result.stderr[:200]}")
                        
                        time.sleep(2)
                        
                        logger.info(f"  Starting container {container_name}...")
                        up_result = subprocess.run(
                            ["docker", "compose", "-f", str(compose_file), "up", "-d"],
                            capture_output=True,
                            text=True,
                            timeout=30
                        )
                        
                        if up_result.returncode == 0:
                            logger.info(f"  ✓ Container {container_name} started")
                            time.sleep(5)
                            
                            check_result = subprocess.run(
                                ["docker", "exec", container_name, "echo", "ok"],
                                capture_output=True,
                                timeout=5
                            )
                            
                            if check_result.returncode == 0:
                                logger.info("  ✓ Container is running correctly")
                                
                                logger.info("  Checking Cursor Agent installation...")
                                agent_check = subprocess.run(
                                    ["docker", "exec", container_name, "/root/.local/bin/agent", "--version"],
                                    capture_output=True,
                                    text=True,
                                    timeout=10
                                )
                                
                                if agent_check.returncode == 0:
                                    agent_version = agent_check.stdout.strip()[:50] if agent_check.stdout else "unknown"
                                    logger.info(f"  ✓ Cursor Agent installed: {agent_version}")
                                else:
                                    logger.warning("  ⚠ Cursor Agent not found, attempting to reinstall...")
                                    reinstall_result = subprocess.run(
                                        ["docker", "exec", container_name, "bash", "-c", "curl https://cursor.com/install -fsS | bash"],
                                        capture_output=True,
                                        text=True,
                                        timeout=60
                                    )
                                    if reinstall_result.returncode == 0:
                                        logger.info("  ✓ Cursor Agent reinstalled")
                                        verify_result = subprocess.run(
                                            ["docker", "exec", container_name, "/root/.local/bin/agent", "--version"],
                                            capture_output=True,
                                            text=True,
                                            timeout=10
                                        )
                                        if verify_result.returncode == 0:
                                            logger.info("  ✓ Cursor Agent confirmed after reinstall")
                                        else:
                                            logger.warning("  ⚠ Cursor Agent still not working after reinstall")
                                    else:
                                        logger.error(f"  ✗ Failed to reinstall Cursor Agent: {reinstall_result.stderr[:200]}")
                                
                                logger.info("=" * 80)
                                logger.info("RESTART SUCCESSFUL")
                                logger.info("=" * 80)
                                return True
                            else:
                                logger.warning(f"  ⚠ Container started but not responding: {check_result.stderr[:200]}")
                        else:
                            logger.error(f"  ✗ Failed to start container: {up_result.stderr[:200]}")
                    except Exception as e:
                        logger.error(f"  ✗ Error during Docker restart: {e}", exc_info=True)
                        return False
                else:
                    logger.info("  Docker not used, skipping container restart")
                    logger.info("=" * 80)
                    logger.info("RESTART COMPLETE (without Docker)")
                    logger.info("=" * 80)
                    return True
            else:
                logger.warning("  Cursor CLI unavailable, skipping restart")
                return False
                
        except Exception as e:
            logger.error(f"Error restarting Cursor environment: {e}", exc_info=True)
            return False

    def _safe_print(self, message: str, end: str = "\n") -> None:
        """
        Safely prints a message to the console, protecting against stream errors.
        
        Args:
            message: The message to print.
            end: The string appended after the last value, default a newline.
        """
        try:
            print(message, end=end, flush=True)
        except (OSError, IOError, ValueError):
            try:
                sys.stderr.write(message + (end if end else ""))
                sys.stderr.flush()
            except (OSError, IOError, ValueError):
                pass

    def stop_server_due_to_cursor_errors(self, error_message: str):
        """
        Stops the server due to critical Cursor errors.
        
        Args:
            error_message: The error message.
        """
        error_msg = "=" * 80 + "\n"
        error_msg += "SERVER STOPPING DUE TO CRITICAL CURSOR ERRORS\n"
        error_msg += "=" * 80 + "\n"
        error_msg += f"Error repeated: {error_message}\n"
        error_msg += f"Repetition count: {self._cursor_error_count}\n"
        error_msg += "Docker container restart failed\n"
        error_msg += "=" * 80 + "\n"
        error_msg += "RECOMMENDATIONS:\n"
        error_msg += "1. Check Cursor account status: https://cursor.com/dashboard\n"
        error_msg += "2. Check Docker container availability\n"
        error_msg += "3. Check Cursor logs for error details\n"
        error_msg += "4. Restart the server manually after fixing the issue\n"
        error_msg += "=" * 80
        
        self._safe_print("\n" + error_msg + "\n")
        logger.error(error_msg)
        
        if self.status_manager:
            self.status_manager.append_status(
                f"CRITICAL ERROR: Cursor error repeated ({self._cursor_error_count} times). "
                f"Error: {error_message}. Server stopped.",
                level=2
            )
        
        # Set the internal flag to signal the main server to stop
        with self._stop_lock:
            self._should_stop = True
        
        if self.checkpoint_manager:
            self.checkpoint_manager.mark_server_stop(clean=False)
        
        if self.server_logger:
            self.server_logger.log_server_shutdown(
                f"Stopping due to critical Cursor errors: {error_message} (repeated {self._cursor_error_count} times)"
            )

    def is_cursor_cli_available(self) -> bool:
        """
        Checks if Cursor CLI is available.
        
        Returns:
            True if CLI is available, False otherwise.
        """
        return self.cursor_cli is not None and self.cursor_cli.is_available()

    # MCP interaction methods - these will eventually be replaced by direct DI or dedicated MCP client
    def update_mcp_task_context(self, task_id: str, context: Dict[str, Any]):
        """
        Updates the task context in the MCP server (if available).

        Args:
            task_id: Task ID.
            context: Task context.
        """
        if self.mcp_server and self.mcp_enabled:
            try:
                self.mcp_server.update_task_context(task_id, context)
                logger.debug(f"Updated MCP context for task {task_id}")
            except Exception as e:
                logger.warning(f"Failed to update MCP task context: {e}")

    def update_mcp_task_result(self, task_id: str, result: Dict[str, Any]):
        """
        Updates the task result in the MCP server (if available).

        Args:
            task_id: Task ID.
            result: Task execution result.
        """
        if self.mcp_server and self.mcp_enabled:
            try:
                self.mcp_server.update_task_result(task_id, result)
                logger.debug(f"Updated MCP result for task {task_id}")
            except Exception as e:
                logger.warning(f"Failed to update MCP task result: {e}")

    def get_cursor_error_delay(self) -> int:
        with self._cursor_error_lock:
            return self._cursor_error_delay
