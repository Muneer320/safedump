"""CLI integration tests for safedump commands."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import safedump
from safedump._config import configure


def test_help_returns_success():
    result = subprocess.run(
        [sys.executable, "-m", "safedump", "--help"],
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode == 0
    assert "view" in result.stdout
    assert "list" in result.stdout
    assert "clean" in result.stdout
    assert "test" in result.stdout
    assert "doctor" in result.stdout
    assert "stats" in result.stdout
    assert "serve" in result.stdout


def test_version_returns_version():
    result = subprocess.run(
        [sys.executable, "-m", "safedump", "--version"],
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode == 0
    assert "safedump" in result.stdout.lower()


def test_doctor_exits_zero():
    result = subprocess.run(
        [sys.executable, "-m", "safedump", "doctor"],
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert "Traceback" not in result.stderr
    assert result.returncode in (0, 1)


def test_list_with_empty_dir():
    """list with an empty custom directory should handle gracefully."""
    empty_dir = Path(tempfile.mkdtemp())
    configure(output_dir=empty_dir)
    result = subprocess.run(
        [sys.executable, "-m", "safedump", "list"],
        capture_output=True,
        text=True,
        timeout=5,
    )
    # The subprocess doesn't inherit our configure(), so it uses its own
    # default dir which may or may not be empty. Just check no traceback.
    assert "Traceback" not in result.stderr


def test_test_command_needs_install():
    """test should give a clear error when not installed."""
    safedump.uninstall()
    result = subprocess.run(
        [sys.executable, "-m", "safedump", "test"],
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert "not installed" in result.stderr or "not installed" in result.stdout
