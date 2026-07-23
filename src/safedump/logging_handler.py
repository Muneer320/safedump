"""Optional logging integration for Safedump.

Provides a :class:`SafedumpLogHandler` that writes crash summaries
to Python's standard :mod:`logging` system alongside the usual JSON
report files.  Fully optional -- importing Safedump never configures
logging automatically.
"""

# SPDX-FileCopyrightText: 2026 Muneer Alam
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

import contextlib
import logging
from typing import Any

from safedump._capture import capture_exception

__all__ = ["SafedumpLogHandler"]


class SafedumpLogHandler(logging.Handler):
    """A logging handler that captures exceptions via Safedump.

    When an exception is logged at or above the configured level,
    the handler calls :func:`safedump.capture_exception` to produce
    a structured crash report in addition to the log message.

    Typical usage::

        import logging
        import safedump
        from safedump.logging_handler import SafedumpLogHandler

        safedump.configure(preset="production")
        safedump.install()

        logger = logging.getLogger("myapp")
        logger.addHandler(SafedumpLogHandler())
        logger.setLevel(logging.ERROR)

    Args:
        level: Minimum log level that triggers capture. Defaults to ERROR.
        capture_kwargs: Extra keyword arguments forwarded to
            :func:`safedump.capture_exception` (e.g. ``privacy_tier``,
            ``output_dir``).
    """

    def __init__(
        self,
        level: int = logging.ERROR,
        **capture_kwargs: Any,
    ) -> None:
        super().__init__(level)
        self._capture_kwargs = capture_kwargs

    def emit(self, record: logging.LogRecord) -> None:
        """Capture the current exception if one is being handled.

        Examines ``sys.exc_info()`` and, if an exception is present,
        calls :func:`safedump.capture_exception` to write a crash report.
        The handler never raises -- any failure is silently ignored so
        logging itself remains unaffected.
        """
        if record.exc_info is not None and record.exc_info[1] is not None:
            with contextlib.suppress(Exception):
                capture_exception(
                    record.exc_info[1],
                    **self._capture_kwargs,
                )
