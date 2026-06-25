"""JSON serialization for Safedump crash reports.

Converts CrashReport objects to versioned JSON strings.
Runs in the crash-time hot path — must never raise.
"""

from __future__ import annotations

import json
from base64 import b64encode
from dataclasses import is_dataclass
from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum
from pathlib import Path, PurePath
from typing import Any
from uuid import UUID

from safedump._types import CrashReport, SafedumpConfig

# Sentinel for depth limit
DEPTH_LIMIT_SENTINEL = object()


class SafedumpEncoder(json.JSONEncoder):
    """Custom JSON encoder for Safedump crash reports.

    Handles Python types that stdlib json cannot encode natively.
    Never raises — all failures produce a marker object instead.
    """

    def __init__(self, config: SafedumpConfig, **kwargs: Any):
        super().__init__(**kwargs)
        self._config = config
        self._seen: set[int] = set()  # object id tracking for cycle detection
        self._depth: int = 0

    def default(self, o: Any) -> Any:
        """Route objects to type-specific handlers."""
        try:
            self._depth += 1
            if self._depth > self._config.max_depth:
                return {"__depth_limit__": True}

            obj_id = id(o)
            if obj_id in self._seen:
                return {"__circular_ref__": obj_id}
            self._seen.add(obj_id)

            result = self._encode(o)
        except Exception:
            result = {"__serialization_error__": type(o).__name__}
        finally:
            self._depth -= 1

        return result

    def _encode(self, obj: Any) -> Any:
        """Type-specific encoding dispatch."""
        # Primitives — handled by base encoder
        if isinstance(obj, (str, int, float, bool, type(None))):
            return obj

        # datetime family
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, date):
            return obj.isoformat()
        if isinstance(obj, time):
            return obj.isoformat()

        # Standard library types
        if isinstance(obj, Decimal):
            return str(obj)
        if isinstance(obj, UUID):
            return str(obj)
        if isinstance(obj, (Path, PurePath)):
            return str(obj)
        if isinstance(obj, bytes):
            return b64encode(obj).decode("ascii")
        if isinstance(obj, bytearray):
            return b64encode(bytes(obj)).decode("ascii")
        if isinstance(obj, Enum):
            return {"__enum__": type(obj).__name__, "name": obj.name, "value": obj.value}

        # Collections
        if isinstance(obj, set):
            return self._truncate_list(sorted(obj, key=str))
        if isinstance(obj, frozenset):
            return self._truncate_list(sorted(obj, key=str))
        if isinstance(obj, tuple):
            return self._truncate_list(list(obj))
        if isinstance(obj, list):
            return self._truncate_list(obj)
        if isinstance(obj, dict):
            return self._truncate_dict(obj)

        # Dataclasses
        if is_dataclass(obj) and not isinstance(obj, type):
            return self._encode_dataclass(obj)

        # Fallback — safe string representation
        try:
            s = str(obj)
            if len(s) > self._config.max_string_length:
                s = s[: self._config.max_string_length] + "..."
            return s
        except Exception:
            return f"<{type(obj).__name__}>"

    def _truncate_list(self, lst: list[Any]) -> list[Any]:
        """Truncate list to configured max items."""
        limit = self._config.max_collection_items
        if len(lst) > limit:
            truncated = lst[:limit]
            truncated.append(f"... ({len(lst) - limit} more items)")
            return truncated
        return lst

    def _truncate_dict(self, d: dict[str, Any]) -> dict[str, Any]:
        """Truncate dict values, respecting string length limits."""
        result: dict[str, Any] = {}
        count = 0
        limit = self._config.max_collection_items
        for key, value in d.items():
            if count >= limit:
                result["__truncated__"] = f"... ({len(d) - limit} more keys)"
                break
            # Truncate string values
            if isinstance(value, str) and len(value) > self._config.max_string_length:
                value = value[: self._config.max_string_length] + "..."
            result[key] = value
            count += 1
        return result

    def _encode_dataclass(self, obj: Any) -> dict[str, Any]:
        """Encode a dataclass instance as a dict."""
        result: dict[str, Any] = {"__type__": type(obj).__name__}
        for field_meta in type(obj).__dataclass_fields__.values():
            value = getattr(obj, field_meta.name)
            result[field_meta.name] = self.default(value)
        return result


def serialize(report: CrashReport, config: SafedumpConfig) -> str:
    """Convert a crash report to a versioned JSON string.

    Uses :class:`SafedumpEncoder` to handle Python types that stdlib
    JSON cannot encode. Never raises — all serialization failures
    produce marker objects (``__serialization_error__``, etc.).

    Args:
        report: The sanitized crash report to serialize.
        config: Active configuration with size/depth limits.

    Returns:
        Valid JSON string with a ``safedump_version`` field.
    """
    # Build the report payload
    payload: dict[str, Any] = {
        "safedump_version": report.safedump_version,
        "timestamp": report.timestamp,
        "python_version": report.python_version,
        "platform": report.platform,
        "exception": _serialize_exception(report.exception),
        "frames": [_serialize_frame(f) for f in report.frames],
        "environment": _serialize_environment(report.environment),
        "threads": [_serialize_thread(t) for t in report.threads],
        "redactions": [
            {"location": r.location, "reason": r.reason, "rule": r.rule, "timestamp": r.timestamp}
            for r in report.redactions
        ],
        "metadata": report.metadata,
    }

    encoder = SafedumpEncoder(config, indent=2, sort_keys=False, ensure_ascii=False)

    try:
        return encoder.encode(payload)
    except Exception:
        # Absolute last resort — a minimal valid JSON
        return json.dumps(
            {
                "safedump_version": report.safedump_version,
                "error": "serialization failed",
                "exception_type": report.exception.type,
                "exception_message": report.exception.message,
            }
        )


def _serialize_exception(exc: Any) -> dict[str, Any]:
    """Serialize an ExceptionSnapshot or similar to a dict."""
    return {
        "type": getattr(exc, "type", ""),
        "message": getattr(exc, "message", ""),
        "module": getattr(exc, "module", ""),
        "is_explicitly_chained": getattr(exc, "is_explicitly_chained", False),
        "sub_exceptions": [
            _serialize_exception(sub) for sub in getattr(exc, "sub_exceptions", [])
        ],
    }


def _serialize_frame(frame: Any) -> dict[str, Any]:
    """Serialize a FrameSnapshot to a dict."""
    locals_dict: dict[str, Any] = {}
    for name, var in getattr(frame, "locals", {}).items():
        locals_dict[name] = {
            "type": getattr(var, "type", "unknown"),
            "value": getattr(var, "value", None),
            "is_truncated": getattr(var, "is_truncated", False),
        }

    return {
        "index": getattr(frame, "index", -1),
        "file": getattr(frame, "file", ""),
        "line": getattr(frame, "line", 0),
        "function": getattr(frame, "function", ""),
        "code_context": getattr(frame, "code_context", []),
        "locals": locals_dict,
        "is_crash_site": getattr(frame, "is_crash_site", False),
    }


def _serialize_environment(env: Any) -> dict[str, Any]:
    """Serialize an EnvironmentSnapshot to a dict."""
    return {
        "os_name": getattr(env, "os_name", ""),
        "os_version": getattr(env, "os_version", ""),
        "python_impl": getattr(env, "python_impl", ""),
        "python_path": getattr(env, "python_path", []),
        "cwd": getattr(env, "cwd", ""),
        "env_var_names": getattr(env, "env_var_names", []),
        "argv": getattr(env, "argv", None),
    }


def _serialize_thread(thread: Any) -> dict[str, Any]:
    """Serialize a ThreadSnapshot to a dict."""
    return {
        "name": getattr(thread, "name", ""),
        "ident": getattr(thread, "ident", None),
        "daemon": getattr(thread, "daemon", False),
        "crashed": getattr(thread, "crashed", False),
    }
