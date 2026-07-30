"""Tests for crash report schema migration framework."""

from __future__ import annotations

import json

from safedump._loader import _migrate_v0_to_v1, load_report
from safedump._types import CRASH_REPORT_SCHEMA_VERSION


class TestMigrationFramework:
    """Schema migration framework tests."""

    def test_migrate_v0_to_v1_adds_schema_version(self):
        raw = {"safedump_version": "1.0.0", "exception": {"type": "ValueError", "message": "test"}}
        result = _migrate_v0_to_v1(raw)
        assert result["schema_version"] == 1

    def test_migrate_v0_to_v1_adds_fingerprint(self):
        raw = {"safedump_version": "1.0.0", "timestamp": "2026-07-30T12:00:00"}
        result = _migrate_v0_to_v1(raw)
        assert result["fingerprint"] == ""

    def test_migrate_v0_to_v1_adds_occurrence_count(self):
        raw = {"safedump_version": "1.0.0"}
        result = _migrate_v0_to_v1(raw)
        assert result["occurrence_count"] == 1

    def test_migrate_v0_to_v1_sets_first_seen_from_timestamp(self):
        raw = {"safedump_version": "1.0.0", "timestamp": "2026-07-30T12:00:00"}
        result = _migrate_v0_to_v1(raw)
        assert result["first_seen"] == "2026-07-30T12:00:00"
        assert result["last_seen"] == "2026-07-30T12:00:00"

    def test_migrate_v0_to_v1_handles_missing_metadata(self):
        raw = {"safedump_version": "1.0.0"}
        result = _migrate_v0_to_v1(raw)
        assert isinstance(result.get("metadata"), dict)

    def test_migrate_v0_preserves_existing_fields(self):
        raw = {
            "safedump_version": "1.0.0",
            "exception": {"type": "KeyError", "message": "missing"},
            "frames": [],
        }
        result = _migrate_v0_to_v1(raw)
        assert result["exception"]["type"] == "KeyError"
        assert result["exception"]["message"] == "missing"

    def test_migrate_v1_is_noop(self):
        # v1 matches current schema, no migrations needed
        assert CRASH_REPORT_SCHEMA_VERSION == 1


class TestLoadReportMigration:
    """Integration tests for load_report with migration."""

    def test_load_report_migrates_v0_on_read(self, tmp_path):
        v0_report = {
            "safedump_version": "1.0.0",
            "timestamp": "2026-07-30T12:00:00",
            "exception": {"type": "ValueError", "message": "test"},
        }
        path = tmp_path / "crash.safedump.json"
        path.write_text(json.dumps(v0_report), encoding="utf-8")

        data = load_report(path)
        assert data["schema_version"] == CRASH_REPORT_SCHEMA_VERSION
        assert data["fingerprint"] == ""
        assert data["occurrence_count"] == 1

    def test_load_report_v1_read(self, tmp_path):
        v1_report = {
            "schema_version": 1,
            "safedump_version": "1.1.0",
            "fingerprint": "abc123def456",
            "occurrence_count": 1,
            "first_seen": "2026-07-30T12:00:00",
            "last_seen": "2026-07-30T12:00:00",
            "timestamp": "2026-07-30T12:00:00",
            "exception": {"type": "ValueError", "message": "test"},
        }
        path = tmp_path / "crash.safedump.json"
        path.write_text(json.dumps(v1_report), encoding="utf-8")

        data = load_report(path)
        assert data["schema_version"] == CRASH_REPORT_SCHEMA_VERSION
        assert data["fingerprint"] == "abc123def456"
