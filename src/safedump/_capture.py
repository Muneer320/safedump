"""Crash capture engine for Safedump.

Orchestrates the capture -> sanitize -> serialize -> persist pipeline.
This module runs inside exception hooks -- it must never fail
and must always preserve the original traceback.

Frame walking, data capture, and hook management were split into
_frame_walker.py and _hook_manager.py respectively.
"""

# SPDX-FileCopyrightText: 2026 Muneer Alam
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

import sys
import threading
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from safedump._config import get_config, save_original_config
from safedump._frame_walker import (
    MAX_FRAMES,
    capture_environment,
    capture_exception_chain,
    capture_frame,
    capture_threads,
    compute_fingerprint,
    walk_traceback,
)
from safedump._sanitize import sanitize
from safedump._serialize import serialize
from safedump._storage import save
from safedump._types import CrashReport

# Pre-allocated fallback buffer for MemoryError scenarios
_fallback_buffer: bytearray | None = None
# Saved original exception hooks for uninstall
_original_excepthook: Any = None
_original_threading_excepthook: Any = None
_original_unraisablehook: Any = None
# Install state
_installed: bool = False


def crash_handler(
    exc_type: type[BaseException],
    exc_value: BaseException,
    exc_tb: Any,
) -> None:
    """Exception hook -- called by Python when an unhandled crash occurs.

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
            exception=capture_exception_chain(exc_value),
            environment=capture_environment(config),
            threads=capture_threads(),
        )

        # Walk frames
        frames = walk_traceback(exc_tb)
        for i, (frame, lineno) in enumerate(frames):
            if i >= MAX_FRAMES:
                break
            fs = capture_frame(frame, lineno, i, config)
            report.frames.append(fs)

        # Compute fingerprint after frames are populated
        report.fingerprint = compute_fingerprint(report)
        now_iso = report.timestamp
        report.first_seen = now_iso
        report.last_seen = now_iso

        # Apply before_capture hook
        if config.before_capture is not None:
            try:
                result = config.before_capture(report)
                if result is not None:
                    report = result
            except Exception:
                pass

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
        print(f"Safedump internal error: {e}", file=sys.stderr)

    finally:
        try:
            traceback.print_exception(saved_type, saved_value, saved_tb)
        except Exception:
            print(f"{saved_type.__name__}: {saved_value}", file=sys.stderr)


def install() -> None:
    """Install Safedump crash hooks globally.

    Replaces sys.excepthook, threading.excepthook, and
    sys.unraisablehook with the Safedump crash handler.
    Uses the current configuration set via configure().

    Safe to call multiple times. Subsequent calls are no-ops.
    """
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

    if _fallback_buffer is None:
        _fallback_buffer = bytearray(1_048_576)

    _installed = True
    print(f"Safedump installed. Crash reports -> {get_config().output_dir}", file=sys.stderr)


def uninstall() -> None:
    """Restore original Python exception hooks.

    Reverses install() by restoring sys.excepthook, threading.excepthook,
    and sys.unraisablehook to their original values.

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
    """Check if Safedump crash hooks are currently active.

    Returns:
        True if install() has been called and uninstall() has not.
    """
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

    Args:
        exc: The exception to capture. If None, uses sys.exc_info().
        privacy_tier: Override the configured privacy tier for this capture.
        output_dir: Override the configured output directory for this capture.

    Returns:
        Path to the written crash report, or None if the write failed.

    Raises:
        RuntimeError: If no exception is available and none was provided.
    """
    if exc is None:
        exc = sys.exc_info()[1]
    if exc is None:
        raise RuntimeError("No exception to capture")

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
            exception=capture_exception_chain(exc),
            environment=capture_environment(config),
            threads=capture_threads(),
        )

        if tb is not None:
            frames = walk_traceback(tb)
            for i, (frame, lineno) in enumerate(frames):
                if i >= config.max_depth:
                    break
                report.frames.append(capture_frame(frame, lineno, i, config))

        report.fingerprint = compute_fingerprint(report)
        now_iso = report.timestamp
        report.first_seen = now_iso
        report.last_seen = now_iso

        report = sanitize(report, config)
        json_str = serialize(report, config)
        return save(json_str, config, report)
    finally:
        config.privacy_tier = saved_tier
        config.output_dir = saved_dir


def test() -> Path | None:
    """Self-test -- verify Safedump is working."""
    if not _installed:
        raise RuntimeError("safedump is not installed. Call safedump.install() first.")

    try:
        raise RuntimeError("safedump self-test exception")
    except RuntimeError:
        return capture_exception()
