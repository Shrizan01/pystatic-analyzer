"""
Tests for analyzer.naming — PEP 8 naming convention checks for functions,
classes, and variables.
"""
import pytest

from analyzer.naming import check_naming
from analyzer.core import Severity


class TestFunctionNaming:
    def test_snake_case_function_name_is_fine(self):
        source = "def do_thing():\n    pass\n"
        issues = check_naming(source)
        assert issues == []

    def test_camel_case_function_name_flagged(self):
        source = "def doThing():\n    pass\n"
        issues = check_naming(source)
        assert len(issues) == 1
        assert issues[0].category == "naming"
        assert "doThing" in issues[0].message

    def test_pascal_case_function_name_flagged(self):
        source = "def DoThing():\n    pass\n"
        issues = check_naming(source)
        assert len(issues) == 1

    def test_dunder_methods_are_exempt(self):
        # __init__, __str__, etc. are mandated by Python's data model,
        # not something the developer chose — shouldn't be flagged.
        source = "class Foo:\n    def __init__(self):\n        pass\n"
        issues = check_naming(source)
        assert issues == []


class TestClassNaming:
    def test_pascal_case_class_name_is_fine(self):
        source = "class MyClass:\n    pass\n"
        issues = check_naming(source)
        assert issues == []

    def test_snake_case_class_name_flagged(self):
        source = "class my_class:\n    pass\n"
        issues = check_naming(source)
        assert len(issues) == 1
        assert "my_class" in issues[0].message

    def test_single_lowercase_letter_class_name_flagged(self):
        source = "class c:\n    pass\n"
        issues = check_naming(source)
        assert len(issues) == 1


class TestVariableNaming:
    def test_snake_case_variable_is_fine(self):
        source = "total_count = 1\n"
        issues = check_naming(source)
        assert issues == []

    def test_camel_case_variable_flagged(self):
        source = "totalCount = 1\n"
        issues = check_naming(source)
        assert len(issues) == 1
        assert "totalCount" in issues[0].message

    def test_module_level_constant_all_caps_is_exempt(self):
        # ALL_CAPS is the conventional way to denote a constant and
        # should not be flagged as a variable naming violation.
        source = "MAX_RETRIES = 5\n"
        issues = check_naming(source)
        assert issues == []


class TestNamingBoundary:
    def test_empty_source_returns_no_issues(self):
        assert check_naming("") == []

    def test_source_with_only_comments_returns_no_issues(self):
        assert check_naming("# just a comment\n") == []

    def test_single_character_snake_case_name_is_fine(self):
        # 'x' is minimal but valid snake_case.
        source = "x = 1\n"
        assert check_naming(source) == []


class TestNamingInvalid:
    def test_non_string_raises_type_error(self):
        with pytest.raises(TypeError):
            check_naming(None)

    def test_syntax_error_raises(self):
        with pytest.raises(SyntaxError):
            check_naming("def foo(:\n    pass\n")

    def test_all_issues_have_warning_severity(self):
        source = "def doThing():\n    pass\n"
        issues = check_naming(source)
        assert all(i.severity == Severity.WARNING for i in issues)
