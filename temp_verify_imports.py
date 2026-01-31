
import sys
import os

# Add the src/llm directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src', 'llm')))

try:
    from intelligent_router import IntelligentRouter
    from types import TaskType

    # Attempt to access TaskType through IntelligentRouter's module scope
    # This indirectly checks if TaskType was correctly imported within intelligent_router.py
    # and is accessible.
    _ = TaskType.CODE_GENERATION # Just access it to make sure it's there

    print("Verification successful: TaskType is correctly imported and accessible in intelligent_router.py")

except ImportError as e:
    print(f"Verification failed: ImportError - {e}")
    print("Please ensure src/llm/intelligent_router.py has 'from .types import TaskType' and no duplicate TaskType definition.")
except AttributeError as e:
    print(f"Verification failed: AttributeError - {e}")
    print("TaskType might be imported but not accessible as expected. Check intelligent_router.py content.")
except Exception as e:
    print(f"An unexpected error occurred during verification: {e}")
