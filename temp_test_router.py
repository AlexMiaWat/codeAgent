
import sys
import os

# Add the project root to the sys.path to resolve imports correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src', 'llm')))

try:
    from intelligent_router import IntelligentRouter, TaskType, ComplexityLevel
    print("Successfully imported IntelligentRouter, TaskType, ComplexityLevel.")
    print(f"TaskType values: {[t.value for t in TaskType]}")
    print(f"ComplexityLevel values: {[c.value for c in ComplexityLevel]}")

    # Further test: try to instantiate a dummy router
    class MockModelRegistry:
        def get_models_by_role(self, role):
            return []
        def get_model(self, name):
            return None

    mock_registry = MockModelRegistry()
    router = IntelligentRouter(registry=mock_registry)
    print("IntelligentRouter instantiated successfully.")

except Exception as e:
    print(f"Error during import or instantiation: {e}")

