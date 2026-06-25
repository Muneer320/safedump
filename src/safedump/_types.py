"""Internal types and constants for Safedump.

These are NOT part of the public API. They may change without notice.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, NamedTuple

# ── Version ──────────────────────────────────────────────────────────

__version__ = "0.1.0"

# ── Configuration ────────────────────────────────────────────────────


class RedactionRule(NamedTuple):
    """A custom secret redaction rule (internal representation).

    Args:
        pattern: Regex pattern to match.
        replacement: Text to replace matches with. Defaults to ``[REDACTED]``.
        apply_to: Where to apply the rule — ``"values"``, ``"names"``, or ``"both"``.
    """

    pattern: str
    replacement: str = "[REDACTED]"
    apply_to: str = "values"  # "values" | "names" | "both"


@dataclass
class SafedumpConfig:
    """Validated, immutable configuration."""

    output_dir: Path = field(default_factory=lambda: Path.home() / ".safedump")
    privacy_tier: int = 1
    include_env_names: bool = True
    include_argv: bool = False
    max_string_length: int = 10000
    max_collection_items: int = 100
    max_depth: int = 5
    max_report_size_bytes: int = 10_485_760  # 10 MB
    generation_timeout_seconds: int = 30
    redaction_rules: list[RedactionRule] = field(default_factory=list)
    before_capture: Callable[[Any], Any | None] | None = None

    def __post_init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
        if not 0 <= self.privacy_tier <= 4:
            raise ValueError(f"privacy_tier must be 0-4, got {self.privacy_tier}")
        if self.max_string_length < 100:
            raise ValueError(f"max_string_length must be >= 100, got {self.max_string_length}")
        if self.max_collection_items < 1:
            raise ValueError(f"max_collection_items must be >= 1, got {self.max_collection_items}")
        if self.max_depth < 1:
            raise ValueError(f"max_depth must be >= 1, got {self.max_depth}")

    @property
    def denylist(self) -> list[str]:
        """Variable name denylist — what to redact from captured locals."""
        return list(DENYLIST_SUBSTRING_MATCH)  # placeholder — will expand per C13

    @property
    def secret_patterns(self) -> list[str]:
        """Regex patterns for detecting secrets in values."""
        return [
            r"AKIA[0-9A-Z]{16}",  # AWS Access Key
            r"ghp_[0-9a-zA-Z]{36}",  # GitHub Personal Access Token
            r"gho_[0-9a-zA-Z]{36}",  # GitHub OAuth Token
            r"sk_live_[0-9a-zA-Z]{24}",  # Stripe Live Key
            r"sk_test_[0-9a-zA-Z]{24}",  # Stripe Test Key
            r"eyJ[a-zA-Z0-9_-]+\.eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+",  # JWT
        ]


# ── Denylists ────────────────────────────────────────────────────────
# Tiered matching per Gate Review C13 resolution:
#   ≤3 chars → exact match
#   4 chars  → word-boundary match
#   ≥5 chars → substring match

EXACT_MATCH: set[str] = {"key", "pwd", "pin", "sid", "uid", "cid"}

WORD_BOUNDARY_MATCH: set[str] = {"pass", "auth", "cert", "hash", "salt", "cred"}

DENYLIST_SUBSTRING_MATCH: set[str] = {
    "token",
    "secret",
    "password",
    "passwd",
    "apikey",
    "api_key",
    "credential",
    "authorization",
    "private_key",
    "secret_key",
    "access_key",
    "access_token",
    "refresh_token",
    "session_key",
    "master_key",
    "db_password",
    "database_url",
    "connection_string",
    "aws_secret",
    "aws_key",
    "stripe_key",
    "github_token",
    "ssh_key",
}


def is_denylisted(name: str) -> bool:
    """Check if a variable name matches the denylist.

    Uses tiered matching strategy:
    - ≤3 chars: exact match only
    - 4 chars: word-boundary match (treats _ as boundary)
    - ≥5 chars: case-insensitive substring match
    """
    name_lower = name.lower()

    # Exact match (for short patterns)
    if name_lower in EXACT_MATCH:
        return True

    # Word-boundary match (4-char patterns)
    # Use a pattern that treats underscores as boundaries too
    for pattern in WORD_BOUNDARY_MATCH:
        if re.search(rf"(?:^|_|\b){re.escape(pattern)}(?:\b|_|$)", name_lower):
            return True

    # Substring match (5+ char patterns)
    return any(pattern in name_lower for pattern in DENYLIST_SUBSTRING_MATCH)


# ── Data Model ───────────────────────────────────────────────────────
# These objects form the internal contract between capture,
# sanitize, serialize, storage, loader, and render modules.


@dataclass
class VariableSnapshot:
    """One captured variable."""

    name: str
    type: str
    value: Any
    is_truncated: bool = False
    original_length: int | None = None


@dataclass
class FrameSnapshot:
    """One stack frame captured at crash time."""

    index: int
    file: str
    line: int
    function: str
    lineno: int
    code_context: list[str] = field(default_factory=list)
    locals: dict[str, VariableSnapshot] = field(default_factory=dict)
    is_crash_site: bool = False


@dataclass
class ExceptionSnapshot:
    """One exception in the chain."""

    type: str = ""
    message: str = ""
    module: str = ""
    traceback: list[int] = field(default_factory=list)  # indices into frames list
    sub_exceptions: list[ExceptionSnapshot] = field(default_factory=list)
    is_explicitly_chained: bool = False


@dataclass
class EnvironmentSnapshot:
    """System environment at crash time."""

    os_name: str = ""
    os_version: str = ""
    python_impl: str = "CPython"
    python_path: list[str] = field(default_factory=list)
    cwd: str = ""
    env_var_names: list[str] = field(default_factory=list)
    env_var_values: dict[str, str] = field(default_factory=dict)
    argv: list[str] | None = None


@dataclass
class ThreadSnapshot:
    """One thread at crash time."""

    name: str = ""
    ident: int | None = None
    daemon: bool = False
    crashed: bool = False


@dataclass
class RedactionRecord:
    """Record of what was redacted."""

    location: str
    reason: str
    rule: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class CrashReport:
    """Complete crash report — the root object of the data model."""

    safedump_version: str = __version__
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    python_version: str = field(default_factory=lambda: sys.version)
    platform: str = field(default_factory=lambda: sys.platform)
    exception: ExceptionSnapshot = field(default_factory=ExceptionSnapshot)
    frames: list[FrameSnapshot] = field(default_factory=list)
    environment: EnvironmentSnapshot = field(default_factory=EnvironmentSnapshot)
    threads: list[ThreadSnapshot] = field(default_factory=list)
    redactions: list[RedactionRecord] = field(default_factory=list)
    metadata: dict[str, str] = field(default_factory=dict)
