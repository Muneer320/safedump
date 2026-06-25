"""Crash capture engine for Safedump.

Walks traceback frames, extracts locals and environment data,
and orchestrates the capture → sanitize → serialize → persist pipeline.

This module runs inside exception hooks — it must never fail
and must always preserve the original traceback.
"""

from __future__ import annotations

import contextlib
import os
import reprlib
import sys
import threading
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from safedump._config import get_config, save_original_config
from safedump._sanitize import sanitize
from safedump._serialize import serialize
from safedump._storage import save
from safedump._types import (
    CrashReport,
    EnvironmentSnapshot,
    ExceptionSnapshot,
    FrameSnapshot,
    SafedumpConfig,
    ThreadSnapshot,
    VariableSnapshot,
)

# Pre-allocated fallback buffer for MemoryError scenarios
_fallback_buffer: bytearray | None = None
# Saved original exception hooks for uninstall
_original_excepthook: Any = None
_original_threading_excepthook: Any = None
_original_unraisablehook: Any = None
# Install state
_installed: bool = False


def _safe_repr(obj: Any, max_chars: int = 500) -> str:
    """Safely convert an object to its string representation.

    Three-layer defense (C2 resolution):
    1. ``reprlib.repr()`` with built-in recursion and length limits
    2. ``try/except BaseException`` catches anything that slips through
    3. Falls back to ``<ClassName>`` if all else fails

    Never raises. Never calls ``object.__repr__()`` directly.
    """
    try:
        # reprlib.repr has built-in limits for recursion, strings, etc.
        result = reprlib.repr(obj)
        if len(result) > max_chars:
            result = result[:max_chars] + "..."
        return result
    except BaseException:
        try:
            return f"<{type(obj).__name__}>"
        except BaseException:
            return "<unknown>"


def _walk_traceback(tb: Any) -> list[tuple[Any, int]]:
    """Walk a traceback chain, yielding (frame, lineno) pairs.

    Uses ``traceback.walk_tb`` on Python 3.12+, manual iteration
    on older versions (C1 resolution).
    """
    frames: list[tuple[Any, int]] = []
    if hasattr(traceback, "walk_tb"):
        frames.extend(traceback.walk_tb(tb))
    else:
        while tb is not None:
            frames.append((tb.tb_frame, tb.tb_lineno))
            tb = tb.tb_next
    return frames


def _capture_frame(frame: Any, lineno: int, index: int, config: SafedumpConfig) -> FrameSnapshot:
    """Capture a single stack frame's data."""
    # Extract locals safely — dict() handles both old dict and 3.13+ proxy
    try:
        raw_locals = dict(frame.f_locals) if hasattr(frame, "f_locals") else {}
    except (ValueError, RuntimeError):
        raw_locals = {}

    # Build VariableSnapshot for each local, respecting limits
    variables: dict[str, VariableSnapshot] = {}
    count = 0
    for name, value in raw_locals.items():
        if count >= config.max_collection_items:
            break
        # Skip dunder variables (optional — privacy consideration)
        if name.startswith("__") and name.endswith("__"):
            continue
        var = VariableSnapshot(
            name=name,
            type=type(value).__name__,
            value=_safe_repr(value, config.max_string_length),
        )
        variables[name] = var
        count += 1

    # Extract source context
    code_context: list[str] = []
    try:
        if hasattr(frame, "f_code"):
            fname = frame.f_code.co_filename
            first_line = frame.f_code.co_firstlineno
            try:
                import linecache

                for i in range(lineno - 3, lineno + 2):
                    if i >= first_line:
                        line = linecache.getline(fname, i)
                        if line:
                            code_context.append(line.rstrip())
            except Exception:
                pass
    except Exception:
        pass

    return FrameSnapshot(
        index=index,
        file=(getattr(frame, "f_code", None) and frame.f_code.co_filename) or "<unknown>",
        line=lineno,
        function=(getattr(frame, "f_code", None) and frame.f_code.co_name) or "<unknown>",
        lineno=lineno,
        code_context=code_context,
        locals=variables,
        is_crash_site=(index == 0),
    )


def _capture_exception_chain(exc_value: BaseException) -> ExceptionSnapshot:
    """Walk exception chain (__cause__, __context__, ExceptionGroup)."""
    snap = ExceptionSnapshot(
        type=type(exc_value).__name__,
        message=str(exc_value),
        module=type(exc_value).__module__,
        is_explicitly_chained=exc_value.__cause__ is not None,
    )

    # Handle ExceptionGroup (Python 3.11+)
    if hasattr(exc_value, "exceptions"):
        for sub in exc_value.exceptions:  # type: ignore[attr-defined]
            snap.sub_exceptions.append(_capture_exception_chain(sub))

    # Walk __cause__ chain
    if exc_value.__cause__ is not None and exc_value.__cause__ is not exc_value:
        snap.sub_exceptions.append(_capture_exception_chain(exc_value.__cause__))

    # Walk __context__ chain (if different from __cause__)
    ctx = exc_value.__context__
    if ctx is not None and ctx is not exc_value and ctx is not exc_value.__cause__:
        snap.sub_exceptions.append(_capture_exception_chain(ctx))

    return snap


def _capture_environment(config: SafedumpConfig) -> EnvironmentSnapshot:
    """Capture system environment data."""
    env = EnvironmentSnapshot(
        os_name=os.name,
        os_version=_safe_repr(sys.platform),
        python_impl=sys.implementation.name,
        python_path=[str(p) for p in sys.path],
        cwd=os.getcwd(),
    )

    if config.include_env_names:
        with contextlib.suppress(Exception):
            env.env_var_names = sorted(os.environ.keys())

    if config.include_argv:
        env.argv = list(sys.argv)

    return env


def _capture_threads() -> list[ThreadSnapshot]:
    """Capture all thread information."""
    current = threading.current_thread()
    threads = []
    for t in threading.enumerate():
        snap = ThreadSnapshot(
            name=t.name,
            ident=t.ident,
            daemon=t.daemon,
            crashed=(t is current),
        )
        threads.append(snap)
    # Put crashing thread first
    threads.sort(key=lambda t: not t.crashed)
    return threads


def crash_handler(
    exc_type: type[BaseException],
    exc_value: BaseException,
    exc_tb: Any,
) -> None:
    """Exception hook — called by Python when an unhandled crash occurs.

    This is the outer guard.  If ANYTHING inside this function fails,
    the original traceback is printed and the process continues.
    """
    global _fallback_buffer

    # Save original exception info for fallback
    saved_type = exc_type
    saved_value = exc_value
    saved_tb = exc_tb

    try:
        config = get_config()

        # Build CrashReport
        report = CrashReport(
            timestamp=datetime.now(timezone.utc).isoformat(),
            exception=_capture_exception_chain(exc_value),
            environment=_capture_environment(config),
            threads=_capture_threads(),
        )

        # Walk frames
        frames = _walk_traceback(exc_tb)
        for i, (frame, lineno) in enumerate(frames):
            if i >= config.max_depth:
                break
            fs = _capture_frame(frame, lineno, i, config)
            report.frames.append(fs)

        # Apply before_capture hook (C8)
        if config.before_capture is not None:
            try:
                result = config.before_capture(report)
                if result is not None:
                    report = result
            except Exception:
                pass  # hook failure should not block capture

        # Sanitize
        report = sanitize(report, config)

        # Serialize
        json_str = serialize(report, config)

        # Persist
        path = save(json_str, config, report)

        if path is not None:
            print(f"Crash report saved: {path}", file=sys.stderr)
        else:
            print("Safedump: could not write crash report", file=sys.stderr)

    except Exception as e:
        # Double fault — handler itself crashed
        print(f"Safedump internal error: {e}", file=sys.stderr)

    finally:
        # Always print the original traceback — this is the ultimate fallback
        try:
            traceback.print_exception(saved_type, saved_value, saved_tb)
        except Exception:
            # If even printing fails, write a minimal message
            print(f"{saved_type.__name__}: {saved_value}", file=sys.stderr)


def install() -> None:
    """Install Safedump crash hooks globally."""
    global _installed, _original_excepthook, _original_threading_excepthook
    global _original_unraisablehook, _fallback_buffer

    if _installed:
        return

    save_original_config()

    _original_excepthook = sys.excepthook
    _original_threading_excepthook = getattr(threading, "_excepthook", None)
    _original_unraisablehook = sys.unraisablehook

    sys.excepthook = crash_handler
    threading.excepthook = crash_handler  # type: ignore[assignment]
    sys.unraisablehook = crash_handler  # type: ignore[assignment]

    # Pre-allocate fallback buffer for MemoryError scenarios
    if _fallback_buffer is None:
        _fallback_buffer = bytearray(1_048_576)  # 1 MB

    _installed = True
    print(f"Safedump installed. Crash reports → {get_config().output_dir}", file=sys.stderr)


def uninstall() -> None:
    """Restore original Python exception hooks."""
    global _installed

    if not _installed:
        return

    if _original_excepthook is not None:
        sys.excepthook = _original_excepthook
    if _original_threading_excepthook is not None:
        threading.excepthook = _original_threading_excepthook  # type: ignore[assignment]
    if _original_unraisablehook is not None:
        sys.unraisablehook = _original_unraisablehook  # type: ignore[assignment]

    _installed = False
    print("Safedump uninstalled.", file=sys.stderr)


def is_installed() -> bool:
    """Check if Safedump hooks are currently active."""
    return _installed


def capture_exception(
    exc: BaseException | None = None,
    *,
    privacy_tier: int | None = None,
    output_dir: str | Path | None = None,
) -> Path | None:
    """Manual crash capture for try/except blocks.

    If exc is None, captures sys.exc_info().
    """
    if exc is None:
        exc = sys.exc_info()[1]
    if exc is None:
        raise RuntimeError("No exception to capture")

    # Build a synthetic traceback from the exception
    tb = exc.__traceback__

    config = get_config()
    saved_tier = config.privacy_tier
    saved_dir = config.output_dir

    try:
        if privacy_tier is not None:
            config.privacy_tier = privacy_tier
        if output_dir is not None:
            config.output_dir = Path(output_dir)

        report = CrashReport(
            timestamp=datetime.now(timezone.utc).isoformat(),
            exception=_capture_exception_chain(exc),
            environment=_capture_environment(config),
            threads=_capture_threads(),
        )

        if tb is not None:
            frames = _walk_traceback(tb)
            for i, (frame, lineno) in enumerate(frames):
                if i >= config.max_depth:
                    break
                report.frames.append(_capture_frame(frame, lineno, i, config))

        report = sanitize(report, config)
        json_str = serialize(report, config)
        return save(json_str, config, report)
    finally:
        config.privacy_tier = saved_tier
        config.output_dir = saved_dir


def test() -> Path | None:
    """Self-test — verify Safedump is working."""
    if not _installed:
        raise RuntimeError("safedump is not installed. Call safedump.install() first.")

    try:
        raise RuntimeError("safedump self-test exception")
    except RuntimeError:
        return capture_exception()
