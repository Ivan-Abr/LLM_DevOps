import json

from .context_collector import collect
from .knowledge_base import get_system_prompt, GENERATORS

def read_request(request_file: str) -> dict:
    try:
        with open(request_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Файл запроса не найден: {request_file}")
    except json.JSONDecodeError:
        raise ValueError(f"Файл {request_file} содержит невалидный JSON.")
    if "description" not in data:
        raise ValueError("В JSON отсутствует обязательное поле: 'description'")

    return data


def build_user_prompt(description: str, context: dict) -> str:
    prompt = f"Project: {description}\n\n"
    if context:
        prompt += "Existing project context:\n"
        if context.get("tech_hints"):
            prompt += f"- Detected stack: {', '.join(context['tech_hints'])}\n"
            prompt += (
                "CRITICAL RULES: You MUST strictly use the build tools corresponding to the Detected Stack. "
                "For example, if Gradle is detected, DO NOT use Maven (pom.xml) under any circumstances. "
                "Base all generated files on the exact stack provided.\n"
            )
            if "Gradle" in str(context['tech_hints']):
                prompt += (
                    "CRITICAL BUILD RULE: You MUST use the Gradle wrapper for all build and test commands. "
                    "Use './gradlew build' or './gradlew bootJar'. "
                    "Any use of 'mvn' or 'pom.xml' is a hallucination and will fail the pipeline.\n"
                )
        if context.get("existing_devops"):
            prompt += f"- Existing DevOps files: {', '.join(context['existing_devops'])}\n"

        if context.get("config_contents"):
            prompt += "\nConfiguration files content:\n"
            for filename, content in context["config_contents"].items():
                prompt += f"--- {filename} ---\n{content}\n------\n"
    return prompt.strip()


def build_prompts_from_request(request_file: str = "request.json") -> tuple[list[dict], str]:
    """
    Читает запрос, собирает контекст и формирует список промптов.
    Возвращает кортеж: (список промптов, директория для сохранения файлов).
    """
    request = read_request(request_file)

    description = request["description"]
    project_path = request.get("project_path", "")
    platform = request.get("platform", "github")
    output_dir = request.get("output_dir", "generated")

    # Собираем контекст
    context = collect(project_path)

    ci_key = "github_actions" if platform == "github" else "gitlab_ci"
    keys_to_generate = ["dockerfile", "compose", ci_key, "deploy"]

    prompts = []
    for key in keys_to_generate:
        sys_prompt = get_system_prompt(key, context.get("tech_hints", []))
        user_prompt = build_user_prompt(description, context)

        prompts.append({
            "filename": GENERATORS[key]["filename"],
            "system": sys_prompt,
            "user": user_prompt
        })

    return prompts, output_dir

if __name__ == "__main__":
    import argparse
    from pathlib import Path

    parser = argparse.ArgumentParser(description="Тестирование генерации промптов")
    parser.add_argument(
        "--request",
        default="default_request.json",
        help="Путь к JSON файлу (по умолчанию default_request.json)"
    )
    parser.add_argument(
        "--output-txt",
        default="generated_prompts.txt",
        help="Путь к результирующему TXT файлу для проверки промптов"
    )
    args = parser.parse_args()

    try:
        prompts, out_dir = build_prompts_from_request(args.request)
        print(f"Директория для сохранения: {out_dir}\n")
        for i, p in enumerate(prompts, 1):
            print(f" ФАЙЛ {i}: {p['filename']} \n")
            print(f" SYSTEM PROMPT:\n{p['system']}")
            print(f" USER PROMPT:\n{p['user']}")
    except Exception as e:
        print(f"\n ОШИБКА: {e}")

    try:
        prompts, out_dir = build_prompts_from_request(args.request)

        # Формируем красивый текстовый отчет со всеми промптами
        lines = []
        lines.append("DEVOPS LLM AGENT - PROMPTS EXPORT")
        lines.append(f"Target Output Directory: {out_dir}\n")

        for i, p in enumerate(prompts, 1):
            lines.append(f" PROMPT BLOCK {i} FOR FILE: {p['filename']} \n")
            lines.append("\n [SYSTEM PROMPT]:")
            lines.append(p['system'])
            lines.append("\n[USER PROMPT]:")
            lines.append(p['user'])

        output_content = "\n".join(lines)

        # Сохраняем в txt файл
        Path(args.output_txt).write_text(output_content, encoding="utf-8")

    except Exception as e:
        print(f"\n ОШИБКА: {e}")
