
import sys
import os

# Add the parent directory of src/llm to sys.path to allow absolute imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

try:
    from src.llm.intelligent_router import IntelligentRouter
    from src.llm.types import TaskType

    # Check if TaskType is correctly accessible
    _ = IntelligentRouter._classify_task_type # Access a method that uses TaskType internally
    _ = TaskType.CODE_GENERATION # Directly access an enum member

    print("Verification successful: intelligent_router.py imports without errors and TaskType is accessible.")

except ImportError as e:
    print(f"Verification failed: ImportError - {e}")
except AttributeError as e:
    print(f"Verification failed: AttributeError - {e}")
except Exception as e:
    print(f"Verification failed: An unexpected error occurred - {e}")
finally:
    # Clean up sys.path
    sys.path.pop(0)
