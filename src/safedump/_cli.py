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

    # safedump doctor
    doctor_parser = subparsers.add_parser(
        "doctor", help="Diagnose common issues with safedump configuration"
    )
    doctor_parser.add_argument(
        "--verbose", action="store_true", help="Show detailed diagnostic output"
    )

    # safedump stats
    subparsers.add_parser("stats", help="Show aggregate crash statistics")

    # safedump serve
    serve_parser = subparsers.add_parser(
        "serve", help="Start a local web server for browsing crash reports"
    )
    serve_parser.add_argument("--port", type=int, default=4567, help="Port number (default: 4567)")
    serve_parser.add_argument(
        "--host", type=str, default="127.0.0.1", help="Host to bind to (default: 127.0.0.1)"
    )

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
    elif args.command == "doctor":
        _cmd_doctor(args.verbose)
    elif args.command == "stats":
        _cmd_stats()
    elif args.command == "serve":
        _cmd_serve(host=args.host, port=args.port)
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


def _cmd_serve(*, host: str = "127.0.0.1", port: int = 4567) -> None:
    """Handle the 'serve' subcommand."""
    from safedump._server import serve as _serve

    _serve(host=host, port=port)


def _cmd_stats() -> None:
    """Handle the 'stats' subcommand."""
    from safedump._config import get_config
    from safedump._loader import compute_stats

    stats = compute_stats(get_config().output_dir)
    print(f"Total crashes: {stats['total']}")

    if stats["total"] == 0:
        return

    print("\nBy exception type:")
    for exc_type, count in stats["by_type"].items():
        bar = "#" * min(count, 40)
        print(f"  {exc_type:20s} {count:4d}  {bar}")

    print("\nBy day (last 14):")
    days = list(stats["by_day"].items())[-14:]
    for day, count in days:
        print(f"  {day}  {count:4d}")

    print("\nBy crash site (top 5):")
    for site, count in list(stats["by_site"].items())[:5]:
        bar = "#" * min(count, 40)
        print(f"  {site:40s} {count:4d}  {bar}")


def _cmd_doctor(verbose: bool = False) -> None:
    """Handle the 'doctor' subcommand -- diagnose common issues."""
    checks = _doctor_checks()
    all_ok = True

    for name, status, message in checks:
        if status == "ok":
            icon = "[OK]"
        elif status == "warn":
            icon = "[WARN]"
        else:
            icon = "[FAIL]"
            all_ok = False
        print(f"  {icon} {name}")
        if verbose and message:
            print(f"        {message}")

    if all_ok:
        print("\nAll checks passed.")
    else:
        print("\nSome checks failed. Review the messages above.")
        sys.exit(1)


def _doctor_checks() -> list[tuple[str, str, str]]:
    """Run diagnostic checks and return (name, status, message) triples.

    Status is one of: "ok", "warn", "fail"
    """
    import os as _os
    import sys as _sys

    from safedump._capture import is_installed
    from safedump._config import get_config

    results: list[tuple[str, str, str]] = []

    # Python version
    py_version = f"{_sys.version_info.major}.{_sys.version_info.minor}"
    results.append(("Python version", "ok", f"Python {py_version} is supported"))

    # Check output directory
    try:
        config = get_config()
        out_dir = config.output_dir
        if out_dir.exists():
            if _os.access(str(out_dir), _os.W_OK):
                results.append(("Output directory", "ok", f"{out_dir} is writable"))
            else:
                results.append(
                    ("Output directory", "fail", f"{out_dir} exists but is not writable")
                )
        else:
            results.append(
                (
                    "Output directory",
                    "warn",
                    f"{out_dir} does not exist yet (will be created on first crash)",
                )
            )
    except Exception as e:
        results.append(("Configuration", "fail", f"Could not load config: {e}"))

    # Check if hooks are installed
    if is_installed():
        results.append(("Exception hooks", "ok", "Safedump hooks are active"))
    else:
        results.append(
            (
                "Exception hooks",
                "warn",
                "Hooks not installed (run safedump.install() in your application)",
            )
        )

    # Check for corrupted reports
    from safedump._loader import list_reports

    try:
        reports = list_reports(get_config().output_dir, count=10)
        corrupted = 0
        for path in reports:
            try:
                from safedump._loader import load_report

                load_report(path)
            except Exception:
                corrupted += 1
        if corrupted == 0:
            results.append(
                ("Report integrity", "ok", f"All {len(reports)} recent reports are valid")
            )
        else:
            results.append(
                ("Report integrity", "warn", f"{corrupted} of {len(reports)} reports are corrupted")
            )
    except Exception as e:
        results.append(("Report integrity", "warn", f"Could not scan reports: {e}"))

    # Check Rich availability
    try:
        import rich  # noqa: F401

        results.append(("Rich terminal viewer", "ok", "Rich is available"))
    except ImportError:
        results.append(
            (
                "Rich terminal viewer",
                "warn",
                "Rich not installed (install with: pip install safedump[view])",
            )
        )

    return results
