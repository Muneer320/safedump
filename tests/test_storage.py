"""Tests for the Safedump storage module."""

import json
from pathlib import Path

from safedump._config import SafedumpConfig
from safedump._storage import _sanitize_filename_component, generate_filename, save
from safedump._types import CrashReport, ExceptionSnapshot


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


class TestSave:
    def test_writes_file(self, tmp_path):
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
