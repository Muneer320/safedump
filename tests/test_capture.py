"""Unit tests for internal capture-engine functions in ``safedump._capture``.

These exercise ``_walk_traceback`` and the crash_handler's outer guard
directly, for scenarios that are impractical to trigger via a real
subprocess crash (an empty/None traceback, and a MemoryError raised
mid-capture).
"""

# SPDX-FileCopyrightText: 2026 Muneer Alam
#
# SPDX-License-Identifier: MIT


from __future__ import annotations

import sys

from safedump import _capture


class TestEmptyTracebackHandling:
    def test_none_traceback_returns_empty_list(self) -> None:
        """A None traceback (e.g. a manually constructed exception with no
        __traceback__) must not raise â€” it should walk to an empty list."""
        frames = _capture._walk_traceback(None)
        assert frames == []

    def test_capture_exception_with_no_traceback(self, tmp_path) -> None:
        """capture_exception() must not crash when exc.__traceback__ is None."""
        exc = RuntimeError("no traceback here")
        assert exc.__traceback__ is None

        path = _capture.capture_exception(exc, output_dir=tmp_path)

        # No frames to walk, but a report should still be written.
        assert path is not None
        assert path.exists()


class TestMemoryErrorHandling:
    def test_crash_handler_survives_memory_error_in_capture(
        self, monkeypatch, tmp_path, capsys
    ) -> None:
        """If something inside the try-block of crash_handler raises
        MemoryError, the outer guard must catch it (MemoryError is an
        Exception subclass) and still print the original traceback."""

        def _boom(*args, **kwargs):
            raise MemoryError("simulated allocation failure")

        monkeypatch.setattr(_capture, "_capture_environment", _boom)

        try:
            raise ValueError("original crash")
        except ValueError:
            exc_type, exc_value, exc_tb = sys.exc_info()

        _capture.crash_handler(exc_type, exc_value, exc_tb)

        captured = capsys.readouterr()
        assert "Safedump internal error" in captured.err
        assert "ValueError" in captured.err
        assert "original crash" in captured.err

    def test_fallback_buffer_preallocated_on_install(self) -> None:
        """install() pre-allocates a 1MB fallback buffer so a real
        MemoryError during capture has headroom to be handled."""
        _capture.uninstall()
        _capture._fallback_buffer = None

        _capture.install()
        try:
            assert _capture._fallback_buffer is not None
            assert len(_capture._fallback_buffer) == 1_048_576
        finally:
            _capture.uninstall()
