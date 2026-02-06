import os
import sys
from pathlib import Path
import json
import yaml

# Add src to path
sys.path.append(str(Path("src").resolve()))

from agents.gemini_agent.gemini_agent_cli import GeminiDeveloperAgent

def test_new_tools():
    print("Testing improved check_syntax and new read_symbol tool...")
    
    agent = GeminiDeveloperAgent(api_key="fake", project_path=Path("."))
    
    # 1. Test check_syntax with JSON
    print("\n--- Testing check_syntax (JSON) ---")
    json_path = Path("test_file.json")
    json_path.write_text('{"key": "value"}', encoding='utf-8')
    result = agent.check_syntax("test_file.json")
    print(f"JSON Valid: {result}")
    
    json_path.write_text('{"key": "value"', encoding='utf-8') # Invalid JSON
    result = agent.check_syntax("test_file.json")
    print(f"JSON Invalid: {result}")
    
    # 2. Test check_syntax with YAML
    print("\n--- Testing check_syntax (YAML) ---")
    yaml_path = Path("test_file.yaml")
    yaml_path.write_text("key: value\nlist:\n  - item1", encoding='utf-8')
    result = agent.check_syntax("test_file.yaml")
    print(f"YAML Valid: {result}")
    
    yaml_path.write_text("key: value\n  invalid_indent", encoding='utf-8')
    result = agent.check_syntax("test_file.yaml")
    print(f"YAML Invalid: {result}")
    
    # 3. Test read_symbol
    print("\n--- Testing read_symbol ---")
    py_path = Path("test_file.py")
    py_content = """
class MyClass:
    def method1(self, x):
        return x + 1

def my_function(y):
    print(y)
"""
    py_path.write_text(py_content, encoding='utf-8')
    
    result = agent.read_symbol("test_file.py", "MyClass")
    print(f"Read MyClass:\n{result}")
    
    result = agent.read_symbol("test_file.py", "my_function")
    print(f"Read my_function:\n{result}")
    
    result = agent.read_symbol("test_file.py", "NonExistent")
    print(f"Read NonExistent: {result}")

    # Cleanup
    for p in [json_path, yaml_path, py_path]:
        if p.exists():
            p.unlink()

if __name__ == "__main__":
    test_new_tools()
