import json
import sys
from datetime import datetime
from pathlib import Path

from . import static_analyzer
from . import security_policy

def load_files(generated_dir: str) -> list[dict]:
    root = Path(generated_dir)
    manifest = root / "manifest.json"
    files = []
    if manifest.exists():
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
            entries = [e for e in data.get("generated_files", []) if e.get("success")]

            for entry in entries:
                path = Path(entry["path"])
                if not path.exists():
                    path = root / entry["file"]
                if path.exists():
                    files.append({
                        "filename": entry["file"],
                        "path": str(path),
                        "content": path.read_text(encoding="utf-8", errors="ignore"),
                    })
            return files
        except (json.JSONDecodeError, KeyError):
            pass
    skip = {"manifest.json", "verification_report.json"}
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name not in skip:
            files.append({
                "filename": str(path.relative_to(root)),
                "path": str(path),
                "content": path.read_text(encoding="utf-8", errors="ignore"),
            })

    return files


def determine_status(static_findings: list[dict], policy_violations: list[dict]) -> str:
    has_fail = any(f["status"] == "fail" for f in static_findings)
    has_high = any(v["severity"] == "HIGH" for v in policy_violations)

    if has_fail or has_high:
        return "FAIL"

    has_warn = any(f["status"] == "warn" for f in static_findings)
    has_medium = any(v["severity"] in ("MEDIUM", "LOW") for v in policy_violations)

    if has_warn or has_medium:
        return "WARN"

    return "PASS"


def run(generated_dir: str = "generated") -> dict:
    sep = "=" * 55
    print(f"\n{sep}")
    print(f"  Verifier")
    print(f"{sep}")
    print(f"  Directory : {Path(generated_dir).resolve()}")
    print(f"  Timestamp : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{sep}\n")

    files = load_files(generated_dir)

    if not files:
        print(f"[ERROR] No generated files found in '{generated_dir}'.")
        print("        Run agent.py or prompt_manager.py first.\n")
        return {}

    print(f"Found {len(files)} file(s) to verify:\n")

    results = []
    count_pass = 0
    count_warn = 0
    count_fail = 0
    high_total = 0

    for item in files:
        filename = item["filename"]
        content = item["content"]
        path = item["path"]

        static = static_analyzer.analyze(filename, content, path)
        policy = security_policy.check(filename, content)
        status = determine_status(static, policy)

        high_count = sum(1 for v in policy if v["severity"] == "HIGH")
        high_total += high_count

        if status == "PASS":
            count_pass += 1
        elif status == "WARN":
            count_warn += 1
        else:
            count_fail += 1

        label = {"PASS": "PASS", "WARN": "WARN", "FAIL": "FAIL"}[status]
        print(
            f"  [{label}]  {filename}"
            f"  —  {len(static)} static finding(s), {len(policy)} policy violation(s)"
        )

        if status != "PASS":
            for f in static:
                if f["status"] != "pass":
                    icon = "    " if f["status"] == "warn" else "    X"
                    print(f"{icon} [{f['status'].upper()}] {f['check']}: {f['message']}")
            for v in policy:
                print(f"    ! [{v['severity']}] {v['rule_id']} {v['name']}: {v['message']}")

        results.append({
            "file": filename,
            "status": status,
            "static_analysis": static,
            "security_policy": policy,
        })

    total = len(files)
    report = {
        "timestamp": datetime.now().isoformat(),
        "generated_dir": generated_dir,
        "summary": {
            "total": total,
            "passed": count_pass,
            "warned": count_warn,
            "failed": count_fail,
            "high_violations": high_total,
        },
        "files": results,
    }

    report_path = Path(generated_dir) / "verification_report.json"
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(f"\n{sep}")
    print(
        f"  Summary: {count_pass}/{total} passed  |  "
        f"{count_warn} warned  |  {count_fail} failed  |  "
        f"HIGH violations: {high_total}"
    )
    print(f"  Report  → {report_path}")
    print(f"{sep}\n")

    return report

if __name__ == "__main__":
    generated_dir = sys.argv[1] if len(sys.argv) > 1 else "generated"
    report = run(generated_dir)
    if not report:
        sys.exit(2)
    failed = report.get("summary", {}).get("failed", 0)
    sys.exit(1 if failed > 0 else 0)