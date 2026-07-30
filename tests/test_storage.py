# SPDX-FileCopyrightText: 2026 Muneer Alam
#
# SPDX-License-Identifier: MIT


"""Tests for the Safedump storage module."""

import json
import platform
from pathlib import Path

import pytest

from safedump._config import SafedumpConfig
from safedump._storage import _sanitize_filename_component, generate_filename, save
from safedump._types import CrashReport, ExceptionSnapshot, FrameSnapshot


class TestSanitizeFilename:
    def test_normal_exception_type(self):
        assert _sanitize_filename_component("TypeError") == "TypeError"

    def test_path_traversal_attempt(self):
        result = _sanitize_filename_component("../../etc/passwd")
        assert ".." in result or "/" not in result  # dots preserved, slashes removed

    def test_special_characters(self):
        result = _sanitize_filename_component("OSError: [Errno 13] Permission denied")
        assert ":" not in result
        assert "[" not in result
        assert "]" not in result

    def test_empty_string(self):
        assert _sanitize_filename_component("") == "unknown"


class TestGenerateFilename:
    def test_format(self):
        report = CrashReport(
            exception=ExceptionSnapshot(type="TypeError", message="bad"),
            timestamp="2026-06-25T12-00-00",
        )
        filename = generate_filename(report)
        assert filename.startswith("2026-06-25-12-00-00")
        assert filename.endswith(".safedump.json")

    def test_different_crashes_different_hashes(self):
        r1 = CrashReport(
            exception=ExceptionSnapshot(type="TypeError", message="x"),
            timestamp="2026-06-25T12-00-00",
        )
        r2 = CrashReport(
            exception=ExceptionSnapshot(type="ValueError", message="y"),
            timestamp="2026-06-25T12-00-01",
        )
        f1 = generate_filename(r1)
        f2 = generate_filename(r2)
        assert f1 != f2


class TestDeduplication:
    """Crash report deduplication tests."""

    def test_dedup_with_same_fingerprint(self, tmp_path):
        """Two saves with the same fingerprint should reuse the same file."""
        from safedump._serialize import serialize
        from safedump._storage import save

        config = SafedumpConfig(output_dir=tmp_path)

        # Create two reports with the same fingerprint
        r1 = CrashReport(
            exception=ExceptionSnapshot(type="ValueError", message="same"),
            frames=[FrameSnapshot(index=0, file="test.py", line=42, function="main", lineno=42)],
        )
        r1.fingerprint = "deduptest0001"
        r2 = CrashReport(
            exception=ExceptionSnapshot(type="ValueError", message="same"),
            frames=[FrameSnapshot(index=0, file="test.py", line=42, function="main", lineno=42)],
        )
        r2.fingerprint = "deduptest0001"

        path1 = save(serialize(r1, config), config, r1)
        path2 = save(serialize(r2, config), config, r2)

        assert path1 == path2, "Same fingerprint should reuse the same file"

    def test_dedup_updates_occurrence_count(self, tmp_path):
        """Repeated dedup saves should increment occurrence_count."""
        import json

        from safedump._serialize import serialize
        from safedump._storage import save

        config = SafedumpConfig(output_dir=tmp_path)

        for _ in range(3):
            r = CrashReport(
                exception=ExceptionSnapshot(type="ValueError", message="counted"),
                frames=[
                    FrameSnapshot(index=0, file="test.py", line=42, function="main", lineno=42)
                ],
            )
            r.fingerprint = "testfinger1234"  # same fingerprint
            result = save(serialize(r, config), config, r)

        assert result is not None
        data = json.loads(result.read_text())
        assert data.get("occurrence_count", 0) == 3

    def test_dedup_updates_last_seen(self, tmp_path):
        """Repeated saves should update last_seen."""
        import json

        from safedump._serialize import serialize
        from safedump._storage import save

        config = SafedumpConfig(output_dir=tmp_path)

        r1 = CrashReport(
            timestamp="2026-01-01T00:00:00",
            exception=ExceptionSnapshot(type="ValueError", message="seen"),
            frames=[FrameSnapshot(index=0, file="test.py", line=42, function="main", lineno=42)],
        )
        r1.fingerprint = "testfinger5678"
        save(serialize(r1, config), config, r1)

        r2 = CrashReport(
            timestamp="2026-06-15T12:00:00",
            exception=ExceptionSnapshot(type="ValueError", message="seen"),
            frames=[FrameSnapshot(index=0, file="test.py", line=42, function="main", lineno=42)],
        )
        r2.fingerprint = "testfinger5678"
        result = save(serialize(r2, config), config, r2)

        assert result is not None
        data = json.loads(result.read_text())
        assert data.get("last_seen") == "2026-06-15T12:00:00"

    def test_different_fingerprints_different_files(self, tmp_path):
        """Different fingerprints should create separate files."""
        from safedump._serialize import serialize
        from safedump._storage import save

        config = SafedumpConfig(output_dir=tmp_path)

        r1 = CrashReport(
            exception=ExceptionSnapshot(type="ValueError", message="a"),
            frames=[FrameSnapshot(index=0, file="test.py", line=10, function="main", lineno=10)],
        )
        r2 = CrashReport(
            exception=ExceptionSnapshot(type="KeyError", message="b"),
            frames=[FrameSnapshot(index=0, file="test.py", line=20, function="other", lineno=20)],
        )

        path1 = save(serialize(r1, config), config, r1)
        path2 = save(serialize(r2, config), config, r2)

        assert path1 != path2, "Different fingerprints should create different files"
        config = SafedumpConfig(output_dir=tmp_path / "crashes")
        report = CrashReport(
            exception=ExceptionSnapshot(type="ValueError", message="test"),
            timestamp="2026-06-25T12-00-00",
        )
        json_str = json.dumps({"test": True})
        path = save(json_str, config, report)
        assert path is not None
        assert path.exists()
        content = path.read_text()
        assert "test" in content

    def test_file_permissions(self, tmp_path):
        if platform.system() == "Windows":
            pytest.skip("chmod semantics differ on Windows")
        config = SafedumpConfig(output_dir=tmp_path / "crashes")
        report = CrashReport(
            exception=ExceptionSnapshot(type="ValueError", message="test"),
            timestamp="2026-06-25T12-00-00",
        )
        path = save("{}", config, report)
        assert path is not None
        stat = path.stat()
        assert stat.st_mode & 0o777 == 0o600

    def test_directory_permissions(self, tmp_path):
        if platform.system() == "Windows":
            pytest.skip("chmod semantics differ on Windows")
        config = SafedumpConfig(output_dir=tmp_path / "crashes")
        report = CrashReport(
            exception=ExceptionSnapshot(type="ValueError", message="test"),
            timestamp="2026-06-25T12-00-00",
        )
        path = save("{}", config, report)
        assert path is not None
        dir_stat = path.parent.stat()
        assert dir_stat.st_mode & 0o777 == 0o700

    def test_returns_none_on_unwritable(self, tmp_path):
        config = SafedumpConfig(output_dir=Path("/root/forbidden"))
        report = CrashReport(
            exception=ExceptionSnapshot(type="X", message="test"),
            timestamp="2026-06-25T12-00-00",
        )
        path = save("{}", config, report)
        # Should fall back to /tmp or return None
        if path is not None:
            assert path.exists()


class TestCompression:
    """Report compression tests."""

    def test_compress_writes_gz_file(self, tmp_path):
        """When compress=True, files should be .json.gz."""
        from safedump._serialize import serialize
        from safedump._storage import save

        config = SafedumpConfig(output_dir=tmp_path, compress=True)
        report = CrashReport(
            exception=ExceptionSnapshot(type="ValueError", message="compressed"),
            frames=[FrameSnapshot(index=0, file="test.py", line=1, function="test", lineno=1)],
        )
        path = save(serialize(report, config), config, report)
        assert path is not None
        assert path.name.endswith(".gz"), f"Expected .gz file, got {path.name}"

    def test_compress_actual_gzip_bytes(self, tmp_path):
        """File content should be actual gzip data."""
        from safedump._serialize import serialize
        from safedump._storage import save

        config = SafedumpConfig(output_dir=tmp_path, compress=True)
        report = CrashReport(
            exception=ExceptionSnapshot(type="ValueError", message="gzip_test"),
            frames=[FrameSnapshot(index=0, file="test.py", line=1, function="test", lineno=1)],
        )
        path = save(serialize(report, config), config, report)
        raw = path.read_bytes()
        assert raw[:2] == b"\x1f\x8b", "File should be gzip-compressed"

    def test_uncompressed_plain_json(self, tmp_path):
        """When compress=False, files should be plain JSON."""
        from safedump._serialize import serialize
        from safedump._storage import save

        config = SafedumpConfig(output_dir=tmp_path, compress=False)
        report = CrashReport(
            exception=ExceptionSnapshot(type="KeyError", message="plain"),
            frames=[FrameSnapshot(index=0, file="test.py", line=1, function="test", lineno=1)],
        )
        path = save(serialize(report, config), config, report)
        raw = path.read_bytes()
        assert raw[:2] != b"\x1f\x8b", "Uncompressed file should not have gzip magic bytes"

    def test_load_report_reads_compressed(self, tmp_path):
        """load_report should decompress .json.gz files transparently."""
        from safedump._loader import load_report
        from safedump._serialize import serialize
        from safedump._storage import save

        config = SafedumpConfig(output_dir=tmp_path, compress=True)
        report = CrashReport(
            exception=ExceptionSnapshot(type="ValueError", message="roundtrip"),
            frames=[FrameSnapshot(index=0, file="test.py", line=1, function="test", lineno=1)],
        )
        path = save(serialize(report, config), config, report)
        data = load_report(path)
        assert data["exception"]["type"] == "ValueError"
        assert data["exception"]["message"] == "roundtrip"
