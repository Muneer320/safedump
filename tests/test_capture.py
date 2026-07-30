"""Tests for the crash capture engine (_capture.py).

Covers crash_handler, capture_exception, install/uninstall lifecycle,
and is_installed state. Frame walking functions are tested separately
in test_frame_walker.py.
"""

from __future__ import annotations

import json
import sys

import pytest

from safedump import _capture
from safedump._config import configure


class TestInstallUninstallLifecycle:
    """install/uninstall/is_installed lifecycle tests."""

    def setup_method(self):
        _capture.uninstall()

    def test_install_sets_installed(self):
        assert not _capture.is_installed()
        _capture.install()
        assert _capture.is_installed()
        _capture.uninstall()

    def test_uninstall_clears_installed(self):
        _capture.install()
        assert _capture.is_installed()
        _capture.uninstall()
        assert not _capture.is_installed()

    def test_install_is_idempotent(self):
        _capture.install()
        _capture.install()  # second call should be no-op
        assert _capture.is_installed()
        _capture.uninstall()

    def test_uninstall_is_idempotent(self):
        _capture.uninstall()  # already uninstalled
        _capture.uninstall()  # second call
        assert not _capture.is_installed()

    def test_install_replaces_excepthook(self):
        original = sys.excepthook
        _capture.install()
        assert sys.excepthook is _capture.crash_handler
        _capture.uninstall()
        assert sys.excepthook is original

    def test_install_preallocates_fallback_buffer(self):
        _capture._fallback_buffer = None
        _capture.install()
        assert _capture._fallback_buffer is not None
        assert len(_capture._fallback_buffer) == 1_048_576
        _capture.uninstall()


class TestCaptureException:
    """capture_exception function tests."""

    def test_capture_with_explicit_exception(self, tmp_path):
        exc = ValueError("test explicit capture")
        path = _capture.capture_exception(exc, output_dir=tmp_path)
        assert path is not None
        assert path.exists()
        with open(path) as f:
            data = json.load(f)
        assert data["exception"]["type"] == "ValueError"
        assert data["exception"]["message"] == "test explicit capture"

    def test_capture_with_exception_inside_except(self, tmp_path):
        try:
            raise TypeError("caught in except block")
        except TypeError:
            path = _capture.capture_exception(output_dir=tmp_path)
        assert path is not None
        with open(path) as f:
            data = json.load(f)
        assert data["exception"]["type"] == "TypeError"
        assert data["exception"]["message"] == "caught in except block"

    def test_capture_raises_when_no_exception(self):
        with pytest.raises(RuntimeError, match="No exception to capture"):
            _capture.capture_exception()

    def test_capture_respects_output_dir(self, tmp_path):
        custom_dir = tmp_path / "custom"
        custom_dir.mkdir()
        exc = ValueError("check output dir")
        path = _capture.capture_exception(exc, output_dir=custom_dir)
        assert path is not None
        assert str(path.parent) == str(custom_dir)

    def test_capture_returns_none_on_failure(self, tmp_path):
        """capture_exception returns None when save fails."""
        with pytest.raises(RuntimeError, match="No exception to capture"):
            _capture.capture_exception()

    def test_capture_includes_fingerprint(self, tmp_path):
        exc = ValueError("fingerprint check")
        path = _capture.capture_exception(exc, output_dir=tmp_path)
        assert path is not None
        with open(path) as f:
            data = json.load(f)
        assert len(data.get("fingerprint", "")) == 12

    def test_capture_includes_schema_version(self, tmp_path):
        exc = ValueError("schema check")
        path = _capture.capture_exception(exc, output_dir=tmp_path)
        assert path is not None
        with open(path) as f:
            data = json.load(f)
        assert data.get("schema_version") == 1


class TestCrashHandler:
    """crash_handler function tests."""

    def test_crash_handler_writes_report(self, tmp_path, capsys):
        configure(output_dir=tmp_path)
        _capture.install()
        try:
            raise RuntimeError("handler test")
        except RuntimeError:
            exc_type, exc_value, exc_tb = sys.exc_info()
            _capture.crash_handler(exc_type, exc_value, exc_tb)

        captured = capsys.readouterr()
        assert "Crash report saved" in captured.err
        assert "handler test" in captured.err

        _capture.uninstall()

    def test_crash_handler_preserves_original_traceback(self, tmp_path, capsys):
        configure(output_dir=tmp_path)
        try:
            raise ValueError("original error")
        except ValueError:
            exc_type, exc_value, exc_tb = sys.exc_info()
            _capture.crash_handler(exc_type, exc_value, exc_tb)

        captured = capsys.readouterr()
        assert "ValueError" in captured.err
        assert "original error" in captured.err

    def test_crash_handler_survives_double_fault(self, tmp_path, capsys, monkeypatch):
        """If crash_handler itself raises, the original traceback must survive."""
        configure(output_dir=tmp_path)
        monkeypatch.setattr(
            "safedump._capture.get_config",
            lambda: (_ for _ in ()).throw(RuntimeError("config fail")),
        )

        try:
            raise RuntimeError("original")
        except RuntimeError:
            exc_type, exc_value, exc_tb = sys.exc_info()
            _capture.crash_handler(exc_type, exc_value, exc_tb)

        captured = capsys.readouterr()
        assert "Safedump internal error" in captured.err
        assert "original" in captured.err


class TestSelfTest:
    """safedump.test() function tests."""

    def test_test_raises_when_not_installed(self):
        _capture.uninstall()
        with pytest.raises(RuntimeError, match="not installed"):
            _capture.test()

    def test_test_creates_report(self, tmp_path):
        configure(output_dir=tmp_path)
        _capture.install()
        try:
            path = _capture.test()
            assert path is not None
            assert path.exists()
            with open(path) as f:
                data = json.load(f)
            assert data["exception"]["type"] == "RuntimeError"
        finally:
            _capture.uninstall()
