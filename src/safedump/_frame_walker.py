"""Frame walking and data capture utilities for Safedump.

Handles traceback walking, turning frame locals into JSON-safe snapshots,
environment capture and exception chain parsing. These run inside exception
hooks: they must never raise and must always preserve the original traceback.
"""

# SPDX-FileCopyrightText: 2026 Muneer Alam
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

import contextlib
import hashlib
import linecache
import math
import os
import reprlib
import sys
import threading
import traceback
import types
from base64 import b64encode
from dataclasses import fields, is_dataclass
from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum
from pathlib import PurePath
from typing import Any
from uuid import UUID

from safedump._types import (
    CrashReport,
    EnvironmentSnapshot,
    ExceptionSnapshot,
    FrameSnapshot,
    SafedumpConfig,
    ThreadSnapshot,
    VariableSnapshot,
)

# Maximum stack frames to capture (unrelated to max_depth, which limits how deep
# nested values are expanded). When a traceback is deeper, the innermost frames
# are kept, because that is where the crash happened.
MAX_FRAMES: int = 100

# Strings are captured slightly longer than max_string_length. Redaction runs on
# the captured value and truncation to the configured limit happens afterwards,
# so a secret that straddles the cut-off is still seen whole by the patterns.
REDACTION_SLACK: int = 512


def crash_site(report: CrashReport) -> FrameSnapshot | None:
    """The frame where the exception was raised (the innermost one)."""
    for frame in reversed(report.frames):
        if frame.is_crash_site:
            return frame
    return report.frames[-1] if report.frames else None


def compute_fingerprint(report: CrashReport) -> str:
    """Generate a stable, deterministic fingerprint for a crash report.

    Based on exception type, message, and crash site (file + line).
    Same crash in the same location always produces the same fingerprint.

    Returns a 12-character hex string.
    """
    digest = hashlib.sha256()
    digest.update(report.exception.type.encode("utf-8"))
    digest.update(report.exception.message.encode("utf-8")[:200])
    site = crash_site(report)
    if site is not None:
        digest.update(site.file.encode("utf-8"))
        digest.update(str(site.line).encode("utf-8"))
    return digest.hexdigest()[:12]


def _make_repr(max_chars: int) -> reprlib.Repr:
    r = reprlib.Repr()
    r.maxstring = max_chars
    r.maxother = max_chars
    r.maxlong = max_chars
    r.maxlist = r.maxtuple = r.maxset = r.maxfrozenset = r.maxdeque = r.maxarray = 20
    r.maxdict = 20
    r.maxlevel = 3
    return r


def safe_repr(obj: Any, max_chars: int = 500) -> str:
    """Safely convert an object to its string representation.

    Uses a ``reprlib.Repr`` sized to ``max_chars``, catches anything an
    object's ``__repr__`` can raise, and falls back to ``<ClassName>``.
    Never raises.
    """
    try:
        result = _make_repr(max_chars).repr(obj)
        if len(result) > max_chars:
            result = result[:max_chars] + "..."
        return result
    except BaseException:
        try:
            return f"<{type(obj).__name__}>"
        except BaseException:
            return "<unknown>"


def snapshot_value(
    obj: Any, config: SafedumpConfig, *, _depth: int = 0, _active: set[int] | None = None
) -> Any:
    """Turn any Python value into a JSON-safe structure, within the configured limits.

    - Primitives are kept as-is (non-finite floats become strings).
    - Strings are kept up to ``max_string_length`` plus a small redaction slack;
      final truncation happens after secrets have been redacted.
    - Lists, tuples, sets and dicts are expanded up to ``max_depth`` levels and
      ``max_collection_items`` entries.
    - Types registered with :func:`safedump.register_serializer` use their handler.
    - At privacy tier 2+, objects are expanded into their attributes.
    - Anything else becomes a safe ``repr``.

    Never raises.
    """
    try:
        return _snapshot(obj, config, _depth, _active if _active is not None else set())
    except BaseException:
        try:
            return f"<{type(obj).__name__}>"
        except BaseException:
            return "<unknown>"


def _snapshot(obj: Any, config: SafedumpConfig, depth: int, active: set[int]) -> Any:
    from safedump._serialize import _serializer_registry  # avoid an import cycle

    limit = config.max_string_length + REDACTION_SLACK
    items = config.max_collection_items

    if obj is None or isinstance(obj, int):  # includes bool
        return obj
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else repr(obj)
    if isinstance(obj, str):
        return obj[:limit]

    handler = _serializer_registry.get(type(obj))
    if handler is not None:
        try:
            return _snapshot(handler(obj), config, depth, active)
        except Exception:
            return {"__serialization_error__": type(obj).__name__}

    if isinstance(obj, (datetime, date, time)):
        return obj.isoformat()
    if isinstance(obj, (Decimal, UUID, PurePath)):
        return str(obj)
    if isinstance(obj, (bytes, bytearray)):
        data = bytes(obj[: config.max_string_length])
        return {"__bytes__": len(obj), "base64": b64encode(data).decode("ascii")}
    if isinstance(obj, Enum):
        return {
            "__enum__": type(obj).__name__,
            "name": obj.name,
            "value": safe_repr(obj.value, 200),
        }
    if isinstance(obj, (types.ModuleType, types.FunctionType, types.BuiltinFunctionType, type)):
        return safe_repr(obj, 200)

    is_container = isinstance(obj, (list, tuple, set, frozenset, dict))
    expands_object = config.privacy_tier >= 2 and (is_dataclass(obj) or hasattr(obj, "__dict__"))
    if not (is_container or expands_object):
        return safe_repr(obj, limit)

    if id(obj) in active:
        return {"__circular_ref__": type(obj).__name__}
    if depth >= config.max_depth:
        return {"__depth_limit__": type(obj).__name__, "repr": safe_repr(obj, 200)}

    active.add(id(obj))
    try:
        if isinstance(obj, dict):
            result: dict[str, Any] = {}
            for count, (key, value) in enumerate(obj.items()):
                if count >= items:
                    result["__truncated__"] = f"... ({len(obj) - items} more keys)"
                    break
                result[key if isinstance(key, str) else safe_repr(key, 200)] = _snapshot(
                    value, config, depth + 1, active
                )
            return result
        if is_container:
            seq = list(obj)
            if isinstance(obj, (set, frozenset)):
                with contextlib.suppress(Exception):
                    seq = sorted(seq, key=repr)
            out = [_snapshot(v, config, depth + 1, active) for v in seq[:items]]
            if len(seq) > items:
                out.append(f"... ({len(seq) - items} more items)")
            return out

        # Object expansion (tier 2+): dataclass fields or instance __dict__
        attrs: dict[str, Any] = {"__type__": type(obj).__name__}
        if is_dataclass(obj):
            names = [f.name for f in fields(obj)]
        else:
            names = [n for n in vars(obj) if not (n.startswith("__") and n.endswith("__"))]
        for count, name in enumerate(names):
            if count >= items:
                attrs["__truncated__"] = f"... ({len(names) - items} more attributes)"
                break
            try:
                value = getattr(obj, name)
            except Exception:
                value = "<unreadable>"
            attrs[name] = _snapshot(value, config, depth + 1, active)
        return attrs
    finally:
        active.discard(id(obj))


def walk_traceback(tb: Any) -> list[tuple[Any, int]]:
    """Walk a traceback chain, returning (frame, lineno) pairs, outermost first."""
    frames: list[tuple[Any, int]] = []
    if hasattr(traceback, "walk_tb"):
        frames.extend(traceback.walk_tb(tb))
    else:
        while tb is not None:
            frames.append((tb.tb_frame, tb.tb_lineno))
            tb = tb.tb_next
    return frames


def _snapshot_namespace(
    namespace: dict[str, Any], config: SafedumpConfig, *, skip_code: bool
) -> dict[str, VariableSnapshot]:
    variables: dict[str, VariableSnapshot] = {}
    for name, value in namespace.items():
        if len(variables) >= config.max_collection_items:
            break
        if name.startswith("__") and name.endswith("__"):
            continue
        if skip_code and isinstance(value, (types.ModuleType, types.FunctionType, type)):
            continue
        variables[name] = VariableSnapshot(
            name=name,
            type=type(value).__name__,
            value=snapshot_value(value, config),
        )
    return variables


def capture_frame(
    frame: Any,
    lineno: int,
    index: int,
    config: SafedumpConfig,
    *,
    is_crash_site: bool = False,
) -> FrameSnapshot:
    """Capture a single stack frame's data according to the privacy tier.

    - Tier 0: location and source context only, no variable values.
    - Tier 1+: local variables.
    - Tier 3+: the crash-site frame also records module globals (excluding
      modules, functions and classes).
    """
    code = getattr(frame, "f_code", None)
    variables: dict[str, VariableSnapshot] = {}
    module_globals: dict[str, VariableSnapshot] = {}

    if config.privacy_tier >= 1:
        try:
            raw_locals = dict(frame.f_locals) if hasattr(frame, "f_locals") else {}
        except (ValueError, RuntimeError):
            raw_locals = {}
        variables = _snapshot_namespace(raw_locals, config, skip_code=False)

    if config.privacy_tier >= 3 and is_crash_site:
        with contextlib.suppress(Exception):
            module_globals = _snapshot_namespace(dict(frame.f_globals), config, skip_code=True)

    code_context: list[str] = []
    if code is not None:
        with contextlib.suppress(Exception):
            first_line = code.co_firstlineno
            for i in range(lineno - 3, lineno + 2):
                if i >= first_line:
                    line = linecache.getline(code.co_filename, i)
                    if line:
                        code_context.append(line.rstrip())

    return FrameSnapshot(
        index=index,
        file=(code and code.co_filename) or "<unknown>",
        line=lineno,
        function=(code and code.co_name) or "<unknown>",
        lineno=lineno,
        code_context=code_context,
        locals=variables,
        is_crash_site=is_crash_site,
        globals=module_globals,
    )


def capture_frames(tb: Any, config: SafedumpConfig) -> list[FrameSnapshot]:
    """Capture up to MAX_FRAMES frames, keeping the innermost ones. The last is the crash site."""
    pairs = walk_traceback(tb)[-MAX_FRAMES:]
    last = len(pairs) - 1
    return [
        capture_frame(frame, lineno, i, config, is_crash_site=(i == last))
        for i, (frame, lineno) in enumerate(pairs)
    ]


def capture_exception_chain(exc_value: BaseException, _depth: int = 0) -> ExceptionSnapshot:
    """Walk exception chain (__cause__, __context__, ExceptionGroup)."""
    snap = ExceptionSnapshot(
        type=type(exc_value).__name__,
        message=_safe_str(exc_value),
        module=type(exc_value).__module__,
        is_explicitly_chained=exc_value.__cause__ is not None,
    )
    if _depth > 20:
        return snap

    for sub in getattr(exc_value, "exceptions", ()) or ():
        if isinstance(sub, BaseException):
            snap.sub_exceptions.append(capture_exception_chain(sub, _depth + 1))

    if exc_value.__cause__ is not None and exc_value.__cause__ is not exc_value:
        snap.sub_exceptions.append(capture_exception_chain(exc_value.__cause__, _depth + 1))

    ctx = exc_value.__context__
    if ctx is not None and ctx is not exc_value and ctx is not exc_value.__cause__:
        snap.sub_exceptions.append(capture_exception_chain(ctx, _depth + 1))

    return snap


def _safe_str(exc: BaseException) -> str:
    try:
        return str(exc)
    except BaseException:
        return f"<unprintable {type(exc).__name__}>"


def capture_environment(config: SafedumpConfig) -> EnvironmentSnapshot:
    """Capture system environment data according to the privacy tier.

    - Tier 0: OS, interpreter and working directory only.
    - Tier 1+: env var names (if ``include_env_names``) and argv (if ``include_argv``).
    - Tier 4: env var values as well (secrets are redacted by the sanitizer).
    """
    env = EnvironmentSnapshot(
        os_name=os.name,
        os_version=sys.platform,
        python_impl=sys.implementation.name,
        python_path=[str(p) for p in sys.path],
        cwd=_safe_cwd(),
    )

    if config.privacy_tier >= 1:
        if config.include_env_names:
            with contextlib.suppress(Exception):
                env.env_var_names = sorted(os.environ.keys())
        if config.include_argv:
            env.argv = list(sys.argv)

    if config.privacy_tier >= 4:
        with contextlib.suppress(Exception):
            env.env_var_values = dict(os.environ)

    return env


def _safe_cwd() -> str:
    try:
        return os.getcwd()
    except OSError:
        return "<unavailable>"


def capture_threads(crashed: threading.Thread | None = None) -> list[ThreadSnapshot]:
    """Capture all thread information. ``crashed`` defaults to the current thread."""
    crashed = crashed or threading.current_thread()
    threads = [
        ThreadSnapshot(name=t.name, ident=t.ident, daemon=t.daemon, crashed=(t is crashed))
        for t in threading.enumerate()
    ]
    if crashed not in threading.enumerate():
        # A thread that crashed is already finishing; record it explicitly.
        threads.append(
            ThreadSnapshot(
                name=crashed.name, ident=crashed.ident, daemon=crashed.daemon, crashed=True
            )
        )
    threads.sort(key=lambda t: not t.crashed)
    return threads
