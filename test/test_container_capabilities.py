import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Set UTF-8 for stdout
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, errors='replace')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, errors='replace')

# Add src to path
sys.path.append(str(Path("src").resolve()))

# Load .env to get GOOGLE_API_KEY
load_dotenv()

from agents.gemini_agent.gemini_cli_interface import create_gemini_cli_interface

logging.basicConfig(level=logging.INFO)

def test_container_skeleton():
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("Error: GOOGLE_API_KEY not found in .env file.")
        return
    print(f"GOOGLE_API_KEY found: {api_key[:5]}...{api_key[-5:]}")

    print("Initializing Gemini CLI Interface (Docker)...")
    interface = create_gemini_cli_interface(
        project_dir=os.getcwd(),
        container_name="gemini-agent"
    )

    if not interface.is_available():
        print("Error: Gemini CLI is not available via Docker.")
        return

    # Task 1: Ask for skeleton with ONLY classes
    task_id = "test_skeleton_classes_only"
    instruction = "Get the code skeleton of 'src/agents/executor_agent.py'. I ONLY want to see class definitions, no top-level functions."

    print(f"\n--- Sending instruction: {instruction} ---")
    result = interface.execute_instruction(
        instruction=instruction,
        task_id=task_id,
        wait_for_file=f"docs/results/{task_id}.md"
    )

    if result["success"]:
        print("\nTask 1 Success!")
        print(f"Stdout (last 500 chars):\n...{result['stdout'][-500:]}")
    else:
        print(f"\nTask 1 Failed: {result.get('error_message')}")

    # Task 2: Ask for skeleton with ONLY functions
    task_id = "test_skeleton_functions_only"
    instruction = "Get the code skeleton of 'src/agents/executor_agent.py'. I ONLY want to see top-level functions, no class definitions."

    print(f"\n--- Sending instruction: {instruction} ---")
    result = interface.execute_instruction(
        instruction=instruction,
        task_id=task_id,
        wait_for_file=f"docs/results/{task_id}.md"
    )

    if result["success"]:
        print("\nTask 2 Success!")
        print(f"Stdout (last 500 chars):\n...{result['stdout'][-500:]}")
    else:
        print(f"\nTask 2 Failed: {result.get('error_message')}")

if __name__ == "__main__":
    test_container_skeleton()
