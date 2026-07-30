"""Frame walking and data capture utilities for Safedump.

Handles traceback walking, frame local extraction, environment capture,
and exception chain parsing. These run inside exception hooks -- they
must never raise and must always preserve the original traceback.
"""

# SPDX-FileCopyrightText: 2026 Muneer Alam
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

import contextlib
import hashlib
import os
import reprlib
import sys
import threading
import traceback
from typing import Any

from safedump._types import (
    CrashReport,
    EnvironmentSnapshot,
    ExceptionSnapshot,
    FrameSnapshot,
    SafedumpConfig,
    ThreadSnapshot,
    VariableSnapshot,
)

# Maximum stack frames to capture (unrelated to max_depth, which controls
# nested object serialization depth). Set high enough to capture deep
# tracebacks including asyncio coroutine frames.
MAX_FRAMES: int = 100


def compute_fingerprint(report: CrashReport) -> str:
    """Generate a stable, deterministic fingerprint for a crash report.

    Based on exception type, message, and crash site (file + line).
    Same crash in the same location always produces the same fingerprint.

    Returns a 12-character hex string.
    """
    digest = hashlib.sha256()
    digest.update(report.exception.type.encode("utf-8"))
    digest.update(report.exception.message.encode("utf-8")[:200])
    if report.frames:
        first = report.frames[0]
        digest.update(first.file.encode("utf-8"))
        digest.update(str(first.line).encode("utf-8"))
    return digest.hexdigest()[:12]


def safe_repr(obj: Any, max_chars: int = 500) -> str:
    """Safely convert an object to its string representation.

    Three-layer defense (C2 resolution):
    1. ``reprlib.repr()`` with built-in recursion and length limits
    2. ``try/except BaseException`` catches anything that slips through
    3. Falls back to ``<ClassName>`` if all else fails

    Never raises. Never calls ``object.__repr__()`` directly.
    """
    try:
        result = reprlib.repr(obj)
        if len(result) > max_chars:
            result = result[:max_chars] + "..."
        return result
    except BaseException:
        try:
            return f"<{type(obj).__name__}>"
        except BaseException:
            return "<unknown>"


def walk_traceback(tb: Any) -> list[tuple[Any, int]]:
    """Walk a traceback chain, returning (frame, lineno) pairs.

    Uses ``traceback.walk_tb`` on Python 3.12+, manual iteration
    on older versions.
    """
    frames: list[tuple[Any, int]] = []
    if hasattr(traceback, "walk_tb"):
        frames.extend(traceback.walk_tb(tb))
    else:
        while tb is not None:
            frames.append((tb.tb_frame, tb.tb_lineno))
            tb = tb.tb_next
    return frames


def capture_frame(frame: Any, lineno: int, index: int, config: SafedumpConfig) -> FrameSnapshot:
    """Capture a single stack frame's data."""
    try:
        raw_locals = dict(frame.f_locals) if hasattr(frame, "f_locals") else {}
    except (ValueError, RuntimeError):
        raw_locals = {}

    variables: dict[str, VariableSnapshot] = {}
    count = 0
    for name, value in raw_locals.items():
        if count >= config.max_collection_items:
            break
        if name.startswith("__") and name.endswith("__"):
            continue
        var = VariableSnapshot(
            name=name,
            type=type(value).__name__,
            value=safe_repr(value, config.max_string_length),
        )
        variables[name] = var
        count += 1

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


def capture_exception_chain(exc_value: BaseException) -> ExceptionSnapshot:
    """Walk exception chain (__cause__, __context__, ExceptionGroup)."""
    snap = ExceptionSnapshot(
        type=type(exc_value).__name__,
        message=str(exc_value),
        module=type(exc_value).__module__,
        is_explicitly_chained=exc_value.__cause__ is not None,
    )

    sub_exceptions = getattr(exc_value, "exceptions", ())
    for sub in sub_exceptions:
        snap.sub_exceptions.append(capture_exception_chain(sub))

    if exc_value.__cause__ is not None and exc_value.__cause__ is not exc_value:
        snap.sub_exceptions.append(capture_exception_chain(exc_value.__cause__))

    ctx = exc_value.__context__
    if ctx is not None and ctx is not exc_value and ctx is not exc_value.__cause__:
        snap.sub_exceptions.append(capture_exception_chain(ctx))

    return snap


def capture_environment(config: SafedumpConfig) -> EnvironmentSnapshot:
    """Capture system environment data."""
    env = EnvironmentSnapshot(
        os_name=os.name,
        os_version=safe_repr(sys.platform),
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


def capture_threads() -> list[ThreadSnapshot]:
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
    threads.sort(key=lambda t: not t.crashed)
    return threads
