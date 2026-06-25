"""Integration tests — real subprocess crashes."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


def _run_crash(fixture_name: str, crash_dir: str) -> tuple[int, str, str]:
    """Run a crash fixture. crash_dir must exist for the lifetime needed."""
    fixture = FIXTURES / fixture_name
    script = fixture.read_text().replace("CRASH_DIR_PLACEHOLDER", crash_dir)
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        timeout=30,
    )
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
        data = json.loads(report.read_text())
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
        data = json.loads(report.read_text())
        assert data["exception"]["type"] == "ValueError"


class TestSecretRedaction:
    def test_passwords_are_redacted(self, crash_dir):
        _, _, stderr = _run_crash("secret_containing.py", str(crash_dir))
        report = _find_report(crash_dir)
        assert report is not None, f"No report. stderr: {stderr}"
        report_text = json.dumps(json.loads(report.read_text()))
        assert "my-secret-password-123" not in report_text

    def test_normal_values_preserved(self, crash_dir):
        _run_crash("secret_containing.py", str(crash_dir))
        report = _find_report(crash_dir)
        assert report is not None
        report_text = json.dumps(json.loads(report.read_text()))
        assert "Alice" in report_text
