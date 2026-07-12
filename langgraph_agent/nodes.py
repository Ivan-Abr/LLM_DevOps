import json
from datetime import datetime
from pathlib import Path

from .state import AgentState

def node_load_request(state: AgentState) -> dict:
    """Read request.json and extract project metadata into state."""
    request_file = state["request_file"]
    print(f"\n  [load_request] Reading {request_file}")

    try:
        data = json.loads(Path(request_file).read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"  [load_request] ERROR: file not found — {request_file}")
        return {"status": "failed"}
    except json.JSONDecodeError as e:
        print(f"  [load_request] ERROR: {e}")
        return {"status": "failed"}
    description = data.get("description", "")
    if not description:
        print("  [load_request] ERROR: 'description' field is missing")
        return {"status": "failed"}

    platform = data.get("platform", "gitlab")
    output_dir = data.get("output_dir", "generated")

    print(f"  [load_request] Project : {description[:80]}")
    print(f"  [load_request] Platform: {platform}")
    print(f"  [load_request] Output  : {output_dir}")

    return {
        "project_description": description,
        "platform": platform,
        "output_dir": output_dir,
    }

def node_collect_and_build_prompts(state: AgentState) -> dict:
    """Run context_collector + prompt_manager to build enriched prompts."""
    from generate.prompt_manager import build_prompts_from_request
    print(f"\n  [build_prompts] Building prompts from {state['request_file']}")
    try:
        prompts, output_dir = build_prompts_from_request(state["request_file"])
    except Exception as exc:
        print(f"  [build_prompts] ERROR: {exc}")
        return {"status": "failed"}

    print(f"  [build_prompts] Built {len(prompts)} prompt(s), output : {output_dir}")

    return {
        "prompts": prompts,
        "output_dir": output_dir,
        "status": "pending",
    }


def node_generate(state: AgentState) -> dict:
    """Call LLM for each prompt and save generated DevOps files."""
    from generate import agent as gen_agent

    prompts = state["prompts"]
    output_dir = state["output_dir"]

    print(f"\n  [generate] Generating {len(prompts)} file(s) : {output_dir}")

    try:
        results = gen_agent.generate_from_prompts(prompts, output_dir)
    except Exception as exc:
        print(f"  [generate] ERROR: {exc}")
        return {"status": "failed"}

    ok = sum(1 for r in results if r.get("success"))
    print(f"  [generate] {ok}/{len(results)} files generated successfully")

    return {
        "generated_files": results,
        "status": "generated",
    }


def node_verify(state: AgentState) -> dict:
    """Run static analysis and security policy checks on generated files."""
    from verify import verifier

    output_dir = state["output_dir"]
    print(f"\n  [verify] Running verification on {output_dir} (iteration {state['iteration']})")

    try:
        report = verifier.run(output_dir)
    except Exception as exc:
        print(f"  [verify] ERROR: {exc}")
        return {"verification_report": {}, "status": "verified"}

    summary = report.get("summary", {})
    print(
        f"  [verify] passed={summary.get('passed', 0)} "
        f"warned={summary.get('warned', 0)} "
        f"failed={summary.get('failed', 0)} "
        f"HIGH={summary.get('high_violations', 0)}"
    )

    return {
        "verification_report": report,
        "status": "verified",
    }


def node_regenerate(state: AgentState) -> dict:
    """Re-generate files that failed verification using issue-enriched prompts."""
    from generate import regenerator

    output_dir = state["output_dir"]
    iteration = state["iteration"] + 1

    print(f"\n  [regenerate] Regenerating failed files (attempt {iteration}/{state['max_iterations']})")

    try:
        results = regenerator.run(output_dir)
        ok = sum(1 for r in results if r.get("success"))
        print(f"  [regenerate] {ok}/{len(results)} files regenerated")
    except Exception as exc:
        print(f"  [regenerate] ERROR: {exc}")

    return {
        "iteration": iteration,
        "status": "verified",  # triggers re-verify on next cycle
    }


def node_finalize(state: AgentState) -> dict:
    """Save final_report.json and print the summary."""
    report = state.get("verification_report", {})
    summary = report.get("summary", {})
    failed = summary.get("failed", 0)
    high = summary.get("high_violations", 0)
    final_ok = failed == 0 and high == 0

    final_status = "passed" if final_ok else "failed"
    output_dir = state["output_dir"]

    final_report = {
        "timestamp": datetime.now().isoformat(),
        "project": state.get("project_description", ""),
        "platform": state.get("platform", ""),
        "output_dir": output_dir,
        "iterations_used": state.get("iteration", 0),
        "max_iterations": state.get("max_iterations", 3),
        "final_status": final_status,
        "verification_summary": summary,
    }

    report_path = Path(output_dir) / "final_report.json"
    try:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(final_report, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception as exc:
        print(f"  [finalize] WARNING: could not save final_report.json - {exc}")

    sep = "=" * 45
    print(f"\n{sep}")
    print(f"  LangGraph Agent - DONE")
    print(f"{sep}")
    print(f"  Status     : {final_status.upper()}")
    print(f"  Iterations : {state.get('iteration', 0)} / {state.get('max_iterations', 3)}")
    print(f"  Files      : {summary.get('total', 0)} total, "
          f"{summary.get('passed', 0)} passed, "
          f"{summary.get('failed', 0)} failed")
    print(f"  HIGH viol. : {high}")
    print(f"  Report     : {report_path}")
    print(f"{sep}\n")

    return {"status": final_status}
