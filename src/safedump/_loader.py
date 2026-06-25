"""Crash report loading for Safedump.

Parses JSON report files and discovers recent crashes.
Runs in the cold path — can fail safely.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


def load_report(path: str | Path) -> dict[str, Any]:
    """Load a Safedump crash report from disk.

    Args:
        path: Path to a ``.safedump.json`` file.

    Returns:
        Parsed report dict with all fields.

    Raises:
        FileNotFoundError: If ``path`` does not exist.
        ValueError: If the file is not valid Safedump JSON
            (missing ``safedump_version`` field).
    """
    filepath = Path(path).expanduser()
    if not filepath.exists():
        raise FileNotFoundError(f"Crash report not found: {filepath}")

    with open(filepath, encoding="utf-8") as f:
        data = json.load(f)

    if "safedump_version" not in data:
        raise ValueError(f"Not a valid safedump report (missing safedump_version): {filepath}")

    return data


def find_latest(output_dir: str | Path) -> Path | None:
    """Find the most recent crash report in a directory.

    Args:
        output_dir: Directory to scan for ``.safedump.json`` files.

    Returns:
        Path to the most recent report, or ``None`` if no reports exist.
    """
    directory = Path(output_dir).expanduser()
    if not directory.exists():
        return None

    reports = sorted(
        directory.glob("*.safedump.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return reports[0] if reports else None


def list_reports(output_dir: str | Path, count: int = 20) -> list[Path]:
    """List recent crash reports.

    Args:
        output_dir: Directory to scan.
        count: Maximum number of reports to return.

    Returns:
        List of report paths, newest first.
    """
    directory = Path(output_dir).expanduser()
    if not directory.exists():
        return []

    reports = sorted(
        directory.glob("*.safedump.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return reports[:count]


def clean_older_than(output_dir: str | Path, days: int) -> int:
    """Delete crash reports older than ``days`` days.

    Args:
        output_dir: Directory to clean.
        days: Delete reports older than this many days.

    Returns:
        Number of reports deleted.
    """
    directory = Path(output_dir).expanduser()
    if not directory.exists():
        return 0

    cutoff = time.time() - (days * 86400)
    deleted = 0
    for report in directory.glob("*.safedump.json"):
        try:
            if report.stat().st_mtime < cutoff:
                report.unlink()
                deleted += 1
        except OSError:
            pass
    return deleted
