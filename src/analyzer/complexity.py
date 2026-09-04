"""
analyzer.complexity — cyclomatic complexity per function/method.

Complexity starts at 1 (one linear path through the function) and each
decision point that creates an additional path adds 1: `if`/`elif`,
`for`, `while`, `except` clauses, boolean `and`/`or` operators,
comprehension `if` clauses, and ternary (`IfExp`) expressions.
"""
from __future__ import annotations

import ast

from analyzer.core import Issue, Severity


class _ComplexityVisitor(ast.NodeVisitor):
    """Walks a single function body and counts decision points."""

    def __init__(self) -> None:
        self.complexity = 1

    def visit_If(self, node: ast.If) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_While(self, node: ast.While) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        # `a and b and c` has 2 operators -> 2 extra decision points.
        self.complexity += len(node.values) - 1
        self.generic_visit(node)

    def visit_IfExp(self, node: ast.IfExp) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_comprehension(self, node: ast.comprehension) -> None:
        self.complexity += len(node.ifs)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        # Don't descend into nested function definitions — they're
        # measured separately by the outer walk in calculate_complexities.
        pass

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        pass


def _qualified_names(tree: ast.AST) -> list[tuple[str, ast.FunctionDef]]:
    """Return (qualified_name, node) pairs for every function/method,
    including nested and class-scoped ones, walking the whole module."""
    results: list[tuple[str, ast.FunctionDef]] = []

    def walk(node: ast.AST, prefix: str) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                qualified = f"{prefix}{child.name}"
                results.append((qualified, child))
                walk(child, qualified + ".")
            elif isinstance(child, ast.ClassDef):
                walk(child, f"{prefix}{child.name}.")
            else:
                walk(child, prefix)

    walk(tree, "")
    return results


def calculate_complexities(source: str) -> dict[str, int]:
    if not isinstance(source, str):
        raise TypeError(f"source must be a str, got {type(source).__name__}")

    tree = ast.parse(source)  # raises SyntaxError on invalid input

    result: dict[str, int] = {}
    for name, node in _qualified_names(tree):
        visitor = _ComplexityVisitor()
        for statement in node.body:
            visitor.visit(statement)
        result[name] = visitor.complexity
    return result


def check_complexity(source: str, threshold: int = 10) -> list[Issue]:
    if threshold < 1:
        raise ValueError(f"threshold must be a positive integer, got {threshold}")

    complexities = calculate_complexities(source)
    tree = ast.parse(source)
    line_by_name = {name: node.lineno for name, node in _qualified_names(tree)}

    issues: list[Issue] = []
    for name, value in complexities.items():
        if value > threshold:
            issues.append(
                Issue(
                    category="complexity",
                    message=(
                        f"Function '{name}' has cyclomatic complexity {value}, "
                        f"which exceeds the threshold of {threshold}."
                    ),
                    line=line_by_name[name],
                    severity=Severity.WARNING,
                )
            )
    return issues
