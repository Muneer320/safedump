# Changelog

## [2.1.0] — 2026-10-01

Fixes for features that 2.0 documented but that did not work, plus a
hardened local web server. Reports now use schema version 2. Older reports
are migrated automatically when loaded.

### Fixed
- **Privacy tiers.** `privacy_tier` had no effect. Now:
  - tier 0 captures no variable or environment data;
  - tier 1 captures redacted locals;
  - tier 2 expands objects into their attributes;
  - tier 3 adds the crash site's module globals;
  - tier 4 adds environment variable values, with secrets redacted.
- **Presets.** `safedump.configure(preset=...)` silently ignored the preset. It is now forwarded.
- **Thread and unraisable crashes.** Crashes in threads and in `__del__` were not captured. The hooks were installed with the wrong signature, so the report described safedump's own `TypeError` and the thread's exception was lost. Python's normal output is still printed.
- **Partial secret leaks.** Locals were cut to about 30 characters (`reprlib` defaults) before redaction ran, so tokens could leak partially. Values are now captured as structured data within `max_string_length`, `max_collection_items` and `max_depth`. Redaction runs first and truncation afterwards.
- **Token patterns.** They now match the whole token, so no tail is left behind after redaction.
- **Custom serializers.** `register_serializer()` handlers were never applied to locals. They now are.
- **Custom redaction rules.** They logged a redaction but left exception messages and plain fields unchanged. Every redaction is now applied before it is recorded. Secrets inside a longer string are replaced in place, so messages stay readable.
- **Nested values.** Dicts nested inside locals have their denylisted keys redacted.
- **Crash site and fingerprint.** These pointed at the outermost frame (the caller) instead of the frame that raised. Deduplication and `stats` by-site were affected. For tracebacks deeper than 100 frames, the innermost frames are now kept.
- **Compression.** `compress=True` combined with deduplication raised `UnicodeDecodeError` on the second identical crash. Filters and `stats` also ignored `.gz` reports.
- **`capture_exception()` / `watch()`.**
  - They kept only 5 frames.
  - They skipped the `before_capture` hook.
  - They mutated the global configuration for per-call overrides, which was not thread-safe.
- **`safedump test`.** It always failed from the command line. It now works without `install()`.
- **`safedump stats`.** It now counts occurrences, not report files.
- **pytest plugin.** It no longer creates reports for skipped and xfail tests.
- **Click integration.** `wrap_click()` no longer reports Click/Typer control-flow exceptions (`Exit`, `Abort`, usage errors).

### Added
- `SAFEDUMP_DIR` environment variable and a global `safedump --dir DIR` option. Previously the CLI could only find reports in `~/.safedump`.
- Report schema v2:
  - `frames[].globals` (tier 3+);
  - `environment.env_var_values` (tier 4);
  - structured local values.

### Security
- `safedump serve`:
  - no longer sends `Access-Control-Allow-Origin: *`, which let any open website read every report;
  - checks the `Host` header (DNS rebinding);
  - requires a per-run token for `DELETE`;
  - only serves `*.safedump.json[.gz]` names from the report directory.

### Removed
- Unused internals: the `SafedumpConfig.denylist` property, the
  `max_report_size_bytes` and `generation_timeout_seconds` settings, and the
  never-used 1 MB fallback buffer.

## [2.0.0] — 2026-07-30

### Added
- **Complete documentation site** — 17 pages with MkDocs + Material theme
- **Deprecation policy** — formal API deprecation timeline
- **API freeze** — 12 public symbols stabilized, `__all__` frozen

### Changed
- Public API is now frozen. No breaking changes without a deprecation cycle.
- All modules reviewed for type correctness (mypy strict).

### Docs
- MkDocs documentation site with 17 pages covering all features
- Architecture documentation with pipeline diagram
- Security & Privacy guide with redaction layers
- Migration guide for all versions v1.0 through v2.0

## [1.3.0] — 2026-07-30

_Tagged on GitHub but never published to PyPI. These changes first shipped on PyPI in 2.0.0._

### Added
- **Entropy-based secret detection.** Opt-in Shannon entropy check (`enable_entropy_detection`, `entropy_threshold`).
- **Crash deduplication.** A repeated crash with the same fingerprint bumps `occurrence_count` and `last_seen` instead of writing a new file.
- **Report compression.** `compress=True` writes `.safedump.json.gz`.
- **`on_crash` hook.** A callback with the report path after each capture.
- **pytest plugin.** `safedump.integrations.pytest_plugin`.
- **Click/Typer integration.** `@wrap_click()`.

## [1.2.0] — 2026-07-30

### Added
- **HTML crash report export** — `safedump view --html [output.html]` generates a self-contained crash report viewer (no external resources, dark theme)
- **Local web server** — `safedump serve` starts a web UI for browsing reports via `http.server`, reuses HTML renderer
- **CLI report filtering** — `safedump list --type KeyError --since 7d --search error` with human-readable time formats
- **`safedump doctor`** — diagnostic command with 5 checks (Python version, output dir, hooks, report integrity, Rich availability)
- **`safedump stats`** — aggregate crash statistics with ASCII bar charts
- **Crash fingerprint** — stable SHA256 fingerprint per crash, displayed in list output, included in report JSON
- **Schema version** — `schema_version` field added to report format (v1), migration framework for forward compatibility
- **Extended data model** — `occurrence_count`, `first_seen`, `last_seen` fields for future deduplication
- **`__main__.py`** — allow `python -m safedump` usage

### Changed
- **`_capture.py` split** — frame walking extracted to `_frame_walker.py` (206 lines), hook management in `_capture.py` (264 lines)
- **`metadata` field** — type widened from `dict[str, str]` to `dict[str, Any]`
- **Migration framework** — old v0 reports auto-migrated on load via `_loader.py`

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
