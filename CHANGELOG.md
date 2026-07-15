# Changelog

## [Unreleased]
### Added
- **`watch()` context manager** — scoped crash monitoring for a specific code block without installing global exception hooks; supports `privacy_tier` and `output_dir` overrides (by @Diyaaa-12)

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
