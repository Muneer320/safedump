"""Tests for the Safedump serializer."""

from __future__ import annotations

import json

from safedump._serialize import serialize
from safedump._types import CRASH_REPORT_SCHEMA_VERSION, CrashReport, SafedumpConfig, __version__


class TestSerialize:
    def test_produces_valid_json(self):
        report = CrashReport()
        config = SafedumpConfig()
        result = serialize(report, config)
        assert isinstance(result, str)
        parsed = json.loads(result)
        assert parsed["safedump_version"] == __version__
        assert "frames" in parsed
        assert "exception" in parsed

    def test_serializes_schema_version(self):
        report = CrashReport()
        config = SafedumpConfig()
        result = json.loads(serialize(report, config))
        assert result["schema_version"] == CRASH_REPORT_SCHEMA_VERSION

    def test_serializes_fingerprint(self):
        report = CrashReport()
        config = SafedumpConfig()
        result = json.loads(serialize(report, config))
        assert "fingerprint" in result
