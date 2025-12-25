"""FastAPI entrypoint for WMS orchestrator."""
from __future__ import annotations

from fastapi import FastAPI, HTTPException
from sqlalchemy.orm import Session

from orchestrator.config import get_settings
from orchestrator.db import engine, session_scope
from orchestrator.models import Base, Decision, DecisionKind, DecisionValue, Run, Stage, Task, TaskStatus
from orchestrator.pipeline import create_initial_runs
from orchestrator.schemas import TaskCreate, TaskOut
from orchestrator.util import logger
from orchestrator.worker import run_once

settings = get_settings()
app = FastAPI(title="WMS Orchestrator")


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)


@app.post("/tasks", response_model=TaskOut)
def create_task(payload: TaskCreate):
    with session_scope() as session:
        task = Task(title=payload.title, raw_request=payload.raw_request, status=TaskStatus.PENDING)
        session.add(task)
        session.flush()
        create_initial_runs(task, session, settings.max_attempts)
        session.refresh(task)
        return task


@app.get("/tasks/{task_id}", response_model=TaskOut)
def get_task(task_id: int):
    with session_scope() as session:
        task = session.get(Task, task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        return task


@app.post("/tasks/{task_id}/approve", response_model=TaskOut)
def approve_task(task_id: int, comment: str | None = None):
    with session_scope() as session:
        task = session.get(Task, task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        decision = Decision(task_id=task.id, kind=DecisionKind.HUMAN_APPROVAL, decision=DecisionValue.APPROVE, comment=comment)
        session.add(decision)
        session.refresh(task)
        return task


@app.post("/tasks/{task_id}/reject", response_model=TaskOut)
def reject_task(task_id: int, comment: str):
    if not comment:
        raise HTTPException(status_code=400, detail="Comment required")
    with session_scope() as session:
        task = session.get(Task, task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        decision = Decision(task_id=task.id, kind=DecisionKind.HUMAN_APPROVAL, decision=DecisionValue.REJECT, comment=comment)
        task.status = TaskStatus.FAILED
        session.add(decision)
        session.add(task)
        session.refresh(task)
        return task


@app.post("/tasks/{task_id}/kick")
def kick_worker(task_id: int):
    # Run worker once for manual trigger
    if run_once():
        return {"status": "processed"}
    return {"status": "no_work"}


@app.get("/health")
def health():
    return {"status": "ok"}
