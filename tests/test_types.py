"""Tests for the Safedump data model."""

import pytest

from safedump._types import (
    CrashReport,
    FrameSnapshot,
    SafedumpConfig,
    is_denylisted,
)


class TestSafedumpConfig:
    def test_default_config(self):
        config = SafedumpConfig()
        assert config.privacy_tier == 1
        assert config.max_string_length == 10000
        assert config.max_depth == 5

    def test_invalid_privacy_tier(self):
        with pytest.raises(ValueError, match="privacy_tier"):
            SafedumpConfig(privacy_tier=99)

    def test_invalid_max_string_length(self):
        with pytest.raises(ValueError, match="max_string_length"):
            SafedumpConfig(max_string_length=50)

    def test_invalid_max_collection_items(self):
        with pytest.raises(ValueError, match="max_collection_items"):
            SafedumpConfig(max_collection_items=0)

    def test_invalid_max_depth(self):
        with pytest.raises(ValueError, match="max_depth"):
            SafedumpConfig(max_depth=0)


class TestDenylist:
    def test_exact_match_short_patterns(self):
        assert is_denylisted("key")
        assert is_denylisted("pwd")
        assert is_denylisted("pin")

    def test_exact_match_not_substring(self):
        assert not is_denylisted("monkey")
        assert not is_denylisted("keyboard")
        assert not is_denylisted("spindown")

    def test_word_boundary_match(self):
        assert is_denylisted("user_pass")
        assert is_denylisted("auth_token")

    def test_word_boundary_not_in_word(self):
        assert not is_denylisted("passive")
        assert not is_denylisted("author")

    def test_substring_match_long_patterns(self):
        assert is_denylisted("api_token")
        assert is_denylisted("my_secret_key")
        assert is_denylisted("db_password")

    def test_case_insensitive(self):
        assert is_denylisted("PASSWORD")
        assert is_denylisted("Api_Key")
        assert is_denylisted("SecretToken")


class TestCrashReport:
    def test_default_construction(self):
        report = CrashReport()
        assert report.safedump_version == "1.0.0"
        assert len(report.frames) == 0
        assert len(report.redactions) == 0

    def test_can_add_frames(self):
        report = CrashReport()
        frame = FrameSnapshot(index=0, file="test.py", line=1, function="test", lineno=1)
        report.frames.append(frame)
        assert len(report.frames) == 1
        assert report.frames[0].function == "test"
