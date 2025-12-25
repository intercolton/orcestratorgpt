"""Pydantic schemas for API and pipeline payloads."""
from datetime import datetime
from enum import Enum
from typing import Any, List, Optional

from pydantic import BaseModel, Field

from orchestrator.models import DecisionKind, DecisionValue, RunStatus, Stage, TaskStatus


class TaskCreate(BaseModel):
    title: str
    raw_request: str


class TaskSpec(BaseModel):
    goal: str
    acceptance_criteria: list[str]
    constraints: list[str] = Field(default_factory=list)


class ContextPack(BaseModel):
    task_id: int
    title: str
    task_spec: TaskSpec
    stage: Stage
    artifacts: list[dict[str, Any]] = Field(default_factory=list)


class WorkItem(BaseModel):
    summary: str
    files_to_change: list[str] = Field(default_factory=list)
    diff_plan: list[str] = Field(default_factory=list)


class ReviewResult(BaseModel):
    stage: Stage
    passed: bool
    issues: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


class GateDecision(BaseModel):
    gate: Stage
    passed: bool
    details: Optional[str] = None


class ArtifactOut(BaseModel):
    id: int
    kind: str
    data: dict[str, Any]
    created_at: datetime


class RunOut(BaseModel):
    id: int
    stage: Stage
    status: RunStatus
    attempt: int
    max_attempts: int
    payload: Optional[dict[str, Any]]
    result: Optional[dict[str, Any]]
    error: Optional[str]
    created_at: datetime
    updated_at: datetime


class DecisionOut(BaseModel):
    id: int
    kind: DecisionKind
    decision: DecisionValue
    comment: Optional[str]
    created_at: datetime


class TaskOut(BaseModel):
    id: int
    title: str
    raw_request: str
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
    runs: List[RunOut]
    artifacts: List[ArtifactOut]
    decisions: List[DecisionOut]

    class Config:
        orm_mode = True
