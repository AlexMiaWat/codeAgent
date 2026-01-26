import os
import google.generativeai as genai

# Настройка API ключа
# 1. Получите API ключ на https://aistudio.google.com/app/apikey
# 2. Замените "YOUR_API_KEY" на ваш действительный ключ
# Загрузка API ключа из файла .env
# Загрузка API ключа из переменной окружения
# Настройка OAuth2 аутентификации
import google.auth
from google.oauth2.credentials import Credentials

# Загрузка переменных окружения
env_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(env_path):
    from dotenv import load_dotenv
    load_dotenv(env_path)

# Получение OAuth2 токена
credentials, project = google.auth.default()
genai.configure(credentials=credentials)

# Создание модели
model = genai.GenerativeModel('gemini-pro')

# Пример запроса
response = model.generate_content("Привет! Как я могу помочь?")
print(response.text)