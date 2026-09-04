"""
analyzer.metrics — basic code metrics for a Python source file:
total/blank/comment/code line counts, function count, class count.

v2: comment and blank-line detection is token-based (via `tokenize`)
rather than naive string matching. The naive version (v1) classified any
line whose stripped text started with '#' as a comment and any
whitespace-only line as blank — which misclassifies lines that merely
*look* like comments or blank lines but are actually inside a multi-line
string/docstring, e.g.:

    def foo():
        '''
        # not a real comment, this is inside a docstring
        '''

`tokenize` distinguishes real COMMENT tokens from '#' characters that
appear inside STRING tokens, so it's used here instead.
"""
from __future__ import annotations

import ast
import io
import tokenize


def compute_metrics(source: str) -> dict:
    if not isinstance(source, str):
        raise TypeError(f"source must be a str, got {type(source).__name__}")

    tree = ast.parse(source)  # raises SyntaxError on invalid input

    if source == "":
        lines: list[str] = []
    else:
        lines = source.split("\n")
        if source.endswith("\n"):
            lines = lines[:-1]

    comment_line_numbers, string_line_numbers = _classify_lines_by_token(source)

    blank_lines = 0
    comment_lines = 0
    for i, line in enumerate(lines, start=1):
        if i in comment_line_numbers:
            comment_lines += 1
        elif line.strip() == "" and i not in string_line_numbers:
            blank_lines += 1

    code_lines = len(lines) - blank_lines - comment_lines

    function_count = sum(1 for node in ast.walk(tree) if isinstance(node, ast.FunctionDef))
    class_count = sum(1 for node in ast.walk(tree) if isinstance(node, ast.ClassDef))

    # FR6 requires average function length (not just average complexity,
    # which engine.py separately computes). Length is measured in physical
    # lines per function (end_lineno - lineno + 1), averaged across every
    # top-level and nested function definition found in the module.
    function_lengths = [
        node.end_lineno - node.lineno + 1
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.end_lineno is not None
    ]
    average_function_length = (
        sum(function_lengths) / len(function_lengths) if function_lengths else 0
    )

    return {
        "total_lines": len(lines),
        "blank_lines": blank_lines,
        "comment_lines": comment_lines,
        "code_lines": code_lines,
        "function_count": function_count,
        "class_count": class_count,
        "average_function_length": average_function_length,
    }


def _classify_lines_by_token(source: str) -> tuple[set[int], set[int]]:
    """Return (comment_line_numbers, string_span_line_numbers) via tokenize."""
    comment_lines: set[int] = set()
    string_lines: set[int] = set()

    try:
        tokens = tokenize.generate_tokens(io.StringIO(source).readline)
        for tok in tokens:
            if tok.type == tokenize.COMMENT:
                comment_lines.add(tok.start[0])
            elif tok.type == tokenize.STRING:
                start_line, end_line = tok.start[0], tok.end[0]
                for ln in range(start_line, end_line + 1):
                    string_lines.add(ln)
    except tokenize.TokenizeError:
        # Fall back to no reclassification — ast.parse() above already
        # validated the source, so this path is only hit on edge cases
        # tokenize is stricter about than the parser.
        pass

    return comment_lines, string_lines
