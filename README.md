# Orchestrator GPT

A minimal skeleton illustrating a gated orchestration workflow with product, backend, frontend, QA, security, and documentation steps.

## Что сделано (по-русски)
Этот репозиторий демонстрирует упрощённый оркестратор, который проводит рабочий элемент через цепочку агентных гейтов.
`orchestrator.py` создаёт PRD, критерии приёмки и черновик OpenAPI, а затем последовательно имитирует работу бэкенда, фронтенда, QA, безопасности и документации.
После успешного прохождения всех гейтов оркестратор помечает задачу как готовую к пользовательскому подтверждению и сохраняет трассировку шагов в `artifacts` объекта `WorkItem`.

## Overview
The `orchestrator.py` module defines lightweight data structures and an `Orchestrator` helper that progresses a `WorkItem` through gates:
- Product generates PRD, acceptance criteria, and an OpenAPI draft.
- Backend, QA, and Security collaborate to pass the backend gate.
- Frontend and QA drive the frontend gate.
- Docs validate alignment with implementation.

Each stage logs trace entries to `WorkItem.artifacts` and marks gate outcomes, setting `ready_for_user_approval` when all gates pass.

## Running the demo
```
python - <<'PY'
from orchestrator import Orchestrator, WorkItem

work = WorkItem(user_request="Implement WMS orchestrator")
result = Orchestrator(work).run()
print(result)
print(result.artifacts)
PY
```

### CLI helper
You can also run the demo directly:

```
python orchestrator.py "Ship feature X"
```
