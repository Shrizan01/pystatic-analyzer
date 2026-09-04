"""
Tests for the core data model: Issue, Severity, AnalysisResult.

These are written before core.py exists (test-first). They pin down the
contract every analyzer module (metrics, complexity, naming, unused_vars,
duplicate_code) is expected to use when reporting findings, so getting this
right first keeps every later module consistent.
"""
import pytest

from analyzer.core import Issue, Severity, AnalysisResult


class TestSeverity:
    def test_severity_has_expected_levels(self):
        assert Severity.INFO.value == "info"
        assert Severity.WARNING.value == "warning"
        assert Severity.ERROR.value == "error"


class TestIssue:
    def test_issue_stores_required_fields(self):
        issue = Issue(
            category="naming",
            message="Function 'DoThing' does not follow snake_case",
            line=12,
            severity=Severity.WARNING,
        )
        assert issue.category == "naming"
        assert issue.line == 12
        assert issue.severity == Severity.WARNING
        assert "DoThing" in issue.message

    def test_issue_line_must_be_positive(self):
        # Boundary / invalid input: line numbers are 1-indexed in source
        # files, so 0 or negative line numbers are invalid.
        with pytest.raises(ValueError):
            Issue(category="naming", message="bad", line=0, severity=Severity.INFO)

    def test_issue_line_rejects_negative(self):
        with pytest.raises(ValueError):
            Issue(category="naming", message="bad", line=-5, severity=Severity.INFO)

    def test_issue_category_cannot_be_empty(self):
        # Invalid input: an issue with no category can't be grouped/reported.
        with pytest.raises(ValueError):
            Issue(category="", message="bad", line=1, severity=Severity.INFO)

    def test_issue_is_immutable(self):
        # Findings shouldn't be mutated after creation once collected into
        # a report — guards against accidental cross-module tampering.
        issue = Issue(category="naming", message="bad", line=1, severity=Severity.INFO)
        with pytest.raises(AttributeError):
            issue.line = 99


class TestAnalysisResult:
    def test_empty_result_has_no_issues(self):
        result = AnalysisResult(filename="empty.py")
        assert result.issues == []
        assert result.metrics == {}

    def test_add_issue_appends_to_list(self):
        result = AnalysisResult(filename="sample.py")
        issue = Issue(category="naming", message="bad", line=1, severity=Severity.INFO)
        result.add_issue(issue)
        assert result.issues == [issue]

    def test_issues_by_category_filters_correctly(self):
        result = AnalysisResult(filename="sample.py")
        result.add_issue(Issue(category="naming", message="a", line=1, severity=Severity.INFO))
        result.add_issue(Issue(category="complexity", message="b", line=2, severity=Severity.WARNING))
        result.add_issue(Issue(category="naming", message="c", line=3, severity=Severity.INFO))

        naming_issues = result.issues_by_category("naming")
        assert len(naming_issues) == 2
        assert all(i.category == "naming" for i in naming_issues)

    def test_issues_by_category_unknown_category_returns_empty(self):
        # Boundary: querying a category with zero matches should not error.
        result = AnalysisResult(filename="sample.py")
        assert result.issues_by_category("nonexistent") == []

    def test_has_errors_reflects_severity(self):
        result = AnalysisResult(filename="sample.py")
        assert result.has_errors() is False
        result.add_issue(Issue(category="x", message="y", line=1, severity=Severity.ERROR))
        assert result.has_errors() is True
