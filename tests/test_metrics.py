"""
Tests for analyzer.metrics — basic code metrics (line counts, function and
class counts). Written before metrics.py exists.
"""
import pytest

from analyzer.metrics import compute_metrics


NORMAL_SOURCE = '''"""Module docstring."""
import os

# a comment
def foo(x):
    return x + 1


class Bar:
    def method(self):
        pass
'''


class TestComputeMetricsNormal:
    def test_total_lines_counts_every_line(self):
        m = compute_metrics(NORMAL_SOURCE)
        assert m["total_lines"] == NORMAL_SOURCE.count("\n")

    def test_counts_functions_and_classes(self):
        m = compute_metrics(NORMAL_SOURCE)
        assert m["function_count"] == 2  # foo + Bar.method
        assert m["class_count"] == 1

    def test_counts_blank_lines(self):
        # NORMAL_SOURCE actually has 3 blank lines (after `import os`, and
        # two between `foo` and `class Bar`) — the original assertion of 2
        # was a hand-counting error, caught on the first red run.
        m = compute_metrics(NORMAL_SOURCE)
        assert m["blank_lines"] == 3

    def test_counts_comment_lines(self):
        m = compute_metrics(NORMAL_SOURCE)
        assert m["comment_lines"] == 1

    def test_average_function_length_known_value(self):
        # TC-FR6-01: foo (def + return, 2 lines) and Bar.method
        # (def + pass, 2 lines) -> average 2.0.
        m = compute_metrics(NORMAL_SOURCE)
        assert m["average_function_length"] == pytest.approx(2.0)


class TestComputeMetricsBoundary:
    def test_empty_source_returns_zeroed_metrics(self):
        m = compute_metrics("")
        assert m["total_lines"] == 0
        assert m["function_count"] == 0
        assert m["class_count"] == 0

    def test_empty_source_average_function_length_is_zero(self):
        # TC-FR6-02: no functions present -> average is 0, no
        # division-by-zero error.
        m = compute_metrics("")
        assert m["average_function_length"] == 0

    def test_single_function_average_equals_its_own_length(self):
        # TC-FR6-03: exactly one function -> average equals that
        # function's exact line count.
        source = "def foo():\n    a = 1\n    b = 2\n    return a + b\n"
        m = compute_metrics(source)
        assert m["function_count"] == 1
        assert m["average_function_length"] == pytest.approx(4.0)

    def test_whitespace_only_source(self):
        m = compute_metrics("\n\n\n")
        assert m["function_count"] == 0
        assert m["blank_lines"] == 3

    def test_single_line_no_trailing_newline(self):
        m = compute_metrics("x = 1")
        assert m["total_lines"] == 1
        assert m["code_lines"] == 1


class TestComputeMetricsRegression:
    def test_hash_inside_docstring_is_not_counted_as_comment(self):
        # Regression test: v1 used naive `line.strip().startswith('#')`
        # matching, which misclassified '#' characters that appear inside
        # a multi-line string/docstring as real comments, and blank-looking
        # lines inside that string as blank lines. Fixed in v2 by using
        # `tokenize` to distinguish real COMMENT tokens from STRING tokens.
        source = (
            "def foo():\n"
            "    '''\n"
            "    # not a real comment, this is inside a docstring\n"
            "\n"
            "    '''\n"
            "    return 1\n"
        )
        m = compute_metrics(source)
        assert m["comment_lines"] == 0
        assert m["blank_lines"] == 0

    def test_real_comment_outside_string_is_still_counted(self):
        source = "# a real comment\nx = 1\n"
        m = compute_metrics(source)
        assert m["comment_lines"] == 1


class TestComputeMetricsInvalid:
    def test_none_source_raises_type_error(self):
        with pytest.raises(TypeError):
            compute_metrics(None)

    def test_non_string_source_raises_type_error(self):
        with pytest.raises(TypeError):
            compute_metrics(12345)

    def test_syntax_error_source_raises_syntax_error(self):
        # Invalid Python: metrics still counts lines from raw text, but
        # function/class counts require a parseable AST, so this must
        # surface as a SyntaxError rather than silently returning zeros.
        with pytest.raises(SyntaxError):
            compute_metrics("def foo(:\n    pass\n")
