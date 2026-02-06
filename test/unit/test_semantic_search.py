import os
from pathlib import Path
from src.agents.gemini_agent.gemini_agent_cli import GeminiDeveloperAgent

def test_search():
    # Инициализируем агента с фейковым ключом (он не нужен для локальных инструментов)
    project_path = Path(".").resolve()
    agent = GeminiDeveloperAgent(api_key="fake-key", project_path=project_path)
    
    print("--- Testing Semantic Search: 'GeminiDeveloperAgent' ---")
    result = agent.semantic_search("GeminiDeveloperAgent")
    print(result)
    
    print("\n--- Testing Semantic Search: 'semantic_search' ---")
    result = agent.semantic_search("semantic_search")
    print(result)

    print("\n--- Testing Semantic Search: 'auth' (likely no matches) ---")
    result = agent.semantic_search("auth")
    print(result)

if __name__ == "__main__":
    test_search()
