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

# ГЕНЕРАТОРЫ
# Каждый генератор как отдельный промпт + имя файла на выходе.
# Агент вызывает LLM отдельно для каждого файла.
GENERATORS = {
    "dockerfile": {
        "filename": "Dockerfile",
        "system":   (
            "You are a DevOps expert. Generate a production-ready Dockerfile. "
            "Rules: return ONLY the Dockerfile content. "
            "No markdown fences, no preamble, no explanations. "
            "Use multi-stage builds where appropriate. Add comments for clarity."
        ),
    },
    "compose": {
        "filename": "docker-compose.yml",
        "system":   (
            "You are a DevOps expert. Generate a docker-compose.yml for local development. "
            "Rules: return ONLY valid YAML. "
            "No markdown fences, no preamble, no explanations. "
            "Include all services the project needs (app, db, cache, etc.). "
            "Use named volumes, healthchecks, and environment variable placeholders."
        ),
    },
    "gitlab_ci": {
        "filename": ".gitlab-ci.yml",
        "system":   (
            "You are a DevOps expert. Generate a .gitlab-ci.yml CI/CD pipeline. "
            "Rules: return ONLY valid YAML. "
            "No markdown fences, no preamble, no explanations. "
            "Include stages: build, test, deploy. "
            "Use Docker-in-Docker for build if needed. Add caching."
        ),
    },
    "github_actions": {
        "filename": ".github/workflows/ci.yml",
        "system":   (
            "You are a DevOps expert. Generate a GitHub Actions CI/CD workflow. "
            "Rules: return ONLY valid YAML. "
            "No markdown fences, no preamble, no explanations. "
            "Include jobs: build, test, deploy. Use caching for dependencies."
        ),
    },
    "deploy": {
        "filename": "deploy.sh",
        "system":   (
            "You are a DevOps expert. Generate a bash deployment script. "
            "Rules: return ONLY the bash script starting with #!/bin/bash. "
            "No markdown fences, no preamble, no explanations. "
            "Add: set -euo pipefail. Add comments. Handle errors gracefully."
        ),
    },
}
