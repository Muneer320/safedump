"""Secret detection and data sanitization for Safedump.

Applies redaction rules to crash reports before serialization. Captured values
are structured (dicts, lists, strings), so redaction walks them recursively,
and every redaction is written back before it is recorded in the audit trail.

Runs in the crash-time hot path: must never raise.
"""

# SPDX-FileCopyrightText: 2026 Muneer Alam
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

import math
import re
from datetime import datetime, timezone
from typing import Any

from safedump._types import (
    CrashReport,
    RedactionRecord,
    SafedumpConfig,
    VariableSnapshot,
    is_denylisted,
)

REDACTED = "[REDACTED]"

# Env var names that look sensitive to the denylist (they contain "pwd") but
# only hold the working directory, which the report records anyway.
_SAFE_ENV_NAMES = {"PWD", "OLDPWD"}


def _detect_secret(value: str, patterns: list[str]) -> str | None:
    """Return the first secret pattern that matches ``value``, or ``None``."""
    for pattern in patterns:
        try:
            if re.search(pattern, value):
                return pattern
        except re.error:
            continue
    return None


def _compute_shannon_entropy(value: str) -> float:
    """Shannon entropy of a string in bits per character (0.0 to ~8.0 for text)."""
    if not value:
        return 0.0
    length = len(value)
    freq: dict[str, int] = {}
    for char in value:
        freq[char] = freq.get(char, 0) + 1
    entropy = -sum((count / length) * math.log2(count / length) for count in freq.values())
    return round(entropy, 2)


def _make_record(location: str, reason: str, rule: str) -> RedactionRecord:
    return RedactionRecord(
        location=location,
        reason=reason,
        rule=rule,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


class _Sanitizer:
    def __init__(self, config: SafedumpConfig, redactions: list[RedactionRecord]):
        self.config = config
        self.redactions = redactions
        self.patterns = config.secret_patterns
        self.value_rules = [r for r in config.redaction_rules if r.apply_to in ("values", "both")]
        self.name_rules = [r for r in config.redaction_rules if r.apply_to in ("names", "both")]

    def record(self, location: str, reason: str, rule: str) -> None:
        self.redactions.append(_make_record(location, reason, rule))

    # -- names -----------------------------------------------------------
    def name_is_sensitive(self, name: str, path: str) -> bool:
        if is_denylisted(name):
            self.record(path, f"matched denylist: '{name}'", "variable_name_denylist")
            return True
        for rule in self.name_rules:
            try:
                if re.search(rule.pattern, name):
                    self.record(path, f"name matched custom rule: {rule.pattern}", "custom_rule")
                    return True
            except re.error:
                continue
        return False

    # -- values ----------------------------------------------------------
    def scrub_string(self, value: str, path: str) -> str:
        for pattern in self.patterns:
            try:
                new_value, count = re.subn(pattern, REDACTED, value)
            except re.error:
                continue
            if count:
                value = new_value
                self.record(path, f"matched pattern: {pattern}", "secret_pattern")

        if (
            self.config.enable_entropy_detection
            and value != REDACTED
            and len(value) >= 16
            and not any(ch.isspace() for ch in value)
        ):
            entropy = _compute_shannon_entropy(value)
            if entropy > self.config.entropy_threshold:
                self.record(path, f"high entropy: {entropy}", "entropy_detection")
                return REDACTED

        for rule in self.value_rules:
            try:
                new_value, count = re.subn(rule.pattern, rule.replacement, value)
            except re.error:
                continue
            if count:
                value = new_value
                self.record(path, f"matched custom rule: {rule.pattern}", "custom_rule")
        return value

    def scrub(self, value: Any, path: str) -> Any:
        """Return a scrubbed copy of a JSON-like value."""
        if isinstance(value, str):
            return self.scrub_string(value, path)
        if isinstance(value, dict):
            result = {}
            for key, item in value.items():
                key_path = f"{path}.{key}"
                if (
                    isinstance(key, str)
                    and not key.startswith("__")
                    and self.name_is_sensitive(key, key_path)
                ):
                    result[key] = REDACTED
                else:
                    result[key] = self.scrub(item, key_path)
            return result
        if isinstance(value, list):
            return [self.scrub(item, f"{path}[{i}]") for i, item in enumerate(value)]
        return value

    def variables(self, variables: dict[str, VariableSnapshot], path: str) -> None:
        for name, var in variables.items():
            var_path = f"{path}.{name}"
            if self.name_is_sensitive(name, var_path):
                var.value = REDACTED
            else:
                var.value = self.scrub(var.value, var_path)

    def exception(self, exc: Any, path: str, depth: int = 0) -> None:
        if depth > 20:
            return
        exc.message = self.scrub_string(exc.message, f"{path}.message")
        for i, sub in enumerate(getattr(exc, "sub_exceptions", [])):
            self.exception(sub, f"{path}.sub_exceptions[{i}]", depth + 1)


def sanitize(report: CrashReport, config: SafedumpConfig) -> CrashReport:
    """Apply redaction rules to a crash report, in place.

    Covers frame locals and globals (including nested values), exception
    messages along the whole chain, environment data and thread names.
    Uses name denylists, secret patterns, optional entropy detection and
    custom rules. Every redaction is applied and then recorded in
    ``report.redactions``.

    Never raises. A failure is recorded as a ``sanitization_error`` redaction.
    """
    s = _Sanitizer(config, report.redactions)
    try:
        for frame in report.frames:
            s.variables(frame.locals, f"frames[{frame.index}].locals")
            s.variables(frame.globals, f"frames[{frame.index}].globals")

        s.exception(report.exception, "exception")

        env = report.environment
        env.cwd = s.scrub_string(env.cwd, "environment.cwd")
        env.python_path = [
            s.scrub_string(p, f"environment.python_path[{i}]")
            for i, p in enumerate(env.python_path)
        ]

        if env.env_var_names:
            kept = [n for n in env.env_var_names if n in _SAFE_ENV_NAMES or not is_denylisted(n)]
            removed = len(env.env_var_names) - len(kept)
            if removed:
                env.env_var_names = kept
                s.record(
                    "environment.env_var_names",
                    f"removed {removed} denylisted name(s)",
                    "variable_name_denylist",
                )

        if env.env_var_values:
            values = {}
            for name, value in env.env_var_values.items():
                path = f"environment.env_var_values.{name}"
                if name not in _SAFE_ENV_NAMES and s.name_is_sensitive(name, path):
                    values[name] = REDACTED
                else:
                    values[name] = s.scrub_string(str(value), path)
            env.env_var_values = values

        if env.argv:
            env.argv = [
                s.scrub_string(str(a), f"environment.argv[{i}]") for i, a in enumerate(env.argv)
            ]

        for thread in report.threads:
            if is_denylisted(thread.name):
                thread.name = REDACTED
                s.record(
                    f"threads[{thread.ident}].name",
                    "thread name matched denylist",
                    "variable_name_denylist",
                )

        if report.metadata:
            report.metadata = s.scrub(report.metadata, "metadata")

    except Exception as e:
        report.redactions.append(
            _make_record("sanitize", f"sanitization error: {e}", "sanitization_error")
        )

    return report
