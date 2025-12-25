from __future__ import annotations

import dataclasses
import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class GateStatus(str, Enum):
    PENDING = "pending"
    PASS = "pass"
    FAIL = "fail"


@dataclass
class Deliverable:
    name: str
    description: str


@dataclass
class AgentReport:
    agent: str
    status: GateStatus
    notes: str = ""
    deliverables: List[Deliverable] = field(default_factory=list)


@dataclass
class WorkItem:
    user_request: str
    prd: Optional[str] = None
    acceptance_criteria: Optional[str] = None
    openapi_draft: Optional[str] = None
    backend_gate: GateStatus = GateStatus.PENDING
    frontend_gate: GateStatus = GateStatus.PENDING
    docs_gate: GateStatus = GateStatus.PENDING
    ready_for_user_approval: bool = False
    artifacts: Dict[str, List[str]] = field(default_factory=dict)

    def record(self, key: str, message: str) -> None:
        self.artifacts.setdefault(key, []).append(message)


class Orchestrator:
    def __init__(self, work_item: WorkItem) -> None:
        self.work_item = work_item

    def run(self) -> WorkItem:
        self._product_phase()
        self._backend_phase()
        self._frontend_phase()
        self._docs_phase()
        self._finalize()
        return self.work_item

    def _product_phase(self) -> None:
        self.work_item.record("trace", "Product agent: drafting PRD, AC, OpenAPI")
        self.work_item.prd = f"PRD for: {self.work_item.user_request}"
        self.work_item.acceptance_criteria = "- Criteria TBD"
        self.work_item.openapi_draft = "openapi: 3.1.0\ninfo:\n  title: Draft\n"

    def _backend_phase(self) -> None:
        backend_report = AgentReport(
            agent="Backend",
            status=GateStatus.PASS,
            notes="Scaffolded backend implementation",
            deliverables=[Deliverable(name="backend", description="Initial backend stub")],
        )
        qa_report = AgentReport(agent="QA", status=GateStatus.PASS, notes="Backend QA passed")
        security_report = AgentReport(agent="Security", status=GateStatus.PASS, notes="Security review passed")
        if backend_report.status is GateStatus.PASS and qa_report.status is GateStatus.PASS and security_report.status is GateStatus.PASS:
            self.work_item.backend_gate = GateStatus.PASS
        else:
            self.work_item.backend_gate = GateStatus.FAIL
        self.work_item.record("trace", f"Backend gate: {self.work_item.backend_gate}")

    def _frontend_phase(self) -> None:
        frontend_report = AgentReport(
            agent="Frontend",
            status=GateStatus.PASS,
            notes="Scaffolded frontend implementation",
            deliverables=[Deliverable(name="frontend", description="Initial frontend stub")],
        )
        qa_report = AgentReport(agent="QA", status=GateStatus.PASS, notes="Frontend QA passed")
        if frontend_report.status is GateStatus.PASS and qa_report.status is GateStatus.PASS:
            self.work_item.frontend_gate = GateStatus.PASS
        else:
            self.work_item.frontend_gate = GateStatus.FAIL
        self.work_item.record("trace", f"Frontend gate: {self.work_item.frontend_gate}")

    def _docs_phase(self) -> None:
        docs_report = AgentReport(
            agent="Docs",
            status=GateStatus.PASS,
            notes="Docs aligned with implementation",
            deliverables=[Deliverable(name="docs", description="Docs prepared")],
        )
        if docs_report.status is GateStatus.PASS:
            self.work_item.docs_gate = GateStatus.PASS
        else:
            self.work_item.docs_gate = GateStatus.FAIL
        self.work_item.record("trace", f"Docs gate: {self.work_item.docs_gate}")

    def _finalize(self) -> None:
        gates = [self.work_item.backend_gate, self.work_item.frontend_gate, self.work_item.docs_gate]
        if all(status is GateStatus.PASS for status in gates):
            self.work_item.ready_for_user_approval = True
        self.work_item.record("trace", f"Ready for user approval: {self.work_item.ready_for_user_approval}")


def run_demo(user_request: str = "Implement WMS orchestrator") -> WorkItem:
    """Run the orchestration flow and return the populated WorkItem."""

    work = WorkItem(user_request=user_request)
    orchestrated = Orchestrator(work).run()
    print(orchestrated)
    print(orchestrated.artifacts)
    return orchestrated


if __name__ == "__main__":
    request = sys.argv[1] if len(sys.argv) > 1 else "Implement WMS orchestrator"
    run_demo(request)


__all__ = [
    "GateStatus",
    "Deliverable",
    "AgentReport",
    "WorkItem",
    "Orchestrator",
]
