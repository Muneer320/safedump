"""Terminal crash report viewer for Safedump.

Uses Rich for syntax-highlighted, color-coded output.
Runs in the cold path — can fail safely.
"""

from __future__ import annotations

from typing import Any


def _get_rich() -> Any:
    """Lazy-import Rich. Returns None if not installed."""
    try:
        import rich.console
        import rich.panel
        import rich.syntax
        import rich.table
        import rich.text
        import rich.traceback

        return rich
    except ImportError:
        return None


def render(report: dict[str, Any], *, color: bool = True) -> None:
    """Display a crash report in the terminal.

    Args:
        report: Loaded crash report dict.
        color: Whether to use ANSI colors.

    If Rich is not installed, falls back to plain-text output.
    """
    rich = _get_rich()

    if rich is None:
        _render_plain(report)
        return

    console = rich.console.Console(color_system="auto" if color else None)

    # Exception header
    exc = report.get("exception", {})
    exc_type = exc.get("type", "Unknown")
    exc_msg = exc.get("message", "")
    console.print(
        rich.panel.Panel(
            f"[bold red]{exc_type}[/bold red]: {exc_msg}",
            title="Exception",
            border_style="red",
        )
    )

    # Frames with locals
    frames = report.get("frames", [])
    for frame in frames:
        _render_frame(console, frame, rich)

    # Environment
    env = report.get("environment", {})
    if env:
        env_text = (
            f"OS: {env.get('os_name', '?')} | "
            f"Python: {report.get('python_version', '?')} | "
            f"Platform: {report.get('platform', '?')}\n"
            f"CWD: {env.get('cwd', '?')}"
        )
        console.print(rich.panel.Panel(env_text, title="Environment", border_style="blue"))

    # Redactions
    redactions = report.get("redactions", [])
    if redactions:
        table = rich.table.Table(title="Redactions")
        table.add_column("Location", style="dim")
        table.add_column("Reason")
        for r in redactions:
            table.add_row(r.get("location", "?"), r.get("reason", "?"))
        console.print(table)


def _render_frame(console: Any, frame: dict[str, Any], rich: Any) -> None:
    """Render a single stack frame."""
    func = frame.get("function", "?")
    ffile = frame.get("file", "?")
    line = frame.get("line", 0)
    is_crash = frame.get("is_crash_site", False)

    style = "bold red" if is_crash else "yellow"
    console.print(
        rich.panel.Panel(
            f"{ffile}:{line} in [bold]{func}[/bold]",
            border_style=style,
        )
    )

    # Source context
    code_context = frame.get("code_context", [])
    if code_context:
        source = "\n".join(code_context)
        console.print(rich.syntax.Syntax(source, "python", theme="monokai"))

    # Locals table
    locals_dict = frame.get("locals", {})
    if locals_dict:
        table = rich.table.Table(show_header=True, header_style="bold")
        table.add_column("Variable", style="cyan")
        table.add_column("Type", style="dim")
        table.add_column("Value")
        for name, var in locals_dict.items():
            table.add_row(name, var.get("type", "?"), str(var.get("value", "")))
        console.print(table)


def _render_plain(report: dict[str, Any]) -> None:
    """Fallback plain-text rendering when Rich is not available."""
    exc = report.get("exception", {})
    print(f"Exception: {exc.get('type', 'Unknown')}: {exc.get('message', '')}")

    frames = report.get("frames", [])
    for frame in frames:
        print(f"  {frame.get('file', '?')}:{frame.get('line', 0)} in {frame.get('function', '?')}")
        for name, var in frame.get("locals", {}).items():
            print(f"    {name} = {var.get('value', '')}")

    env = report.get("environment", {})
    if env:
        print(f"Environment: {env.get('os_name', '?')} | CWD: {env.get('cwd', '?')}")
