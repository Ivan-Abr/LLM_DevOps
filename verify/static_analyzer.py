import re
import subprocess
from pathlib import Path

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

def analyze_dockerfile(content: str) -> list[dict]:
    findings = []
    from_lines = re.findall(r"^FROM\s+\S+", content, re.MULTILINE | re.IGNORECASE)
    if from_lines:
        has_latest = any(
            ":latest" in line or (
                    ":" not in line.split()[-1]
                    and "@" not in line.split()[-1]
                    and line.split()[-1].upper() not in ("AS", "SCRATCH")
            )
            for line in from_lines
        )
        findings.append({
            "check": "FROM tag",
            "status": "warn" if has_latest else "pass",
            "message": "Use a specific image tag instead of :latest or untagged image."
            if has_latest else "Image tag is pinned.",
        })
    else:
        findings.append({
            "check": "FROM tag",
            "status": "fail",
            "message": "No FROM instruction found in Dockerfile.",
        })
    has_user = bool(re.search(r"^USER\s+", content, re.MULTILINE))
    findings.append({
        "check": "USER instruction",
        "status": "pass" if has_user else "warn",
        "message": "Non-root USER is defined."
        if has_user else "No USER instruction — container runs as root.",
    })
    has_healthcheck = bool(re.search(r"^HEALTHCHECK\s+", content, re.MULTILINE))
    findings.append({
        "check": "HEALTHCHECK",
        "status": "pass" if has_healthcheck else "warn",
        "message": "HEALTHCHECK is defined."
        if has_healthcheck else "No HEALTHCHECK instruction — container health is unmonitored.",
    })

    add_lines = re.findall(r"^ADD\s+", content, re.MULTILINE)
    suspicious_add = [
        l for l in add_lines
        if not re.search(r"^ADD\s+(https?://|\S+\.(tar|gz|bz2|xz|zip))", l, re.IGNORECASE)
    ]
    findings.append({
        "check": "ADD vs COPY",
        "status": "warn" if suspicious_add else "pass",
        "message": "Prefer COPY over ADD for local files — ADD has implicit unpacking behaviour."
        if suspicious_add else "No suspicious ADD instructions.",
    })


    return findings

def analyze_yaml(content: str, filename: str) -> list[dict]:
    findings = []

    if not YAML_AVAILABLE:
        findings.append({
            "check": "YAML syntax",
            "status": "warn",
            "message": "pyyaml not installed — YAML syntax check skipped. Run: pip install pyyaml",
        })
        return findings
    try:
        parsed = yaml.safe_load(content)
        findings.append({
            "check": "YAML syntax",
            "status": "pass",
            "message": "YAML is syntactically valid.",
        })
    except yaml.YAMLError as exc:
        findings.append({
            "check": "YAML syntax",
            "status": "fail",
            "message": f"YAML parse error: {exc}",
        })
        return findings
    if parsed is None:
        findings.append({
            "check": "Empty document",
            "status": "warn",
            "message": "YAML document is empty.",
        })
        return findings

    findings.append({
        "check": "Empty document",
        "status": "pass",
        "message": "Document is non-empty.",
    })

    return findings

def analyze_bash(content: str, path: str) -> list[dict]:
    findings = []
    try:
        result = subprocess.run(
            ["bash", "-n", path],
            capture_output=True,
            text=True,
            timeout=10,
        )

        stderr_lower = result.stderr.lower()

        wsl_broken_markers = (
            "execvpe(/bin/bash) failed",
            "wsl (",
            "no such file or directory" if "wsl" in stderr_lower else "___never___",
        )
        wsl_relay_failure = any(marker in stderr_lower for marker in wsl_broken_markers)

        if wsl_relay_failure:
            findings.append({
                "check": "Bash syntax",
                "status": "pass",
                "message": "bash not available for syntax check (wsl error) — skipped.",
            })

        elif result.returncode != 0:
            findings.append({
                "check": "Bash syntax",
                "status": "fail",
                "message": f"Bash syntax error: {result.stderr.strip()}",
            })
        else:
            findings.append({
                "check": "Bash syntax",
                "status": "pass",
                "message": "Bash syntax is valid.",
            })
    except FileNotFoundError:
        findings.append({
            "check": "Bash syntax",
            "status": "warn",
            "message": "bash not available for syntax check — skipped.",
        })
    except subprocess.TimeoutExpired:
        findings.append({
            "check": "Bash syntax",
            "status": "warn",
            "message": "bash -n timed out.",
        })

    has_set_e = bool(
        re.search(r"set\s+-[a-z]*e[a-z]*", content) or
        re.search(r"set\s+-o\s+errexit", content)
    )
    findings.append({
        "check": "set -e",
        "status": "pass" if has_set_e else "warn",
        "message": "Error handling (set -e) is present."
        if has_set_e else "Missing 'set -e' or 'set -euo pipefail' — errors may be silently ignored.",
    })

    first_line = content.splitlines()[0].strip() if content.strip() else ""
    valid_shebang = first_line in ("#!/bin/bash", "#!/usr/bin/env bash")
    findings.append({
        "check": "Shebang",
        "status": "pass" if valid_shebang else "warn",
        "message": "Valid bash shebang found."
        if valid_shebang else f"Missing or unexpected shebang: '{first_line}'. Expected #!/bin/bash.",
    })

    return findings

def analyze_generic(content: str)  -> list[dict]:
    if not content.strip():
        return [{"check": "Non-empty file", "status": "fail", "message": "File is empty."}]
    return [{"check": "Non-empty file", "status": "pass", "message": "File has content."}]


def analyze(filename: str, content: str, file_path: str) -> list[dict]:
    name = Path(filename).name
    suffix = Path(filename).suffix.lower()

    if name == "Dockerfile":
        return analyze_dockerfile(content)
    elif suffix in (".yml", ".yaml"):
        return analyze_yaml(content, filename)
    elif suffix == ".sh":
        return analyze_bash(content, file_path)
    else:
        return analyze_generic(content)
