"""
Tests for analyzer.cli — the command-line entry point.
"""
import pytest

from analyzer.cli import main


CLEAN_SOURCE = "def add(a, b):\n    return a + b\n"
MESSY_SOURCE = "def doThing():\n    unused_local = 42\n    return 1\n"
BROKEN_SOURCE = "def foo(:\n    pass\n"


@pytest.fixture
def clean_file(tmp_path):
    p = tmp_path / "clean.py"
    p.write_text(CLEAN_SOURCE)
    return str(p)


@pytest.fixture
def messy_file(tmp_path):
    p = tmp_path / "messy.py"
    p.write_text(MESSY_SOURCE)
    return str(p)


@pytest.fixture
def broken_file(tmp_path):
    p = tmp_path / "broken.py"
    p.write_text(BROKEN_SOURCE)
    return str(p)


class TestCliNormal:
    def test_clean_file_exits_zero(self, clean_file, capsys):
        exit_code = main([clean_file])
        assert exit_code == 0

    def test_clean_file_prints_no_issues_found(self, clean_file, capsys):
        main([clean_file])
        captured = capsys.readouterr()
        assert "No issues found" in captured.out

    def test_messy_file_prints_issues_and_exits_zero_by_default(self, messy_file, capsys):
        # Warnings alone (no ERROR-severity issues) don't fail the run
        # unless --strict is passed.
        exit_code = main([messy_file])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert "naming" in captured.out
        assert "unused_variable" in captured.out


class TestCliStrictMode:
    def test_messy_file_with_strict_flag_exits_nonzero(self, messy_file):
        exit_code = main([messy_file, "--strict"])
        assert exit_code == 1


class TestCliBoundary:
    def test_broken_file_exits_nonzero(self, broken_file, capsys):
        exit_code = main([broken_file])
        captured = capsys.readouterr()
        assert exit_code == 1
        assert "syntax_error" in captured.out

    def test_custom_complexity_threshold_is_applied(self, tmp_path, capsys):
        source = "def foo(x):\n    if x:\n        return 1\n    return 0\n"  # complexity 2
        p = tmp_path / "f.py"
        p.write_text(source)
        exit_code = main([str(p), "--complexity-threshold", "1", "--strict"])
        captured = capsys.readouterr()
        assert exit_code == 1
        assert "complexity" in captured.out


class TestCliInvalid:
    def test_missing_file_exits_with_error_code(self, capsys):
        exit_code = main(["/nonexistent/path/nope.py"])
        captured = capsys.readouterr()
        assert exit_code == 2
        assert "Error" in captured.err

    def test_no_arguments_exits_nonzero(self):
        with pytest.raises(SystemExit):
            main([])

    def test_non_py_file_exits_with_error_code(self, tmp_path, capsys):
        p = tmp_path / "notes.txt"
        p.write_text("hello")
        exit_code = main([str(p)])
        captured = capsys.readouterr()
        assert exit_code == 2
        assert "Error" in captured.err

    def test_invalid_utf8_file_exits_with_error_code_not_crash(self, tmp_path, capsys):
        p = tmp_path / "bad_encoding.py"
        p.write_bytes(b"x = 1\n\xff\xfe invalid bytes\n")
        exit_code = main([str(p)])
        captured = capsys.readouterr()
        assert exit_code == 2
        assert "Error" in captured.err
