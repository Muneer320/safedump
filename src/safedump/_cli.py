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
    subparsers.add_parser("list", help="List recent crash reports")

    # safedump test
    subparsers.add_parser("test", help="Self-test — verify safedump is working")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    # All commands are placeholders until M8
    print(f"safedump {args.command}: not yet implemented")
    print("This is a development build. Implementation is in progress.")
