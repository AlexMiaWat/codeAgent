import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from src.agents.gemini_agent.gemini_agent_cli import GeminiDeveloperAgent
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("GOOGLE_API_KEY not set")
    sys.exit(1)

# Создаем временный файл для отчета
output_path = Path("test_report.md")
control_phrase = "TEST_COMPLETE"

agent = GeminiDeveloperAgent(api_key=api_key, project_path=Path("."))
print("Testing agent with simple instruction...")
try:
    agent.execute(
        instruction="Say hello and introduce yourself.",
        output_file_path=output_path,
        control_phrase=control_phrase
    )
    print("Agent executed successfully")
    if output_path.exists():
        content = output_path.read_text()
        print(f"Report content (first 500 chars): {content[:500]}")
        # Удаляем временный файл
        output_path.unlink()
except Exception as e:
    print(f"Agent execution failed: {e}")
    import traceback
    traceback.print_exc()