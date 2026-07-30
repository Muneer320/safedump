# SPDX-FileCopyrightText: 2026 Muneer Alam
#
# SPDX-License-Identifier: MIT


"""Tests for the Safedump data model."""

import pytest

from safedump._frame_walker import compute_fingerprint
from safedump._types import (
    CrashReport,
    ExceptionSnapshot,
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


class TestFingerprint:
    """Fingerprint generation tests."""

    def test_same_report_same_fingerprint(self):
        r1 = CrashReport(
            exception=ExceptionSnapshot(type="ValueError", message="test"),
            frames=[FrameSnapshot(index=0, file="app.py", line=42, function="main", lineno=42)],
        )
        r2 = CrashReport(
            exception=ExceptionSnapshot(type="ValueError", message="test"),
            frames=[FrameSnapshot(index=0, file="app.py", line=42, function="main", lineno=42)],
        )
        f1 = compute_fingerprint(r1)
        f2 = compute_fingerprint(r2)
        assert f1 == f2

    def test_different_exception_different_fingerprint(self):
        r1 = CrashReport(
            exception=ExceptionSnapshot(type="ValueError", message="test"),
            frames=[FrameSnapshot(index=0, file="app.py", line=42, function="main", lineno=42)],
        )
        r2 = CrashReport(
            exception=ExceptionSnapshot(type="KeyError", message="missing"),
            frames=[FrameSnapshot(index=0, file="app.py", line=42, function="main", lineno=42)],
        )
        assert compute_fingerprint(r1) != compute_fingerprint(r2)

    def test_different_location_different_fingerprint(self):
        r1 = CrashReport(
            exception=ExceptionSnapshot(type="ValueError", message="test"),
            frames=[FrameSnapshot(index=0, file="app.py", line=42, function="main", lineno=42)],
        )
        r2 = CrashReport(
            exception=ExceptionSnapshot(type="ValueError", message="test"),
            frames=[FrameSnapshot(index=0, file="app.py", line=99, function="main", lineno=99)],
        )
        assert compute_fingerprint(r1) != compute_fingerprint(r2)

    def test_fingerprint_12_chars(self):
        report = CrashReport(
            exception=ExceptionSnapshot(type="ValueError", message="test"),
            frames=[FrameSnapshot(index=0, file="app.py", line=42, function="main", lineno=42)],
        )
        fp = compute_fingerprint(report)
        assert len(fp) == 12
        assert all(c in "0123456789abcdef" for c in fp)

    def test_fingerprint_no_frames(self):
        """A report with no frames gets a fingerprint based on exception only."""
        report = CrashReport(
            exception=ExceptionSnapshot(type="ValueError", message="no frames"),
        )
        fp = compute_fingerprint(report)
        assert len(fp) == 12

    def test_default_construction(self):
        report = CrashReport()
        assert report.safedump_version == "2.0.0"
        assert len(report.frames) == 0
        assert len(report.redactions) == 0

    def test_can_add_frames(self):
        report = CrashReport()
        frame = FrameSnapshot(index=0, file="test.py", line=1, function="test", lineno=1)
        report.frames.append(frame)
        assert len(report.frames) == 1
        assert report.frames[0].function == "test"


class TestNewPatterns:
    """测试新加的 5 个脱敏模式"""

    def test_passphrase_detected(self):
        assert is_denylisted("ssl_passphrase")
        assert is_denylisted("passphrase")
        assert is_denylisted("my_passphrase")

    def test_certificate_detected(self):
        assert is_denylisted("ssl_certificate")
        assert is_denylisted("certificate_path")
        assert is_denylisted("my_certificate")

    def test_encryption_key_detected(self):
        assert is_denylisted("encryption_key")
        assert is_denylisted("my_encryption_key")
        assert is_denylisted("aes_encryption_key")

    def test_signing_key_detected(self):
        assert is_denylisted("signing_key")
        assert is_denylisted("my_signing_key")
        assert is_denylisted("signing_key_path")

    def test_bearer_detected(self):
        assert is_denylisted("bearer_token")
        assert is_denylisted("bearer")
        assert is_denylisted("my_bearer")
