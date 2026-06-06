import re
from pathlib import Path
from config import RULES


def get_file_type(filename: str) -> str:
    name = Path(filename).name
    suffix = Path(filename).suffix.lstrip(".")
    if name == "Dockerfile":
        return "Dockerfile"
    return suffix.lower() if suffix else name.lower()

def rule_applies(rule: dict, file_type: str)-> bool:
    types = rule["file_types"]
    if types == ["*"]:
        return True
    return file_type in types

def check(filename: str, content: str) -> list[dict]:
    file_type = get_file_type(filename)
    violations = []

    for rule in RULES:
        if not rule_applies(rule, file_type):
            continue
        try:
            match = re.search(
                rule["pattern"],
                content,
                re.IGNORECASE | re.MULTILINE
            )
        except re.error as e:
            continue

        if match:
            violations.append({
                "rule_id": rule["id"],
                "name": rule["name"],
                "severity": rule["severity"],
                "message": rule["message"]
            })

    return violations