
import subprocess
from typing import Dict

\
    # NOTE: This interface directly calls the `cursor-agent` CLI using subprocess.
    # While it provides basic execution, advanced features like integrated Docker/WSL support,
    # chat session management, or explicit fault tolerance mechanisms are not
    # implemented directly within this class. These concerns are either handled
    # by the `cursor-agent` itself, or are part of higher-level architectural components
    # or future development plans for an enterprise-grade solution.
    
class CursorCLIInterface:
    """Интерфейс взаимодействия с Cursor через CLI."""
    
    def execute(self, prompt: str, working_dir: str = None) -> Dict:
        """Выполнить команду через Cursor CLI."""
        command = ["cursor-agent", "execute", "--prompt", prompt]
        if working_dir:
            command.extend(["--working-dir", working_dir])
        
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True
            )
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
        except FileNotFoundError:
            return {
                "stdout": "",
                "stderr": "Cursor CLI (cursor-agent) not found.",
                "returncode": 127
            }
        except subprocess.CalledProcessError as e:
            return {
                "stdout": e.stdout,
                "stderr": e.stderr,
                "returncode": e.returncode
            }

