# Changelog

This page lists notable changes to Safedump.

For the full changelog, see [CHANGELOG.md](https://github.com/Muneer320/safedump/blob/main/CHANGELOG.md) on GitHub.

## v2.1.0 — Correctness & Hardening (2026-10-01)

- Privacy tiers, presets, thread/unraisable capture and `register_serializer()` work as documented
- Secrets are redacted before values are truncated (no partial leaks)
- Crash site and fingerprint use the frame that raised
- Compression works with deduplication, filters and stats
- `SAFEDUMP_DIR` environment variable and `safedump --dir`
- `safedump test` works without `install()`
- `safedump serve`: no CORS, Host header check, token for deletes
- Report schema v2 (older reports migrate automatically)

## v1.3.0 — Smart Detection (2026-07-30)

- Entropy-based secret detection (opt-in)
- Crash report deduplication by fingerprint
- Optional gzip report compression
- `on_crash` notification hook
- pytest integration plugin
- Click/Typer integration (`@wrap_click()`)
- 181 tests

## v1.2.0 — Foundation & Shareability (2026-07-30)

- Schema versioning and migration framework
- Crash fingerprint generation
- HTML crash report export (`--html`)
- CLI report filtering (`--type`, `--since`)
- `safedump doctor`, `safedump stats`
- `safedump serve` local web server
- Module refactoring (`_capture.py` split)
- 172 tests

## v1.1.0 — Community & Integration (2026-07-09)

- Framework integration guides (Flask, FastAPI, Django)
- `safedump view --json` flag
- Capture-layer edge case tests
- Improved error handling for missing Rich
- Dynamic version via importlib.metadata
- Windows compatibility fixes

## v1.0.0 — Stable API (2026-06-25)

- Stable public API (12 functions)
- Full crash capture pipeline
- Secret redaction (denylist + regex)
- Three exception hooks (sys, threading, unraisable)
- CLI subcommands (view, list, clean, test)
- Privacy tiers (0-4)
- Rich-powered terminal viewer
- Config presets
- 67 tests across 5 Python versions
