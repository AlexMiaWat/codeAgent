from google.genai import types
import pickle
import json

def test_serialization():
    content = types.Content(parts=[types.Part.from_text(text="Hello")], role="user")
    
    print("Testing Pickle serialization...")
    try:
        serialized = pickle.dumps(content)
        deserialized = pickle.loads(serialized)
        print("Pickle successful")
        print(f"Original: {content}")
        print(f"Deserialized: {deserialized}")
    except Exception as e:
        print(f"Pickle failed: {e}")

    print("\nTesting JSON serialization (to_json/from_json if available)...")
    try:
        # Check if to_json exists or similar
        if hasattr(content, "to_json"):
            json_str = content.to_json()
            print(f"to_json successful: {json_str}")
        elif hasattr(content, "to_dict"):
            json_dict = content.to_dict()
            print(f"to_dict successful: {json_dict}")
        else:
            print("No direct JSON serialization method found")
            
    except Exception as e:
        print(f"JSON failed: {e}")

if __name__ == "__main__":
    test_serialization()
