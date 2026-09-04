"""
analyzer.engine — orchestrates every check (metrics, complexity, naming,
unused_vars, duplicate_code) against a source file and aggregates the
results into a single AnalysisResult.

Design note: the individual check modules (metrics.py, complexity.py,
naming.py, unused_vars.py, duplicate_code.py) raise SyntaxError/TypeError
directly and are unit-tested that way, because that keeps each module's
contract simple and explicit. This orchestrator is the boundary a CLI
user actually interacts with, so it is more defensive: a syntax error in
the *file being analysed* is an expected, normal outcome for a static
analysis tool (the user is pointing it at code that doesn't parse), not
a bug in the analyzer — so it's caught and reported as an Issue rather
than raised.
"""
from __future__ import annotations

import os

from analyzer.core import AnalysisResult, Issue, Severity
from analyzer.metrics import compute_metrics
from analyzer.complexity import calculate_complexities, check_complexity
from analyzer.naming import check_naming
from analyzer.unused_vars import check_unused_variables
from analyzer.duplicate_code import find_duplicate_code

DEFAULT_COMPLEXITY_THRESHOLD = 10
DEFAULT_DUPLICATE_MIN_LINES = 3 # per project spec Section 1.2/TC-FR4-03


def analyze_source(
    source: str,
    filename: str = "<string>",
    complexity_threshold: int = DEFAULT_COMPLEXITY_THRESHOLD,
    duplicate_min_lines: int = DEFAULT_DUPLICATE_MIN_LINES,
) -> AnalysisResult:
    if not isinstance(source, str):
        raise TypeError(f"source must be a str, got {type(source).__name__}")

    result = AnalysisResult(filename=filename)

    try:
        result.metrics = compute_metrics(source)
        complexities = calculate_complexities(source)
        result.metrics["average_complexity"] = (
            sum(complexities.values()) / len(complexities) if complexities else 0
        )

        for issue in check_complexity(source, threshold=complexity_threshold):
            result.add_issue(issue)
        for issue in check_naming(source):
            result.add_issue(issue)
        for issue in check_unused_variables(source):
            result.add_issue(issue)
        for issue in find_duplicate_code(source, min_lines=duplicate_min_lines):
            result.add_issue(issue)

    except SyntaxError as e:
        result.add_issue(
            Issue(
                category="syntax_error",
                message=f"Could not parse '{filename}': {e.msg} (line {e.lineno or 1})",
                line=e.lineno or 1,
                severity=Severity.ERROR,
            )
        )
        result.metrics = {}

    return result


def analyze_file(
    path: str,
    complexity_threshold: int = DEFAULT_COMPLEXITY_THRESHOLD,
    duplicate_min_lines: int = DEFAULT_DUPLICATE_MIN_LINES,
) -> AnalysisResult:
    if not os.path.isfile(path):
        raise FileNotFoundError(f"No such file: {path}")
    if not path.endswith(".py"):
        raise ValueError(f"Expected a .py file, got: {path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            source = f.read()
    except UnicodeDecodeError as e:
        # Section 1.8: a file that cannot be decoded as UTF-8 is an
        # invalid-input scenario, not a program bug — report it the same
        # way as a missing file or wrong extension, rather than crashing.
        raise ValueError(f"Could not read '{path}' as UTF-8: {e}") from e

    return analyze_source(
        source,
        filename=path,
        complexity_threshold=complexity_threshold,
        duplicate_min_lines=duplicate_min_lines,
    )
