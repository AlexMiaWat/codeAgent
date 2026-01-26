import requests
import json
import os

# Загрузка API ключа из файла .env
from dotenv import load_dotenv
load_dotenv()

api_key = os.getenv("GEMENI_API_KEY")
if not api_key:
    raise ValueError("API ключ не найден. Убедитесь, что переменная GEMENI_API_KEY установлена в файле .env")

url = "https://aiplatform.googleapis.com/v1/publishers/google/models/gemini-2.5-flash-lite:streamGenerateContent"

headers = {
    "Content-Type": "application/json"
}

payload = {
    "contents": [
        {
            "role": "user",
            "parts": [
                {
                    "text": "Объясни, как работает ИИ в нескольких словах"
                }
            ]
        }
    ]
}

response = requests.post(
    f"{url}?key={api_key}",
    headers=headers,
    data=json.dumps(payload)
)

print(response.json())