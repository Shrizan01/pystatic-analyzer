# Python Static Code Analyzer

A command-line static analysis tool for Python source files. Analyses a
given `.py` file and reports:

- Cyclomatic complexity per function
- Unused local variables
- Duplicate code blocks
- Naming convention violations (PEP 8)
- Overall code metrics (LOC, function/class counts, average complexity)

Built as part of PRT582 (Software Testing) using an AI-assisted
Test-Driven Development workflow.

## Usage

```bash
python -m analyzer.cli path/to/file.py
```

## Running tests

```bash
pytest --cov=analyzer --cov-report=term-missing
```
