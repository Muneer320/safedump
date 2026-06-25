# Changelog

All notable changes to Safedump will be documented in this file.

## [0.1.0] — 2026-06-25

### Added
- Core crash capture with frame walking (Python 3.9–3.13)
- Local variable capture with type information
- Exception chaining support (__cause__, __context__, ExceptionGroup)
- Secret redaction: variable name denylist + regex pattern detection
- Custom redaction rules via `RedactionRule`
- `before_capture` hook for application-specific scrubbing
- Versioned JSON crash report format
- Atomic file writes with 0o600 permissions
- /tmp fallback when primary output_dir is unwritable
- Rich-powered terminal viewer (`safedump view`)
- Crash report listing (`safedump list`)
- Self-test (`safedump test`)
- Configuration with eager validation
- Privacy tiers (0–4) with configurable capture levels
- Environment variable name capture
- Thread information capture
- Pre-allocated fallback buffer for MemoryError scenarios
- Double-fault guard — original traceback always preserved
- Public API: `configure`, `install`, `uninstall`, `enable`, `disable`,
  `capture_exception`, `test`, `load_report`, `RedactionRule`
- 67 tests (unit + integration)
- CI/CD workflows (lint, type-check, test matrix 3.9–3.13, build)

## [0.0.0] — 2026-06-25

### Added
- Repository bootstrap and project infrastructure
