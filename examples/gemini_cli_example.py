import subprocess
import sys

# Запуск gemini-cli через системный PATH
result = subprocess.run(
    ["gemini", "--model", "gemini-pro", "Привет! Как я могу помочь?"],
    capture_output=True,
    text=True,
    encoding='utf-8'
)

print(result.stdout)