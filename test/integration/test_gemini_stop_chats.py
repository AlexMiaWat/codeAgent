import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import subprocess

# Add src to path
sys.path.append(str(Path("src").resolve()))

from agents.gemini_agent.gemini_cli_interface import GeminiCLIInterface

def test_stop_active_chats():
    print("Testing stop_active_chats...")
    
    # 1. Test Docker mode
    print("\nCase 1: Docker mode")
    with patch("subprocess.run") as mock_run:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        interface = GeminiCLIInterface(container_name="test_container")
        interface.stop_active_chats()
        
        args, kwargs = mock_run.call_args
        cmd = args[0]
        print(f"Command run: {' '.join(cmd)}")
        # Command should contain pkill
        assert any("pkill" in part for part in cmd)

    # 2. Test Local mode (Unix-like)
    print("\nCase 2: Local mode (Unix-like)")
    with patch("subprocess.run") as mock_run, patch("sys.platform", "linux"):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        interface = GeminiCLIInterface()
        interface.stop_active_chats()
        
        args, kwargs = mock_run.call_args
        cmd = args[0]
        print(f"Command run: {' '.join(cmd)}")
        assert "pkill" in cmd
        assert "gemini_agent_cli" in cmd

    print("\nPASSED: stop_active_chats test")

if __name__ == "__main__":
    test_stop_active_chats()
