"""Crash report file persistence for Safedump.

Handles filename generation, atomic writes, permissions,
and fallback paths. Runs in the crash-time hot path.
"""

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


def _write_atomic(output_dir: Path, filename: str, content: str) -> Path | None:
    """Write content to a file atomically.

    Uses tempfile + os.replace() for atomicity on POSIX.
    Sets file permissions to 0o600 (owner read/write only).
    """
    try:
        # Write to temp file in the same directory
        fd, tmp_path = tempfile.mkstemp(
            suffix=".tmp", prefix=".", dir=str(output_dir)
        )
        try:
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

    1. Generates a safe filename from the crash report.
    2. Ensures the output directory exists (0o700).
    3. Writes the JSON atomically (tempfile + rename).
    4. Sets file permissions to 0o600.
    5. Falls back to /tmp if primary output_dir fails.

    Args:
        json_str: JSON string to write.
        config: Active configuration (output_dir).
        report: Crash report for filename generation.

    Returns:
        Path to the written file, or None if all write attempts failed.
    """
    filename = generate_filename(report)

    # Primary path
    primary_dir = _ensure_output_dir(config.output_dir)
    if primary_dir is not None:
        result = _write_atomic(primary_dir, filename, json_str)
        if result is not None:
            return result

    # Fallback to /tmp
    fallback_dir = Path(f"/tmp/safedump-fallback-{os.getpid()}")
    fb_dir = _ensure_output_dir(fallback_dir)
    if fb_dir is not None:
        result = _write_atomic(fb_dir, filename, json_str)
        if result is not None:
            return result

    return None
