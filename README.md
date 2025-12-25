# WMS Orchestrator

Production-grade оркестратор для агентной фуллстек разработки WMS без n8n. Реализует 6 ролей агентов, 3 гейта с реворками и финальный human approval перед merge.

## Дерево репозитория
```
wms-orchestrator/
  README.md
  Dockerfile
  requirements.txt
  ops/
    docker-compose.yml
    .env.example
  migrations/
    001_init.sql
  orchestrator/
    __init__.py
    main.py
    config.py
    db.py
    models.py
    schemas.py
    pipeline.py
    worker.py
    llm.py
    prompts.py
    github_client.py
    ci_gate.py
    security.py
    util.py
  .github/
    workflows/
      ci-backend.yml
      ci-frontend.yml
      secret-scan.yml
  scripts/
    init_db.sh
    run_local.sh
```

## Запуск локально
1. `cp ops/.env.example .env` и заполнить переменные (минимум `DATABASE_URL`).
2. `docker-compose -f ops/docker-compose.yml up -d db`
3. `DATABASE_URL=postgresql://wms:wms@localhost:5432/wms ./scripts/init_db.sh`
4. `docker-compose -f ops/docker-compose.yml up --build`
5. Проверить: `curl -X POST http://localhost:8000/tasks -H "Content-Type: application/json" -d '{"title":"Demo","raw_request":"Сделать WMS"}'`

## API
- `POST /tasks {title, raw_request}` — создаёт задачу, стартует PRODUCT run.
- `GET /tasks/{id}` — возвращает состояние задачи с runs/artifacts/decisions.
- `POST /tasks/{id}/approve {comment?}` — записывает human approval.
- `POST /tasks/{id}/reject {comment}` — фиксирует отказ, статус FAILED.
- `POST /tasks/{id}/kick` — однократно запускает worker обработку (pull модель).
- `GET /health` — healthcheck.

## Pipeline
Последовательность стадий: `PRODUCT -> ORCHESTRATE -> (BACKEND -> QA -> SECURITY -> BACKEND_GATE) -> (FRONTEND -> QA -> FRONTEND_GATE) -> DOCS -> DOCS_GATE -> CI_WAIT -> HUMAN_APPROVAL -> MERGE -> DONE`. Реворки до 3 попыток на каждый stage: провал QA или Security возвращает на соответствующий BACKEND/FRONTEND run, gate-фейлы возвращают на Docs/Backend/Frontend; при исчерпании попыток задача переводится в FAILED. HUMAN_APPROVAL требует явного решения в таблице decisions.

## Примеры JSON
### TaskSpec
```json
{
  "goal": "Оптимизировать складские приемки",
  "acceptance_criteria": [
    "API возвращает новые статусы",
    "Логирование ошибок без токенов"
  ],
  "constraints": ["Postgres", "FastAPI"]
}
```

### ContextPack
```json
{
  "task_id": 1,
  "title": "Demo",
  "task_spec": {
    "goal": "Оптимизировать склад",
    "acceptance_criteria": ["Все гейты проходят"],
    "constraints": []
  },
  "stage": "BACKEND",
  "artifacts": []
}
```

### ReviewResult
```json
{
  "stage": "QA_BACKEND",
  "passed": true,
  "issues": [],
  "suggestions": ["Добавить unit-тест на ошибки"]
}
```

### GateDecision
```json
{
  "gate": "BACKEND_GATE",
  "passed": true,
  "details": "Backend, QA, Security all passed"
}
```

## CI и безопасность
- `ci-backend.yml` и `ci-frontend.yml` запускают проверки только если найдены соответствующие папки; иначе — skip без падения.
- `secret-scan.yml` запускает gitleaks на каждом push/PR.
- `security.py` содержит простую политику детекта секретов (`sk-`, `ghp_`).

## Обработчик worker
`orchestrator.worker.worker_loop()` опрашивает таблицу runs и последовательно выполняет стадии. При PASS создаётся следующий run, при FAIL — планируется повтор до max_attempts, иначе task становится FAILED.
