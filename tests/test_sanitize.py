"""Tests for the Safedump sanitization module."""

from safedump._sanitize import _detect_secret, sanitize
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
