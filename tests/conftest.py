"""Test configuration and shared fixtures for Safedump."""

import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_output_dir():
    """Create a temporary directory for crash reports."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def crash_script(tmp_path: Path, request):
    """Write a crash fixture script to a temporary file and return its path.

    Usage:
        def test_something(crash_script):
            script = crash_script("simple_zero_division.py")
            result = subprocess.run([sys.executable, script], capture_output=True)
    """

    def _write(fixture_name: str) -> Path:
        fixture_path = Path(__file__).parent / "fixtures" / fixture_name
        if not fixture_path.exists():
            raise FileNotFoundError(f"Fixture not found: {fixture_path}")
        dest = tmp_path / fixture_name
        dest.write_text(fixture_path.read_text())
        return dest

    return _write


# Placeholder — real fixtures will be added as crash scenarios are built
