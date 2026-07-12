from langgraph.graph import StateGraph, START, END

from .state import AgentState
from .nodes import (
    node_load_request,
    node_collect_and_build_prompts,
    node_generate,
    node_verify,
    node_regenerate,
    node_finalize,
)

def route_after_verify(state: AgentState) -> str:
    if state.get("status") == "failed":
        return "finalize"

    report  = state.get("verification_report", {})
    summary = report.get("summary", {})
    failed  = summary.get("failed", 0)
    high    = summary.get("high_violations", 0)
    warned = summary.get("warned", 0)

    if failed == 0 and high == 0 and warned == 0:
        print("\n  [router] Verification passed - finalizing")
        return "finalize"

    if state["iteration"] >= state["max_iterations"]:
        print(
            f"\n  [router] Max iterations ({state['max_iterations']}) reached "
            f"with {failed} failed file(s) — finalizing anyway"
        )
        return "finalize"

    print(
        f"\n  [router] {failed} failed file(s), {high} HIGH violation(s) "
        f"— regenerating (attempt {state['iteration'] + 1}/{state['max_iterations']})"
    )
    return "regenerate"

def build_graph():

    graph = StateGraph(AgentState)

    graph.add_node("load_request",  node_load_request)
    graph.add_node("build_prompts", node_collect_and_build_prompts)
    graph.add_node("generate",      node_generate)
    graph.add_node("verify",        node_verify)
    graph.add_node("regenerate",    node_regenerate)
    graph.add_node("finalize",      node_finalize)

    graph.add_edge(START,            "load_request")
    graph.add_edge("load_request",   "build_prompts")
    graph.add_edge("build_prompts",  "generate")
    graph.add_edge("generate",       "verify")
    graph.add_edge("finalize",       END)

    graph.add_edge("regenerate", "verify")

    graph.add_conditional_edges(
        "verify",
        route_after_verify,
        {
            "finalize":   "finalize",
            "regenerate": "regenerate",
        },
    )
    return graph.compile()
