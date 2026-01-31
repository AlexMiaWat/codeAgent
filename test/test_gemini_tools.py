import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("GOOGLE_API_KEY not set")
    sys.exit(1)

def get_current_weather(location: str) -> str:
    """Example method. Returns the current weather.
    Args:
        location: The city and state, e.g. San Francisco, CA
    """
    weather_map = {
        "Boston, MA": "snowing",
        "San Francisco, CA": "foggy",
        "Seattle, WA": "raining",
        "Austin, TX": "hot",
        "Chicago, IL": "windy",
    }
    return weather_map.get(location, "unknown")

client = genai.Client(api_key=api_key, http_options=types.HttpOptions(api_version='v1beta'))
model_id = "gemini-2.5-flash"

print("Testing with tools as list of functions...")
try:
    response = client.models.generate_content(
        model=model_id,
        contents="What is the weather like in Boston?",
        config=types.GenerateContentConfig(
            tools=[get_current_weather],
            temperature=0,
        ),
    )
    print("Success! Response:", response.text)
except Exception as e:
    print(f"Error with tools: {e}")
    import traceback
    traceback.print_exc()

print("\nTesting with system_instruction...")
try:
    response = client.models.generate_content(
        model=model_id,
        contents="Good morning! How are you?",
        config=types.GenerateContentConfig(
            system_instruction="You are a cat. Your name is Neko.",
        ),
    )
    print("Success! Response:", response.text)
except Exception as e:
    print(f"Error with system_instruction: {e}")
    import traceback
    traceback.print_exc()

print("\nTesting with both tools and system_instruction...")
try:
    response = client.models.generate_content(
        model=model_id,
        contents="What is the weather like in Boston?",
        config=types.GenerateContentConfig(
            tools=[get_current_weather],
            system_instruction="You are a helpful weather assistant.",
        ),
    )
    print("Success! Response:", response.text)
except Exception as e:
    print(f"Error with both: {e}")
    import traceback
    traceback.print_exc()