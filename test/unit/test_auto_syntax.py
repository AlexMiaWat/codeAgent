import sys
import os
from pathlib import Path
from src.agents.gemini_agent.gemini_agent_cli import GeminiDeveloperAgent

def test_automatic_syntax_check():
    api_key = os.getenv("GOOGLE_API_KEY", "dummy")
    project_path = Path(".").resolve()
    agent = GeminiDeveloperAgent(api_key, project_path)
    
    test_file = "test_syntax.py"
    
    print("Testing write_file with valid code...")
    result = agent.write_file(test_file, "print('hello')\n")
    print(f"Result: {result}")
    assert "Syntax check: ✅" in result
    
    print("\nTesting write_file with invalid code...")
    result = agent.write_file(test_file, "print('hello'\n") # Missing parenthesis
    print(f"Result: {result}")
    assert "Syntax check: ❌ SyntaxError" in result

    print("\nTesting write_file with valid code again...")
    result = agent.write_file(test_file, "print('hello')\n")
    assert "Syntax check: ✅" in result

    print("\nTesting replace_in_file with valid code...")
    result = agent.replace_in_file(test_file, "print('hello')", "x = 10")
    print(f"Result: {result}")
    assert "Syntax check: ✅" in result

    print("\nTesting insert_at_line with invalid code...")
    result = agent.insert_at_line(test_file, 2, "if True:") # Missing indentation
    print(f"Result: {result}")
    assert "Syntax check: ❌ SyntaxError" in result
    
    # Cleanup
    if os.path.exists(test_file):
        os.remove(test_file)
    print("\nAll tests passed!")

if __name__ == "__main__":
    test_automatic_syntax_check()
