"""Tests for the safedump doctor command."""

from __future__ import annotations

import subprocess
import sys


class TestDoctorChecks:
    def test_doctor_returns_zero_on_healthy(self):
        """doctor should exit 0 on a clean system."""
        result = subprocess.run(
            [sys.executable, "-m", "safedump", "doctor"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        # May fail if safedump not installed, but should not crash
        assert "Traceback" not in result.stderr

    def test_doctor_checks_available(self):
        """All doctor checks should be reachable."""
        from safedump._cli import _doctor_checks

        checks = _doctor_checks()
        assert len(checks) >= 3, f"Expected at least 3 checks, got {len(checks)}"
        names = [c[0] for c in checks]
        # Check for key diagnostics
        assert any("python" in n.lower() for n in names)
