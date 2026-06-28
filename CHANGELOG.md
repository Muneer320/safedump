# Changelog

## [Unreleased]

### Fixed
- **`safedump view` without Rich now shows a friendly install hint** instead of an
  unfriendly traceback. When Rich is not installed, `render()` prints
  `Rich is not installed — install it for formatted output: pip install "safedump[view]"`
  to stderr and falls back to plain-text output. Fixes [#9](https://github.com/Muneer320/safedump/issues/9).

## [1.0.0] — 2026-06-25

### Added
- **Stable public API** — 11 functions frozen: `configure`, `install`, `uninstall`,
  `capture_exception`, `test`, `load_report`, `register_serializer`, `enable`,
  `disable`, `RedactionRule`, `__version__`
- **Plugin architecture** — `register_serializer()` for custom type serialization
- **Cross-thread capture** — all threads captured at crash time
- **Config presets** — `configure(preset="production")` shorthand
- **`safedump clean --older-than DAYS`** — report rotation
- Core crash capture with frame walking (Python 3.9–3.13)
- Local variable capture with type information
- Exception chaining support (__cause__, __context__, ExceptionGroup)
- Secret redaction: variable name denylist + regex pattern detection
- Custom redaction rules via `RedactionRule`
- `before_capture` hook for application-specific scrubbing
- Versioned JSON crash report format
- Atomic file writes with 0o600 permissions
- Rich-powered terminal viewer (`safedump view`)
- Crash report listing (`safedump list`)
- Self-test (`safedump test`)
- Privacy tiers (0–4) with configurable capture levels
- Double-fault guard — original traceback always preserved
- 67 tests (unit + integration)
- CI/CD workflows (lint, type-check, test matrix 3.9–3.13, build)

### Changed
- **API stability guarantee** — semver enforced from v1.0.0 onward
- **Deprecation policy** — 2 minor versions of DeprecationWarning before removal

## [0.1.0] — 2026-06-25

Initial release.
