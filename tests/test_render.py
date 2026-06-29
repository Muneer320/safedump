"""Tests for safedump._render.

Covers the plain-text fallback path and the friendly install hint
that should appear when Rich is not available (fixes #9).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

from safedump._render import _get_rich, _render_plain, render

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


MINIMAL_REPORT: dict[str, Any] = {
    "exception": {"type": "ZeroDivisionError", "message": "division by zero"},
    "frames": [],
    "environment": {},
    "redactions": [],
}

REPORT_WITH_FRAMES: dict[str, Any] = {
    "exception": {"type": "ValueError", "message": "bad value"},
    "frames": [
        {
            "file": "/app/main.py",
            "line": 10,
            "function": "main",
            "locals": {"x": {"type": "int", "value": "42"}},
            "code_context": [],
            "is_crash_site": True,
        }
    ],
    "environment": {"os_name": "posix", "cwd": "/app"},
    "redactions": [],
}


# ---------------------------------------------------------------------------
# _get_rich
# ---------------------------------------------------------------------------


class TestGetRich:
    def test_returns_none_when_rich_unavailable(self) -> None:
        """_get_rich() must return None (not raise) when Rich is missing."""
        import builtins

        original_import = builtins.__import__

        def blocked_import(name: str, *args: Any, **kwargs: Any) -> Any:
            if name.startswith("rich"):
                raise ImportError(f"No module named '{name}'")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=blocked_import):
            result = _get_rich()

        assert result is None

    def test_returns_rich_module_when_installed(self) -> None:
        """_get_rich() returns the rich module object when Rich is installed."""
        rich = _get_rich()
        if rich is None:
            pytest.skip("Rich not installed in this environment")
        import rich as expected_rich

        assert rich is expected_rich


# ---------------------------------------------------------------------------
# render() — Rich missing path
# ---------------------------------------------------------------------------


class TestRenderWithoutRich:
    """Verify the friendly-message behaviour introduced to fix #9."""

    def test_prints_friendly_message_to_stderr(self, capsys: pytest.CaptureFixture[str]) -> None:
        """A clear install hint must appear on stderr when Rich is missing."""
        with patch("safedump._render._get_rich", return_value=None):
            render(MINIMAL_REPORT)

        captured = capsys.readouterr()
        assert "Rich is not installed" in captured.err

    def test_friendly_message_includes_install_command(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """The hint must tell users the exact install command."""
        with patch("safedump._render._get_rich", return_value=None):
            render(MINIMAL_REPORT)

        captured = capsys.readouterr()
        assert "safedump[view]" in captured.err

    def test_still_outputs_plain_text_report(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Despite Rich being absent, the crash report must still be shown."""
        with patch("safedump._render._get_rich", return_value=None):
            render(MINIMAL_REPORT)

        captured = capsys.readouterr()
        assert "ZeroDivisionError" in captured.out
        assert "division by zero" in captured.out

    def test_no_exception_raised_when_rich_missing(self) -> None:
        """render() must never raise when Rich is absent."""
        with patch("safedump._render._get_rich", return_value=None):
            render(MINIMAL_REPORT)


class TestRenderWithRich:
    def test_no_warning_when_rich_available(self, capsys: pytest.CaptureFixture[str]) -> None:
        """The 'Rich not installed' warning must NOT appear when Rich is present."""
        if _get_rich() is None:
            pytest.skip("Rich not installed in this environment")

        render(MINIMAL_REPORT)

        captured = capsys.readouterr()
        assert "Rich is not installed" not in captured.err


# ---------------------------------------------------------------------------
# _render_plain
# ---------------------------------------------------------------------------


class TestRenderPlain:
    def test_shows_exception_type_and_message(self, capsys: pytest.CaptureFixture[str]) -> None:
        _render_plain(MINIMAL_REPORT)
        out = capsys.readouterr().out
        assert "ZeroDivisionError" in out
        assert "division by zero" in out

    def test_shows_frame_file_line_function(self, capsys: pytest.CaptureFixture[str]) -> None:
        _render_plain(REPORT_WITH_FRAMES)
        out = capsys.readouterr().out
        assert "/app/main.py:10 in main" in out

    def test_shows_local_variables(self, capsys: pytest.CaptureFixture[str]) -> None:
        _render_plain(REPORT_WITH_FRAMES)
        out = capsys.readouterr().out
        assert "x = 42" in out

    def test_shows_environment_info(self, capsys: pytest.CaptureFixture[str]) -> None:
        _render_plain(REPORT_WITH_FRAMES)
        out = capsys.readouterr().out
        assert "posix" in out
        assert "/app" in out

    def test_handles_empty_report_without_raising(self, capsys: pytest.CaptureFixture[str]) -> None:
        _render_plain({})
        out = capsys.readouterr().out
        assert "Unknown" in out

    def test_skips_environment_when_empty(self, capsys: pytest.CaptureFixture[str]) -> None:
        _render_plain(MINIMAL_REPORT)
        out = capsys.readouterr().out
        assert "Environment:" not in out
