"""Tests for Safedump developer tool integrations."""

from __future__ import annotations

import contextlib


class TestClickPlugin:
    """Tests for the Click/Typer integration."""

    def test_wrap_click_captures_exception(self, tmp_path):
        """wrap_click() should capture exceptions."""
        from safedump._config import configure
        from safedump.integrations.click_plugin import wrap_click

        configure(output_dir=tmp_path)

        @wrap_click()
        def failing_func():
            raise ValueError("click test error")

        with contextlib.suppress(ValueError):
            failing_func()

        # A report should have been written
        from safedump._loader import list_reports

        reports = list_reports(tmp_path)
        assert len(reports) >= 1

    def test_wrap_click_re_raises(self):
        """wrap_click() should re-raise the exception."""
        from safedump.integrations.click_plugin import wrap_click

        @wrap_click()
        def failing_func():
            raise ValueError("re-raise test")

        import pytest

        with pytest.raises(ValueError, match="re-raise test"):
            failing_func()

    def test_wrap_click_passes_return_value(self):
        """wrap_click() should return the function's result on success."""
        from safedump.integrations.click_plugin import wrap_click

        @wrap_click()
        def success_func():
            return 42

        assert success_func() == 42


class TestPytestPlugin:
    """Tests for the pytest integration."""

    def test_plugin_can_be_imported(self):
        from safedump.integrations.pytest_plugin import pytest_runtest_makereport

        assert callable(pytest_runtest_makereport)
