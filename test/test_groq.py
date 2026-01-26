from groq import Groq
import os

# Set up your API key as an environment variable
# export GROQ_API_KEY="your-api-key-here"

# Initialize the Groq client
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# Test the connection by making a simple request
try:
    # Create a chat completion request
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": "Explain the importance of fast language models",
            }
        ],
        model="llama-3.3-70b-versatile",
    )

    # Print the response
    print("API connection successful!")
    print("Response:", chat_completion.choices[0].message.content)

except Exception as e:
    print(f"An error occurred: {e}")
    print("Please check your API key and network connection.")
    print("If you haven't created an API key yet, visit https://console.groq.com/keys to create one.")