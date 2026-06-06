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

RULES: list[dict] = [
    {
        "id":         "SEC-001",
        "name":       "Hardcoded password",
        "pattern":    r"password\s*[=:]\s*['\"][^'\"]{3,}['\"]",
        "severity":   "HIGH",
        "message":    "Hardcoded password detected. Use environment variables instead.",
        "file_types": ["*"],
    },
    {
        "id":         "SEC-002",
        "name":       "Dangerous rm -rf",
        "pattern":    r"rm\s+-rf\s+/\s*$|rm\s+-rf\s+/\*",
        "severity":   "HIGH",
        "message":    "Destructive 'rm -rf /' or 'rm -rf /*' detected. This will wipe the filesystem.",
        "file_types": ["sh"],
    },
    {
        "id":         "SEC-003",
        "name":       "Insecure chmod 777",
        "pattern":    r"chmod\s+777",
        "severity":   "MEDIUM",
        "message":    "chmod 777 grants full permissions to all users. Use more restrictive permissions.",
        "file_types": ["*"],
    },
    {
        "id":         "SEC-004",
        "name":       "Docker privileged mode",
        "pattern":    r"privileged\s*:\s*true",
        "severity":   "HIGH",
        "message":    "Privileged container detected. This grants full host access. Avoid unless strictly necessary.",
        "file_types": ["yml", "yaml"],
    },
    {
        "id":         "SEC-005",
        "name":       "Pipe to shell (curl|wget)",
        "pattern":    r"(curl|wget)[^\n]*\|\s*(ba)?sh",
        "severity":   "HIGH",
        "message":    "Piping curl/wget output directly to bash is dangerous. Download, verify, then execute.",
        "file_types": ["sh"],
    },
    {
        "id":         "SEC-006",
        "name":       "SSL verification disabled",
        "pattern":    r"--no-check-certificate|--insecure\b|-k\s",
        "severity":   "MEDIUM",
        "message":    "SSL certificate verification is disabled. This exposes connections to MITM attacks.",
        "file_types": ["sh"],
    },
    {
        "id":         "SEC-007",
        "name":       "Hardcoded secret or API key",
        "pattern":    r"(api_key|secret_key|private_key|access_token)\s*[=:]\s*\S{8,}",
        "severity":   "HIGH",
        "message":    "Hardcoded secret/key detected. Use a secrets manager or environment variables.",
        "file_types": ["*"],
    },
    {
        "id":         "SEC-008",
        "name":       "Interactive sudo",
        "pattern":    r"sudo(?!\s+-n)\s+",
        "severity":   "MEDIUM",
        "message":    "sudo used without -n (non-interactive) flag. May hang in CI or require manual input.",
        "file_types": ["sh"],
    },
    {
        "id":         "SEC-009",
        "name":       "Host network mode",
        "pattern":    r"network_mode\s*:\s*['\"]?host['\"]?",
        "severity":   "MEDIUM",
        "message":    "network_mode: host removes network isolation. Container shares the host network stack.",
        "file_types": ["yml", "yaml"],
    },
    {
        "id":         "SEC-010",
        "name":       "allow_failure: true in CI/CD",
        "pattern":    r"allow_failure\s*:\s*true",
        "severity":   "LOW",
        "message":    "allow_failure: true suppresses job failure. Ensure this is intentional and not hiding errors.",
        "file_types": ["yml", "yaml"],
    },
    {
        "id":         "SEC-011",
        "name":       "Hardcoded IP address",
        "pattern":    r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b",
        "severity":   "LOW",
        "message":    "Hardcoded IP address detected. Use hostnames or environment variables for portability.",
        "file_types": ["*"],
    },
    {
        "id":         "SEC-012",
        "name":       "Dockerfile runs as root",
        "pattern":    r"USER\s+root",
        "severity":   "HIGH",
        "message":    "Container explicitly set to run as root. Use a non-root USER for security.",
        "file_types": ["Dockerfile"],
    },
]

