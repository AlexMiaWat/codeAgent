import sys
import os
from pathlib import Path

# Add src to sys.path
src_path = str(Path("d:/Space/codeAgent/src").resolve())
if src_path not in sys.path:
    sys.path.append(src_path)

from agents.gemini_agent.gemini_cli_interface import GeminiCLIInterface

def test_version():
    # Test local
    interface = GeminiCLIInterface()
    version = interface.check_version()
    print(f"Local version: {version}")

    # Test docker (if possible)
    # interface_docker = GeminiCLIInterface(container_name="gemini-agent-container")
    # version_docker = interface_docker.check_version()
    # print(f"Docker version: {version_docker}")

if __name__ == "__main__":
    test_version()
