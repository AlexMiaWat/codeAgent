
import os
import sys
import logging
from pathlib import Path
from src.agents.gemini_agent.gemini_cli_interface import GeminiCLIInterface

# Настройка логирования
logging.basicConfig(level=logging.INFO)

def test_streaming():
    # Инициализация интерфейса (локально для простоты теста)
    interface = GeminiCLIInterface(project_dir=".")
    
    if not interface.is_available():
        print("Gemini CLI is not available. Check GOOGLE_API_KEY and gemini_agent_cli.py")
        return

    print("--- Starting Task with Streaming ---")
    result = interface.execute_instruction(
        instruction="Print 'Step 1', then wait 2 seconds, then print 'Step 2'. Do not use any tools, just print thoughts.",
        task_id="test_streaming",
        timeout=60
    )
    
    print("\n--- Task Finished ---")
    print(f"Success: {result['success']}")
    # print(f"Output: {result['stdout']}")

if __name__ == "__main__":
    test_streaming()
