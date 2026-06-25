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

__version__ = "0.1.0.dev0"

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
from typing import Any, NamedTuple


class RedactionRule(NamedTuple):
    """A custom secret redaction rule.

    Args:
        pattern: Regex pattern to match.
        replacement: Text to replace matches with. Defaults to ``[REDACTED]``.
        apply_to: Where to apply the rule — ``"values"``, ``"names"``, or ``"both"``.
    """

    pattern: str
    replacement: str = "[REDACTED]"
    apply_to: str = "values"


# All public functions are placeholders — implementation begins in M1.
# They exist so the package imports successfully and IDEs show completions.


def configure(
    *,
    output_dir: str | Path = "~/.safedump",
    privacy_tier: int = 1,
    include_env_names: bool = True,
    include_argv: bool = False,
    max_string_length: int = 10000,
    max_collection_items: int = 100,
    max_depth: int = 5,
    redaction_rules: list[str | RedactionRule] | None = None,
    before_capture: Any = None,
) -> None:
    """Configure Safedump globally. Call before :func:`install`.

    All parameters are keyword-only. Validates eagerly.
    """
    raise NotImplementedError("safedump is not yet implemented")


def install() -> None:
    """Install Safedump crash hooks.

    Replaces ``sys.excepthook``, ``threading.excepthook``, and
    ``sys.unraisablehook``.  Uses current configuration.
    """
    raise NotImplementedError("safedump is not yet implemented")


def uninstall() -> None:
    """Restore original Python exception hooks."""
    raise NotImplementedError("safedump is not yet implemented")


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
) -> Path:
    """Capture an exception and write a crash report.

    If *exc* is ``None``, captures ``sys.exc_info()`` — the currently
    handled exception.  Use inside ``except`` blocks.

    Returns:
        Path to the written crash report file.
    """
    raise NotImplementedError("safedump is not yet implemented")


def test() -> Path:
    """Self-test — verify Safedump is working correctly.

    Deliberately raises and captures a test exception.

    Returns:
        Path to the generated test report.

    Raises:
        RuntimeError: If Safedump is not installed.
    """
    raise NotImplementedError("safedump is not yet implemented")


def load_report(path: str | Path) -> dict[str, Any]:
    """Load a Safedump crash report as a Python dict.

    Returns:
        Parsed report with all fields. Schema is versioned —
        check ``report["safedump_version"]``.

    Raises:
        FileNotFoundError: If *path* does not exist.
        ValueError: If file is not valid Safedump JSON.
    """
    raise NotImplementedError("safedump is not yet implemented")
