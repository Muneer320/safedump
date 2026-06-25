"""Secret detection and data sanitization for Safedump.

Applies redaction rules to crash reports before serialization.
Runs in the crash-time hot path — must never raise.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from safedump._types import (
    CrashReport,
    RedactionRecord,
    SafedumpConfig,
    is_denylisted,
)


def _detect_secret(value: str, patterns: list[str]) -> str | None:
    """Check a string value against regex secret patterns.

    Returns the matching pattern if found, ``None`` otherwise.
    Never raises — invalid patterns are silently skipped.
    """
    for pattern in patterns:
        try:
            if re.search(pattern, value):
                return pattern
        except re.error:
            continue
    return None


def _is_string(value: Any) -> bool:
    """Check if value is a string (str only, not bytes)."""
    return isinstance(value, str)


def _redact_value(original: Any) -> str:
    """Replace a redacted value with a safe marker."""
    return "[REDACTED]"


def _make_record(
    location: str,
    reason: str,
    rule: str,
) -> RedactionRecord:
    """Create a redaction audit record."""
    return RedactionRecord(
        location=location,
        reason=reason,
        rule=rule,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def _sanitize_dict(
    d: dict[str, Any],
    path_prefix: str,
    config: SafedumpConfig,
    redactions: list[RedactionRecord],
) -> None:
    """Recursively sanitize a dictionary in-place.

    Handles both plain values and VariableSnapshot objects
    (which have a ``.value`` attribute).
    """
    for key in list(d.keys()):
        current_path = f"{path_prefix}.{key}"
        entry = d[key]

        # Check variable name against denylist
        if is_denylisted(key):
            _apply_redaction(
                entry,
                current_path,
                "matched denylist: '{key}'",
                "variable_name_denylist",
                redactions,
            )
            continue

        # Check string values against regex patterns
        if _is_string(entry):
            matched = _detect_secret(entry, config.secret_patterns)
            if matched:
                d[key] = _redact_value(entry)
                redactions.append(
                    _make_record(
                        current_path,
                        f"matched pattern: {matched}",
                        "secret_pattern",
                    )
                )

        # Handle VariableSnapshot objects
        elif hasattr(entry, "value") and hasattr(entry, "name"):
            _sanitize_variable(entry, current_path, config, redactions)

        # Recurse into nested dicts
        elif isinstance(entry, dict):
            _sanitize_dict(entry, current_path, config, redactions)

        # Recurse into lists
        elif isinstance(entry, list):
            for i, item in enumerate(entry):
                if _is_string(item):
                    matched = _detect_secret(item, config.secret_patterns)
                    if matched:
                        entry[i] = _redact_value(item)
                        redactions.append(
                            _make_record(
                                f"{current_path}[{i}]",
                                f"matched pattern: {matched}",
                                "secret_pattern",
                            )
                        )
                elif isinstance(item, dict):
                    _sanitize_dict(item, f"{current_path}[{i}]", config, redactions)

        # Apply custom user rules to string values
        _apply_custom_rules(entry, key, current_path, config, redactions)


def _sanitize_variable(
    var: Any,
    path: str,
    config: SafedumpConfig,
    redactions: list[RedactionRecord],
) -> None:
    """Sanitize a single variable (name + value pair)."""
    # Check name
    if is_denylisted(var.name):
        var.value = _redact_value(var.value)
        redactions.append(
            _make_record(
                path,
                f"matched denylist: '{var.name}'",
                "variable_name_denylist",
            )
        )
        return

    # Check value if it's a string
    raw_value = var.value
    if _is_string(raw_value):
        matched = _detect_secret(raw_value, config.secret_patterns)
        if matched:
            var.value = _redact_value(raw_value)
            redactions.append(
                _make_record(
                    path,
                    f"matched pattern: {matched}",
                    "secret_pattern",
                )
            )


def _apply_redaction(
    entry: Any,
    path: str,
    reason: str,
    rule: str,
    redactions: list[RedactionRecord],
) -> None:
    """Apply redaction to an entry, handling both plain values and objects."""
    if hasattr(entry, "value"):
        entry.value = _redact_value(entry.value)
    # For plain values, the caller has already replaced d[key]
    redactions.append(_make_record(path, reason, rule))


def _apply_custom_rules(
    entry: Any,
    key: str,
    path: str,
    config: SafedumpConfig,
    redactions: list[RedactionRecord],
) -> None:
    """Apply user-defined custom redaction rules."""
    raw_value = getattr(entry, "value", entry)
    if not _is_string(raw_value):
        return

    for rule in config.redaction_rules:
        try:
            if re.search(rule.pattern, raw_value):
                replacement = re.sub(rule.pattern, rule.replacement, raw_value)
                if hasattr(entry, "value"):
                    entry.value = replacement
                redactions.append(
                    _make_record(
                        path,
                        f"matched custom rule: {rule.pattern}",
                        "custom_rule",
                    )
                )
                break  # one redaction per value
        except re.error:
            continue


def sanitize(
    report: CrashReport,
    config: SafedumpConfig,
) -> CrashReport:
    """Apply redaction rules to a crash report.

    Walks the report's variable names and string values, applying
    denylist matching, regex secret detection, and custom user rules.
    Every redaction is recorded in ``report.redactions``.

    Returns the same report object (modified in-place).  Never raises —
    all operations are wrapped and failures are recorded as redactions
    with reason ``"sanitization_error"``.

    Args:
        report: The captured crash report to sanitize.
        config: Active configuration with redaction rules.

    Returns:
        The sanitized report (same object).
    """
    try:
        # Sanitize frame locals (primary target)
        for frame in report.frames:
            _sanitize_dict(
                frame.locals,
                f"frames[{frame.index}].locals",
                config,
                report.redactions,
            )

        # Sanitize environment strings
        env = report.environment
        env_dict = {
            "cwd": env.cwd,
            "os_name": env.os_name,
            "os_version": env.os_version,
            "python_impl": env.python_impl,
        }
        _sanitize_dict(env_dict, "environment", config, report.redactions)

        # Sanitize env var names if present
        if env.env_var_names:
            for name in list(env.env_var_names):
                if is_denylisted(name):
                    env.env_var_names.remove(name)
                    report.redactions.append(
                        _make_record(
                            "environment.env_var_names",
                            f"removed denylisted name: '{name}'",
                            "variable_name_denylist",
                        )
                    )

        # Sanitize argv if present
        if env.argv:
            for i, arg in enumerate(env.argv):
                if _is_string(arg):
                    matched = _detect_secret(arg, config.secret_patterns)
                    if matched:
                        env.argv[i] = _redact_value(arg)
                        report.redactions.append(
                            _make_record(
                                f"environment.argv[{i}]",
                                f"matched pattern: {matched}",
                                "secret_pattern",
                            )
                        )

        # Sanitize exception messages
        exc = report.exception
        exc_dict: dict[str, Any] = {"message": exc.message, "type": exc.type}
        _sanitize_dict(exc_dict, "exception", config, report.redactions)
        exc.message = exc_dict["message"]
        exc.type = exc_dict["type"]

        # Sanitize sub-exceptions recursively
        _sanitize_exception_chain(exc, config, report.redactions)

        # Sanitize thread names
        for thread in report.threads:
            if is_denylisted(thread.name):
                thread.name = _redact_value(thread.name)
                report.redactions.append(
                    _make_record(
                        f"threads[{thread.ident}].name",
                        f"matched denylist: '{thread.name}'",
                        "variable_name_denylist",
                    )
                )

    except Exception as e:
        # Never let sanitization failure prevent report generation
        report.redactions.append(
            _make_record(
                "sanitize",
                f"sanitization error: {e}",
                "sanitization_error",
            )
        )

    return report


def _sanitize_exception_chain(
    exc: Any,
    config: SafedumpConfig,
    redactions: list[RedactionRecord],
    depth: int = 0,
) -> None:
    """Recursively sanitize exception chains."""
    if depth > 10:  # safety limit
        return

    for sub in getattr(exc, "sub_exceptions", []):
        sub_dict = {"message": getattr(sub, "message", ""), "type": getattr(sub, "type", "")}
        _sanitize_dict(sub_dict, f"exception.sub[{depth}]", config, redactions)
        # Write back
        try:
            sub.message = sub_dict["message"]
            sub.type = sub_dict["type"]
        except (AttributeError, TypeError):
            pass
        _sanitize_exception_chain(sub, config, redactions, depth + 1)
