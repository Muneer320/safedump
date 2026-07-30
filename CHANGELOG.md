# Changelog

## [1.2.0] — 2026-07-30

### Added
- **HTML crash report export** — `safedump view --html [output.html]` generates a self-contained crash report viewer (no external resources, dark theme) (by @Foaly)
- **Local web server** — `safedump serve` starts a web UI for browsing reports via `http.server`, reuses HTML renderer (by @Foaly)
- **CLI report filtering** — `safedump list --type KeyError --since 7d --search error` with human-readable time formats (by @Foaly)
- **`safedump doctor`** — diagnostic command with 5 checks (Python version, output dir, hooks, report integrity, Rich availability) (by @Foaly)
- **`safedump stats`** — aggregate crash statistics with ASCII bar charts (by @Foaly)
- **Crash fingerprint** — stable SHA256 fingerprint per crash, displayed in list output, included in report JSON (by @Foaly)
- **Schema version** — `schema_version` field added to report format (v1), migration framework for forward compatibility (by @Foaly)
- **Extended data model** — `occurrence_count`, `first_seen`, `last_seen` fields for future deduplication (by @Foaly)
- **`__main__.py`** — allow `python -m safedump` usage (by @Foaly)

### Changed
- **`_capture.py` split** — frame walking extracted to `_frame_walker.py` (206 lines), hook management in `_capture.py` (264 lines) (by @Foaly)
- **`metadata` field** — type widened from `dict[str, str]` to `dict[str, Any]` (by @Foaly)
- **Migration framework** — old v0 reports auto-migrated on load via `_loader.py` (by @Foaly)

### Tests
- **173 tests** (up from 107) — 66 new tests across capture engine, frame walker, HTML renderer, loader, and CLI
- **Capture engine coverage** — from ~18% to ~75%
- **CLI tests** — smoke tests for all subcommands (view, list, clean, test, doctor, stats, serve)
- **HTML renderer tests** — 20 tests: XSS prevention, external URL detection, Unicode, empty state
- **Migration tests** — v0-to-v1 schema migration verified

## [1.1.0] — 2026-07-09

### Added
- **Framework integration guides** — Flask, FastAPI, Django docs at `docs/frameworks/` (by @TunahanB)
- **`safedump view --json` flag** — output raw JSON for piping to `jq` (by @SemTiOne)
- **Capture-layer edge case tests** — MemoryError, KeyboardInterrupt, SystemExit, Unicode, None values (by @Diyaaa-12)
- **Serializer edge-case tests** — circular references, broken `__repr__`, `__slots__` objects (by @uttam12331)

### Fixed
- **Friendly error when Rich is missing** — `safedump view` now shows `pip install safedump[view]` hint instead of traceback (by @SemTiOne)
- **Dynamic version** — `--version` reads from `importlib.metadata` instead of hardcoded string (by @Diyaaa-12)
- **Windows `_run_crash` path** — uses tempfile instead of `-c` to avoid backslash escaping issues (by @Diyaaa-12)

### Docs
- Framework integration guides (Flask, FastAPI, Django)
- CodeRabbit review fixes applied before merge

## [1.0.0] — 2026-06-25

### Added
- **Stable public API** — 11 functions frozen: `configure`, `install`, `uninstall`,
  `capture_exception`, `test`, `load_report`, `register_serializer`, `enable`,
  `disable`, `RedactionRule`, `__version__`
- **Plugin architecture** — `register_serializer()` for custom type serialization
- **Cross-thread capture** — all threads captured at crash time via `threading.enumerate()`
- **Config presets** — `configure(preset="production")`, `"development"`, `"debug"`, `"minimal"`
- **`safedump clean --older-than DAYS`** — report rotation
- **Full crash capture** with frame walking, local variables, exception chains (Python 3.9–3.13)
- **ExceptionGroup support** (Python 3.11+) and `__cause__`/`__context__` chaining
- **Secret redaction** — variable name denylist + regex credential detection + custom rules
- **`before_capture` hook** for application-specific scrubbing
- **Three exception hooks** — `sys.excepthook`, `threading.excepthook`, `sys.unraisablehook`
- **Versioned JSON crash report format** with schema validation
- **Atomic file writes** with 0o600 permissions and `/tmp` fallback
- **Pre-allocated fallback buffer** for MemoryError scenarios
- **Double-fault guard** — original traceback always preserved
- **Rich-powered terminal viewer** (`safedump view`) with syntax highlighting
- **CLI subcommands** — `view`, `list`, `clean`, `test`
- **Privacy tiers 0–4** with configurable capture levels
- **Environment variable name capture** (values never captured by default)
- **67 tests** (unit + integration) across 5 Python versions
- **CI/CD workflows** — lint, type-check, test matrix (3.9–3.13), build, PyPI publish

### Fixed
- `--version` now shows correct version from `safedump.__version__`
- Python 3.9 compatibility for `X | Y` union syntax
