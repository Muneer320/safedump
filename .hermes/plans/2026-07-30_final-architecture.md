# Safedump — Final Architecture & Implementation Blueprint

**Date:** July 30, 2026
**Current version:** v1.1.0 (shipped)
**Codebase:** 2,326 source lines, 1,421 test lines, 107 tests
**Architecture:** sys.excepthook → frame walker → sanitizer → serializer → storage

---

## 1. Core Data Model

### Current State

All data objects are already dataclasses. CrashReport, FrameSnapshot, ExceptionSnapshot, EnvironmentSnapshot, ThreadSnapshot, VariableSnapshot, RedactionRecord — all dataclasses. The NamedTuple migration recommendation from the previous review is **already satisfied**.

### What needs to change

**1.1 Schema version field**
CrashReport has `safedump_version` but no `schema_version`. This is a gap. Add:

```python
CRASH_REPORT_SCHEMA_VERSION = 1
```

And include it in the serialized JSON:

```python
@dataclass
class CrashReport:
    schema_version: int = CRASH_REPORT_SCHEMA_VERSION
    # ... existing fields ...
```

The serialized JSON should include `"schema_version": 1` at the top level, BEFORE any other fields. This ensures forward compatibility — any future parser can detect the schema version immediately.

**1.2 metadata should be dict[str, Any]**
Currently `metadata: dict[str, str]`. This is too restrictive. Change to `dict[str, Any]` for future extensibility. Plugins, custom hooks, and future features will want to attach non-string data.

**1.3 CrashReport needs a fingerprint field**
Currently `_compute_hash` in _storage.py computes an 8-char hash for filenames but the fingerprint is not stored in the report. Add:

```python
fingerprint: str = ""
```

Computed as SHA256 of (exception_type + crash_site_file + crash_site_line)[:12]. Included in the serialized JSON.

**1.4 CrashReport needs an occurrence_count field**
For future deduplication. Default 1. Not used until dedup is enabled, but having the field from the start avoids a schema migration later:

```python
occurrence_count: int = 1
first_seen: str = ""  # same as timestamp on first write
last_seen: str = ""  # same as timestamp on first write
```

**Verdict:** All four changes are additive — they add fields with defaults. No existing code breaks. No migration needed for existing reports (old reports loaded by load_report() will get defaults for missing fields). Implement in v1.2 foundation.

---

## 2. Renderer Architecture

### Decision: DO NOT introduce a Renderer protocol yet.

**Reasoning:**
- There is currently ONE renderer: the Rich terminal viewer in `_render.py` (133 lines).
- The HTML renderer will be a second renderer.
- Introducing a protocol abstraction for TWO implementations is premature.
- The risk of duplicated formatting logic is real, but the cost of the abstraction is not zero — it adds indirection, testing surface, and decision paralysis ("does this belong in the protocol or in the implementation?").

**Alternative approach:** Keep the HTML renderer as a standalone function in `_html_render.py`. If a third format emerges (Markdown, PDF, JSON, etc.), refactor to a Renderer protocol at that point. The migration cost is small (one Protocol definition, one factory, two implementation classes) and the refactoring is mechanical.

**Why this is safe:** The HTML renderer receives a `CrashReport` object and returns an HTML string. The terminal renderer receives the same object and outputs Rich-widgets-to-terminal. Their APIs are already implicitly consistent — they share the same input type. A formal protocol adds no type safety that isn't already provided by the CrashReport dataclass.

**Self-critique:** The previous review recommended a Renderer protocol. I now believe that was premature optimization. YAGNI applies here.

---

## 3. Storage Layer

### Decision: DO NOT introduce a StorageBackend abstraction.

**Current architecture:** `_storage.py` is 133 lines, clean, well-tested. It handles:
- Filename generation
- Directory creation with permissions
- Atomic file writes with tempfile+rename
- Fallback to system temp directory

**Why no abstraction:**
- There is exactly one storage backend: the local filesystem.
- A StorageBackend protocol would be a solution in search of a problem.
- The only plausible future storage format is S3/GCS, which is an explicit post-v2.0 non-goal.
- The `save()` function already has a clean single-responsibility signature: `save(json_str, config, report) -> Path | None`.
- Testing is done via `tmp_path` (pytest fixture), not by mocking a storage backend.

**When to add:** If a second storage backend is ever needed (remote S3, encrypted storage). This is not on the roadmap.

---

## 4. Schema Evolution

### Decision: Implement migration framework in v1.2 foundation.

**Current state:** No schema version in the report format. `_loader.py` reads JSON silently. Old reports are read as-is with no version check. This is a ticking time bomb.

**Design:**

```python
# _types.py
CRASH_REPORT_SCHEMA_VERSION = 1

# _loader.py
MIGRATIONS: dict[int, Callable[[dict], dict]] = {}


def load_report(path: str | Path) -> CrashReport:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    version = raw.get("schema_version", 0)

    # Apply migrations sequentially
    for v in range(version, CRASH_REPORT_SCHEMA_VERSION):
        if v in MIGRATIONS:
            raw = MIGRATIONS[v](raw)
        raw["schema_version"] = v + 1

    return CrashReport(**{k: v for k, v in raw.items() if k in CrashReport.__dataclass_fields__})
```

**Migration examples:**
```python
def _migrate_v0_to_v1(raw: dict) -> dict:
    """v0 reports had no fingerprint, occurrence_count, or schema_version."""
    raw.setdefault("fingerprint", "")
    raw.setdefault("occurrence_count", 1)
    raw.setdefault("first_seen", raw.get("timestamp", ""))
    raw.setdefault("last_seen", raw.get("timestamp", ""))
    return raw


MIGRATIONS[0] = _migrate_v0_to_v1
```

**Compatibility policy:**
- Current reports (v0, no schema_version field) are always readable.
- Minimum supported schema version: 0 (backward compatibility forever).
- Schema version increments ONLY when adding/removing/renaming fields.
- New fields must have defaults (backward compatible).
- Field removal: deprecate in one version, remove in next major version.

**Why v1.2 foundation:** Every feature that changes the report format (fingerprint, dedup, compression) requires this framework first. Build it once, then all future schema changes are cheap.

---

## 5. Crash Fingerprints

### Decision: Implement as foundation in v1.2.

**Algorithm:**

```python
def compute_fingerprint(report: CrashReport) -> str:
    digest = hashlib.sha256()
    digest.update(report.exception.type.encode("utf-8"))
    digest.update(report.exception.message.encode("utf-8")[:200])
    if report.frames:
        first = report.frames[0]
        digest.update(first.file.encode("utf-8"))
        digest.update(str(first.line).encode("utf-8"))
    return digest.hexdigest()[:12]
```

**Stability properties:**
- Deterministic: same crash always produces same fingerprint.
- Code-movement resistant within a file: changing code before the crash site does not change the fingerprint.
- Code-movement sensitive across files: moving the crash to a different file changes the fingerprint (desired — it IS a different crash location).
- Exception message changes change the fingerprint (desired — different messages mean different crashes).

**Storage:** Add `fingerprint` field to CrashReport. Compute in `crash_handler()` after frame walking. Display in `safedump list` output. Exclude from `__repr__` to avoid noise.

**Schema migration:** Add `_migrate_v0_to_v1` that sets `fingerprint = ""`. Old reports without fingerprints get the empty string, which is fine for display purposes.

---

## 6. Web Interface Boundaries

### Architectural guardrails (non-negotiable):

1. **Stdlib only:** http.server, no framework. This makes it impossible to add routes/auth/middleware without conscious effort.
2. **127.0.0.1 only by default.** `--host` flag exists but prints a warning if not localhost.
3. **One file:** `_server.py` must stay under 300 lines. If it exceeds this, extract the HTML template, not the server logic.
4. **Read-only API except DELETE:** The server can delete reports. It cannot create or modify them. This is intentional — crash reports are created by the crash handler, not by user interaction.
5. **The server is a VIEWER, not a platform.** It lists, renders, and deletes. That is the complete feature set.

**Scope creep prevention:** The file structure itself enforces boundaries. `_server.py` imports from `_html_render.py` for report rendering. If someone wants to add authentication, they must add auth logic to `_server.py`. The diff will be visible in code review.

---

## 7. HTML Export Self-Containment

### Non-negotiable constraint.

**Implementation rules:**
- System font stack only (`-apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif`)
- Zero images: use Unicode emoji/characters for icons (⚠️, ✅, ❌, 🔒 for redactions)
- Zero external resources in the generated HTML
- A `test_html_has_no_external_urls()` test that fails if any `http://`, `https://`, `//`, or `src=` pointing outside the file is found
- The generated HTML must render correctly when opened with `file://`

---

## 8. CLI Design

### Commands (current + planned):

| Command | v1.1 | v1.2 | v1.3 | Status |
|---|---|---|---|---|
| `install` | ✅ | ✅ | ✅ | Stable |
| `view` | ✅ | ✅ | ✅ | +`--html` in v1.2 |
| `list` | ✅ | ✅ | ✅ | +`--type/--since/--search` in v1.2 |
| `clean` | ✅ | ✅ | ✅ | Stable |
| `test` | ✅ | ✅ | ✅ | Stable |
| `serve` | ❌ | ✅ | ✅ | v1.2 new |
| `doctor` | ❌ | ✅ | ✅ | v1.2 new |
| `stats` | ❌ | ✅ | ✅ | v1.2 new |

**CLI philosophy:** Each command does one thing. No subcommand has more than 5 flags. If a command needs more flags, it should be a separate command.

**`doctor` design:**
```
safedump doctor
  ✓ Output directory is writable
  ✓ sys.excepthook points to Safedump
  ✓ No corrupted report files
  ✓ Python 3.9+ compatibility check
  ✓ Rich available (for view)
  ✓ Plugin loading status (when available)
```

Exit code: 0 if all checks pass, 1 if any check fails.

---

## 9. Extensibility Framework

### Decision: Three tiers, clearly defined.

| Tier | What | Example | Where |
|---|---|---|---|
| **1. Core** | Built-in, always available | denylist, sanitizer, serializer, storage | src/safedump/ |
| **2. Plugin** | Optional, installed via pip | numpy serializer, pytest integration | safedump-plugins/ or third-party |
| **3. User callback** | User-provided function | `before_capture`, `on_crash` | configure() |

**Decision criteria for tier placement:**

A feature belongs in **core** if:
- It is required for the basic crash capture pipeline to function
- Removing it would break existing users
- It has no external dependencies

A feature belongs in a **plugin** if:
- It has external dependencies (numpy, pandas, requests)
- It is specific to a particular framework/language/tool
- It would add more than one optional dependency to core

A feature belongs in a **user callback** if:
- It requires user-specific logic (notification destinations, custom scrubbing)
- It involves credentials or secrets
- Different users want different behavior

**Impact on existing roadmap:**
- SMTP/webhook notifications: user callback tier (via `on_crash`). Not core, not plugin.
- pytest integration: plugin tier.
- Entropy detection: core tier (opt-in config flag, no external deps).

---

## 10. Notifications — Final Decision

### Decision: `on_crash` shell hook. No built-in SMTP/webhook.

**Architecture:**

```python
configure(
    on_crash="/path/to/script.sh"  # str, Path, or Callable
)
```

**Behavior:**
- If str or Path: subprocess.Popen([script_path, report_path]) with 10-second timeout
- If Callable: callable(report_path) in a thread with 10-second timeout
- Runs AFTER save() completes successfully
- Failure is logged to stderr, never blocks capture
- No retries, no queue, no state

**Why this is the right choice:**
- Zero external dependencies (subprocess is stdlib)
- Zero credential management (Safedump never touches passwords)
- Users choose their notification method (email via msmtp, Slack via curl, etc.)
- Works completely offline (the script can queue and send later)
- Can be composed with existing tools and cron jobs
- The script can be in any language (bash, Python, compiled binary)

**Tradeoff:** Users who just want "send email on crash" have to write a 5-line shell script. This is acceptable — developer tools should compose, not prescribe.

**Self-critique:** The previous review recommended this approach, but with lower conviction. I now believe the `on_crash` hook is the ONLY correct approach for Safedump. Built-in notifications would violate the privacy-first identity and create ongoing maintenance burden. This decision is final.

---

## 11. Integrations

### Which are worth building:

| Integration | Value | Lines | Verdict |
|---|---|---|---|
| **pytest** | High — auto-capture test failures | ~50 | ✅ v1.3 |
| **Click/Typer** | Medium — CLI app crash capture | ~30 | ✅ v1.3 (P1) |
| **IPython** | Medium — notebook crash capture | ~40 | ❌ Postpone to v2.x |
| **Rich** | Already done | ✅ | Done |

**pytest integration design (v1.3):**

```python
# safedump/integrations/pytest_plugin.py
def pytest_runtest_makereport(item, call):
    if call.excinfo is not None:
        safedump.capture_exception(call.excinfo.value)
```

Installed via `pip install safedump[pytest]` and `pytest --safedump` or conftest.

**Why Click/Typer:** CLI applications are a natural use case for crash capture. A decorator `@safedump.catch` that wraps a Click command in a crash handler is minimal code and immediately useful.

---

## 12. Testing Strategy

### Current gaps identified from codebase review:

| Module | Source lines | Test lines | Ratio | Verdict |
|---|---|---|---|---|
| _capture.py | 422 | 75 | 18% | Needs improvement |
| _cli.py | 156 | 31 | 20% | Needs improvement |
| _sanitize.py | 333 | 123 | 37% | Acceptable |
| _serialize.py | 273 | 153 | 56% | Good |
| _storage.py | 133 | 110 | 83% | Good |
| _render.py | 133 | 0 | 0% | Needs testing |
| _types.py | 242 | 113 | 47% | Acceptable |
| watch.py | 89 | 168 | 189% | Excellent |
| logging_handler.py | 72 | 123 | 171% | Excellent |

### Planned testing additions:

| Type | Priority | When | Tool |
|---|---|---|---|
| **Snapshot testing** for HTML renderer | Medium | v1.2 (with feature) | pytest + inline snapshots |
| **CLI tests** for existing commands | High | v1.2 incremental | subprocess + tmp_path |
| **fuzz testing** for serializer/loader | Low | v2.1 | Hypothesis |
| **Performance benchmarks** | Low | v2.1 | custom script |
| **Golden HTML tests** | Medium | v1.2 (with feature) | pytest + expected files |

**Self-critique on benchmarks/fuzz:** Postponing these to v2.1 is correct. The codebase is actively changing. Fuzz tests and benchmarks written now would need constant updating, creating noise rather than signal. After v2.0 stabilization, they become valuable regression detection tools.

---

## 13. Technical Debt — Modules to Split

### Decision: Split _capture.py in v1.2 foundation.

The 422-line `_capture.py` currently handles:
- Frame walking (lines 55-91) — independent
- Frame capture (lines 94-147) — independent
- Exception chain walking (lines 150-173) — independent
- Environment capture (lines 176-193) — independent
- Thread capture (lines 196-210) — independent
- Crash handler (lines 213-283) — orchestrator
- Install/uninstall (lines 285-348) — independent
- capture_exception() (lines 351-411) — semi-independent
- test() (lines 414-422) — independent

**Proposed split:**

```
_capture.py        → crash handler + capture_exception + test (~200 lines)
_frame_walker.py   → _safe_repr, _walk_traceback, _capture_frame,
                     _capture_exception_chain, _capture_environment,
                     _capture_threads (~200 lines)
_hook_manager.py   → install, uninstall, is_installed, module state (~80 lines)
```

**Why now:** These functions are already logically independent. The split is mechanical — no design decisions needed. It is pure refactoring with no behavior change. Doing it now prevents _capture.py from growing further (it will grow when `on_crash`, `fingerprint`, and `schema_version` support are added in v1.2).

### Decision: Do NOT split other modules.

- `_sanitize.py` (333 lines) is complex because redaction is complex. The complexity is inherent, not structural. Splitting it would create artificial boundaries that make the flow harder to follow.
- `_serialize.py` (273 lines) is a single encoder with clear sections. The length is justified by the number of types it handles.
- `_cli.py` (156 lines) grows predictably with each command. If it exceeds 300 lines, split by command group at that point.

---

## 14. Remaining Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| **Schema migration never tested with real data** | Medium | High | Test migration from v0 (current) to v1 with real crash reports from the wild |
| **HTML renderer diverges from terminal renderer** | Medium | Low | Both renderers receive the same CrashReport object. Formatting differences are cosmetic, not structural. |
| **on_crash hook security (shell injection)** | Low | Medium | Document that users must validate their script paths. Use subprocess with list form, not shell=True. |
| **_capture.py still too large after split** | Low | Low | Target 200 lines. If it exceeds 250, split again. |
| **Entropy detection causes performance regression** | Medium | Medium | Opt-in, runs after denylist, time-boxed to 500ms. |
| **CLI test coverage still low after v1.2** | Medium | Low | Each new command comes with tests. Old commands get tested as they are touched. |

---

## 15. Revised Roadmap

```
┌─────────────────────────────────────────────────────────────────────┐
│                     v1.2 — Foundation + Shareability                │
│                     (Weeks 1-2, estimated 14 days)                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  DAY 1-3: Foundation                                                │
│  ┌─ Schema migration framework (_loader.py, _types.py)              │
│  ├─ Add schema_version, fingerprint, occurrence_count to CrashReport │
│  ├─ _capture.py split (_frame_walker.py, _hook_manager.py)          │
│  ├─ Upgrade _capture.py test coverage (+50 lines)                    │
│  └─ All tests pass, CI green                                         │
│                                                                      │
│  DAY 4-7: HTML Export + CLI improvements                            │
│  ┌─ HTML renderer (_html_render.py)                                 │
│  ├─ --html flag on safedump view                                    │
│  ├─ --type/--since/--search/sort on safedump list                    │
│  ├─ safedump doctor (6 checks)                                      │
│  ├─ safedump stats (basic ASCII stats)                              │
│  └─ All tests pass, CI green                                         │
│                                                                      │
│  DAY 8-10: Web Server                                               │
│  ┌─ safedump serve (http.server, 127.0.0.1 only)                   │
│  ├─ Reuses _html_renderer for report viewing                        │
│  ├─ JSON API: list, view, delete                                    │
│  ├─ Server test suite (lifecycle, empty state, port conflicts)      │
│  └─ All tests pass, CI green                                         │
│                                                                      │
│  DAY 11-14: Polish + Release                                        │
│  ┌─ CLI test coverage improvements                                  │
│  ├─ Bug fixes from integration testing                              │
│  ├─ CHANGELOG.md update                                             │
│  ├─ Version bump to 1.2.0                                           │
│  ├─ GitHub release + PyPI publish                                   │
│  └─ Post-release feedback discussion on GitHub                      │
│                                                                      │
│  v1.2.1 (Day 15-17): Bug fix release if needed                      │
│                                                                      │
├─────────────────────────────────────────────────────────────────────┤
│                     v1.3 — Smarter Capture                           │
│                     (Weeks 4-6, estimated 14 days)                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  DAY 1-4: Entropy Detection                                         │
│  ┌─ _entropy.py module (Shannon entropy, skip lists, threshold)     │
│  ├─ configure(entropy_detection=True)                               │
│  ├─ Integration with _sanitize.py (runs after denylist)             │
│  ├─ Comprehensive test suite (false positive verification)          │
│  └─ All tests pass, CI green                                         │
│                                                                      │
│  DAY 5-7: Deduplication + Compression                               │
│  ┌─ Dedup: configure(dedup=True), fingerprint-based grouping        │
│  ├─ Compression: configure(compress=True), transparent .json.gz     │
│  ├─ load_report() handles both compressed and uncompressed          │
│  └─ All tests pass, CI green                                         │
│                                                                      │
│  DAY 8-10: on_crash Hook + Integrations                             │
│  ┌─ on_crash hook (str/Path/Callable, subprocess, 10s timeout)     │
│  ├─ pytest integration (safedump[pytest] extra)                     │
│  ├─ Click/Typer integration (safedump[cli] extra)                   │
│  └─ All tests pass, CI green                                         │
│                                                                      │
│  DAY 11-14: Polish + Release                                        │
│  ┌─ Edge case hardening, fuzzing (manual)                           │
│  ├─ Documentation updates                                           │
│  ├─ Version bump to 1.3.0                                           │
│  ├─ GitHub release + PyPI publish                                   │
│  └─ Post-release feedback discussion                                │
│                                                                      │
├─────────────────────────────────────────────────────────────────────┤
│                     v2.0 — Documentation + Stability                 │
│                     (Weeks 8-10, estimated 14 days)                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  DAY 1-5: Documentation Site                                        │
│  ┌─ MkDocs with Material theme                                      │
│  ├─ Home, getting-started, configuration, API reference, guides     │
│  ├─ FAQ, troubleshooting, changelog                                 │
│  ├─ GitHub Pages CI/CD workflow                                     │
│  └─ Review by external contributor                                  │
│                                                                      │
│  DAY 6-10: API Freeze + Deprecation Policy                          │
│  ┌─ Audit __all__ for completeness                                  │
│  ├─ Document deprecation policy in CONTRIBUTING.md                  │
│  ├─ Add versionadded/versionchanged to all docstrings               │
│  ├─ Remove any deprecated parameters (none expected)                │
│  └─ All tests pass, CI green                                         │
│                                                                      │
│  DAY 11-14: Polish + Release                                        │
│  ┌─ Performance benchmark script (manual run)                       │
│  ├─ Final review of all open issues                                 │
│  ├─ Version bump to 2.0.0                                           │
│  ├─ GitHub release + PyPI publish                                   │
│  └─ Announce on Python Reddit, Hacker News                          │
│                                                                      │
├─────────────────────────────────────────────────────────────────────┤
│                     v2.1 — Plugin Ecosystem                          │
│                     (Weeks 11-14, estimated 14 days)                │
│                     Only after real user demand is confirmed.        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─ Plugin discovery via importlib.metadata entry points            │
│  ├─ 3 reference plugins (numpy, pandas, PIL)                        │
│  ├─ Plugin development guide                                        │
│  ├─ Fuzz testing (Hypothesis)                                       │
│  ├─ Performance benchmarks (CI)                                     │
│  └─ Version bump to 2.1.0                                           │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 16. Implementation Order — Dependencies

```
v1.2 FOUNDATION (must be first):
  1. Schema migration framework     ← blocks everything
  2. Add schema_version field        ← blocked by 1
  3. Add fingerprint field           ← independent of 1
  4. Split _capture.py               ← independent, but easier before adding new features
  5. Upgrade _capture.py tests       ← after 4

v1.2 FEATURES (order independent, can be parallelized):
  6. HTML renderer                   ← independent
  7. CLI filtering (list)            ← independent
  8. safedump doctor                 ← independent
  9. safedump stats                  ← independent
  10. safedump serve                 ← depends on 6 (reuses HTML renderer)
  11. CLI test coverage              ← ongoing

v1.3:
  12. Entropy detection              ← independent
  13. Deduplication                  ← depends on 3 (fingerprint)
  14. Compression                    ← independent
  15. on_crash hook                  ← independent
  16. pytest integration             ← independent

v2.0:
  17. Documentation site             ← independent
  18. API freeze                     ← requires all v1.x features to be stable
  19. Benchmarks                     ← independent

v2.1:
  20. Plugin API                     ← only if users request it
  21. Fuzz testing                   ← only after v2.0 stability
```

Dependency rule: No feature depends on another feature within the same version. Everything in v1.2 can be built independently after the foundation is laid.

---

## 17. Future Vision (Post-v2.0)

Not features. Architecture.

**Identity:** Safedump is the `~/.safedump` directory on every Python developer's machine — the place crashes go to be understood. It is not a SaaS product. It is not a monitoring platform. It is a local tool that respects the user's privacy by default.

**Ecosystem position:** Safedump coexists with Sentry (for production monitoring) and Rich (for terminal UX). It fills the gap between "I saw an error" and "I can reproduce it." It is the first tool you reach for when something crashes locally, and the last tool you check when a production crash report arrives via your monitoring pipeline.

**What Safedump is NOT:**
- A SaaS platform (never will be)
- A remote crash aggregator (that would be a separate product)
- A general-purpose debugging tool (it does ONE thing)
- A replacement for proper error handling (it's a safety net)

**What Safedump might become:**
- The local crash investigation standard (`.safedump` files shared like core dumps)
- An ecosystem of community report analyzers (plugins)
- A CLI tool that CI systems call to process crash reports from test suites

---

## 18. Final Critical Self-Review

Before finalizing, I challenged every recommendation:

**1. Is the schema migration framework overengineered?**
The framework is 30 lines. The alternative (ad-hoc version handling in every loader) creates hidden debt. 30 lines is cheap insurance.

**2. Is no-Renderer-protocol the right call?**
Yes. Two implementations don't justify an abstraction. When a third appears, the refactoring cost is one hour. YAGNI.

**3. Is the on_crash hook too minimal?**
Yes and that is the point. Developers who need more can use a shell script. Developers who want nothing get nothing. This is the correct minimum viable notification system.

**4. Should _capture.py really be split?**
Yes. 422 lines with 18% test coverage in the most critical module is a maintenance risk. The split is mechanical and has zero design cost.

**5. Are the CLI additions (doctor, stats) necessary?**
`doctor` is cheap and valuable. `stats` is cheap and nice-to-have. Both are under 60 lines. The cost of not having them is users asking "how do I check if it's working?" on GitHub issues.

**6. Is entropy detection worth the complexity?**
Opt-in, runs after denylist, uses stdlib math. The complexity is ~80 lines. The value is catching secrets the denylist misses. The risk is false positives, mitigated by opt-in + conservative threshold. Worth it.

**7. Is the v2.0 scope correct?**
Yes. v2.0 is documentation and API freeze — NOT features. This is the right order. Plugin ecosystem comes only after real users validate the API.

**8. Would an experienced Python maintainer agree with these decisions?**
I believe they would. The decisions prioritize:
- Additive changes over breaking changes (schema fields with defaults)
- Delayed abstraction over premature abstraction (no Renderer protocol)
- Composition over prescription (on_crash hook over built-in notifications)
- Local-first identity over feature count (rejecting SMTP/webhook)
- Mechanical refactoring over design change (splitting _capture.py)

**If there is one thing to disagree with, it would be the v1.2 scope.** Four features (HTML export, serve, filtering, doctor, stats) plus foundation work (migration, fingerprint, split) in 14 days is ambitious. If something must be cut, cut `stats` first (lowest value, independent, can be deferred to v1.3).
