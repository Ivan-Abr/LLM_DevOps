from typing import TypedDict

class AgentState(TypedDict):
    request_file: str  # путь к request.json
    output_dir: str  # куда сохранять файлы
    project_description: str  # описание проекта из request
    platform: str  # github | gitlab
    prompts: list[dict]  # сформированные промпты (from prompt_manager)
    generated_files: list[dict]  # результаты generate_from_prompts
    verification_report: dict  # результат verifier.run()
    iteration: int  # текущая итерация регенерации (0-based)
    max_iterations: int  # максимальное число итераций регенерации
    status: str
