import os
from pathlib import Path
from knowledge_base import TECH_HINTS

def collect(project_path: str) -> dict:
    if not project_path or not os.path.exists(project_path):
        return {}
    path = Path(project_path)

    result = {
        "tech_hints": [],
        "found_configs": [],
        "existing_devops": [],
        "config_contents": {}
    }

    for marker_file, hint in TECH_HINTS.items():
        target = path / marker_file
        if target.is_file():
            result["tech_hints"].append(hint)
            result["found_configs"].append(marker_file)
            try:
                content = target.read_text(encoding="utf-8")
                result["config_contents"][marker_file] = content[:3000]
            except Exception:
                pass
    devops_markers = ["Dockerfile", "docker-compose.yml", ".gitlab-ci.yml"]
    for dm in devops_markers:
        if (path / dm).is_file():
            result["existing_devops"].append(dm)

    gh_actions_dir = path / ".github" / "workflows"
    if gh_actions_dir.is_dir():
        for yml_file in gh_actions_dir.glob("*.yml"):
            result["existing_devops"].append(f".github/workflows/{yml_file.name}")
        for yaml_file in gh_actions_dir.glob("*.yaml"):
            result["existing_devops"].append(f".github/workflows/{yaml_file.name}")

    return result
