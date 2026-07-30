"""
Safedump — Local-first crash diagnostics for Python.

Capture complete debugging context at crash time, redact secrets
automatically, and inspect crashes offline.

Quick start:
    import safedump
    safedump.install()  # Replace sys.excepthook

View crashes:
    $ safedump view      # latest crash report
    $ safedump list      # recent crashes
"""

# SPDX-FileCopyrightText: 2026 Muneer Alam
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

__version__ = "2.0.0"

# Public API — these are the only stable names.
# Everything else is private (_-prefixed modules) and may change.
__all__ = [
    "RedactionRule",
    "__version__",
    "capture_exception",
    "configure",
    "disable",
    "enable",
    "install",
    "load_report",
    "register_serializer",
    "test",
    "uninstall",
    "watch",
]

from pathlib import Path
from typing import Any, Callable

from safedump._capture import (
    capture_exception as _capture_exception,
)
from safedump._capture import (
    install as _install,
)
from safedump._capture import (
    test as _test,
)
from safedump._capture import (
    uninstall as _uninstall,
)
from safedump._config import configure as _configure
from safedump._loader import load_report as _load_report
from safedump._serialize import register_serializer as _register_serializer
from safedump._types import RedactionRule
from safedump.watch import _Watch
from safedump.watch import watch as _watch


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
    on_crash: Callable[[Path], Any] | None = None,
) -> None:
    """Configure Safedump globally. Call before :func:`install`.

    All parameters are keyword-only. Validates eagerly.

    Args:
        preset: Configuration preset (``\"production\"``, ``\"development\"``,
            ``\"debug\"``, ``\"minimal\"``). Overrides individual parameters.
        output_dir: Directory for crash report files. Default ``~/.safedump``.
        privacy_tier: Capture detail level 0-4. Higher captures more.
        include_env_names: Include environment variable names (not values).
        include_argv: Include command-line arguments in reports.
        max_string_length: Maximum length for captured string values.
        max_collection_items: Maximum items from collections.
        max_depth: Maximum depth for nested object serialization.
        redaction_rules: Additional redaction rules (strings or RedactionRule).
        before_capture: Callback invoked before report generation.
        enable_entropy_detection: Enable Shannon entropy-based secret detection.
        entropy_threshold: Entropy threshold in bits/char (default 4.5).
        compress: Write reports as gzip-compressed JSON (``.json.gz``).
        on_crash: Callable invoked with report path after each capture.
    """
    _configure(
        output_dir=output_dir,
        privacy_tier=privacy_tier,
        include_env_names=include_env_names,
        include_argv=include_argv,
        max_string_length=max_string_length,
        max_collection_items=max_collection_items,
        max_depth=max_depth,
        redaction_rules=redaction_rules,
        before_capture=before_capture,
        enable_entropy_detection=enable_entropy_detection,
        entropy_threshold=entropy_threshold,
        compress=compress,
        on_crash=on_crash,
    )


def install() -> None:
    """Install Safedump crash hooks.

    Replaces ``sys.excepthook``, ``threading.excepthook``, and
    ``sys.unraisablehook``.  Uses current configuration.
    """
    _install()


def uninstall() -> None:
    """Restore original Python exception hooks."""
    _uninstall()


def enable() -> None:
    """Alias for :func:`install`."""
    install()


def disable() -> None:
    """Alias for :func:`uninstall`."""
    uninstall()


def capture_exception(
    exc: BaseException | None = None,
    *,
    privacy_tier: int | None = None,
    output_dir: str | Path | None = None,
) -> Path | None:
    """Capture an exception and write a crash report.

    If *exc* is ``None``, captures ``sys.exc_info()`` — the currently
    handled exception.  Use inside ``except`` blocks.

    Returns:
        Path to the written crash report file.
    """
    return _capture_exception(
        exc=exc,
        privacy_tier=privacy_tier,
        output_dir=output_dir,
    )


def watch(
    *,
    privacy_tier: int | None = None,
    output_dir: str | Path | None = None,
) -> _Watch:
    """Return a context manager for scoped crash monitoring.

    Unlike :func:`install`, this does not install global exception
    hooks — it only captures exceptions raised within the ``with``
    block and re-raises them.

    Example:
        >>> with safedump.watch():
        ...     dangerous_code()
    """
    return _watch(privacy_tier=privacy_tier, output_dir=output_dir)


def test() -> Path | None:
    """Self-test — verify Safedump is working correctly.

    Deliberately raises and captures a test exception.

    Returns:
        Path to the generated test report.

    Raises:
        RuntimeError: If Safedump is not installed.
    """
    return _test()


def load_report(path: str | Path) -> dict[str, Any]:
    """Load a Safedump crash report as a Python dict.

    Supports both ``.safedump.json`` and ``.safedump.json.gz`` files.
    Gzip files are transparently decompressed on read.

    Args:
        path: Path to a crash report file.

    Returns:
        Parsed report dict with all fields migrated to the current
        schema version.

    Raises:
        FileNotFoundError: If *path* does not exist.
        ValueError: If the file is not a valid Safedump report.
    """
    return _load_report(path)


def register_serializer(type_: type, handler: Any) -> None:
    """Register a custom serializer for a Python type.

    Args:
        type_: The Python type to handle (e.g., ``numpy.ndarray``).
        handler: A callable that takes an instance of ``type_``
                 and returns a JSON-serializable value.

    Example:
        >>> import numpy as np
        >>> safedump.register_serializer(np.ndarray, lambda a: a.tolist())
    """
    _register_serializer(type_, handler)
