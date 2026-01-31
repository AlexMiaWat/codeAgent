import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from src.agents.gemini_agent.gemini_agent_cli import GeminiDeveloperAgent

api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("GOOGLE_API_KEY not set")
    sys.exit(1)

agent = GeminiDeveloperAgent(api_key=api_key, project_path=Path("."))
print("Agent created, testing simple request...")
try:
    # Временный вызов метода execute с простой инструкцией, но мы не хотим сохранять файл.
    # Вместо этого вызовем client.models.generate_content напрямую.
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=api_key, vertexai=False, http_options=types.HttpOptions(api_version='v1beta'))
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents="Hello, world!",
        config=None
    )
    print("Success! Response:", response.text[:100])
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()