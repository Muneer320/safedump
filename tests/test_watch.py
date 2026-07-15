"""Tests for the ``safedump.watch()`` context manager API."""

# SPDX-FileCopyrightText: 2026 Muneer Alam
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

import json

import pytest

import safedump


class TestNormalExit:
    def test_no_exception_writes_no_report(self, tmp_path) -> None:
        """A watch() block that exits normally must not write a report."""
        with safedump.watch(output_dir=tmp_path):
            pass

        assert list(tmp_path.glob("*.safedump.json")) == []

    def test_returns_no_error_for_non_raising_block(self, tmp_path) -> None:
        result = []
        with safedump.watch(output_dir=tmp_path):
            result.append(1)

        assert result == [1]


class TestExceptionExit:
    def test_exception_is_captured_and_reraised(self, tmp_path) -> None:
        """capture_exception() must be invoked and the original exception
        must still propagate out of the with-block."""
        with pytest.raises(ValueError, match="boom"), safedump.watch(output_dir=tmp_path):
            raise ValueError("boom")

        reports = list(tmp_path.glob("*.safedump.json"))
        assert len(reports) == 1

    def test_report_contains_correct_exception_type(self, tmp_path) -> None:
        with pytest.raises(RuntimeError), safedump.watch(output_dir=tmp_path):
            raise RuntimeError("something broke")

        report = next(tmp_path.glob("*.safedump.json"))
        data = json.loads(report.read_text(encoding="utf-8"))
        assert data["exception"]["type"] == "RuntimeError"
        assert data["exception"]["message"] == "something broke"

    def test_original_traceback_is_preserved(self, tmp_path) -> None:
        """The exception re-raised out of watch() must retain its
        original traceback, not a synthetic/truncated one."""
        with pytest.raises(ValueError) as exc_info, safedump.watch(output_dir=tmp_path):
            raise ValueError("traceback check")

        assert exc_info.value.__traceback__ is not None


class TestNestedUsage:
    def test_nested_watch_blocks_each_capture_independently(self, tmp_path, monkeypatch) -> None:
        """An exception raised in an inner watch() block should be captured
        by the inner block; if it propagates further into an outer
        watch() block, the outer block captures it too.

        Note: both captures may land in the same file if they happen within
        the same second (capture_exception()'s filename is timestamp+hash
        based) â€” that collision is a pre-existing _storage.py behavior, not
        something watch() controls. So we assert on call count, not file count.
        """
        import sys

        watch_module = sys.modules["safedump.watch"]
        call_count = {"n": 0}
        original = watch_module.capture_exception

        def _counting(exc, **kwargs):
            call_count["n"] += 1
            return original(exc, **kwargs)

        monkeypatch.setattr(watch_module, "capture_exception", _counting)

        with (
            pytest.raises(ValueError),
            safedump.watch(output_dir=tmp_path),
            safedump.watch(output_dir=tmp_path),
        ):
            raise ValueError("nested boom")

        assert call_count["n"] == 2

    def test_inner_exception_handled_does_not_affect_outer(self, tmp_path) -> None:
        """If the inner block's exception is fully handled before reaching
        the outer block, the outer block must not produce a report."""
        with safedump.watch(output_dir=tmp_path):
            try:
                with safedump.watch(output_dir=tmp_path):
                    raise ValueError("caught inside")
            except ValueError:
                pass

        reports = list(tmp_path.glob("*.safedump.json"))
        assert len(reports) == 1


class TestParams:
    def test_output_dir_is_respected(self, tmp_path) -> None:
        custom_dir = tmp_path / "custom"
        custom_dir.mkdir()
        with pytest.raises(ValueError), safedump.watch(output_dir=custom_dir):
            raise ValueError("goes to custom dir")

        assert list(custom_dir.glob("*.safedump.json")) != []

    def test_privacy_tier_is_passed_through(self, tmp_path, monkeypatch) -> None:
        """watch() must forward privacy_tier to capture_exception()."""
        received = {}

        import sys

        watch_module = sys.modules["safedump.watch"]
        original = watch_module.capture_exception

        def _spy(exc, *, privacy_tier=None, output_dir=None):
            received["privacy_tier"] = privacy_tier
            received["output_dir"] = output_dir
            return original(exc, privacy_tier=privacy_tier, output_dir=output_dir)

        monkeypatch.setattr(watch_module, "capture_exception", _spy)

        with pytest.raises(ValueError), safedump.watch(privacy_tier=3, output_dir=tmp_path):
            raise ValueError("tier check")

        assert received["privacy_tier"] == 3

    def test_default_params_are_none(self, tmp_path) -> None:
        """When no output_dir is passed, watch() should fall back to the
        globally configured output_dir rather than erroring."""
        safedump.configure(output_dir=tmp_path, privacy_tier=1)
        with pytest.raises(ValueError), safedump.watch():
            raise ValueError("uses global config")

        assert list(tmp_path.glob("*.safedump.json")) != []


class TestControlFlowExceptions:
    def test_system_exit_is_not_captured(self, tmp_path) -> None:
        """SystemExit is control flow, not a crash — watch() must not
        write a report for it, matching capture_exception()'s behavior
        for unhandled SystemExit at the top level."""
        with pytest.raises(SystemExit), safedump.watch(output_dir=tmp_path):
            raise SystemExit(1)

        assert list(tmp_path.glob("*.safedump.json")) == []

    def test_keyboard_interrupt_is_not_captured(self, tmp_path) -> None:
        with pytest.raises(KeyboardInterrupt), safedump.watch(output_dir=tmp_path):
            raise KeyboardInterrupt()

        assert list(tmp_path.glob("*.safedump.json")) == []

    def test_regular_exception_still_captured(self, tmp_path) -> None:
        """Sanity check: the control-flow filter doesn't accidentally
        swallow normal exceptions."""
        with pytest.raises(ValueError), safedump.watch(output_dir=tmp_path):
            raise ValueError("still a real crash")

        assert list(tmp_path.glob("*.safedump.json")) != []
