"""Configuration storage and validation for Safedump.

Provides module-level configuration with thread-safe access.
This is a private module — use the public ``configure()`` in
``safedump.__init__`` instead of importing this directly.
"""

# SPDX-FileCopyrightText: 2026 Muneer Alam
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any, Callable

from safedump._types import RedactionRule, SafedumpConfig

# Module-level state
_active_config: SafedumpConfig | None = None
_config_lock = threading.Lock()
_original_config: SafedumpConfig | None = None  # saved for uninstall


def configure(
    *,
    preset: str | None = None,
    output_dir: str | Path = "~/.safedump",
    privacy_tier: int = 1,
    include_env_names: bool = True,
    include_argv: bool = False,
    max_string_length: int = 10000,
    max_collection_items: int = 100,
    max_depth: int = 5,
    redaction_rules: list[str | RedactionRule] | None = None,
    before_capture: Callable[[Any], Any | None] | None = None,
    enable_entropy_detection: bool = False,
    entropy_threshold: float = 4.5,
    compress: bool = False,
) -> None:
    """Configure Safedump globally.

    All parameters are keyword-only. Validates eagerly: invalid
    values raise ValueError immediately. Safe to call multiple times;
    each call replaces the previous configuration.

    Call before install().

    Args:
        preset: Configuration preset.
        output_dir: Directory for crash report files.
        privacy_tier: Capture detail level (0-4).
        include_env_names: Include environment variable names.
        include_argv: Include command-line arguments.
        max_string_length: Maximum length for captured string values.
        max_collection_items: Maximum items from lists/dicts/sets.
        max_depth: Maximum depth for nested object traversal.
        redaction_rules: Additional redaction rules.
        before_capture: Callback invoked before report generation.
        enable_entropy_detection: Enable Shannon entropy-based detection.
        entropy_threshold: Entropy threshold (bits/char, default 4.5).
        compress: Write crash reports as gzip-compressed JSON files.

    Raises:
        ValueError: If preset is unknown or parameter validation fails.
    """
    # Apply preset if specified
    if preset is not None:
        if preset not in PRESETS:
            raise ValueError(f"Unknown preset: '{preset}'. Available: {', '.join(sorted(PRESETS))}")
        p = PRESETS[preset]
        privacy_tier = int(p["privacy_tier"])
        include_env_names = bool(p["include_env_names"])
        include_argv = bool(p["include_argv"])
        max_depth = int(p["max_depth"])

    # Auto-convert string rules to RedactionRule objects
    resolved_rules: list[RedactionRule] = []
    if redaction_rules:
        for rule in redaction_rules:
            if isinstance(rule, str):
                resolved_rules.append(RedactionRule(pattern=rule))
            else:
                resolved_rules.append(rule)

    # Expand user home directory in path
    resolved_output_dir = Path(output_dir).expanduser().resolve()

    config = SafedumpConfig(
        output_dir=resolved_output_dir,
        privacy_tier=privacy_tier,
        include_env_names=include_env_names,
        include_argv=include_argv,
        max_string_length=max_string_length,
        max_collection_items=max_collection_items,
        max_depth=max_depth,
        redaction_rules=resolved_rules,
        before_capture=before_capture,
        enable_entropy_detection=enable_entropy_detection,
        entropy_threshold=entropy_threshold,
        compress=compress,
    )
    # Validation happens in SafedumpConfig.__post_init__

    with _config_lock:
        global _active_config
        _active_config = config


def get_config() -> SafedumpConfig:
    """Return the current active configuration.

    If :func:`configure` has never been called, returns a default
    ``SafedumpConfig``.  The returned object is the live config
    reference — do not mutate it.
    """
    global _active_config
    if _active_config is not None:
        return _active_config
    # Create and cache a default config on first access
    with _config_lock:
        if _active_config is None:  # double-check under lock
            _active_config = SafedumpConfig()
    return _active_config


def reset_config() -> None:
    """Reset configuration to defaults.

    Intended for testing.  After calling this, the next call to
    :func:`get_config` returns a fresh default ``SafedumpConfig``.
    """
    global _active_config
    with _config_lock:
        _active_config = None


def save_original_config() -> None:
    """Save the current config before install (so uninstall can restore it)."""
    global _original_config
    _original_config = get_config()


def restore_original_config() -> None:
    """Restore the config saved by :func:`save_original_config`."""
    global _active_config
    if _original_config is not None:
        _active_config = _original_config


PRESETS = {
    "production": {
        "privacy_tier": 1,
        "include_env_names": False,
        "include_argv": False,
        "max_depth": 5,
    },
    "development": {
        "privacy_tier": 2,
        "include_env_names": True,
        "include_argv": False,
        "max_depth": 10,
    },
    "debug": {
        "privacy_tier": 4,
        "include_env_names": True,
        "include_argv": True,
        "max_depth": 50,
    },
    "minimal": {
        "privacy_tier": 0,
        "include_env_names": False,
        "include_argv": False,
        "max_depth": 3,
    },
}
