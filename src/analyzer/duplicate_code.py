"""
analyzer.duplicate_code — a simple, line-based duplicate-code detector.

Approach: build a sliding window of `min_lines` consecutive non-blank
source lines (each normalised by stripping leading/trailing whitespace so
re-indented copies still match), hash each window's content, and report
when a window's content has already been seen earlier in the file.

This is intentionally a textual/line-based technique rather than a
semantic (AST) one — it is simple, fast, and catches the common
copy-paste case, but it will not detect duplicates that are equivalent
after renaming variables. That trade-off is documented in the project
report as an accepted, deliberate limitation.
"""
from __future__ import annotations

import ast

from analyzer.core import Issue, Severity


def find_duplicate_code(source: str, min_lines: int = 4) -> list[Issue]:
    if not isinstance(source, str):
        raise TypeError(f"source must be a str, got {type(source).__name__}")
    if min_lines < 2:
        raise ValueError(f"min_lines must be >= 2, got {min_lines}")

    ast.parse(source)  # validates syntax; raises SyntaxError on invalid input

    raw_lines = source.split("\n")
    if source.endswith("\n"):
        raw_lines = raw_lines[:-1]

    # (original_line_number, normalised_text), blank lines excluded so
    # they can't anchor or interrupt a comparison window.
    non_blank = [(i + 1, line.strip()) for i, line in enumerate(raw_lines) if line.strip() != ""]

    n = len(non_blank)
    seen: dict[tuple[str, ...], int] = {}
    issues: list[Issue] = []

    start = 0
    while start <= n - min_lines:
        window_lines = non_blank[start:start + min_lines]
        window_key = tuple(text for _, text in window_lines)
        first_line_of_window = window_lines[0][0]

        if window_key in seen:
            original_line = seen[window_key]
            issues.append(
                Issue(
                    category="duplicate_code",
                    message=(
                        f"Code block starting at line {first_line_of_window} "
                        f"duplicates the block starting at line {original_line} "
                        f"({min_lines}+ matching lines)."
                    ),
                    line=first_line_of_window,
                    severity=Severity.WARNING,
                )
            )
            # Skip past this whole matched chunk rather than re-checking
            # every overlapping window inside it, so one duplicated region
            # produces one issue per min_lines chunk, not one per offset.
            start += min_lines
        else:
            seen[window_key] = first_line_of_window
            start += 1

    return issues
