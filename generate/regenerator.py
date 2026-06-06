import json
import sys
import argparse
from datetime import datetime
from pathlib import Path

from . import agent
from .knowledge_base import get_system_prompt

FILENAME_TO_KEY: dict[str, str] = {
    "Dockerfile":               "dockerfile",
    "docker-compose.yml":       "compose",
    "docker-compose.yaml":      "compose",
    ".gitlab-ci.yml":           "gitlab_ci",
    ".github/workflows/ci.yml": "github_actions",
    "deploy.sh":                "deploy",
}

def format_issues(static_findings: list[dict], policy_violations: list[dict]) -> str:
    lines = []
    static_issues = [f for f in static_findings if ["status"] != ["pass"]]
    if static_issues:
        lines.append("Static analysis issues:")
        for f in static_issues:
            lines.append(f"-[{f['status'].upper()}] {f['check']}: {f['message']}")
    if policy_violations:
        lines.append("Security policy violations:")
        for v in policy_violations:
            lines.append(
                f"  - [{v['severity']}] {v['rule_id']} {v['name']}: {v['message']}"
            )
    return "\n".join(lines)

def build_fix_prompt(project: str, original_content: str, issues_text: str) -> str:
    return (
        f"Project: {project}\n\n"
        f"You previously generated the following file:\n\n"
        f"{original_content}\n\n"
        f"The following issues were found during verification:\n\n"
        f"{issues_text}\n\n"
        f"Regenerate the file fixing ALL issues listed above.\n"
        f"Return ONLY the corrected file content. No explanations, no markdown fences."
    )

def get_system_prompt_regen(filename: str) -> str:
    key = FILENAME_TO_KEY.get(filename)
    if key:
        return get_system_prompt(key, [])
    return (
        "You are a DevOps expert. Fix the issues in the provided DevOps file. "
        "Return ONLY the corrected file content. No markdown fences, no explanations."
    )

def run(
    generated_dir: str = "generated",
    only_failed: bool = False,
    reverify: bool = False
) -> list[dict]:
    root = Path(generated_dir)
    sep = "=" * 55
    report_path = root / "verification_report.json"
    if not report_path.exists():
        print(f"[ERROR] verification_report.json not found in '{generated_dir}'.")
        print("        Run verifier first:  python -m verify.verifier")
        return []
    report = json.loads(report_path.read_text(encoding="utf-8"))

    project = "Unknown project"
    manifest_path = root / "manifest.json"
    manifest_data = {}
    if manifest_path.exists():
        manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
        project = manifest_data.get("project", project)

    treshold = ["FAIL"] if only_failed else ["WARN", "FAIL"]
    to_fix = [f for f in report["files"] if f["status"] in treshold]

    print(f"\n{sep}")
    print(f"  Regenerator")
    print(f"{sep}")
    print(f"  Directory : {root.resolve()}")
    print(f"  Project   : {project}")
    print(f"  Mode      : {'FAIL only' if only_failed else 'WARN + FAIL'}")
    print(f"  To fix    : {len(to_fix)} file(s)")
    print(f"{sep}\n")

    if not to_fix:
        print("Nothing to regenerate — all files passed verification.")
        return []

    results: list[dict] = []

    for i, entry in enumerate(to_fix, 1):
        filename = entry["file"]
        status = entry["status"]
        static = entry["static_analysis"]
        policy = entry["security_policy"]

        print(f"[{i}/{len(to_fix)}] {filename}  (was {status})")

        # Read current file from disk
        file_path = root / filename
        if not file_path.exists():
            print(f"not found: {file_path}")
            results.append({"file": filename, "success": False, "error": "File not found"})
            continue

        original = file_path.read_text(encoding="utf-8", errors="ignore")

        # Build prompts
        issues_text = format_issues(static, policy)
        system_prompt = get_system_prompt_regen(filename)
        user_prompt = build_fix_prompt(project, original, issues_text)

        print(f"       Issues passed to LLM:\n" +
              "\n".join(f"         {l}" for l in issues_text.splitlines()))
        try:
            fixed = agent.call_llm(system_prompt, user_prompt)
            file_path.write_text(fixed, encoding="utf-8")
            if filename.endswith(".sh"):
                file_path.chmod(0o755)
            print(f"regenerated: {file_path}\n")
            results.append({"file": filename, "success": True})
        except Exception as exc:
            print(f"LLM call failed: {exc}\n")
            results.append({"file": filename, "success": False, "error": str(exc)})
    if manifest_path.exists():
        manifest_data["last_regeneration"] = datetime.now().isoformat()
        manifest_data["regenerated_files"] = [
            r["file"] for r in results if r["success"]
        ]
        manifest_path.write_text(
            json.dumps(manifest_data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    ok = sum(1 for r in results if r["success"])
    print(f"{sep}")
    print(f"  Regenerated: {ok}/{len(results)} files successfully")
    print(f"{sep}\n")
    if reverify and ok > 0:
        print("Re-running verifier on updated files...\n")
        from verify import verifier
        verifier.run(generated_dir)
    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Re-generate DevOps files that failed verification",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python regenerator.py                           fix WARN + FAIL in ./generated/
  python regenerator.py my_output --only-failed   fix only FAIL status
  python regenerator.py generated/ --reverify     fix + re-run verifier
        """,
    )
    parser.add_argument("generated_dir", nargs="?", default="generated",
                        help="Directory with generated files (default: generated/)")
    parser.add_argument("--only-failed", action="store_true",
                        help="Regenerate only FAIL files, skip WARN")
    parser.add_argument("--reverify", action="store_true",
                        help="Re-run verifier after regeneration")
    args = parser.parse_args()

    results = run(args.generated_dir, args.only_failed, args.reverify)
    failed = [r for r in results if not r.get("success")]
    sys.exit(1 if failed else 0)