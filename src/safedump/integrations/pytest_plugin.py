"""pytest integration for Safedump.

Automatically installs Safedump crash hooks during test runs so test
failures produce structured crash reports alongside the usual pytest
output.

Usage:

    # conftest.py
    pytest_plugins = ["safedump.integrations.pytest_plugin"]
"""

from __future__ import annotations

import contextlib

from safedump import capture_exception


def pytest_runtest_makereport(item, call):
    """Capture crash reports when a test raises an unexpected exception."""
    if call.excinfo is not None and call.excinfo.value is not None:
        with contextlib.suppress(BaseException):
            capture_exception(call.excinfo.value)
