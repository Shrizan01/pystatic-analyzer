"""
Core data model shared by every analyzer module.

Every check (metrics, complexity, naming, unused_vars, duplicate_code)
reports its findings as Issue objects collected into an AnalysisResult.
Keeping this contract in one place means each module can be developed
and tested independently while still producing a consistent report.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Severity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True)
class Issue:
    """A single finding reported by an analyzer module."""

    category: str
    message: str
    line: int
    severity: Severity

    def __post_init__(self) -> None:
        if self.line < 1:
            raise ValueError(f"line must be a positive (1-indexed) integer, got {self.line}")
        if not self.category:
            raise ValueError("category must not be empty")


@dataclass
class AnalysisResult:
    """Aggregated findings and metrics for a single analysed file."""

    filename: str
    issues: list[Issue] = field(default_factory=list)
    metrics: dict[str, object] = field(default_factory=dict)

    def add_issue(self, issue: Issue) -> None:
        self.issues.append(issue)

    def issues_by_category(self, category: str) -> list[Issue]:
        return [i for i in self.issues if i.category == category]

    def has_errors(self) -> bool:
        return any(i.severity == Severity.ERROR for i in self.issues)
