"""Polling worker that advances pipeline runs."""
from __future__ import annotations

import time
from typing import Callable, Dict

from sqlalchemy import select
from sqlalchemy.orm import Session

from orchestrator import llm
from orchestrator.ci_gate import wait_for_checks
from orchestrator.config import get_settings
from orchestrator.db import session_scope
from orchestrator.github_client import GitHubClient
from orchestrator.models import Decision, DecisionKind, DecisionValue, Run, RunStatus, Stage, Task, TaskStatus
from orchestrator.pipeline import (
    create_initial_runs,
    enqueue_next,
    fail_run,
    is_backend_gate_ready,
    is_docs_gate_ready,
    is_frontend_gate_ready,
    pass_run,
    record_artifact,
    spawn_retry_or_fail_task,
    spawn_rework_or_fail_task,
)
from orchestrator.schemas import ContextPack, GateDecision, ReviewResult, TaskSpec, WorkItem
from orchestrator.security import evaluate_security
from orchestrator.util import logger

settings = get_settings()


def get_next_run(session: Session) -> Run | None:
    stmt = select(Run).where(Run.status == RunStatus.PENDING).order_by(Run.created_at.asc())
    return session.scalars(stmt).first()


def _context_for(task: Task, stage: Stage) -> ContextPack:
    artifacts = [
        {"kind": a.kind, "data": a.data, "run_id": a.run_id}
        for a in sorted(task.artifacts, key=lambda a: a.id)
    ]
    task_spec_artifact = next((a for a in task.artifacts if a.kind == "TaskSpec"), None)
    task_spec_data = task_spec_artifact.data if task_spec_artifact else {
        "goal": task.title,
        "acceptance_criteria": [],
        "constraints": [],
    }
    task_spec = TaskSpec(**task_spec_data)
    return ContextPack(task_id=task.id, title=task.title, task_spec=task_spec, stage=stage, artifacts=artifacts)


def handle_product(session: Session, task: Task, run: Run) -> None:
    result = llm.call("Product", {"raw_request": task.raw_request})
    record_artifact(session, task, run, "TaskSpec", result)
    pass_run(session, run, result)


def handle_orchestrate(session: Session, task: Task, run: Run) -> None:
    ctx = _context_for(task, run.stage)
    result = llm.call("Orchestrator", ctx.dict())
    record_artifact(session, task, run, "ContextPack", result)
    pass_run(session, run, result)


def handle_backend(session: Session, task: Task, run: Run) -> None:
    ctx = _context_for(task, run.stage)
    result = llm.call("Backend", ctx.dict())
    record_artifact(session, task, run, "BackendPlan", result)
    pass_run(session, run, result)


def handle_frontend(session: Session, task: Task, run: Run) -> None:
    ctx = _context_for(task, run.stage)
    result = llm.call("Frontend", ctx.dict())
    record_artifact(session, task, run, "FrontendPlan", result)
    pass_run(session, run, result)


def handle_qa(session: Session, task: Task, run: Run, target_stage: Stage) -> None:
    ctx = _context_for(task, run.stage)
    result = llm.call("QA", {"context": ctx.dict(), "target_stage": target_stage.value})
    passed = bool(result.get("passed", True))
    issues = result.get("issues", [])
    suggestions = result.get("suggestions", [])
    review = ReviewResult(stage=run.stage, passed=passed, issues=issues, suggestions=suggestions)
    review_payload = {"llm": result, "review": review.dict()}
    record_artifact(session, task, run, f"QA-{target_stage.value}", review_payload)
    if passed:
        pass_run(session, run, review_payload)
    else:
        fail_run(session, run, "QA reported failures")
        spawn_rework_or_fail_task(session, task, target_stage, run.max_attempts)


def handle_security(session: Session, task: Task, run: Run) -> None:
    ctx = _context_for(task, run.stage)
    diff_summary = "\n".join(plan for plan in ctx.artifacts[-1:]) if ctx.artifacts else ""
    review = evaluate_security(diff_summary)
    record_artifact(session, task, run, "SecurityReview", review.dict())
    if review.passed:
        pass_run(session, run, review.dict())
    else:
        fail_run(session, run, "Security issues found")
        spawn_rework_or_fail_task(session, task, Stage.BACKEND, run.max_attempts)


def handle_gate(
    session: Session, task: Task, run: Run, gate_check: Callable[[Task], GateDecision], rework_stage: Stage
) -> None:
    decision = gate_check(task)
    record_artifact(session, task, run, f"Gate-{decision.gate.value}", decision.dict())
    if decision.passed:
        pass_run(session, run, decision.dict())
    else:
        fail_run(session, run, decision.details or "Gate not ready")
        spawn_rework_or_fail_task(session, task, rework_stage, run.max_attempts)


def handle_docs(session: Session, task: Task, run: Run) -> None:
    ctx = _context_for(task, run.stage)
    result = llm.call("Docs", ctx.dict())
    record_artifact(session, task, run, "Docs", result)
    pass_run(session, run, result)


def handle_ci_wait(session: Session, task: Task, run: Run) -> None:
    pr_number = None
    try:
        pr_number = task.artifacts[-1].data.get("pr_number") if task.artifacts else None
    except Exception:
        pr_number = None
    if pr_number:
        ok = wait_for_checks(pr_number)
    else:
        ok = True
    if ok:
        pass_run(session, run, {"checks": "green"})
    else:
        fail_run(session, run, "CI checks failed or timeout")
        spawn_retry_or_fail_task(session, task, run)


def handle_human_approval(session: Session, task: Task, run: Run) -> None:
    decision = next((d for d in task.decisions if d.kind == DecisionKind.HUMAN_APPROVAL), None)
    if not decision:
        run.status = RunStatus.PENDING
        session.add(run)
        return
    if decision.decision == DecisionValue.APPROVE:
        pass_run(session, run, {"decision": decision.decision.value, "comment": decision.comment})
    else:
        fail_run(session, run, decision.comment or "Rejected")
        spawn_retry_or_fail_task(session, task, run)


def handle_merge(session: Session, task: Task, run: Run) -> None:
    client = GitHubClient()
    pr_number = None
    for art in reversed(task.artifacts):
        if "pr_number" in art.data:
            pr_number = art.data["pr_number"]
            break
    if pr_number:
        client.comment_pull_request(pr_number, "Merging after approval")
    pass_run(session, run, {"merged": True, "pr_number": pr_number})
    task.status = TaskStatus.DONE
    session.add(task)


HANDLERS: Dict[Stage, Callable[[Session, Task, Run], None]] = {
    Stage.PRODUCT: handle_product,
    Stage.ORCHESTRATE: handle_orchestrate,
    Stage.BACKEND: handle_backend,
    Stage.QA_BACKEND: lambda s, t, r: handle_qa(s, t, r, Stage.BACKEND),
    Stage.SECURITY: handle_security,
    Stage.BACKEND_GATE: lambda s, t, r: handle_gate(s, t, r, is_backend_gate_ready, Stage.BACKEND),
    Stage.FRONTEND: handle_frontend,
    Stage.QA_FRONTEND: lambda s, t, r: handle_qa(s, t, r, Stage.FRONTEND),
    Stage.FRONTEND_GATE: lambda s, t, r: handle_gate(s, t, r, is_frontend_gate_ready, Stage.FRONTEND),
    Stage.DOCS: handle_docs,
    Stage.DOCS_GATE: lambda s, t, r: handle_gate(s, t, r, is_docs_gate_ready, Stage.DOCS),
    Stage.CI_WAIT: handle_ci_wait,
    Stage.HUMAN_APPROVAL: handle_human_approval,
    Stage.MERGE: handle_merge,
}


def process_run(session: Session, run: Run) -> None:
    task = session.get(Task, run.task_id)
    if not task:
        return
    run.status = RunStatus.RUNNING
    session.add(run)
    handler = HANDLERS.get(run.stage)
    if not handler:
        fail_run(session, run, f"No handler for stage {run.stage}")
        spawn_retry_or_fail_task(session, task, run)
        return
    try:
        handler(session, task, run)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Error in stage %s for task %s", run.stage, task.id)
        fail_run(session, run, str(exc))
        spawn_retry_or_fail_task(session, task, run)
        return
    if run.status == RunStatus.PASS:
        enqueue_next(session, task, run, run.max_attempts)


def run_once() -> bool:
    with session_scope() as session:
        run = get_next_run(session)
        if not run:
            return False
        process_run(session, run)
        return True


def worker_loop() -> None:
    logger.info("Starting worker loop")
    while True:
        has_work = run_once()
        if not has_work:
            time.sleep(settings.worker_poll_interval_seconds)


__all__ = ["worker_loop", "run_once", "create_initial_runs"]


if __name__ == "__main__":
    worker_loop()
