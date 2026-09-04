"""
analyzer.cli — command-line entry point.

Usage:
    python -m analyzer.cli path/to/file.py [options]
"""
from __future__ import annotations

import argparse
import sys

from analyzer.core import AnalysisResult, Severity
from analyzer.engine import (
    analyze_file,
    DEFAULT_COMPLEXITY_THRESHOLD,
    DEFAULT_DUPLICATE_MIN_LINES,
)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="analyzer",
        description="Static code analysis for a single Python source file.",
    )
    parser.add_argument("path", help="Path to the .py file to analyse")
    parser.add_argument(
        "--complexity-threshold",
        type=int,
        default=DEFAULT_COMPLEXITY_THRESHOLD,
        help=f"Cyclomatic complexity threshold (default: {DEFAULT_COMPLEXITY_THRESHOLD})",
    )
    parser.add_argument(
        "--min-duplicate-lines",
        type=int,
        default=DEFAULT_DUPLICATE_MIN_LINES,
        help=f"Minimum block size for duplicate-code detection (default: {DEFAULT_DUPLICATE_MIN_LINES})",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with a non-zero status if any issues (including warnings) are found",
    )
    return parser


def print_report(result: AnalysisResult) -> None:
    print(f"Static analysis report: {result.filename}")
    print("-" * 60)

    if result.metrics:
        print("Metrics:")
        for key, value in result.metrics.items():
            if isinstance(value, float):
                print(f"  {key}: {value:.2f}")
            else:
                print(f"  {key}: {value}")
        print()

    if not result.issues:
        print("No issues found.")
        return

    categories = sorted({issue.category for issue in result.issues})
    for category in categories:
        cat_issues = result.issues_by_category(category)
        print(f"[{category}] ({len(cat_issues)})")
        for issue in sorted(cat_issues, key=lambda i: i.line):
            print(f"  line {issue.line} [{issue.severity.value}] {issue.message}")
        print()


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        result = analyze_file(
            args.path,
            complexity_threshold=args.complexity_threshold,
            duplicate_min_lines=args.min_duplicate_lines,
        )
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2

    print_report(result)

    if result.has_errors():
        return 1
    if args.strict and result.issues:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
