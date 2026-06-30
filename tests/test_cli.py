"""Tests for the CLI entry point."""

from importlib.metadata import version
import subprocess
import sys


def test_version_matches_package():
    """--version should report the installed package version, not a hardcoded string."""
    result = subprocess.run(
        ["safedump", "--version"],
        capture_output=True,
        text=True,
    )
    expected = f"safedump {version('safedump')}"
    assert expected in result.stdout or expected in result.stderr


def test_version_is_not_hardcoded():
    """--version should never return the old hardcoded 0.1.0."""
    result = subprocess.run(
        ["safedump", "--version"],
        capture_output=True,
        text=True,
    )
    assert "0.1.0" not in result.stdout
    assert "0.1.0" not in result.stderr