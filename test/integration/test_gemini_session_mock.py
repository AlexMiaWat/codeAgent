import os
import sys
import pickle
from pathlib import Path
from unittest.mock import MagicMock, patch
from google.genai import types

# Add src to path
sys.path.append(str(Path("src").resolve()))

from agents.gemini_agent.gemini_agent_cli import GeminiDeveloperAgent

# Mock API key
os.environ["GOOGLE_API_KEY"] = "fake_key"

def test_session_management():
    print("Testing Gemini CLI Session Management...")
    
    project_path = Path(".").resolve()
    session_id = "test_session_123"
    
    # Clean up previous session
    session_file = project_path / ".gemini_sessions" / f"{session_id}.pkl"
    if session_file.exists():
        session_file.unlink()
        
    # --- Step 1: First Run (Save Session) ---
    print("\n--- Step 1: First Run ---")
    agent1 = GeminiDeveloperAgent(api_key="fake_key", project_path=project_path)
    
    # Mock the client generate_content
    mock_response1 = MagicMock()
    mock_response1.candidates = [MagicMock(content=MagicMock(parts=[MagicMock(text="I will remember your favorite color is blue.", function_call=None)]))]
    agent1.client.models.generate_content = MagicMock(return_value=mock_response1)
    
    # Execute with session_id
    # We need to manually simulate what execute does because we want to inspect the saved file
    # But wait, execute is the main loop. Let's just call execute and mock the response.
    
    # We need to ensure execute doesn't crash on mocked response not matching exact structure if complex
    # The agent expects response.candidates[0].content.parts...
    
    output_file = project_path / "test_output_1.md"
    try:
        agent1.execute(
            instruction="My favorite color is blue.",
            output_file_path=output_file,
            control_phrase="DONE",
            session_id=session_id
        )
    except SystemExit:
        # execute calls sys.exit(1) on failure, but we hope for success
        pass
    
    # Check if session file created
    if session_file.exists():
        print(f"✅ Session file created at {session_file}")
    else:
        print("❌ Session file NOT created")
        return

    # --- Step 2: Second Run (Load Session) ---
    print("\n--- Step 2: Second Run ---")
    agent2 = GeminiDeveloperAgent(api_key="fake_key", project_path=project_path)
    
    # Mock response for the second run
    mock_response2 = MagicMock()
    mock_response2.candidates = [MagicMock(content=MagicMock(parts=[MagicMock(text="Your favorite color is blue.", function_call=None)]))]
    agent2.client.models.generate_content = MagicMock(return_value=mock_response2)
    
    # We want to verify that agent2 loaded the history.
    # Let's inspect _load_session directly to see if it picks up the file
    loaded_history = agent2._load_session(session_id)
    print(f"Loaded history length: {len(loaded_history)}")
    
    if len(loaded_history) > 0:
        print("✅ History loaded successfully")
        # Check content of history
        # History should contain user prompt from step 1 and model response from step 1
        # output of pickle load might be complex types, just printing representation
        print(f"History sample: {loaded_history[0]}")
    else:
        print("❌ History NOT loaded or empty")

    # Cleanup
    if session_file.exists():
        session_file.unlink()
    if output_file.exists():
        output_file.unlink()

if __name__ == "__main__":
    test_session_management()
