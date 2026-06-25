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

__version__ = "0.1.0"

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
    "test",
    "uninstall",
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
from safedump._types import RedactionRule

# All public functions are placeholders — implementation begins in M1.
# They exist so the package imports successfully and IDEs show completions.


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
) -> None:
    """Configure Safedump globally. Call before :func:`install`.

    All parameters are keyword-only. Validates eagerly.
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
    """Load a Safedump crash report as a Python dict."""
    return _load_report(path)
