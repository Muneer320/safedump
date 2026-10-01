"""Crash capture engine for Safedump.

Orchestrates the capture -> sanitize -> serialize -> persist pipeline.
The hook entry points run inside Python's exception hooks: they must never
fail and must always preserve the original traceback output.

Frame walking and data capture live in ``_frame_walker.py``.
"""

# SPDX-FileCopyrightText: 2026 Muneer Alam
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

import contextlib
import dataclasses
import sys
import threading
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from safedump._config import get_config, save_original_config
from safedump._frame_walker import (
    capture_environment,
    capture_exception_chain,
    capture_frames,
    capture_threads,
    compute_fingerprint,
)
from safedump._sanitize import sanitize
from safedump._serialize import serialize
from safedump._storage import save
from safedump._types import CrashReport, SafedumpConfig

# Saved original exception hooks for uninstall
_original_excepthook: Any = None
_original_threading_excepthook: Any = None
_original_unraisablehook: Any = None
# Install state
_installed: bool = False


def _build_report(
    exc_value: BaseException,
    tb: Any,
    config: SafedumpConfig,
    crashed_thread: threading.Thread | None = None,
) -> CrashReport:
    report = CrashReport(
        timestamp=datetime.now(timezone.utc).isoformat(),
        exception=capture_exception_chain(exc_value),
        environment=capture_environment(config),
        threads=capture_threads(crashed_thread),
    )
    if tb is not None:
        report.frames = capture_frames(tb, config)
    report.fingerprint = compute_fingerprint(report)
    report.first_seen = report.last_seen = report.timestamp
    return report


def _process(report: CrashReport, config: SafedumpConfig) -> Path | None:
    """Run the user hook, redact, serialize and write. Returns the report path."""
    if config.before_capture is not None:
        try:
            result = config.before_capture(report)
            if result is not None:
                report = result
        except Exception:
            pass
    report = sanitize(report, config)
    path = save(serialize(report, config), config, report)
    if path is not None and config.on_crash is not None:
        with contextlib.suppress(Exception):
            config.on_crash(path)
    return path


def _capture_from_hook(
    exc_value: BaseException | None,
    tb: Any,
    crashed_thread: threading.Thread | None = None,
) -> None:
    """Capture from inside an exception hook. Never raises."""
    if exc_value is None:
        return
    try:
        config = get_config()
        path = _process(_build_report(exc_value, tb, config, crashed_thread), config)
        if path is not None:
            print(f"Crash report saved: {path}", file=sys.stderr)
        else:
            print("Safedump: could not write crash report", file=sys.stderr)
    except Exception as e:
        print(f"Safedump internal error: {e}", file=sys.stderr)


def crash_handler(
    exc_type: type[BaseException],
    exc_value: BaseException,
    exc_tb: Any,
) -> None:
    """``sys.excepthook`` replacement: capture a report, then print the traceback as usual."""
    try:
        _capture_from_hook(exc_value, exc_tb)
    finally:
        try:
            traceback.print_exception(exc_type, exc_value, exc_tb)
        except Exception:
            print(f"{getattr(exc_type, '__name__', exc_type)}: {exc_value}", file=sys.stderr)


def thread_crash_handler(args: Any) -> None:
    """``threading.excepthook`` replacement.

    Receives a single ``threading.ExceptHookArgs`` object. ``SystemExit`` in a
    thread is ignored, exactly like Python's default hook. After capturing, the
    original hook prints the usual "Exception in thread ..." message.
    """
    try:
        if args.exc_type is not SystemExit:
            _capture_from_hook(args.exc_value, args.exc_traceback, args.thread)
    finally:
        # threading.__excepthook__ only exists on Python 3.10+
        original: Any = _original_threading_excepthook or getattr(threading, "__excepthook__", None)
        try:
            if original is None:
                raise RuntimeError("no default threading hook")
            original(args)
        except Exception:
            with contextlib.suppress(Exception):
                traceback.print_exception(args.exc_type, args.exc_value, args.exc_traceback)


def unraisable_handler(unraisable: Any) -> None:
    """``sys.unraisablehook`` replacement.

    Receives a ``sys.UnraisableHookArgs`` object, for example for an exception
    raised in ``__del__``. After capturing, the original hook prints the
    standard message.
    """
    try:
        _capture_from_hook(unraisable.exc_value, unraisable.exc_traceback)
    finally:
        original = _original_unraisablehook or sys.__unraisablehook__
        with contextlib.suppress(Exception):
            original(unraisable)


def install() -> None:
    """Install Safedump crash hooks globally.

    Replaces sys.excepthook, threading.excepthook, and sys.unraisablehook.
    Uses the current configuration set via configure().

    Safe to call multiple times. Subsequent calls are no-ops.
    """
    global _installed, _original_excepthook, _original_threading_excepthook
    global _original_unraisablehook

    if _installed:
        return

    save_original_config()

    _original_excepthook = sys.excepthook
    _original_threading_excepthook = threading.excepthook
    _original_unraisablehook = sys.unraisablehook

    sys.excepthook = crash_handler
    threading.excepthook = thread_crash_handler
    sys.unraisablehook = unraisable_handler

    _installed = True
    print(f"Safedump installed. Crash reports -> {get_config().output_dir}", file=sys.stderr)


def uninstall() -> None:
    """Restore original Python exception hooks.

    Safe to call multiple times. Subsequent calls are no-ops.
    """
    global _installed

    if not _installed:
        return

    if _original_excepthook is not None:
        sys.excepthook = _original_excepthook
    if _original_threading_excepthook is not None:
        threading.excepthook = _original_threading_excepthook
    if _original_unraisablehook is not None:
        sys.unraisablehook = _original_unraisablehook

    _installed = False
    print("Safedump uninstalled.", file=sys.stderr)


def is_installed() -> bool:
    """Check if Safedump crash hooks are currently active."""
    return _installed


def capture_exception(
    exc: BaseException | None = None,
    *,
    privacy_tier: int | None = None,
    output_dir: str | Path | None = None,
) -> Path | None:
    """Capture an exception and write a crash report.

    Use inside except blocks to manually capture exception context.
    If no exception is provided, captures the currently handled
    exception via sys.exc_info().

    Overrides apply to this capture only. The global configuration is not
    modified, so concurrent captures in other threads are unaffected.

    Args:
        exc: The exception to capture. If None, uses sys.exc_info().
        privacy_tier: Override the configured privacy tier for this capture.
        output_dir: Override the configured output directory for this capture.

    Returns:
        Path to the written crash report, or None if the write failed.

    Raises:
        RuntimeError: If no exception is available and none was provided.
        ValueError: If ``privacy_tier`` is outside 0-4.
    """
    if exc is None:
        exc = sys.exc_info()[1]
    if exc is None:
        raise RuntimeError("No exception to capture")

    config = get_config()
    overrides: dict[str, Any] = {}
    if privacy_tier is not None:
        overrides["privacy_tier"] = privacy_tier
    if output_dir is not None:
        overrides["output_dir"] = Path(output_dir).expanduser()
    if overrides:
        config = dataclasses.replace(config, **overrides)

    return _process(_build_report(exc, exc.__traceback__, config), config)


def test() -> Path | None:
    """Self-test: raise and capture an exception with the current configuration.

    Works whether or not the hooks are installed, so it can be used from the
    ``safedump test`` command to check that reports can be written.
    """
    try:
        raise RuntimeError("safedump self-test exception")
    except RuntimeError:
        return capture_exception()
