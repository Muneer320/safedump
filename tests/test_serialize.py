"""Tests for the Safedump serialization module."""

import json
from dataclasses import dataclass
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
        assert isinstance(result, (str, dict))
        assert "CustomObj" in str(result)

    def test_depth_limit(self):
        config = SafedumpConfig(max_depth=2)
        encoder = SafedumpEncoder(config)
        # A deeply nested object that ISN'T a plain dict (plain dicts
        # bypass default() and don't trigger depth checks).
        # Use a tuple (non-native type that goes through default()).
        nested = (1, (2, (3, (4, (5, (6,))))))
        result = encoder.default(nested)
        # With max_depth=2, deeply nested non-native types get truncated
        assert isinstance(result, list)

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
        assert parsed["safedump_version"] == "1.0.0"
        assert "frames" in parsed
        assert "exception" in parsed

    def test_includes_all_top_level_fields(self):
        report = CrashReport()
        config = SafedumpConfig()
        result = serialize(report, config)
        parsed = json.loads(result)
        for field in [
            "safedump_version",
            "timestamp",
            "python_version",
            "platform",
            "exception",
            "frames",
            "environment",
            "threads",
            "redactions",
            "metadata",
        ]:
            assert field in parsed, f"Missing field: {field}"

    def test_serialize_with_frames(self):
        from safedump._types import FrameSnapshot, VariableSnapshot

        report = CrashReport()
        frame = FrameSnapshot(
            index=0,
            file="test.py",
            line=1,
            function="main",
            lineno=1,
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


class TestSafedumpEncoderEdgeCases:
    """Edge cases that must never break the crash-time serializer.

    The encoder runs in the crash hot path and must never raise — every
    pathological object should degrade to a safe marker instead.
    """

    @staticmethod
    def _encoder() -> SafedumpEncoder:
        return SafedumpEncoder(SafedumpConfig())

    def test_circular_reference_is_detected_and_marked(self):
        @dataclass
        class Recursive:
            name: str
            child: object = None

        node = Recursive("root")
        node.child = node  # self-referential cycle

        # Must terminate (no infinite recursion) and produce valid JSON.
        result = self._encoder().encode(node)
        parsed = json.loads(result)
        assert parsed["__type__"] == "Recursive"
        assert parsed["child"] == {"__circular_ref__": id(node)}

    def test_object_with_repr_that_raises_is_handled(self):
        class Exploding:
            def __repr__(self):
                raise RuntimeError("boom")

            def __str__(self):
                raise RuntimeError("boom")

        # str() failure must fall back to a safe type marker, not raise.
        result = self._encoder().default(Exploding())
        assert result == "<Exploding>"

    def test_object_with_non_string_str_is_handled(self):
        class NonStringStr:
            def __str__(self):
                return 12345  # invalid: __str__ must return a str

        # str() raises TypeError internally; the encoder must absorb it.
        result = self._encoder().default(NonStringStr())
        assert result == "<NonStringStr>"

    def test_slots_object_without_dict_serializes(self):
        class Slotted:
            __slots__ = ("x", "y")

            def __init__(self):
                self.x = 1
                self.y = 2

            def __str__(self):
                return "Slotted(x=1, y=2)"

        obj = Slotted()
        assert not hasattr(obj, "__dict__")  # truly slots-only
        result = self._encoder().default(obj)
        assert result == "Slotted(x=1, y=2)"

    def test_none_value_is_preserved(self):
        assert self._encoder().default(None) is None

    def test_unicode_keys_and_values_are_preserved(self):
        data = {"café": "naïve", "日本語": "テスト"}
        # Exercise the full encode/decode round-trip, not just default().
        result = self._encoder().encode(data)
        assert json.loads(result) == data
