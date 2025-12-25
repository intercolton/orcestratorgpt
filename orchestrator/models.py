"""SQLAlchemy models for orchestrator state."""
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Column, DateTime, Enum as SAEnum, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    FAILED = "FAILED"
    DONE = "DONE"


class RunStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    PASS = "PASS"
    FAIL = "FAIL"


class Stage(str, Enum):
    PRODUCT = "PRODUCT"
    ORCHESTRATE = "ORCHESTRATE"
    BACKEND = "BACKEND"
    QA_BACKEND = "QA_BACKEND"
    SECURITY = "SECURITY"
    BACKEND_GATE = "BACKEND_GATE"
    FRONTEND = "FRONTEND"
    QA_FRONTEND = "QA_FRONTEND"
    FRONTEND_GATE = "FRONTEND_GATE"
    DOCS = "DOCS"
    DOCS_GATE = "DOCS_GATE"
    CI_WAIT = "CI_WAIT"
    HUMAN_APPROVAL = "HUMAN_APPROVAL"
    MERGE = "MERGE"


class DecisionKind(str, Enum):
    HUMAN_APPROVAL = "HUMAN_APPROVAL"


class DecisionValue(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    raw_request = Column(Text, nullable=False)
    status = Column(SAEnum(TaskStatus), default=TaskStatus.PENDING, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    runs = relationship("Run", back_populates="task", cascade="all, delete-orphan")
    artifacts = relationship("Artifact", back_populates="task", cascade="all, delete-orphan")
    decisions = relationship("Decision", back_populates="task", cascade="all, delete-orphan")


class Run(Base):
    __tablename__ = "runs"

    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    stage = Column(SAEnum(Stage), nullable=False)
    status = Column(SAEnum(RunStatus), default=RunStatus.PENDING, nullable=False)
    attempt = Column(Integer, default=1, nullable=False)
    max_attempts = Column(Integer, default=3, nullable=False)
    payload = Column(JSON, nullable=True)
    result = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    task = relationship("Task", back_populates="runs")


class Artifact(Base):
    __tablename__ = "artifacts"

    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    run_id = Column(Integer, ForeignKey("runs.id"), nullable=True)
    kind = Column(String(64), nullable=False)
    data = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    task = relationship("Task", back_populates="artifacts")
    run = relationship("Run")


class Decision(Base):
    __tablename__ = "decisions"

    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    kind = Column(SAEnum(DecisionKind), nullable=False)
    decision = Column(SAEnum(DecisionValue), nullable=False)
    comment: Optional[str] = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    task = relationship("Task", back_populates="decisions")
