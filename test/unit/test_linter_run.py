import sys
import os
from pathlib import Path
from src.agents.gemini_agent.gemini_agent_cli import GeminiDeveloperAgent

def test_linter():
    api_key = os.getenv("GOOGLE_API_KEY", "dummy")
    project_path = Path(".").resolve()
    agent = GeminiDeveloperAgent(api_key, project_path)
    
    print("Checking test_linter.py...")
    result = agent.check_syntax("test_linter.py")
    print(result)

if __name__ == "__main__":
    test_linter()
