import os
import pytest

pytestmark = pytest.mark.llm

if os.getenv("CI") and os.getenv("RUN_LLM_TESTS") != "1":
    pytest.skip("LLM tests are disabled in CI.", allow_module_level=True)

groq = pytest.importorskip("groq", reason="groq provider is optional")

if not os.getenv("GROQ_API_KEY"):
    pytest.skip("GROQ_API_KEY is not set.", allow_module_level=True)


def test_groq_chat_completion():
    """Basic Groq API connectivity test (run locally only)."""
    client = groq.Groq(api_key=os.environ.get("GROQ_API_KEY"))

    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": "Explain the importance of fast language models",
            }
        ],
        model="llama-3.3-70b-versatile",
    )

    assert chat_completion.choices[0].message.content
