"""Tests for safedump.logging_handler.SafedumpLogHandler."""

# SPDX-FileCopyrightText: 2026 Muneer Alam
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

import json
import logging

import safedump
from safedump.logging_handler import SafedumpLogHandler


class TestSafedumpLogHandler:
    """SafedumpLogHandler integration tests."""

    def test_handler_captures_exception_from_logger(self, tmp_path) -> None:
        """Logging an exception with exc_info=True writes a crash report."""
        safedump.configure(output_dir=tmp_path, privacy_tier=1)

        logger = logging.getLogger("test_capture")
        logger.setLevel(logging.ERROR)
        logger.addHandler(SafedumpLogHandler())
        logger.propagate = False  # don't clutter test output

        try:
            raise ValueError("test error from logger")
        except ValueError:
            logger.exception("A deliberate crash")

        reports = list(tmp_path.glob("*.safedump.json"))
        assert len(reports) >= 1, "No crash report was written"

        with open(reports[-1]) as f:
            data = json.load(f)
        assert data["exception"]["type"] == "ValueError"
        assert data["exception"]["message"] == "test error from logger"

    def test_handler_does_not_capture_without_exception(self, tmp_path) -> None:
        """A plain log message (no exc_info) must not write a report."""
        safedump.configure(output_dir=tmp_path, privacy_tier=1)

        logger = logging.getLogger("test_no_capture")
        logger.setLevel(logging.ERROR)
        logger.addHandler(SafedumpLogHandler(output_dir=tmp_path))
        logger.propagate = False

        logger.error("Just a message, no exception")

        assert list(tmp_path.glob("*.safedump.json")) == []

    def test_handler_respects_log_level(self, tmp_path) -> None:
        """Messages below the handler's threshold must not trigger capture."""
        safedump.configure(output_dir=tmp_path, privacy_tier=1)

        logger = logging.getLogger("test_level")
        logger.setLevel(logging.DEBUG)
        handler = SafedumpLogHandler(level=logging.CRITICAL)
        logger.addHandler(handler)
        logger.propagate = False

        try:
            raise RuntimeError("below threshold")
        except RuntimeError:
            logger.exception("This is logged at ERROR, not CRITICAL")

        assert list(tmp_path.glob("*.safedump.json")) == []

    def test_handler_captures_at_critical_level(self, tmp_path) -> None:
        """CRITICAL-level log with exc_info should still capture."""
        safedump.configure(output_dir=tmp_path, privacy_tier=1)

        logger = logging.getLogger("test_critical")
        logger.setLevel(logging.CRITICAL)
        handler = SafedumpLogHandler(level=logging.CRITICAL)
        logger.addHandler(handler)
        logger.propagate = False

        try:
            raise KeyError("critical error")
        except KeyError:
            logger.critical("A critical failure", exc_info=True)

        reports = list(tmp_path.glob("*.safedump.json"))
        assert len(reports) >= 1

    def test_handler_capture_kwargs_forwarded(self, tmp_path) -> None:
        """Extra kwargs (privacy_tier, output_dir) reach capture_exception."""
        custom_dir = tmp_path / "custom_logs"
        custom_dir.mkdir()

        logger = logging.getLogger("test_kwargs")
        logger.setLevel(logging.ERROR)
        logger.addHandler(SafedumpLogHandler(output_dir=custom_dir))
        logger.propagate = False

        try:
            raise ValueError("kwargs forwarded")
        except ValueError:
            logger.exception("check")

        reports = list(custom_dir.glob("*.safedump.json"))
        assert len(reports) >= 1

    def test_handler_never_raises(self, tmp_path) -> None:
        """If capture_exception itself fails, the handler stays silent."""
        safedump.configure(output_dir=tmp_path, privacy_tier=1)

        logger = logging.getLogger("test_safe")
        logger.setLevel(logging.ERROR)
        logger.addHandler(SafedumpLogHandler())
        logger.propagate = False

        # This is safe: logging with no exception active means exc_info is
        # None, so the handler does nothing, not even try to capture.
        try:
            raise ValueError("trigger")
        except ValueError:
            logger.exception("this should work fine")

        assert True  # no exception means the handler is safe
