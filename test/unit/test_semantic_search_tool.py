import os
from pathlib import Path
from src.agents.gemini_agent.gemini_agent_cli import GeminiDeveloperAgent

def test_semantic_search():
    api_key = os.getenv("GOOGLE_API_KEY", "dummy")
    project_path = Path(".").resolve()
    agent = GeminiDeveloperAgent(api_key=api_key, project_path=project_path)
    
    print("Testing semantic_search with query 'gemini'...")
    result = agent.semantic_search("gemini")
    print(result)

if __name__ == "__main__":
    test_semantic_search()
