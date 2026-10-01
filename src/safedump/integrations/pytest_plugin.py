"""pytest integration for Safedump.

Writes a crash report for every test that fails with an exception, so the
failure's locals can be inspected later with ``safedump view``. Skipped tests,
expected failures (xfail) and passing tests produce nothing. This plugin does
not install global exception hooks.

Enable it explicitly, it is not activated just by installing safedump:

    # conftest.py
    pytest_plugins = ["safedump.integrations.pytest_plugin"]

or on the command line: ``pytest -p safedump.integrations.pytest_plugin``.
"""

from __future__ import annotations

import contextlib
from collections.abc import Generator
from typing import Any

import pytest

from safedump import capture_exception


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: Any, call: Any) -> Generator[None, Any, None]:
    """Capture a report when a test phase fails with an exception."""
    outcome = yield
    report = outcome.get_result()
    if report.failed and call.excinfo is not None and call.excinfo.value is not None:
        with contextlib.suppress(BaseException):
            capture_exception(call.excinfo.value)
