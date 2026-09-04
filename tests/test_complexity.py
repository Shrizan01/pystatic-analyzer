"""
Tests for analyzer.complexity — cyclomatic complexity per function, and
issue generation for functions exceeding a threshold.
"""
import pytest

from analyzer.complexity import calculate_complexities, check_complexity
from analyzer.core import Severity


class TestCalculateComplexitiesNormal:
    def test_function_with_no_branches_has_complexity_1(self):
        source = "def foo():\n    return 1\n"
        result = calculate_complexities(source)
        assert result["foo"] == 1

    def test_single_if_adds_one(self):
        source = "def foo(x):\n    if x > 0:\n        return 1\n    return 0\n"
        result = calculate_complexities(source)
        assert result["foo"] == 2

    def test_if_elif_else_counts_each_branch(self):
        source = (
            "def foo(x):\n"
            "    if x > 0:\n"
            "        return 1\n"
            "    elif x < 0:\n"
            "        return -1\n"
            "    else:\n"
            "        return 0\n"
        )
        result = calculate_complexities(source)
        # base 1 + if + elif = 3 (else adds no new decision point)
        assert result["foo"] == 3

    def test_loops_and_boolean_operators_add_complexity(self):
        source = (
            "def foo(items):\n"
            "    total = 0\n"
            "    for item in items:\n"
            "        if item > 0 and item < 100:\n"
            "            total += item\n"
            "    return total\n"
        )
        result = calculate_complexities(source)
        # base 1 + for + if + and = 4
        assert result["foo"] == 4

    def test_multiple_functions_reported_independently(self):
        source = (
            "def simple():\n"
            "    return 1\n\n"
            "def branching(x):\n"
            "    if x:\n"
            "        return 1\n"
            "    return 0\n"
        )
        result = calculate_complexities(source)
        assert result["simple"] == 1
        assert result["branching"] == 2

    def test_methods_use_qualified_name(self):
        source = (
            "class Foo:\n"
            "    def bar(self, x):\n"
            "        if x:\n"
            "            return 1\n"
            "        return 0\n"
        )
        result = calculate_complexities(source)
        assert result["Foo.bar"] == 2


    def test_while_loop_adds_one(self):
        source = "def foo(x):\n    while x > 0:\n        x -= 1\n    return x\n"
        result = calculate_complexities(source)
        assert result["foo"] == 2

    def test_except_handler_adds_one_per_except(self):
        source = (
            "def foo():\n"
            "    try:\n"
            "        risky()\n"
            "    except ValueError:\n"
            "        pass\n"
            "    except TypeError:\n"
            "        pass\n"
        )
        result = calculate_complexities(source)
        # base 1 + 2 except handlers = 3
        assert result["foo"] == 3

    def test_ternary_expression_adds_one(self):
        source = "def foo(x):\n    return 1 if x else 0\n"
        result = calculate_complexities(source)
        assert result["foo"] == 2

    def test_comprehension_if_clause_adds_one(self):
        source = "def foo(items):\n    return [i for i in items if i > 0]\n"
        result = calculate_complexities(source)
        # base 1 + comprehension if = 2 (the 'for' in a comprehension is
        # not counted the same way as a statement-level for loop)
        assert result["foo"] == 2

    def test_async_function_and_async_for_are_measured(self):
        source = (
            "async def foo(items):\n"
            "    async for item in items:\n"
            "        pass\n"
        )
        result = calculate_complexities(source)
        assert result["foo"] == 2


class TestCalculateComplexitiesBoundary:
    def test_source_with_no_functions_returns_empty_dict(self):
        result = calculate_complexities("x = 1\ny = 2\n")
        assert result == {}

    def test_empty_source_returns_empty_dict(self):
        assert calculate_complexities("") == {}

    def test_nested_function_is_reported_with_qualified_name(self):
        # Nested functions are reported under a dotted qualified name
        # ("outer.inner") rather than the bare name — this avoids two
        # unrelated nested functions sharing the same short name from
        # colliding in the results dict. Original assertion of a bare
        # "inner" key was wrong; corrected after the first red run.
        source = (
            "def outer():\n"
            "    def inner():\n"
            "        return 1\n"
            "    return inner()\n"
        )
        result = calculate_complexities(source)
        assert "outer" in result
        assert "outer.inner" in result


class TestCalculateComplexitiesInvalid:
    def test_non_string_raises_type_error(self):
        with pytest.raises(TypeError):
            calculate_complexities(None)

    def test_syntax_error_raises(self):
        with pytest.raises(SyntaxError):
            calculate_complexities("def foo(:\n    pass\n")


class TestCheckComplexity:
    def test_function_under_threshold_produces_no_issue(self):
        source = "def foo():\n    return 1\n"
        issues = check_complexity(source, threshold=10)
        assert issues == []

    def test_function_over_threshold_produces_warning_issue(self):
        # Build a function with complexity well above a low threshold.
        lines = ["def foo(x):"]
        for i in range(5):
            lines.append(f"    if x == {i}:")
            lines.append(f"        x += 1")
        source = "\n".join(lines) + "\n    return x\n"
        issues = check_complexity(source, threshold=3)
        assert len(issues) == 1
        assert issues[0].category == "complexity"
        assert issues[0].severity == Severity.WARNING
        assert "foo" in issues[0].message

    def test_threshold_boundary_exact_value_does_not_trigger(self):
        # A function whose complexity == threshold should NOT be flagged;
        # only complexity > threshold should.
        source = "def foo(x):\n    if x:\n        return 1\n    return 0\n"
        # complexity == 2
        issues = check_complexity(source, threshold=2)
        assert issues == []

    def test_threshold_boundary_one_over_triggers(self):
        source = "def foo(x):\n    if x:\n        return 1\n    return 0\n"
        issues = check_complexity(source, threshold=1)
        assert len(issues) == 1

    def test_invalid_threshold_raises_value_error(self):
        with pytest.raises(ValueError):
            check_complexity("def foo():\n    return 1\n", threshold=0)
