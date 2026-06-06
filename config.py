import os
from dotenv import load_dotenv
import sys
load_dotenv()

#Креды

#Ключ LLM
API_KEY = os.getenv("API_KEY", "")
# Имя LLM
MODEL = os.getenv("MODEL", "")
#Ссылка на ЛЛМ
API_URL =os.getenv("API_URL", "")

def validate_credentials():
    credentials = {
        "API_KEY": API_KEY,
        "MODEL": MODEL,
        "API_URL": API_URL
    }
    missing = [name for name, value in credentials.items() if not value]
    if missing:
        sys.exit(
            f"ОШИБКА: Не заполнены обязательные переменные окружения: {', '.join(missing)}"
        )
