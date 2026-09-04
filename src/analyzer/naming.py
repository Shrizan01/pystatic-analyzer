"""
analyzer.naming — PEP 8 naming convention checks for functions, classes,
and simple variable assignments.

Rules applied:
  - function/method names: snake_case          (dunder methods exempt)
  - class names:            PascalCase (CapWords)
  - variable names:         snake_case          (ALL_CAPS constants exempt)
"""
from __future__ import annotations

import ast
import re

from analyzer.core import Issue, Severity

_SNAKE_CASE_RE = re.compile(r"^_{0,2}[a-z][a-z0-9_]*$|^_+$")
_PASCAL_CASE_RE = re.compile(r"^[A-Z][a-zA-Z0-9]*$")
_ALL_CAPS_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")
_DUNDER_RE = re.compile(r"^__[a-zA-Z0-9_]+__$")


def check_naming(source: str) -> list[Issue]:
    if not isinstance(source, str):
        raise TypeError(f"source must be a str, got {type(source).__name__}")

    tree = ast.parse(source)  # raises SyntaxError on invalid input

    issues: list[Issue] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            issues.extend(_check_function_name(node))
        elif isinstance(node, ast.ClassDef):
            issues.extend(_check_class_name(node))
        elif isinstance(node, ast.Assign):
            issues.extend(_check_assignment_names(node))

    return issues


def _check_function_name(node) -> list[Issue]:
    if _DUNDER_RE.match(node.name):
        return []
    if _SNAKE_CASE_RE.match(node.name):
        return []
    return [
        Issue(
            category="naming",
            message=f"Function '{node.name}' should use snake_case naming.",
            line=node.lineno,
            severity=Severity.WARNING,
        )
    ]


def _check_class_name(node: ast.ClassDef) -> list[Issue]:
    if _PASCAL_CASE_RE.match(node.name):
        return []
    return [
        Issue(
            category="naming",
            message=f"Class '{node.name}' should use PascalCase naming.",
            line=node.lineno,
            severity=Severity.WARNING,
        )
    ]


def _check_assignment_names(node: ast.Assign) -> list[Issue]:
    issues: list[Issue] = []
    for target in node.targets:
        if not isinstance(target, ast.Name):
            continue  # skip tuple unpacking, attribute/subscript targets
        name = target.id
        if _SNAKE_CASE_RE.match(name) or _ALL_CAPS_RE.match(name):
            continue
        issues.append(
            Issue(
                category="naming",
                message=f"Variable '{name}' should use snake_case naming.",
                line=node.lineno,
                severity=Severity.WARNING,
            )
        )
    return issues
