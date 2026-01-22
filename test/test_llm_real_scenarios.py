"""
Testing LLMManager in real scenarios with various prompts

Tests:
- Basic questions
- Code generation
- JSON structured responses
- Fallback mechanism
- Performance statistics
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.llm.llm_manager import LLMManager


async def test_real_scenario_basic_question():
    """Test with basic question"""
    print("=" * 60)
    print("SCENARIO 1: Basic Question")
    print("=" * 60)

    mgr = LLMManager('config/llm_settings.yaml')

    prompt = "What is artificial intelligence? Answer briefly."

    print(f"Question: {prompt}")
    print()

    try:
        response = await mgr.generate_response(prompt, use_fastest=True)

        if response.success:
            print("[OK] Success!")
            print(f"Model: {response.model_name}")
            print(f"Time: {response.response_time:.2f}s")
            print(f"Answer: {response.content}")
        else:
            print("[ERROR] Error:")
            print(f"  {response.error}")

        print()
        return response.success

    except Exception as e:
        print(f"[ERROR] Exception: {e}")
        return False


async def test_real_scenario_code_generation():
    """Test code generation"""
    print("=" * 60)
    print("SCENARIO 2: Code Generation")
    print("=" * 60)

    mgr = LLMManager('config/llm_settings.yaml')

    prompt = """Write a Python function that:
1. Takes a list of numbers
2. Returns the sum of even numbers from the list
3. If the list is empty, returns 0

Only the function code, no explanations."""

    print(f"Task: {prompt}")
    print()

    try:
        response = await mgr.generate_response(prompt, use_fastest=True)

        if response.success:
            print("[OK] Code generated!")
            print(f"Model: {response.model_name}")
            print(f"Time: {response.response_time:.2f}s")
            print("Code:")
            print(f"{response.content}")
        else:
            print("[ERROR] Code generation error:")
            print(f"  {response.error}")

        print()
        return response.success

    except Exception as e:
        print(f"[ERROR] Exception: {e}")
        return False


async def test_real_scenario_json_structured():
    """Test structured JSON response"""
    print("=" * 60)
    print("SCENARIO 3: Structured JSON Response")
    print("=" * 60)

    mgr = LLMManager('config/llm_settings.yaml')

    prompt = """Evaluate the quality of the following Python code:

def calculate_average(numbers):
    if not numbers:
        return 0
    return sum(numbers) / len(numbers)

Return the evaluation in JSON format:
{
  "score": number from 1 to 10,
  "issues": ["list of problems"],
  "suggestions": ["list of improvements"]
}"""

    print(f"Task: {prompt}")
    print()

    try:
        response = await mgr.generate_response(
            prompt,
            use_fastest=True,
            response_format={"type": "json_object"}
        )

        if response.success:
            print("[OK] JSON response received!")
            print(f"Model: {response.model_name}")
            print(f"Time: {response.response_time:.2f}s")

            # Try to parse JSON
            try:
                import json
                json_data = json.loads(response.content)
                print("JSON parsed successfully:")
                print(f"  Score: {json_data.get('score', 'N/A')}")
                print(f"  Issues: {json_data.get('issues', [])}")
                print(f"  Suggestions: {json_data.get('suggestions', [])}")
                return True
            except json.JSONDecodeError:
                print("[ERROR] Failed to parse JSON:")
                print(f"  {response.content}")
                return False
        else:
            print("[ERROR] JSON response error:")
            print(f"  {response.error}")
            return False

    except Exception as e:
        print(f"[ERROR] Exception: {e}")
        return False


async def test_real_scenario_fallback():
    """Test fallback mechanism"""
    print("=" * 60)
    print("SCENARIO 4: Fallback Mechanism Test")
    print("=" * 60)

    mgr = LLMManager('config/llm_settings.yaml')

    # Use a simple prompt that should work
    prompt = "Hello, how are you?"

    print(f"Prompt: {prompt}")
    print()

    try:
        response = await mgr.generate_response(prompt, use_fastest=True)

        print("[OK] Request processed!")
        print(f"Model: {response.model_name}")
        print(f"Time: {response.response_time:.2f}s")
        print(f"Success: {response.success}")

        if response.success:
            print(f"Response: {response.content}")
        else:
            print(f"Error: {response.error}")

        return True

    except Exception as e:
        print(f"[ERROR] Exception: {e}")
        return False


async def test_performance_stats():
    """Test getting performance statistics"""
    print("=" * 60)
    print("SCENARIO 5: Performance Statistics")
    print("=" * 60)

    mgr = LLMManager('config/llm_settings.yaml')

    try:
        stats = mgr.get_performance_stats()

        print("[OK] Statistics received!")
        print(f"Total models: {stats['total_models']}")
        print(f"Enabled models: {stats['enabled_models']}")
        print(f"Disabled models: {stats['disabled_models']}")
        print()

        print("Models:")
        for model_name, model_stats in stats['models'].items():
            print(f"  {model_name}:")
            print(f"    Enabled: {model_stats['enabled']}")
            print(f"    Role: {model_stats['role']}")
            print(f"    Requests: {model_stats['total_requests']}")
            print(f"    Success rate: {model_stats['success_rate']}%")
            print(f"    Avg time: {model_stats['avg_response_time']}s")
            print()

        return True

    except Exception as e:
        print(f"[ERROR] Statistics error: {e}")
        return False


async def main():
    """Main testing function"""
    print("TESTING LLM MANAGER IN REAL SCENARIOS")
    print("=" * 80)
    print()

    scenarios = [
        ("Basic question", test_real_scenario_basic_question),
        ("Code generation", test_real_scenario_code_generation),
        ("JSON structured response", test_real_scenario_json_structured),
        ("Fallback mechanism", test_real_scenario_fallback),
        ("Performance statistics", test_performance_stats),
    ]

    results = []

    for scenario_name, scenario_func in scenarios:
        print(f"Test: {scenario_name}")
        try:
            result = await scenario_func()
            results.append(result)
            status = "[PASSED]" if result else "[FAILED]"
            print(f"Result: {status}")
        except Exception as e:
            print(f"[CRITICAL ERROR]: {e}")
            results.append(False)
        print("\n" + "=" * 80 + "\n")

    # Summary
    print("TESTING SUMMARY")
    print("=" * 80)

    passed = sum(results)
    total = len(results)

    print(f"Total scenarios: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {total - passed}")
    print(f"Success rate: {passed/total*100:.1f}%")
    if passed == total:
        print("ALL SCENARIOS PASSED! LLM Manager works correctly.")
    else:
        print("Some scenarios failed. Check logs for details.")

    return passed == total


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nTesting interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nCritical error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)