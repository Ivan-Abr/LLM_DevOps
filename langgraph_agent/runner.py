import sys
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()
from .graph import build_graph
from .state import AgentState

def run(request_file: str = "default_request.json", max_iterations: int = 3) -> dict:
    sep = "=" * 45
    print(f"\n{sep}")
    print(f"  LangGraph DevOps Agent")
    print(f"{sep}")
    print(f"  Request    : {request_file}")
    print(f"  Max retries: {max_iterations}")
    print(f"  Started    : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{sep}")

    graph = build_graph()

    initial_state: AgentState = {
        "request_file": request_file,
        "output_dir": "generated",
        "project_description": "",
        "platform": "gitlab",
        "prompts": [],
        "generated_files": [],
        "verification_report": {},
        "iteration": 0,
        "max_iterations": max_iterations,
        "status": "pending",
    }

    final_state: dict = {}
    for chunk in graph.stream(initial_state, stream_mode="updates"):
        for node_name, node_output in chunk.items():
            final_state.update(node_output)
    return final_state

if __name__ == "__main__":
    request_file   = sys.argv[1] if len(sys.argv) > 1 else "default_request.json"
    max_iterations = int(sys.argv[2]) if len(sys.argv) > 2 else 3

    result = run(request_file, max_iterations)

    final_status = result.get("status", "unknown")
    print(f"Pipeline finished with status: {final_status.upper()}")
    sys.exit(0 if final_status == "passed" else 1)
