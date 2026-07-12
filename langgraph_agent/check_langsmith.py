import os
from dotenv import load_dotenv
load_dotenv()

from langsmith import Client

client = Client()
try:
    projects = list(client.list_projects(limit=1))
    print("Ключ работает, доступ есть")
except Exception as e:
    print(f"Ошибка: {e}")