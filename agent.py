import datetime
from pathlib import Path

import os
import sys
import json
import argparse
import requests
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

# Конфиг
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
MODEL        = "llama-3.3-70b-versatile"

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

#Вызов LLM
def call_llm(system_prompt: str, project_description: str) -> str:
    if not GROQ_API_KEY:
        raise EnvironmentError("GROQ_API_KEY не определен")

    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Project: {project_description}"}
            ],
            "max_tokens": 2048,
            "temperature": 0.2
        },
        timeout=30,
    )
    response.raise_for_status()

    content = response.json()["choices"][0]["message"]["content"].strip()

    if content.startswith("```"):
        lines = content.splitlines()
        content = "\n".join(l for l in lines if not l.startswith("```")).strip()

    return content

# Генерация файла
def generate_file(generator_key: str, project_description: str) -> tuple[str, str]:
    gen = GENERATORS[generator_key]
    content = call_llm(gen["system"], project_description)
    return gen["filename"], content

# Сохранение файла
def save_file(output_dir: Path, filename: str, content: str) -> Path:
    path = output_dir / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    if filename.endswith(".sh"):
        path.chmod(0o755)
    return path

def run_agent(
    project_description: str,
    platform: str = "github",
    output_dir: str = "generated"
) -> list[dict]:
    out = Path(output_dir)
    out.mkdir(exist_ok=True)
    ci_key = "github_actions" if platform == "github" else "gitlab_ci"
    keys_to_generate = ["dockerfile", "compose", ci_key, "deploy"]

    sep = "=" * 35
    print(f"f\n{sep}")
    print(f" DevOps LLM Agent ")
    print(f"{sep}")
    print(f"  Project  : {project_description}")
    print(f"  Platform : {platform}")
    print(f"  Output   : {out.resolve()}/")
    print(f"  Model    : {MODEL}")
    print(f"{sep}\n")

    results = []

    for i, key in enumerate(keys_to_generate, 1):
        filename = GENERATORS[key]["filename"]
        print(f"[{i}/{len(keys_to_generate)}] Generating {filename} ...")
        try:
            _, content = generate_file(key, project_description)
            path = save_file(out, filename, content)
            print(f" saved → {path}")
            results.append({"file": filename, "path": str(path), "success": True})
        except Exception as exc:
            print(f" failed: {exc}")
            results.append({"file": filename, "success": False, "error": str(exc)})

    manifest = {
        "timestamp": datetime.now().isoformat(),
        "project": project_description,
        "platform": platform,
        "model": MODEL,
        "generated_files": results,
    }
    manifest_path = out / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    ok = sum(1 for r in results if r["success"])
    total = len(results)
    print(f"\n{sep}")
    print(f"  Done: {ok}/{total} files generated successfully")
    print(f"  Manifest → {manifest_path}")
    print(f"{sep}\n")

    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="DevOps LLM Agent — generates DevOps files from project description",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
    Examples:
      python agent.py "Python Flask REST API with PostgreSQL and Redis"
      python agent.py "Spring Boot microservice with MySQL" --platform gitlab
      python agent.py "Node.js Express API" --output my_project_devops
            """,
    )

    parser.add_argument(
        "description",
        help="Natural language project description",
    )

    parser.add_argument(
        "--platform",
        choices=["github", "gitlab"],
        default="github",
        help="Target CI/CD platform (default: github)",
    )

    parser.add_argument(
        "--output",
        default="generated",
        help="Output directory for generated files (default: generated/)",
    )

    args = parser.parse_args()

    if not GROQ_API_KEY:
        print("Error: GROQ_API_KEY environment variable is not set")
        print("  export GROQ_API_KEY=your_key_here")
        sys.exit(1)

    results = run_agent(args.description, args.platform, args.output)

    failed = [r for r in results if not r["success"]]
    sys.exit(1 if failed else 0)

