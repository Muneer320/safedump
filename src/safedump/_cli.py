"""CLI entry point for Safedump.

Usage:
    safedump view [FILE]    View a crash report
    safedump list           List recent crashes
    safedump test            Self-test
    safedump --version       Show version
"""

from __future__ import annotations

import argparse
import sys

from safedump._loader import find_latest, list_reports, load_report
from safedump._render import render


def main() -> None:
    """Entry point for the ``safedump`` console command."""
    parser = argparse.ArgumentParser(
        prog="safedump",
        description="Local-first crash diagnostics for Python.",
    )
    parser.add_argument("--version", action="version", version="safedump 0.1.0.dev0")
    subparsers = parser.add_subparsers(dest="command", title="commands")

    # safedump view
    view_parser = subparsers.add_parser("view", help="View a crash report")
    view_parser.add_argument("file", nargs="?", help="Crash report file (default: latest)")

    # safedump list
    list_parser = subparsers.add_parser("list", help="List recent crash reports")
    list_parser.add_argument("--count", type=int, default=20, help="Number of reports to show")

    # safedump test
    subparsers.add_parser("test", help="Self-test — verify safedump is working")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    if args.command == "view":
        _cmd_view(args.file)
    elif args.command == "list":
        _cmd_list(args.count)
    elif args.command == "test":
        _cmd_test()


def _cmd_view(file: str | None) -> None:
    """Handle the 'view' subcommand."""
    try:
        if file:
            report = load_report(file)
        else:
            # Find latest from default output dir
            from safedump._config import get_config

            latest = find_latest(get_config().output_dir)
            if latest is None:
                print("No crash reports found.", file=sys.stderr)
                sys.exit(1)
            report = load_report(latest)
            print(f"Viewing: {latest}")

        render(report)

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def _cmd_list(count: int) -> None:
    """Handle the 'list' subcommand."""
    from safedump._config import get_config

    reports = list_reports(get_config().output_dir, count=count)

    if not reports:
        print("No crash reports found.")
        return

    print(f"Recent crash reports ({len(reports)}):")
    for i, path in enumerate(reports, 1):
        try:
            report = load_report(path)
            exc_type = report.get("exception", {}).get("type", "?")
            ts = report.get("timestamp", "?")[:19]
            print(f"  {i}. {ts}  {exc_type}  {path}")
        except Exception:
            print(f"  {i}. (unreadable)  {path}")


def _cmd_test() -> None:
    """Handle the 'test' subcommand."""
    try:
        from safedump._capture import test
    except ImportError:
        print("Error: safedump is not installed. Run: pip install safedump", file=sys.stderr)
        sys.exit(1)

    try:
        path = test()
        if path:
            print(f"✅ Safedump is working. Test report: {path}")
        else:
            print("❌ Safedump test failed — could not write report.", file=sys.stderr)
            sys.exit(1)
    except RuntimeError as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(1)
