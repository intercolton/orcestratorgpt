"""Security policy checks."""
import re
from typing import List

from orchestrator.schemas import ReviewResult, Stage

SECRET_PATTERNS = [re.compile(r"sk-[A-Za-z0-9]{10,}"), re.compile(r"ghp_[A-Za-z0-9]{10,}")]


def scan_text(text: str) -> List[str]:
    issues: List[str] = []
    for pattern in SECRET_PATTERNS:
        if pattern.search(text):
            issues.append("Potential secret detected")
    return issues


def evaluate_security(diff_summary: str) -> ReviewResult:
    issues = scan_text(diff_summary)
    passed = len(issues) == 0
    return ReviewResult(stage=Stage.SECURITY, passed=passed, issues=issues, suggestions=[])
