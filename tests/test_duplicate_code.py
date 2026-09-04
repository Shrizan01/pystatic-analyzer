"""
Tests for analyzer.duplicate_code — detects repeated blocks of source
lines (a simple, line-based duplicate-code detector).
"""
import pytest

from analyzer.duplicate_code import find_duplicate_code
from analyzer.core import Severity


DUPLICATED_BLOCK = (
    "    total = 0\n"
    "    total += 1\n"
    "    total += 2\n"
    "    print(total)\n"
)


class TestFindDuplicateCodeNormal:
    def test_no_duplication_returns_no_issues(self):
        source = "def a():\n    return 1\n\ndef b():\n    return 2\n"
        issues = find_duplicate_code(source, min_lines=4)
        assert issues == []

    def test_exact_duplicate_block_is_flagged(self):
        source = (
            "def foo():\n" + DUPLICATED_BLOCK +
            "\n"
            "def bar():\n" + DUPLICATED_BLOCK
        )
        issues = find_duplicate_code(source, min_lines=4)
        assert len(issues) == 1
        assert issues[0].category == "duplicate_code"
        assert issues[0].severity == Severity.WARNING

    def test_duplicate_ignoring_leading_whitespace(self):
        # Same statements, different indentation (e.g. copy-pasted into a
        # deeper nesting level) should still be detected as duplicate.
        block_a = "    x = 1\n    y = 2\n    z = 3\n    print(x, y, z)\n"
        block_b = "        x = 1\n        y = 2\n        z = 3\n        print(x, y, z)\n"
        source = "def foo():\n" + block_a + "\nif True:\n    if True:\n" + block_b
        issues = find_duplicate_code(source, min_lines=4)
        assert len(issues) == 1


class TestFindDuplicateCodeBoundary:
    def test_default_threshold_flags_three_line_duplicate(self):
        # TC-FR4-03: at the spec's 3-statement minimum, using the
        # function's default (no min_lines passed), a 3-line duplicate
        # block should be flagged.
        block = "    x = 1\n    y = 2\n    z = 3\n"
        source = "def foo():\n" + block + "\ndef bar():\n" + block
        issues = find_duplicate_code(source)
        assert len(issues) == 1

    def test_default_threshold_does_not_flag_two_line_duplicate(self):
        # TC-FR4-04: one line below the spec's minimum, using the
        # function's default, should NOT be flagged.
        block = "    x = 1\n    y = 2\n"
        source = "def foo():\n" + block + "\ndef bar():\n" + block
        issues = find_duplicate_code(source)
        assert issues == []

    def test_block_shorter_than_min_lines_not_flagged(self):
        # Same 2-line snippet repeated, but min_lines=4 means a 2-line
        # match shouldn't trigger a report.
        source = "def a():\n    x = 1\n    y = 2\n\ndef b():\n    x = 1\n    y = 2\n"
        issues = find_duplicate_code(source, min_lines=4)
        assert issues == []

    def test_longer_duplicate_region_flagged_in_min_lines_chunks(self):
        # An 8-line duplicated region with min_lines=4 is reported as two
        # non-overlapping 4-line chunks rather than every overlapping
        # window — avoids flooding the report with overlapping hits for
        # one underlying duplication.
        block = (
            "    a = 1\n    b = 2\n    c = 3\n    d = 4\n"
            "    e = 5\n    f = 6\n    g = 7\n    h = 8\n"
        )
        source = "def foo():\n" + block + "\ndef bar():\n" + block
        issues = find_duplicate_code(source, min_lines=4)
        assert len(issues) == 2

    def test_empty_source_returns_no_issues(self):
        assert find_duplicate_code("", min_lines=4) == []

    def test_source_shorter_than_min_lines_returns_no_issues(self):
        source = "x = 1\ny = 2\n"
        assert find_duplicate_code(source, min_lines=4) == []

    def test_blank_lines_do_not_count_toward_a_block(self):
        # Blank lines are skipped when building comparison windows, so a
        # block interrupted only by blank lines still compares on content.
        block_a = "x = 1\n\ny = 2\n\nz = 3\n\nw = 4\n"
        block_b = "x = 1\ny = 2\nz = 3\nw = 4\n"
        source = block_a + "\n" + block_b
        issues = find_duplicate_code(source, min_lines=4)
        assert len(issues) == 1


class TestFindDuplicateCodeInvalid:
    def test_non_string_raises_type_error(self):
        with pytest.raises(TypeError):
            find_duplicate_code(None, min_lines=4)

    def test_syntax_error_raises(self):
        with pytest.raises(SyntaxError):
            find_duplicate_code("def foo(:\n    pass\n", min_lines=4)

    def test_invalid_min_lines_raises_value_error(self):
        with pytest.raises(ValueError):
            find_duplicate_code("x = 1\n", min_lines=0)

    def test_min_lines_of_one_raises_value_error(self):
        # A 1-line "duplicate block" would flag any two identical lines
        # anywhere in the file (e.g. two 'return None' statements),
        # which is not a meaningful signal — require at least 2.
        with pytest.raises(ValueError):
            find_duplicate_code("x = 1\n", min_lines=1)
