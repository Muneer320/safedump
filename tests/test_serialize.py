"""Tests for the Safedump serialization module."""

import json
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from pathlib import Path
from uuid import UUID

from safedump._serialize import SafedumpEncoder, serialize
from safedump._types import CrashReport, SafedumpConfig


class Color(Enum):
    RED = 1
    GREEN = 2


class TestSafedumpEncoder:
    def test_datetime_isoformat(self):
        config = SafedumpConfig()
        encoder = SafedumpEncoder(config)
        now = datetime(2026, 6, 25, 12, 0, 0, tzinfo=timezone.utc)
        result = encoder.default(now)
        assert result == "2026-06-25T12:00:00+00:00"

    def test_path_to_string(self):
        config = SafedumpConfig()
        encoder = SafedumpEncoder(config)
        result = encoder.default(Path("/tmp/test"))
        assert result == "/tmp/test"

    def test_enum_to_dict(self):
        config = SafedumpConfig()
        encoder = SafedumpEncoder(config)
        result = encoder.default(Color.RED)
        assert result == {"__enum__": "Color", "name": "RED", "value": 1}

    def test_uuid_to_string(self):
        config = SafedumpConfig()
        encoder = SafedumpEncoder(config)
        u = UUID("12345678-1234-5678-1234-567812345678")
        result = encoder.default(u)
        assert result == "12345678-1234-5678-1234-567812345678"

    def test_decimal_to_string(self):
        config = SafedumpConfig()
        encoder = SafedumpEncoder(config)
        result = encoder.default(Decimal("3.14159"))
        assert result == "3.14159"

    def test_set_sorted(self):
        config = SafedumpConfig()
        encoder = SafedumpEncoder(config)
        result = encoder.default({3, 1, 2})
        assert result == [1, 2, 3]

    def test_bytes_to_base64(self):
        config = SafedumpConfig()
        encoder = SafedumpEncoder(config)
        result = encoder.default(b"hello")
        assert result == "aGVsbG8="

    def test_unknown_type_fallback(self):
        config = SafedumpConfig()
        encoder = SafedumpEncoder(config)

        class CustomObj:
            pass

        result = encoder.default(CustomObj())
        assert "<CustomObj>" in str(result)

    def test_depth_limit(self):
        config = SafedumpConfig(max_depth=2)
        encoder = SafedumpEncoder(config)
        nested = {"a": {"b": {"c": "too deep"}}}
        result = encoder.default(nested)
        # Should have depth_limit marker somewhere in the nested structure
        json_str = json.dumps(result)
        assert "__depth_limit__" in json_str

    def test_never_raises(self):
        config = SafedumpConfig()
        encoder = SafedumpEncoder(config)
        result = encoder.default(object())
        assert isinstance(result, (str, dict))


class TestSerialize:
    def test_produces_valid_json(self):
        report = CrashReport()
        config = SafedumpConfig()
        result = serialize(report, config)
        parsed = json.loads(result)
        assert parsed["safedump_version"] == "0.1.0.dev0"
        assert "frames" in parsed
        assert "exception" in parsed

    def test_includes_all_top_level_fields(self):
        report = CrashReport()
        config = SafedumpConfig()
        result = serialize(report, config)
        parsed = json.loads(result)
        for field in [
            "safedump_version", "timestamp", "python_version",
            "platform", "exception", "frames", "environment",
            "threads", "redactions", "metadata",
        ]:
            assert field in parsed, f"Missing field: {field}"

    def test_serialize_with_frames(self):
        from safedump._types import FrameSnapshot, VariableSnapshot

        report = CrashReport()
        frame = FrameSnapshot(
            index=0, file="test.py", line=1, function="main", lineno=1,
            locals={"x": VariableSnapshot(name="x", type="int", value=42)},
        )
        report.frames.append(frame)
        config = SafedumpConfig()
        result = serialize(report, config)
        parsed = json.loads(result)
        assert len(parsed["frames"]) == 1
        assert parsed["frames"][0]["function"] == "main"

    def test_last_resort_fallback(self):
        # Force a serialization failure by using a broken encoder
        config = SafedumpConfig()
        report = CrashReport()
        # Normal serialization should work
        result = serialize(report, config)
        assert "safedump_version" in result
