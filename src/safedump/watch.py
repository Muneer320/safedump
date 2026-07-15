"""Context manager API for scoped crash monitoring.

Provides ``watch()``, a lightweight alternative to :func:`safedump.install`
for cases where only a specific block of code needs crash capture, rather
than installing global exception hooks.
"""

# SPDX-FileCopyrightText: 2026 Muneer Alam
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

import sys
from pathlib import Path
from types import TracebackType
from typing import Literal

from safedump._capture import capture_exception


class _Watch:
    """Context manager returned by :func:`watch`.

    On ``__exit__`` with an active exception, captures it via
    :func:`safedump.capture_exception` and re-raises (returns ``False``).
    Never installs or touches ``sys.excepthook``.
    """

    def __init__(
        self,
        *,
        privacy_tier: int | None = None,
        output_dir: str | Path | None = None,
    ) -> None:
        self.privacy_tier = privacy_tier
        self.output_dir = output_dir
        self.report_path: Path | None = None

    def __enter__(self) -> _Watch:
        self.report_path = None
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> Literal[False]:
        if exc_value is None or not isinstance(exc_value, Exception):
            return False

        try:
            self.report_path = capture_exception(
                exc_value,
                privacy_tier=self.privacy_tier,
                output_dir=self.output_dir,
            )
        except Exception as e:
            # Never let capture itself mask the original exception.
            print(f"Safedump internal error: {e}", file=sys.stderr)

        return False  # propagate the original exception


def watch(
    *,
    privacy_tier: int | None = None,
    output_dir: str | Path | None = None,
) -> _Watch:
    """Return a context manager for scoped crash monitoring.

    Unlike :func:`safedump.install`, this does not install any global
    exception hooks. It only captures exceptions raised inside the
    ``with`` block, then re-raises them.

    Args:
        privacy_tier: Override the configured privacy tier for captures
            made within this block.
        output_dir: Override the configured output directory for captures
            made within this block.

    Example:
        >>> with safedump.watch():
        ...     dangerous_code()

    Supports nesting — each ``watch()`` block captures independently.
    """
    return _Watch(privacy_tier=privacy_tier, output_dir=output_dir)
