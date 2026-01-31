
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load env
load_dotenv(override=True)

# Add project root to sys.path
project_root = str(Path(__file__).parent.parent.absolute())
if project_root not in sys.path:
    sys.path.insert(0, project_root)

print(f"Current working directory: {os.getcwd()}")
print(f"PYTHONPATH: {sys.path}")

print(f"GOOGLE_API_KEY present: {'GOOGLE_API_KEY' in os.environ}")
if 'GOOGLE_API_KEY' in os.environ:
    print(f"GOOGLE_API_KEY value length: {len(os.environ['GOOGLE_API_KEY'])}")

try:
    from src.agents.gemini_agent.gemini_cli_interface import GeminiCLIInterface, create_gemini_cli_interface
    print("GeminiCLIInterface imported successfully")
    
    # Try to create interface (local)
    cli = create_gemini_cli_interface(project_dir=os.getcwd())
    print(f"Gemini CLI available: {cli.is_available()}")
    
    if not cli.is_available():
        print("Gemini CLI is NOT available. Checking why...")
        # Re-run checks manually
        cli_path = Path("src/agents/gemini_agent/gemini_agent_cli.py").resolve()
        print(f"CLI path exists: {cli_path.exists()} ({cli_path})")
        
        import subprocess
        try:
            res = subprocess.run([sys.executable, "--version"], capture_output=True, text=True)
            print(f"Python execution check: {res.returncode}")
        except Exception as e:
            print(f"Python execution check failed: {e}")

except ImportError as e:
    print(f"Failed to import GeminiCLIInterface: {e}")
except Exception as e:
    print(f"Error during check: {e}")
