from langchain_ollama import ChatOllama
from langchain.tools import tool
# from langgraph.prebuilt import create_agent  # ← правильный импорт
from langchain.agents import create_agent

llm = ChatOllama(
    model="llama3.2",
    temperature=0.2,
    num_ctx=8192,        # ← явно задаём контекст
)



@tool
def generate_devops_files(request_json_path: str) -> str:
    """Generate Dockerfile, docker-compose.yml, CI/CD config and deploy.sh from a request.json file."""
    from generate.prompt_manager import build_prompts_from_request
    from generate import agent
    prompts, output_dir = build_prompts_from_request(request_json_path)
    results = agent.generate_from_prompts(prompts, output_dir)
    return f"Generated {len(results)} files to {output_dir}"

@tool
def verify_generated_files(output_dir: str) -> str:
    """Run static analysis and security policy checks on generated DevOps files."""
    from verify import verifier
    report = verifier.run(output_dir)
    failed = report["summary"]["failed"]
    high = report["summary"]["high_violation"]
    return f"Failed: {failed}, HIGH violations: {high}"

@tool
def regenerate_files(output_dir: str) -> str:
    """Regenerate DevOps files that failed verification, incorporating the found issues."""
    from generate import regenerator
    results = regenerator.run(output_dir)
    return f"Regenerated {len(results)} files"

tools = [generate_devops_files, verify_generated_files, regenerate_files]

# Проверяем что bind_tools вообще работает
test = llm.bind_tools(tools)
result = test.invoke("say hello")
print(result)

agent_graph = create_agent(
    model=llm,
    tools=tools,
    system_prompt=(
        "You are a DevOps automation agent. "
        "When given a task: first generate files, then verify them, "
        "then regenerate if there are failures. "
        "Repeat regeneration maximum 3 times until verification passes."
    ),
    name="devops-agent",
)

REQUEST_FILE = os.path.abspath("default_request.json")
OUTPUT_DIR   = os.path.abspath("generated")

result = agent_graph.invoke({
    "messages": [{
        "role": "user",
        "content": (
            f"Generate DevOps files from {REQUEST_FILE}, "
            f"save output to {OUTPUT_DIR}, "
            f"then verify them, then regenerate if there are failures. "
            f"Repeat until verification passes or 3 attempts are exhausted."
        )
    }]
})

print(result["messages"][-1].content)