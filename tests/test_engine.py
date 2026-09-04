"""
Tests for analyzer.engine — the orchestrator that runs every check
(metrics, complexity, naming, unused_vars, duplicate_code) against a
source file and aggregates the results into a single AnalysisResult.
"""
import pytest

from analyzer.engine import analyze_source, analyze_file
from analyzer.core import Severity


CLEAN_SOURCE = '''"""A clean, well-formed module."""


def add(a, b):
    """Add two numbers."""
    return a + b


class Calculator:
    """A tiny calculator."""

    def multiply(self, a, b):
        return a * b
'''

MESSY_SOURCE = (
    "def doThing():\n"
    "    unused_local = 42\n"
    "    return 1\n"
)


class TestAnalyzeSourceNormal:
    def test_clean_source_has_no_issues(self):
        result = analyze_source(CLEAN_SOURCE, filename="clean.py")
        assert result.issues == []
        assert result.filename == "clean.py"

    def test_metrics_are_populated(self):
        result = analyze_source(CLEAN_SOURCE, filename="clean.py")
        assert result.metrics["function_count"] == 2
        assert result.metrics["class_count"] == 1
        assert "average_complexity" in result.metrics

    def test_messy_source_reports_issues_from_multiple_categories(self):
        result = analyze_source(MESSY_SOURCE, filename="messy.py")
        categories = {issue.category for issue in result.issues}
        assert "naming" in categories          # doThing
        assert "unused_variable" in categories  # unused_local

    def test_average_complexity_matches_manual_calculation(self):
        source = (
            "def a():\n    return 1\n\n"          # complexity 1
            "def b(x):\n    if x:\n        return 1\n    return 0\n"  # complexity 2
        )
        result = analyze_source(source, filename="f.py")
        assert result.metrics["average_complexity"] == pytest.approx(1.5)


class TestAnalyzeSourceBoundary:
    def test_empty_source_has_no_issues_and_zeroed_metrics(self):
        result = analyze_source("", filename="empty.py")
        assert result.issues == []
        assert result.metrics["function_count"] == 0
        assert result.metrics["average_complexity"] == 0

    def test_source_with_no_functions_has_zero_average_complexity(self):
        result = analyze_source("x = 1\ny = 2\n", filename="f.py")
        assert result.metrics["average_complexity"] == 0


class TestAnalyzeSourceInvalid:
    def test_non_string_source_raises_type_error(self):
        with pytest.raises(TypeError):
            analyze_source(None, filename="f.py")

    def test_syntax_error_is_reported_as_an_issue_not_raised(self):
        # A CLI user pointing the analyzer at a broken file is a normal
        # use case, not a programming error — the orchestrator should
        # report it gracefully rather than crash.
        result = analyze_source("def foo(:\n    pass\n", filename="broken.py")
        assert result.has_errors()
        syntax_issues = result.issues_by_category("syntax_error")
        assert len(syntax_issues) == 1
        assert syntax_issues[0].severity == Severity.ERROR

    def test_syntax_error_result_has_empty_metrics(self):
        result = analyze_source("def foo(:\n    pass\n", filename="broken.py")
        assert result.metrics == {}


class TestAnalyzeSourceNeverExecutesAnalysedCode:
    def test_analyzing_code_with_side_effects_does_not_run_them(self, capsys, tmp_path):
        # TC-GEN-07 / FR11: static analysis only, via ast — the code being
        # analysed must never actually run. Prove it directly rather than
        # relying on "we only ever call ast.parse" as an inference: give
        # the analyser source that would print and write a file if it were
        # ever executed, and confirm neither happens.
        marker_file = tmp_path / "should_not_exist.txt"
        source = (
            "print('THIS SHOULD NEVER PRINT')\n"
            f"open(r'{marker_file}', 'w').write('ran')\n"
        )
        analyze_source(source, filename="side_effect.py")
        captured = capsys.readouterr()
        assert "THIS SHOULD NEVER PRINT" not in captured.out
        assert not marker_file.exists()


class TestAnalyzeFile:
    def test_analyze_file_reads_and_analyzes(self, tmp_path):
        file_path = tmp_path / "sample.py"
        file_path.write_text(CLEAN_SOURCE)
        result = analyze_file(str(file_path))
        assert result.issues == []
        assert result.filename == str(file_path)

    def test_analyze_file_missing_file_raises_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            analyze_file("/nonexistent/path/does_not_exist.py")

    def test_analyze_file_rejects_non_py_extension(self, tmp_path):
        file_path = tmp_path / "notes.txt"
        file_path.write_text("hello")
        with pytest.raises(ValueError):
            analyze_file(str(file_path))

    def test_analyze_file_rejects_invalid_utf8_gracefully(self, tmp_path):
        # Section 1.8: a file with bytes that aren't valid UTF-8 should
        # raise a descriptive ValueError (caught and reported by the CLI),
        # not crash with an unhandled UnicodeDecodeError.
        file_path = tmp_path / "bad_encoding.py"
        file_path.write_bytes(b"x = 1\n\xff\xfe invalid bytes\n")
        with pytest.raises(ValueError):
            analyze_file(str(file_path))
