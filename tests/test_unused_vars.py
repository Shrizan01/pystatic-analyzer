"""
Tests for analyzer.unused_vars — detects local variables that are
assigned within a function but never subsequently read.
"""
import pytest

from analyzer.unused_vars import check_unused_variables
from analyzer.core import Severity


class TestUnusedVariablesNormal:
    def test_used_variable_produces_no_issue(self):
        source = "def foo():\n    x = 1\n    return x\n"
        issues = check_unused_variables(source)
        assert issues == []

    def test_unused_variable_flagged(self):
        source = "def foo():\n    x = 1\n    return 2\n"
        issues = check_unused_variables(source)
        assert len(issues) == 1
        assert issues[0].category == "unused_variable"
        assert "x" in issues[0].message

    def test_multiple_unused_variables_all_flagged(self):
        source = "def foo():\n    x = 1\n    y = 2\n    return 3\n"
        issues = check_unused_variables(source)
        assert len(issues) == 2
        names = {i.message for i in issues}
        assert any("x" in m for m in names)
        assert any("y" in m for m in names)

    def test_reassignment_before_use_only_flags_if_never_used(self):
        # x is reassigned, but the final value IS used -> not unused.
        source = "def foo():\n    x = 1\n    x = 2\n    return x\n"
        issues = check_unused_variables(source)
        assert issues == []

    def test_augmented_assignment_counts_as_use(self):
        # x += 1 both reads and writes x, so an initial assignment
        # followed only by augmented assignment is *not* "unused" —
        # the value is being read.
        source = "def foo():\n    x = 1\n    x += 1\n"
        issues = check_unused_variables(source)
        assert issues == []


class TestUnusedVariablesBoundary:
    def test_underscore_prefixed_variable_is_not_exempt(self):
        # Per project spec (TC-FR3-04), only the bare `_` is exempt —
        # other underscore-prefixed names are checked normally.
        source = "def foo():\n    _unused = compute()\n    return 1\n"
        issues = check_unused_variables(source)
        assert len(issues) == 1
        assert "_unused" in issues[0].message

    def test_bare_underscore_is_exempt(self):
        source = "def foo():\n    _ = compute()\n    return 1\n"
        issues = check_unused_variables(source)
        assert issues == []

    def test_module_level_assignment_is_not_checked(self):
        # This checker targets *local* (function-scoped) variables only;
        # module-level globals have different usage patterns (may be
        # imported elsewhere) and are out of scope here.
        source = "x = 1\n"
        issues = check_unused_variables(source)
        assert issues == []

    def test_variable_used_inside_nested_closure_is_not_flagged(self):
        source = (
            "def outer():\n"
            "    total = 0\n"
            "    def inner():\n"
            "        return total\n"
            "    return inner\n"
        )
        issues = check_unused_variables(source)
        assert issues == []

    def test_empty_function_body_produces_no_issues(self):
        source = "def foo():\n    pass\n"
        issues = check_unused_variables(source)
        assert issues == []

    def test_empty_source_returns_no_issues(self):
        assert check_unused_variables("") == []


class TestUnusedVariablesInvalid:
    def test_non_string_raises_type_error(self):
        with pytest.raises(TypeError):
            check_unused_variables(None)

    def test_syntax_error_raises(self):
        with pytest.raises(SyntaxError):
            check_unused_variables("def foo(:\n    pass\n")

    def test_issues_have_warning_severity(self):
        source = "def foo():\n    x = 1\n    return 2\n"
        issues = check_unused_variables(source)
        assert all(i.severity == Severity.WARNING for i in issues)
