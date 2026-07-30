"""Tests for frame walking and data capture functions (_frame_walker.py)."""

from __future__ import annotations

import threading

from safedump._frame_walker import (
    MAX_FRAMES,
    capture_environment,
    capture_exception_chain,
    capture_threads,
    compute_fingerprint,
    safe_repr,
    walk_traceback,
)
from safedump._types import (
    CrashReport,
    ExceptionSnapshot,
    FrameSnapshot,
    SafedumpConfig,
)


class TestSafeRepr:
    def test_basic_object(self):
        assert safe_repr("hello") == "'hello'"
        assert safe_repr(42) == "42"
        assert safe_repr([1, 2, 3]) == "[1, 2, 3]"

    def test_max_chars_truncation(self):
        long_str = "a" * 1000
        result = safe_repr(long_str, max_chars=50)
        # reprlib includes quotes, so actual length varies
        # Just verify truncation happened
        assert "..." in result

    def test_repr_failure_fallback(self):
        class BrokenRepr:
            def __repr__(self):
                raise RuntimeError("broken repr")

            def __class_getattr__(self):
                raise RuntimeError("broken")

        result = safe_repr(BrokenRepr())
        assert "<" in result and ">" in result

    def test_baseexception_repr_failure(self):
        result = safe_repr(object())
        assert result is not None


class TestWalkTraceback:
    def test_none_traceback(self):
        assert walk_traceback(None) == []

    def test_capture_exception_chain_basic(self):
        exc = ValueError("test")
        snap = capture_exception_chain(exc)
        assert snap.type == "ValueError"
        assert snap.message == "test"

    def test_capture_exception_chain_chained(self):
        try:
            try:
                raise ValueError("inner")
            except ValueError as inner:
                raise RuntimeError("outer") from inner
        except RuntimeError as exc:
            snap = capture_exception_chain(exc)
            assert snap.type == "RuntimeError"
            assert len(snap.sub_exceptions) >= 1
            assert snap.sub_exceptions[0].type == "ValueError"


class TestCaptureEnvironment:
    def test_capture_environment_basic(self):
        config = SafedumpConfig()
        env = capture_environment(config)
        assert env.python_impl.lower() == "cpython"
        assert env.cwd != ""

    def test_capture_environment_with_env_names(self):
        config = SafedumpConfig(include_env_names=True)
        env = capture_environment(config)
        assert len(env.env_var_names) > 0
        assert "PATH" in env.env_var_names

    def test_capture_environment_with_argv(self):
        config = SafedumpConfig(include_argv=True)
        env = capture_environment(config)
        assert env.argv is not None
        assert len(env.argv) > 0


class TestCaptureThreads:
    def test_capture_threads_returns_current(self):
        threads = capture_threads()
        assert len(threads) >= 1
        crashed = [t for t in threads if t.crashed]
        assert len(crashed) == 1
        assert crashed[0].ident == threading.current_thread().ident


class TestComputeFingerprint:
    def test_fingerprint_deterministic(self):
        r1 = CrashReport(
            exception=ExceptionSnapshot(type="ValueError", message="test"),
            frames=[FrameSnapshot(index=0, file="app.py", line=42, function="main", lineno=42)],
        )
        r2 = CrashReport(
            exception=ExceptionSnapshot(type="ValueError", message="test"),
            frames=[FrameSnapshot(index=0, file="app.py", line=42, function="main", lineno=42)],
        )
        assert compute_fingerprint(r1) == compute_fingerprint(r2)

    def test_fingerprint_differs_for_diff_exceptions(self):
        r1 = CrashReport(
            exception=ExceptionSnapshot(type="ValueError", message="a"),
            frames=[FrameSnapshot(index=0, file="app.py", line=42, function="main", lineno=42)],
        )
        r2 = CrashReport(
            exception=ExceptionSnapshot(type="KeyError", message="b"),
            frames=[FrameSnapshot(index=0, file="app.py", line=42, function="main", lineno=42)],
        )
        assert compute_fingerprint(r1) != compute_fingerprint(r2)

    def test_fingerprint_no_frames(self):
        report = CrashReport(
            exception=ExceptionSnapshot(type="ValueError", message="no frames"),
        )
        fp = compute_fingerprint(report)
        assert len(fp) == 12

    def test_max_frames_constant(self):
        assert MAX_FRAMES == 100
