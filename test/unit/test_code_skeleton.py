import os
from pathlib import Path
from src.agents.gemini_agent.gemini_agent_cli import GeminiDeveloperAgent

def create_dummy_files(project_path):
    # Python file
    py_content = """
import os
import sys
from typing import List

GLOBAL_VAR = 10

def my_func(a: int, b: str = "test") -> bool:
    '''This is a docstring for my_func.'''
    return True

@decorator
class MyClass(BaseClass):
    '''Class docstring.'''
    class_attr = "value"
    
    def __init__(self, name):
        '''Init docstring.'''
        self.name = name
        
    async def async_method(self) -> None:
        '''Async method docstring.'''
        pass
"""
    (project_path / "dummy.py").write_text(py_content, encoding="utf-8")

    # JS file
    js_content = """
import React from 'react';

const myConst = 42;

export default class MyComponent extends React.Component {
  render() {
    return <div>Hello</div>;
  }
}

export function helper(a, b) {
  return a + b;
}

const arrowFunc = (x) => {
  return x * 2;
}
"""
    (project_path / "dummy.js").write_text(js_content, encoding="utf-8")

def test_skeleton():
    project_path = Path(".").resolve()
    create_dummy_files(project_path)
    
    agent = GeminiDeveloperAgent(api_key="fake-key", project_path=project_path)
    
    print("\n--- Testing Python Skeleton (Default) ---")
    print(agent.get_code_skeleton("dummy.py"))
    
    print("\n--- Testing Python Skeleton (Full Details) ---")
    print(agent.get_code_skeleton("dummy.py", include_imports=True, include_global_variables=True, include_class_attributes=True, include_docstrings=True))
    
    print("\n--- Testing Python Skeleton (Only Classes) ---")
    print(agent.get_code_skeleton("dummy.py", include_functions=False))
    
    print("\n--- Testing Python Skeleton (Only Functions) ---")
    print(agent.get_code_skeleton("dummy.py", include_classes=False))
    
    print("\n--- Testing JS Skeleton ---")
    print(agent.get_code_skeleton("dummy.js", include_imports=True))

    print("\n--- Testing JS Skeleton (Only Classes) ---")
    print(agent.get_code_skeleton("dummy.js", include_functions=False))
    
    print("\n--- Testing JS Skeleton (Only Functions) ---")
    print(agent.get_code_skeleton("dummy.js", include_classes=False))

    # Cleanup
    (project_path / "dummy.py").unlink()
    (project_path / "dummy.js").unlink()

if __name__ == "__main__":
    test_skeleton()
