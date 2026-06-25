"""Tests for the Safedump configuration module."""

from pathlib import Path

import pytest

from safedump._config import configure, get_config, reset_config
from safedump._types import RedactionRule, SafedumpConfig


class TestConfigure:
    def test_defaults(self):
        reset_config()
        configure()
        config = get_config()
        assert config.privacy_tier == 1
        assert config.max_depth == 5
        assert config.include_env_names is True
        assert config.include_argv is False
        assert str(config.output_dir).endswith(".safedump")

    def test_custom_values(self):
        reset_config()
        configure(
            output_dir="/tmp/test-crashes",
            privacy_tier=2,
            max_string_length=500,
            max_depth=3,
            include_argv=True,
        )
        config = get_config()
        assert config.privacy_tier == 2
        assert config.max_string_length == 500
        assert config.max_depth == 3
        assert config.include_argv is True

    def test_eager_validation(self):
        with pytest.raises(ValueError, match="privacy_tier"):
            configure(privacy_tier=-1)
        with pytest.raises(ValueError, match="privacy_tier"):
            configure(privacy_tier=5)
        with pytest.raises(ValueError, match="max_string_length"):
            configure(max_string_length=99)
        with pytest.raises(ValueError, match="max_depth"):
            configure(max_depth=0)

    def test_multiple_calls_replace_config(self):
        reset_config()
        configure(privacy_tier=1)
        assert get_config().privacy_tier == 1
        configure(privacy_tier=3)
        assert get_config().privacy_tier == 3

    def test_string_rules_auto_converted(self):
        reset_config()
        configure(redaction_rules=["my-pattern-\\d+"])
        config = get_config()
        assert len(config.redaction_rules) == 1
        assert isinstance(config.redaction_rules[0], RedactionRule)
        assert config.redaction_rules[0].pattern == "my-pattern-\\d+"
        assert config.redaction_rules[0].replacement == "[REDACTED]"
        assert config.redaction_rules[0].apply_to == "values"

    def test_mixed_string_and_rule(self):
        reset_config()
        configure(
            redaction_rules=[
                "auto-convert-pattern",
                RedactionRule("explicit", "***", "names"),
            ]
        )
        config = get_config()
        assert len(config.redaction_rules) == 2
        assert config.redaction_rules[0].pattern == "auto-convert-pattern"
        assert config.redaction_rules[1].apply_to == "names"

    def test_output_dir_expands_home(self):
        reset_config()
        configure(output_dir="~/my-crashes")
        config = get_config()
        assert str(config.output_dir) == str(Path.home() / "my-crashes")

    def test_before_capture_stored(self):
        reset_config()

        def my_hook(report):
            return report

        configure(before_capture=my_hook)
        assert get_config().before_capture is my_hook


class TestGetConfig:
    def test_returns_live_reference(self):
        reset_config()
        configure()
        c1 = get_config()
        c2 = get_config()
        assert c1 is c2  # same object

    def test_creates_default_if_never_configured(self):
        reset_config()
        config = get_config()
        assert isinstance(config, SafedumpConfig)
        assert config.privacy_tier == 1


class TestResetConfig:
    def test_resets_to_none(self):
        configure(privacy_tier=3)
        assert get_config().privacy_tier == 3
        reset_config()
        # After reset, get_config creates a fresh default
        config = get_config()
        assert config.privacy_tier == 1
