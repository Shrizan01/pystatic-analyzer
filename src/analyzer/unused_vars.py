"""
analyzer.unused_vars — detects local variables assigned within a function
but never subsequently read.

Scope / design decisions:
  - Only function-local variables are checked (module-level globals are
    out of scope — they may be consumed elsewhere, e.g. on import).
  - Only the bare `_` is treated as intentionally unused by convention and
    exempt (per project spec Section 1.4/TC-FR3-04) — other
    underscore-prefixed names (e.g. `_temp`) are checked normally.
  - Usage is searched across the function's entire subtree, including
    nested function bodies, so variables captured by a closure are not
    flagged as unused.
  - Augmented assignment (`x += 1`) counts as both a read and a write of
    `x`, so it satisfies "used".
"""
from __future__ import annotations

import ast

from analyzer.core import Issue, Severity


def check_unused_variables(source: str) -> list[Issue]:
    if not isinstance(source, str):
        raise TypeError(f"source must be a str, got {type(source).__name__}")

    tree = ast.parse(source)  # raises SyntaxError on invalid input

    issues: list[Issue] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            issues.extend(_check_function(node))
    return issues


def _check_function(func: ast.FunctionDef) -> list[Issue]:
    assigned: dict[str, int] = {}  # name -> line of last plain assignment
    used: set[str] = set()

    # Assignment targets at this function's own top-level statements only
    # (not inside nested function defs — those are checked separately).
    for stmt in _walk_body_only(func):
        if isinstance(stmt, ast.Assign):
            for target in stmt.targets:
                for name_node in _simple_name_targets(target):
                    if name_node.id != "_":
                        assigned[name_node.id] = stmt.lineno
        elif isinstance(stmt, ast.AugAssign):
            if isinstance(stmt.target, ast.Name):
                used.add(stmt.target.id)  # read-modify-write counts as use

    # Usage is searched across the WHOLE function (including nested
    # closures), so captured variables aren't false-flagged.
    for node in ast.walk(func):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            used.add(node.id)

    issues: list[Issue] = []
    for name, line in assigned.items():
        if name not in used:
            issues.append(
                Issue(
                    category="unused_variable",
                    message=f"Local variable '{name}' is assigned but never used.",
                    line=line,
                    severity=Severity.WARNING,
                )
            )
    return issues


def _simple_name_targets(target: ast.expr):
    """Yield ast.Name nodes from an assignment target, handling simple
    names directly and tuple/list unpacking targets recursively."""
    if isinstance(target, ast.Name):
        yield target
    elif isinstance(target, (ast.Tuple, ast.List)):
        for elt in target.elts:
            yield from _simple_name_targets(elt)
    # ast.Attribute / ast.Subscript targets (obj.attr = .., d[k] = ..)
    # are intentionally not yielded — they mutate something outside this
    # local scope, so "unused" doesn't apply.


def _walk_body_only(func: ast.FunctionDef):
    """Yield every statement in func's body, without descending into
    nested function/lambda definitions (those are separate scopes,
    checked independently by the outer ast.walk in check_unused_variables)."""
    stack = list(func.body)
    while stack:
        node = stack.pop()
        yield node
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                continue
            stack.append(child)
