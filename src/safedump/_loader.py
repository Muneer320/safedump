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


def list_reports(
    output_dir: str | Path,
    count: int = 20,
    *,
    type_filter: str | None = None,
    since: str | None = None,
    until: str | None = None,
    search: str | None = None,
) -> list[Path]:
    """List recent crash reports, with optional filters.

    Args:
        output_dir: Directory to scan.
        count: Maximum number of reports to return.
        type_filter: Only include reports with this exception type (case-insensitive substring).
        since: ISO-8601 date or human-readable like "7d" (only reports after this time).
        until: ISO-8601 date or human-readable like "24h" (only reports before this time).
        search: Search string (matched against exception type, message, and filename).

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

    # Apply filters
    if type_filter or since or until or search:
        filtered: list[Path] = []
        for report_path in reports:
            try:
                data = json.loads(report_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            exc = data.get("exception", {})

            if type_filter:
                exc_type = exc.get("type", "").lower()
                if type_filter.lower() not in exc_type:
                    continue
            if search:
                search_lower = search.lower()
                exc_type = exc.get("type", "").lower()
                exc_msg = exc.get("message", "").lower()
                fname = report_path.name.lower()
                if (
                    search_lower not in exc_type
                    and search_lower not in exc_msg
                    and search_lower not in fname
                ):
                    continue
            if since or until:
                ts = _parse_time_filter(since, until)
                if ts is not None:
                    mtime = report_path.stat().st_mtime
                    min_ts, max_ts = ts
                    if min_ts is not None and mtime < min_ts:
                        continue
                    if max_ts is not None and mtime > max_ts:
                        continue
            filtered.append(report_path)
        reports = filtered

    return reports[:count]


def _parse_time_filter(
    since: str | None, until: str | None
) -> tuple[float | None, float | None] | None:
    """Parse human-readable time filters into Unix timestamps.

    Returns (min_time, max_time) tuple where None means unbounded.
    """
    import time as time_module

    now = time_module.time()
    min_ts: float | None = None
    max_ts: float | None = None

    if since:
        min_ts = _parse_time_str(since, now)
    if until:
        max_ts = _parse_time_str(until, now)

    if since is None and until is None:
        return None
    return (min_ts, max_ts)


def _parse_time_str(value: str, now: float) -> float:
    """Parse a human-readable time string into a Unix timestamp.

    Supports: ISO-8601 (2026-07-01), human durations (7d, 24h, 30m).
    """
    value = value.strip()

    # Human-readable durations
    if value.endswith("d"):
        days = float(value[:-1])
        return now - (days * 86400)
    if value.endswith("h"):
        hours = float(value[:-1])
        return now - (hours * 3600)
    if value.endswith("m"):
        minutes = float(value[:-1])
        return now - (minutes * 60)

    # ISO-8601 date
    from datetime import datetime

    try:
        dt = datetime.fromisoformat(value)
        return dt.timestamp()
    except ValueError:
        raise ValueError(
            f"Invalid time format: '{value}'. Use ISO date (2026-07-01) or duration (7d, 24h, 30m)."
        ) from None


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
