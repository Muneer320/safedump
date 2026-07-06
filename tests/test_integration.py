"""Integration tests — real subprocess crashes."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


def _run_crash(fixture_name: str, crash_dir: str) -> tuple[int, str, str]:
    """Run a crash fixture. crash_dir must exist for the lifetime needed.

    The script is written to a temp .py file rather than passed via
    ``-c``, since embedding a Windows path (with backslashes) directly
    in a ``-c`` script string causes Python to misinterpret sequences
    like ``\\U...`` as unicode escapes.
    """
    fixture = FIXTURES / fixture_name
    # Use forward slashes so the substituted path is a valid Python string
    # literal — a raw Windows path (with backslashes) embedded in source
    # can have sequences like \U misread as unicode escapes.
    safe_crash_dir = crash_dir.replace("\\", "/")
    script = fixture.read_text(encoding="utf-8").replace("CRASH_DIR_PLACEHOLDER", safe_crash_dir)

    with tempfile.NamedTemporaryFile(
        suffix=".py", mode="w", delete=False, encoding="utf-8"
    ) as f:
        f.write(script)
        script_path = f.name

    try:
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
        )
    finally:
        os.unlink(script_path)

    return result.returncode, result.stdout, result.stderr


def _find_report(crash_dir: Path) -> Path | None:
    reports = list(crash_dir.glob("*.safedump.json"))
    return reports[0] if reports else None


@pytest.fixture
def crash_dir():
    """Temp directory that lives for the duration of the test."""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


class TestSimpleCrash:
    def test_captures_zero_division(self, crash_dir):
        exit_code, _, stderr = _run_crash("simple_zero_division.py", str(crash_dir))
        assert exit_code != 0
        report = _find_report(crash_dir)
        assert report is not None, f"No report in {crash_dir}, stderr: {stderr}"
        data = json.loads(report.read_text(encoding="utf-8"))
        assert data["exception"]["type"] == "ZeroDivisionError"

    def test_original_traceback_preserved(self, crash_dir):
        _, _, stderr = _run_crash("simple_zero_division.py", str(crash_dir))
        assert "ZeroDivisionError" in stderr
        assert "Traceback" in stderr


class TestNestedException:
    def test_captures_exception_chain(self, crash_dir):
        _run_crash("nested_exception.py", str(crash_dir))
        report = _find_report(crash_dir)
        assert report is not None
        data = json.loads(report.read_text(encoding="utf-8"))
        assert data["exception"]["type"] == "ValueError"


class TestSecretRedaction:
    def test_passwords_are_redacted(self, crash_dir):
        _, _, stderr = _run_crash("secret_containing.py", str(crash_dir))
        report = _find_report(crash_dir)
        assert report is not None, f"No report. stderr: {stderr}"
        report_text = json.dumps(json.loads(report.read_text(encoding="utf-8")))
        assert "my-secret-password-123" not in report_text

    def test_normal_values_preserved(self, crash_dir):
        _run_crash("secret_containing.py", str(crash_dir))
        report = _find_report(crash_dir)
        assert report is not None
        report_text = json.dumps(json.loads(report.read_text(encoding="utf-8")))
        assert "Alice" in report_text
class TestKeyboardInterrupt:
    def test_keyboard_interrupt_is_not_suppressed(self, crash_dir):
        exit_code, _, stderr = _run_crash("keyboard_interrupt.py", str(crash_dir))
        assert exit_code != 0
        assert "KeyboardInterrupt" in stderr


class TestSystemExit:
    def test_system_exit_is_not_captured(self, crash_dir):
        exit_code, _, stderr = _run_crash("system_exit.py", str(crash_dir))
        assert exit_code == 3
        report = _find_report(crash_dir)
        assert report is None, f"SystemExit should not produce a crash report, stderr: {stderr}"


class TestUnicodeVariableNames:
    def test_unicode_variable_names_captured(self, crash_dir):
        _run_crash("unicode_variable_names.py", str(crash_dir))
        report = _find_report(crash_dir)
        assert report is not None
        data = json.loads(report.read_text(encoding="utf-8"))
        locals_ = data["frames"][0]["locals"]
        assert "café" in locals_
        assert "naïve_π" in locals_


class TestNoneValuesInLocals:
    def test_none_values_preserved(self, crash_dir):
        _run_crash("none_values_in_locals.py", str(crash_dir))
        report = _find_report(crash_dir)
        assert report is not None
        data = json.loads(report.read_text(encoding="utf-8"))
        locals_ = data["frames"][0]["locals"]
        assert locals_["result"]["value"] == "None"
        assert locals_["config"]["value"] == "None"
