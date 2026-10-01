"""Click/Typer CLI integration for Safedump.

Automatically captures crash reports when a CLI command raises an
unhandled exception.

Usage with Click:

    import click
    from safedump.integrations.click_plugin import wrap_click

    @click.command()
    @wrap_click()
    def my_command():
        ...

Usage with Typer:

    import typer
    from safedump.integrations.click_plugin import wrap_click

    app = typer.Typer()

    @app.command()
    @wrap_click()
    def my_command():
        ...
"""

from __future__ import annotations

import contextlib
import functools
from typing import Any, Callable


def _is_click_control_flow(exc: BaseException) -> bool:
    """Click/Typer use exceptions for normal control flow (ctx.exit(), Abort,
    usage errors, typer.Exit). Those are not crashes and are not captured."""
    return any(
        cls.__module__.startswith(("click.", "typer."))
        and cls.__name__ in {"Exit", "Abort", "UsageError", "BadParameter", "ClickException"}
        for cls in type(exc).__mro__
    )


def wrap_click() -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator that wraps a Click command to capture crash reports.

    If the decorated command raises an unhandled exception, Safedump
    captures it before the exception propagates to Click's error handler.

    Returns:
        A decorator that can be applied to Click command functions.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as exc:
                if not _is_click_control_flow(exc):
                    from safedump import capture_exception

                    with contextlib.suppress(BaseException):
                        capture_exception(exc)
                raise

        return wrapper

    return decorator
