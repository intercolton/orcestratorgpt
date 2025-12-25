"""Role prompts and contracts for LLM calls."""

ROLE_PROMPTS = {
    "Product": "Сформируй TaskSpec (goal, acceptance_criteria, constraints) по raw_request.",
    "Orchestrator": "Преобразуй TaskSpec в WorkItems и ContextPack для ролей.",
    "Backend": "Сделай план backend-правок, список файлов и диффы.",
    "Frontend": "Сделай план frontend-правок, список файлов и диффы.",
    "QA": "Проведи ревью и верни pass/fail с issues.",
    "Security": "Security ревью: pass/fail, найденные риски.",
    "Docs": "Собери ReleaseNotes и HowToVerify на основе реализации.",
}
