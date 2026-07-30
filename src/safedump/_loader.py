"""Crash report loading for Safedump.

Parses JSON report files, discovers recent crashes,
and applies schema migrations for forward compatibility.
Runs in the cold path -- can fail safely.
"""

# SPDX-FileCopyrightText: 2026 Muneer Alam
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable

from safedump._types import CRASH_REPORT_SCHEMA_VERSION

# ── Schema Migration Framework ─────────────────────────────────────

MIGRATIONS: dict[int, Callable[[dict[str, Any]], dict[str, Any]]] = {}


def _migrate_v0_to_v1(raw: dict[str, Any]) -> dict[str, Any]:
    """Migrate schema v0 (no version field) to v1.

    v0 was the initial format used by safedump 1.0.0 through 1.1.0.
    v1 adds: schema_version, fingerprint, occurrence_count,
    first_seen, last_seen, and changes metadata type to dict[str, Any].
    """
    raw.setdefault("schema_version", 1)
    raw.setdefault("fingerprint", "")
    raw.setdefault("occurrence_count", 1)
    raw.setdefault("first_seen", raw.get("timestamp", ""))
    raw.setdefault("last_seen", raw.get("timestamp", ""))
    raw.setdefault("metadata", {})
    # Ensure metadata values survive if any are non-string
    metadata = raw.get("metadata", {})
    if metadata is None:
        raw["metadata"] = {}
    return raw


MIGRATIONS[0] = _migrate_v0_to_v1


def load_report(path: str | Path) -> dict[str, Any]:
    """Load a Safedump crash report from disk, applying migrations.

    Args:
        path: Path to a ``.safedump.json`` file.

    Returns:
        Parsed report dict with all fields migrated to the current
        schema version.

    Raises:
        FileNotFoundError: If ``path`` does not exist.
        ValueError: If the file is not valid Safedump JSON.
    """
    filepath = Path(path).expanduser()
    if not filepath.exists():
        raise FileNotFoundError(f"Crash report not found: {filepath}")

    with open(filepath, encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)

    if "safedump_version" not in data:
        raise ValueError(f"Not a valid safedump report (missing safedump_version): {filepath}")

    # Determine current schema version and apply migrations
    version = data.get("schema_version", 0)
    for v in range(version, CRASH_REPORT_SCHEMA_VERSION):
        if v in MIGRATIONS:
            data = MIGRATIONS[v](data)
        data["schema_version"] = v + 1

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
