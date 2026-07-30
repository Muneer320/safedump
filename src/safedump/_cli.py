"""CLI entry point for Safedump.

Usage:
    safedump view [--json] [--html [FILE]] [FILE]
    safedump list           List recent crashes
    safedump test            Self-test
    safedump --version       Show version
"""

from __future__ import annotations

import argparse
import json
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from safedump._html_render import render_html
from safedump._loader import clean_older_than, find_latest, list_reports, load_report
from safedump._render import render


def main() -> None:
    """Entry point for the ``safedump`` console command."""
    parser = argparse.ArgumentParser(
        prog="safedump",
        description="Local-first crash diagnostics for Python.",
    )
    try:
        pkg_version = version("safedump")
    except PackageNotFoundError:
        pkg_version = "0.0.0+dev"
    parser.add_argument("--version", action="version", version=f"safedump {pkg_version}")
    subparsers = parser.add_subparsers(dest="command", title="commands")

    # safedump view
    view_parser = subparsers.add_parser("view", help="View a crash report")
    view_parser.add_argument("file", nargs="?", help="Crash report file (default: latest)")
    view_parser.add_argument(
        "--json",
        action="store_true",
        help="Print raw JSON instead of Rich-formatted output",
    )
    view_parser.add_argument(
        "--html",
        metavar="OUTPUT",
        nargs="?",
        const=None,
        help="Generate HTML report (optionally specify output file path)",
    )

    # safedump list
    list_parser = subparsers.add_parser("list", help="List recent crash reports")
    list_parser.add_argument("--count", type=int, default=20, help="Number of reports to show")
    list_parser.add_argument(
        "--type", dest="type_filter", help="Filter by exception type (substring, case-insensitive)"
    )
    list_parser.add_argument(
        "--since", help="Show reports after this date (ISO: 2026-07-01, or duration: 7d, 24h, 30m)"
    )
    list_parser.add_argument("--until", help="Show reports before this date (ISO or duration)")
    list_parser.add_argument("--search", help="Search in exception type, message, and filename")

    # safedump clean
    clean_parser = subparsers.add_parser("clean", help="Delete old crash reports")
    clean_parser.add_argument(
        "--older-than",
        type=int,
        default=30,
        metavar="DAYS",
        help="Delete reports older than DAYS (default: 30)",
    )

    # safedump test
    subparsers.add_parser("test", help="Self-test -- verify safedump is working")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    if args.command == "view":
        _cmd_view(args.file, as_json=args.json, html_path=args.html)
    elif args.command == "list":
        _cmd_list(
            args.count,
            type_filter=args.type_filter,
            since=args.since,
            until=args.until,
            search=args.search,
        )
    elif args.command == "clean":
        _cmd_clean(args.older_than)
    elif args.command == "test":
        _cmd_test()


def _cmd_view(file: str | None, *, as_json: bool = False, html_path: str | None = None) -> None:
    """Handle the 'view' subcommand."""
    try:
        if file:
            report = load_report(file)
        else:
            from safedump._config import get_config

            latest = find_latest(get_config().output_dir)
            if latest is None:
                print("No crash reports found.", file=sys.stderr)
                sys.exit(1)
            report = load_report(latest)
            if not as_json and html_path is None:
                print(f"Viewing: {latest}")

        if html_path is not None:
            output_path = Path(html_path)
            html_content = render_html(report)
            output_path.write_text(html_content, encoding="utf-8")
            print(f"HTML report saved: {output_path}")
        elif as_json:
            print(json.dumps(report, indent=2))
        else:
            render(report)

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def _cmd_list(
    count: int,
    *,
    type_filter: str | None = None,
    since: str | None = None,
    until: str | None = None,
    search: str | None = None,
) -> None:
    """Handle the 'list' subcommand."""
    from safedump._config import get_config

    reports = list_reports(
        get_config().output_dir,
        count=count,
        type_filter=type_filter,
        since=since,
        until=until,
        search=search,
    )

    if not reports:
        print("No crash reports found.")
        return

    print(f"Recent crash reports ({len(reports)}):")
    for i, path in enumerate(reports, 1):
        try:
            report = load_report(path)
            exc_type = report.get("exception", {}).get("type", "?")
            ts = report.get("timestamp", "?")[:19]
            fp = report.get("fingerprint", "")
            fp_str = f" [{fp}]" if fp else ""
            print(f"  {i}. {ts}  {exc_type}{fp_str}  {path}")
        except (ValueError, FileNotFoundError) as e:
            print(f"  {i}. [error: {e}]  {path}")


def _cmd_clean(days: int) -> None:
    """Handle the 'clean' subcommand."""
    from safedump._config import get_config

    deleted = clean_older_than(get_config().output_dir, days)
    print(f"Deleted {deleted} crash report(s) older than {days} days.")


def _cmd_test() -> None:
    """Handle the 'test' subcommand."""
    from safedump._capture import test

    path = test()
    if path is not None:
        print(f"Self-test passed. Crash report saved: {path}")
    else:
        print("Self-test failed.", file=sys.stderr)
        sys.exit(1)
