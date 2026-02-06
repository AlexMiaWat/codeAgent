import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import subprocess

# Add src to path
sys.path.append(str(Path("src").resolve()))

from agents.gemini_agent.gemini_cli_interface import GeminiCLIInterface

def test_interface_session_passing():
    print("Testing GeminiCLIInterface session passing...")
    
    # Mock subprocess.run
    with patch("subprocess.run") as mock_run:
        # Configure mock return value
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Success"
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        # Initialize interface (local mode)
        interface = GeminiCLIInterface(project_dir=".")
        
        # 1. Test execute_instruction WITH session_id
        print("Case 1: Explicit session_id")
        interface.execute_instruction(
            instruction="Hello",
            task_id="test_task_1",
            session_id="session_123"
        )
        
        # Verify call arguments
        args, kwargs = mock_run.call_args
        cmd = args[0]
        print(f"Command run: {' '.join(cmd)}")
        assert "--session_id" in cmd
        assert "session_123" in cmd
        
        # 2. Test resume_chat and then execute_instruction
        print("\nCase 2: Using resume_chat")
        interface.resume_chat("session_456")
        interface.execute_instruction(
            instruction="Hello again",
            task_id="test_task_2"
        )
        
        args, kwargs = mock_run.call_args
        cmd = args[0]
        print(f"Command run: {' '.join(cmd)}")
        assert "--session_id" in cmd
        assert "session_456" in cmd
        
        print("\nPASSED: Session ID passing test")

if __name__ == "__main__":
    test_interface_session_passing()
