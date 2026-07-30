# SPDX-FileCopyrightText: 2026 Muneer Alam
#
# SPDX-License-Identifier: MIT


"""Tests for the Safedump sanitization module."""

from safedump._sanitize import _compute_shannon_entropy, _detect_secret, sanitize
from safedump._types import (
    CrashReport,
    EnvironmentSnapshot,
    ExceptionSnapshot,
    FrameSnapshot,
    SafedumpConfig,
    VariableSnapshot,
)

AWS_KEY = "AKIA0000000000000000"
GITHUB_TOKEN = "ghp_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
JWT_TOKEN = "eyJhbbbbb.eyJjddddd.signnnnn"


def make_report_with_locals(locals_dict):
    variables = {
        name: VariableSnapshot(name=name, type="str", value=value)
        for name, value in locals_dict.items()
    }
    frame = FrameSnapshot(
        index=0,
        file="test.py",
        line=1,
        function="test_func",
        lineno=1,
        locals=variables,
    )
    return CrashReport(
        exception=ExceptionSnapshot(type="ValueError", message="test error"),
        frames=[frame],
    )


class TestDetectSecret:
    def test_detects_aws_key(self):
        patterns = [r"AKIA[0-9A-Z]{16}"]
        assert _detect_secret(AWS_KEY, patterns) is not None

    def test_no_match_normal_string(self):
        patterns = [r"AKIA[0-9A-Z]{16}"]
        assert _detect_secret("hello world", patterns) is None

    def test_github_token(self):
        patterns = [r"ghp_[0-9a-zA-Z]{36}"]
        assert _detect_secret(GITHUB_TOKEN, patterns) is not None

    def test_jwt_token(self):
        patterns = [r"eyJ[a-zA-Z0-9_-]+\.eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+"]
        assert _detect_secret(JWT_TOKEN, patterns) is not None

    def test_invalid_pattern_does_not_raise(self):
        assert _detect_secret("anything", [r"["]) is None


class TestEntropyDetection:
    """Shannon entropy secret detection tests."""

    def test_low_entropy_string(self):
        """Normal text should not trigger entropy detection."""
        assert _compute_shannon_entropy("hello world this is normal text") <= 4.5

    def test_high_entropy_string(self):
        """Random-looking strings should trigger detection."""
        entropy = _compute_shannon_entropy("aK9#mP2$xR7&vB4@nQ1!zW5*cE8")
        assert entropy >= 4.5

    def test_empty_string_entropy_zero(self):
        assert _compute_shannon_entropy("") == 0.0

    def test_single_char_entropy_zero(self):
        assert _compute_shannon_entropy("aaaaaa") == 0.0

    def test_entropy_skipped_when_disabled(self, tmp_path):
        """When enable_entropy_detection is False, high-entropy values are preserved."""
        config = SafedumpConfig(enable_entropy_detection=False, output_dir=tmp_path)
        report = CrashReport()
        report.frames.append(
            FrameSnapshot(
                index=0,
                file="test.py",
                line=1,
                function="test",
                lineno=1,
                locals={
                    "user_value": VariableSnapshot(
                        name="user_value",
                        type="str",
                        value="aK9#mP2$xR7&vB4@nQ1!zW5*cE8test",
                    ),
                },
            )
        )
        result = sanitize(report, config)
        frame = result.frames[0]
        assert frame.locals["user_value"].value != "[REDACTED]"

    def test_entropy_triggers_when_enabled(self, tmp_path):
        """When enabled, high-entropy values should be redacted."""
        config = SafedumpConfig(enable_entropy_detection=True, output_dir=tmp_path)
        report = CrashReport()
        report.frames.append(
            FrameSnapshot(
                index=0,
                file="test.py",
                line=1,
                function="test",
                lineno=1,
                locals={
                    "random_token": VariableSnapshot(
                        name="random_token",
                        type="str",
                        value="aK9#mP2$xR7&vB4@nQ1!zW5*cE8testvalue123456",
                    ),
                },
            )
        )
        result = sanitize(report, config)
        frame = result.frames[0]
        assert frame.locals["random_token"].value == "[REDACTED]"

    def test_entropy_skips_short_strings(self, tmp_path):
        """Strings shorter than 16 chars should not trigger entropy detection."""
        config = SafedumpConfig(enable_entropy_detection=True, output_dir=tmp_path)
        report = CrashReport()
        report.frames.append(
            FrameSnapshot(
                index=0,
                file="test.py",
                line=1,
                function="test",
                lineno=1,
                locals={
                    "short": VariableSnapshot(
                        name="short",
                        type="str",
                        value="xyz123!",
                    ),
                },
            )
        )
        result = sanitize(report, config)
        frame = result.frames[0]
        assert frame.locals["short"].value == "xyz123!"

    def test_entropy_record_added(self, tmp_path):
        """Entropy redactions should be recorded."""
        config = SafedumpConfig(enable_entropy_detection=True, output_dir=tmp_path)
        report = CrashReport()
        report.frames.append(
            FrameSnapshot(
                index=0,
                file="test.py",
                line=1,
                function="test",
                lineno=1,
                locals={
                    "high_entropy": VariableSnapshot(
                        name="high_entropy",
                        type="str",
                        value="aK9#mP2$xR7&vB4@nQ1!zW5*cE8testval123456",
                    ),
                },
            )
        )
        result = sanitize(report, config)
        assert any("entropy" in r.rule for r in result.redactions)


class TestSanitize:
    def test_redacts_denylisted_variable_name(self):
        report = make_report_with_locals({"password": "hunter2"})
        config = SafedumpConfig()
        result = sanitize(report, config)
        assert result.frames[0].locals["password"].value == "[REDACTED]"
        assert len(result.redactions) >= 1
        assert any("denylist" in r.reason for r in result.redactions)

    def test_redacts_secret_in_value(self):
        report = make_report_with_locals({"data": AWS_KEY})
        config = SafedumpConfig()
        result = sanitize(report, config)
        assert result.frames[0].locals["data"].value == "[REDACTED]"

    def test_leaves_normal_values_alone(self):
        report = make_report_with_locals({"x": "42", "name": "Alice"})
        config = SafedumpConfig()
        result = sanitize(report, config)
        assert result.frames[0].locals["x"].value == "42"

    def test_multiple_redactions_recorded(self):
        report = make_report_with_locals({"password": "x", "api_token": GITHUB_TOKEN})
        config = SafedumpConfig()
        result = sanitize(report, config)
        assert len(result.redactions) >= 2

    def test_does_not_raise_on_any_input(self):
        report = CrashReport()
        config = SafedumpConfig()
        result = sanitize(report, config)
        assert isinstance(result, CrashReport)

    def test_exception_message_sanitized(self):
        report = CrashReport(
            exception=ExceptionSnapshot(type="ValueError", message=f"key: {GITHUB_TOKEN}")
        )
        config = SafedumpConfig()
        result = sanitize(report, config)
        assert "ghp_" not in result.exception.message

    def test_argv_sanitized(self):
        report = CrashReport(environment=EnvironmentSnapshot(argv=["--t", GITHUB_TOKEN]))
        config = SafedumpConfig()
        result = sanitize(report, config)
        assert result.environment.argv is not None
        assert result.environment.argv[1] == "[REDACTED]"

    def test_env_var_names_removed_if_denylisted(self):
        report = CrashReport(
            environment=EnvironmentSnapshot(env_var_names=["PATH", "DATABASE_URL", "HOME"])
        )
        config = SafedumpConfig()
        result = sanitize(report, config)
        assert "DATABASE_URL" not in result.environment.env_var_names

    def test_case_insensitive_denylist(self):
        report = make_report_with_locals({"PASSWORD": "secret"})
        config = SafedumpConfig()
        result = sanitize(report, config)
        assert result.frames[0].locals["PASSWORD"].value == "[REDACTED]"
