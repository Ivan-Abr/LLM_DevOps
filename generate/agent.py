import datetime
import sys
import json
import argparse
import requests
from datetime import datetime
from pathlib import Path
from config import API_KEY, API_URL, MODEL, validate_credentials
from .knowledge_base import GENERATORS
from .prompt_manager import build_prompts_from_request


#Вызов LLM
def call_llm(system_prompt: str, user_prompt: str) -> str:
    if not API_KEY:
        raise EnvironmentError("API_KEY не определен")

    response = requests.post(
        API_URL,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "max_tokens": 2048,
            "temperature": 0.2
        },
        timeout=120,
    )
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"].strip()
    if content.startswith("```"):
        lines = content.splitlines()
        content = "\n".join(l for l in lines if not l.startswith("```")).strip()
    return content

# Сохранение файла
def save_file(output_dir: Path, filename: str, content: str) -> Path:
    path = output_dir / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    if filename.endswith(".sh"):
        path.chmod(0o755)
    return path

# Генерация файла
def generate_from_prompts(prompts: list[dict], output_dir: str = "generated") -> list[dict]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    sep = "=" * 35
    print(f"\n{sep}")
    print(f" DevOps LLM Agent ")
    print(f"{sep}")
    print(f"  Вывод      : {out.resolve()}/")
    print(f"  Модель ЛЛМ : {MODEL}")
    print(f"{sep}\n")

    results = []

    for i, p in enumerate(prompts, 1):
        filename = p["filename"]
        print(f"{i}. Генерация {filename}")

        try:
            content = call_llm(p["system"], p["user"])
            path = save_file(out, filename, content)
            print(f" Сохранено {path}")
            results.append({"file": filename, "path": str(path), "success": True})
        except Exception as exc:
            print(f" Ошибка: {exc}")
            results.append({"file": filename, "success": False, "error": str(exc)})

    manifest = {
        "timestamp": datetime.now().isoformat(),
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
    print(f"  {ok}/{total} файлов сгенерировано успешно")
    print(f"  Manifest: {manifest_path}")
    print(f"{sep}\n")

    return results


# Запуск в автономном режиме
def run_agent(
        project_description: str,
        platform: str = "github",
        output_dir: str = "generated"
) -> list[dict]:
    ci_key = "github_actions" if platform == "github" else "gitlab_ci"
    keys_to_generate = ["dockerfile", "compose", ci_key, "deploy"]

    prompts = []
    for key in keys_to_generate:
        prompts.append({
            "filename": GENERATORS[key]["filename"],
            "system": GENERATORS[key]["system"],
            "user": f"Project: {project_description}"
        })

    return generate_from_prompts(prompts, output_dir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="DevOps LLM Agent — генерирует DevOps-файлы по описанию проекта",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
    Примеры:
      python -m generate.agent --request request.json
      python -m generate.agent "Kotlin Spring Boot API" --platform gitlab
            """,
    )
    parser.add_argument(
        "description",
        nargs="?",
        help="Описание проекта (игнорируется при использовании --request)",
    )
    parser.add_argument(
        "--platform",
        choices=["github", "gitlab"],
        default="github",
    )
    parser.add_argument(
        "--output",
        default="generated",
    )
    parser.add_argument(
        "--request",
        default="default_request.json",
        help="Путь к request.json — включает сборку контекста через prompt_manager",
    )

    args = parser.parse_args()
    validate_credentials()

    try:
        if args.request:
            prompts, output_dir = build_prompts_from_request(args.request)
            results = generate_from_prompts(prompts, output_dir)
        elif args.description:
            results = run_agent(args.description, args.platform, args.output)
        else:
            parser.print_help()
            sys.exit(1)

        failed = [r for r in results if not r.get("success")]
        sys.exit(1 if failed else 0)


    except Exception as e:
        import traceback
        traceback.print_exc()
        sys.exit(1)
