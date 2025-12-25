"""Pipeline orchestration logic."""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from orchestrator.models import Artifact, Decision, DecisionKind, DecisionValue, Run, RunStatus, Stage, Task, TaskStatus
from orchestrator.schemas import ContextPack, GateDecision, ReviewResult, TaskSpec, WorkItem
from orchestrator.util import logger


def create_initial_runs(task: Task, session: Session, max_attempts: int) -> None:
    """Seed the pipeline with the Product stage."""
    run = Run(task_id=task.id, stage=Stage.PRODUCT, status=RunStatus.PENDING, attempt=1, max_attempts=max_attempts)
    session.add(run)


def next_stage_after(stage: Stage) -> Optional[Stage]:
    order = [
        Stage.PRODUCT,
        Stage.ORCHESTRATE,
        Stage.BACKEND,
        Stage.QA_BACKEND,
        Stage.SECURITY,
        Stage.BACKEND_GATE,
        Stage.FRONTEND,
        Stage.QA_FRONTEND,
        Stage.FRONTEND_GATE,
        Stage.DOCS,
        Stage.DOCS_GATE,
        Stage.CI_WAIT,
        Stage.HUMAN_APPROVAL,
        Stage.MERGE,
    ]
    try:
        idx = order.index(stage)
    except ValueError:
        return None
    if idx == len(order) - 1:
        return None
    return order[idx + 1]


def record_artifact(session: Session, task: Task, run: Run, kind: str, data: dict) -> None:
    session.add(Artifact(task_id=task.id, run_id=run.id, kind=kind, data=data))


def record_decision(session: Session, task: Task, decision_value: DecisionValue, comment: str | None = None) -> Decision:
    decision = Decision(task_id=task.id, kind=DecisionKind.HUMAN_APPROVAL, decision=decision_value, comment=comment)
    session.add(decision)
    return decision


def fail_run(session: Session, run: Run, error: str) -> None:
    run.status = RunStatus.FAIL
    run.error = error
    session.add(run)


def pass_run(session: Session, run: Run, result: dict | None = None) -> None:
    run.status = RunStatus.PASS
    run.result = result
    session.add(run)


def spawn_retry_or_fail_task(session: Session, task: Task, run: Run) -> None:
    if run.attempt < run.max_attempts:
        logger.info("Retrying stage %s for task %s (attempt %s)", run.stage, task.id, run.attempt + 1)
        session.add(
            Run(
                task_id=task.id,
                stage=run.stage,
                status=RunStatus.PENDING,
                attempt=run.attempt + 1,
                max_attempts=run.max_attempts,
            )
        )
    else:
        task.status = TaskStatus.FAILED
        logger.error("Task %s failed at stage %s after max attempts", task.id, run.stage)
        session.add(task)


def enqueue_next(session: Session, task: Task, current: Run, max_attempts: int) -> None:
    next_stage = next_stage_after(current.stage)
    if not next_stage:
        task.status = TaskStatus.DONE
        session.add(task)
        return
    session.add(
        Run(
            task_id=task.id,
            stage=next_stage,
            status=RunStatus.PENDING,
            attempt=1,
            max_attempts=max_attempts,
        )
    )
    task.status = TaskStatus.RUNNING
    session.add(task)


def is_backend_gate_ready(task: Task) -> GateDecision:
    """Verify backend + QA + Security runs passed."""
    stages = {Stage.BACKEND: False, Stage.QA_BACKEND: False, Stage.SECURITY: False}
    for run in task.runs:
        if run.stage in stages and run.status == RunStatus.PASS:
            stages[run.stage] = True
    passed = all(stages.values())
    details = "Backend, QA, Security all passed" if passed else "Awaiting backend/QA/Security pass"
    return GateDecision(gate=Stage.BACKEND_GATE, passed=passed, details=details)


def is_frontend_gate_ready(task: Task) -> GateDecision:
    stages = {Stage.FRONTEND: False, Stage.QA_FRONTEND: False}
    for run in task.runs:
        if run.stage in stages and run.status == RunStatus.PASS:
            stages[run.stage] = True
    passed = all(stages.values())
    details = "Frontend and QA passed" if passed else "Awaiting frontend/QA pass"
    return GateDecision(gate=Stage.FRONTEND_GATE, passed=passed, details=details)


def is_docs_gate_ready(task: Task) -> GateDecision:
    docs_pass = any(r.stage == Stage.DOCS and r.status == RunStatus.PASS for r in task.runs)
    passed = docs_pass
    details = "Docs delivered" if passed else "Docs pending"
    return GateDecision(gate=Stage.DOCS_GATE, passed=passed, details=details)


def should_wait_for_ci(task: Task) -> bool:
    return True


__all__ = [
    "create_initial_runs",
    "next_stage_after",
    "record_artifact",
    "record_decision",
    "fail_run",
    "pass_run",
    "spawn_retry_or_fail_task",
    "enqueue_next",
    "is_backend_gate_ready",
    "is_frontend_gate_ready",
    "is_docs_gate_ready",
    "should_wait_for_ci",
]
