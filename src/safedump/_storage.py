"""Crash report file persistence for Safedump.

Handles filename generation, atomic writes, permissions,
and fallback paths. Runs in the crash-time hot path.
"""

# SPDX-FileCopyrightText: 2026 Muneer Alam
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

import hashlib
import os
import re
import tempfile
from pathlib import Path

from safedump._types import CrashReport, SafedumpConfig


def _sanitize_filename_component(name: str) -> str:
    """Make a string safe for use in a filename.

    Replaces anything that isn't alphanumeric, dash, or underscore
    with a dash. Collapses multiple dashes.
    """
    safe = re.sub(r"[^a-zA-Z0-9_-]", "-", name)
    safe = re.sub(r"-{2,}", "-", safe)
    return safe.strip("-") or "unknown"


def _compute_hash(report: CrashReport) -> str:
    """Generate a short hash from exception type and crash site."""
    digest = hashlib.sha256()
    digest.update(report.exception.type.encode())
    digest.update(report.exception.message.encode()[:200])
    if report.frames:
        first = report.frames[0]
        digest.update(first.file.encode())
        digest.update(str(first.line).encode())
    return digest.hexdigest()[:8]


def generate_filename(report: CrashReport) -> str:
    """Generate a safe, unique, sortable crash report filename.

    Format: ``{timestamp}-{exception_type}-{hash}.safedump.json``

    The timestamp prefix ensures chronological sorting.
    The hash provides deduplication without revealing crash details.
    """
    ts = report.timestamp.replace(":", "-").replace("T", "-")[:19]
    exc_type = _sanitize_filename_component(report.exception.type)
    hash_val = _compute_hash(report)
    return f"{ts}-{exc_type}-{hash_val}.safedump.json"


def _ensure_output_dir(output_dir: Path) -> Path | None:
    """Create the output directory with safe permissions.

    Returns the directory path, or None if creation failed.
    """
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        output_dir.chmod(0o700)
        return output_dir
    except (OSError, PermissionError):
        return None


def _write_atomic(output_dir: Path, filename: str, content: str | bytes) -> Path | None:
    """Write content to a file atomically.

    Uses tempfile + os.replace() for atomicity on POSIX.
    Sets file permissions to 0o600 (owner read/write only).
    """
    try:
        # Write to temp file in the same directory
        fd, tmp_path = tempfile.mkstemp(suffix=".tmp", prefix=".", dir=str(output_dir))
        try:
            if isinstance(content, bytes):
                os.write(fd, content)
            else:
                os.write(fd, content.encode("utf-8"))
        finally:
            os.close(fd)

        # Atomic rename
        final_path = output_dir / filename
        os.replace(tmp_path, final_path)

        # Restrict permissions
        final_path.chmod(0o600)

        return final_path

    except (OSError, PermissionError, FileNotFoundError):
        return None


def save(json_str: str, config: SafedumpConfig, report: CrashReport) -> Path | None:
    """Write a crash report JSON string to disk.

    If a report with the same fingerprint already exists, increments
    its occurrence_count and updates last_seen instead of creating a
    new file (deduplication).

    1. Checks for existing reports with same fingerprint.
    2. Generates a safe filename from the crash report.
    3. Ensures the output directory exists (0o700).
    4. Writes the JSON atomically (tempfile + rename).
    5. Sets file permissions to 0o600.
    6. Falls back to system temp directory if primary output_dir fails.

    Args:
        json_str: JSON string to write.
        config: Active configuration (output_dir).
        report: Crash report for filename generation.

    Returns:
        Path to the written file, or None if all write attempts failed.
    """
    import gzip
    import json as _json

    filename = generate_filename(report)

    # Determine content and filename based on compression setting
    if config.compress:
        json_bytes = json_str.encode("utf-8")
        content_to_write = gzip.compress(json_bytes)
        # Use .safedump.json.gz extension for compressed files
        if not filename.endswith(".gz"):
            filename += ".gz"
    else:
        content_to_write = json_str

    # Check for existing report with same fingerprint (dedup)
    if report.fingerprint:
        existing = _find_existing_by_fingerprint(config.output_dir, report.fingerprint)
        if existing is not None:
            try:
                # Load existing report, increment occurrence count
                data = _json.loads(existing.read_text(encoding="utf-8"))
                data["occurrence_count"] = data.get("occurrence_count", 1) + 1
                data["last_seen"] = report.timestamp
                # Re-serialize and write back
                updated_json = _json.dumps(data, indent=2, ensure_ascii=False)
                primary_dir = _ensure_output_dir(config.output_dir)
                if primary_dir is not None:
                    result = _write_atomic(primary_dir, existing.name, updated_json)
                    if result is not None:
                        return result
            except (OSError, _json.JSONDecodeError):
                pass  # Fall through to normal save if dedup fails

    # Primary path
    primary_dir = _ensure_output_dir(config.output_dir)
    if primary_dir is not None:
        result = _write_atomic(primary_dir, filename, content_to_write)
        if result is not None:
            return result

    # Fallback to system temp directory (cross-platform)
    fallback_dir = Path(tempfile.gettempdir()) / f"safedump-fallback-{os.getpid()}"
    fb_dir = _ensure_output_dir(fallback_dir)
    if fb_dir is not None:
        result = _write_atomic(fb_dir, filename, content_to_write)
        if result is not None:
            return result

    return None


def _find_existing_by_fingerprint(output_dir: Path, fingerprint: str) -> Path | None:
    """Find an existing report file with the given fingerprint.

    Scans the output directory for reports whose JSON contains the
    matching fingerprint. Returns the most recently modified match.
    """
    import json as _json

    if not output_dir.exists():
        return None

    candidates = []
    for p in output_dir.glob("*.safedump.json*"):
        try:
            import gzip

            raw = p.read_bytes()
            if raw[:2] == b"\x1f\x8b":
                raw = gzip.decompress(raw)
            data = _json.loads(raw)
            if data.get("fingerprint") == fingerprint:
                candidates.append(p)
        except (OSError, _json.JSONDecodeError):
            continue

    if not candidates:
        return None
    # Return most recently modified
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]
