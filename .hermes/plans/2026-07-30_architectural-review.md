# Safedump — Architectural Review of v1.2 to v2.0 Roadmap

This document reviews 16 specific suggestions plus 3 unapped technical debt items. Each recommendation is evaluated independently. The final section presents a revised timeline.

---

## Verdict Summary

| # | Suggestion | Verdict | When |
|---|---|---|---|
| 1 | Stronger product vision | **ACCEPT** — modify | Now |
| 2 | Unify rendering pipeline | **MODIFIED** — Renderer protocol, not HTML-first | v1.2 |
| 3 | Keep web server tiny | **ACCEPT** | Enforce in review |
| 4 | Reconsider notifications | **REJECT** — replace with on_crash hook | v1.3 |
| 5 | Report compression | **ACCEPT** | v1.3 |
| 6 | Crash fingerprints earlier | **ACCEPT** — move to v1.2 | v1.2 |
| 7 | Self-contained HTML | **ACCEPT** — non-negotiable | Enforce in review |
| 8 | Plan schema migrations | **ACCEPT** — most critical debt | v1.2 foundation |
| 9 | Evaluate plugin timing | **ACCEPT** — move to v2.1 | v2.1 |
| 10 | Stable object models | **ACCEPT** — NamedTuple to dataclass | v1.2 tech debt |
| 11 | Performance benchmarks | **ACCEPT** | v2.1 |
| 12 | Fuzz testing | **ACCEPT** | v2.1 |
| 13 | Report integrity | **POSTPONE** | post-v2.0 |
| 14 | Ecosystem integrations | **ACCEPT** — replace notifications | v1.3 |
| 15 | safedump doctor | **ACCEPT** | v1.2 P1 |
| 16 | User-driven planning | **ACCEPT** — process change | Ongoing |
| A | Split _capture.py | **NEW** | v1.2 foundation |
| B | Low _capture.py test coverage | **NEW** | v1.2 incremental |
| C | Low _cli.py test coverage | **NEW** | v1.2 incremental |

---

## 1. Add a Stronger Product Vision

**Verdict: ACCEPT -- modified**

The roadmap lists features without explaining why they exist. A north star anchors every decision: when someone proposes a feature, we ask "does this serve the vision?"

**Proposed vision statement:**

Safedump is the local-first, privacy-first crash investigation toolkit for Python developers. It captures what you need, stores it where you control it, and presents it how you want it -- without phoning home.

**Principles derived from this vision:**
- Local-first: everything works offline. No accounts, no servers, no vendor lock-in.
- Privacy-first: secrets are redated before storage. Reports never leave your machine unless you explicitly share them.
- Developer-friendly: CLI-first with optional web UI. Views work without proprietary tools.
- Extensible: plugin architecture available, but core is usable standalone.

**Why this matters:** Against this vision, notification features (SMTP/webhook) are obviously wrong. Self-contained HTML export is a requirement, not an optional feature. The web server becomes a minimal local UX improvement, not a platform play.

**Implementation:** Add vision statement to ROADMAP.md. Each version section references which principles it serves.

---

## 2. Unify the Rendering Pipeline

**Verdict: MODIFIED -- agree with the problem, disagree with "HTML first"**

The roadmap currently treats each output as independent: JSON -> Terminal -> HTML -> serve. This guarantees duplicated formatting logic.

**What I disagree with:** Making HTML the primary engine. HTML is one target. The correct abstraction is a Renderer protocol:

```python
class Renderer(Protocol):
    def render_report(self, report: CrashReport) -> str: ...
    def render_report_list(self, reports: list[ReportSummary]) -> str: ...
```

Concrete implementations: TerminalRenderer (wraps existing Rich code), HtmlRenderer, JsonRenderer.

**Why this is better:**
- The server reuses HtmlRenderer instead of duplicating HTML formatting
- CLI flags --json, --html, --rich all use the same pipeline
- Future formats (Markdown, PDF) are one class each
- No duplicated layout logic that diverges over time

**Tradeoff:** Added abstraction before multiple renderers exist. However, we already have Rich + planned HTML. The abstraction cost is minimal (one Protocol class, ~20 lines). The risk of not abstracting is duplicated formatting that becomes inconsistent over time.

**When to introduce:** During v1.2, before writing the HTML renderer or server. Define Renderer protocol first, then implement HtmlRenderer against it.

**Change to roadmap:** Add "Define Renderer protocol" as a foundation task in v1.2 before HTML export and serve.

---

## 3. Keep the Web Server Intentionally Tiny

**Verdict: ACCEPT -- strongly agree**

The server's job is to serve crash reports over HTTP for local browsing. Nothing more.

**Architectural safeguards:**
1. Use stdlib http.server with a custom RequestHandler. Zero dependencies, zero upgrade path to a framework.
2. The HTML served reuses HtmlRenderer from point 2. Adding a JS framework means rewriting the single-file app -- visible scope creep.
3. The server has no config of its own. It reads SafedumpConfig directly. Adding authentication requires adding parameters, which creates a forcing function.
4. One file: _server.py. If it exceeds 300 lines, it is doing too much.

The existing roadmap already specifies 127.0.0.1 only, no auth, vanilla JS. Add an explicit scope guard comment at the top of _server.py.

---

## 4. Reconsider Notifications

**Verdict: REJECT -- with alternative**

SMTP email and HTTP webhook notifications should NOT be built into Safedump core.

**Why SMTP/webhook is wrong:**
- Adds credential management (passwords in config, stored in memory)
- Adds network I/O during crash handling (retries, timeouts, failures)
- Every notification backend needs individual implementation (email, Slack, SMS, PagerDuty)
- Continuous maintenance burden (SMTP TLS changes, webhook API changes)
- Violates privacy-first and local-first principles -- the tool now reaches out to the network
- This is an integration, not a core feature

**What I propose instead: a file-system notification hook.**

```python
configure(on_crash="/path/to/script.sh")
```

Safedump calls the script with the report path as an argument. The script runs in a subprocess with a timeout. If it fails, the crash report is still saved. Users choose their notification method: email via msmtp, Slack via curl, SMS via twilio-cli.

**Why this is better:**
- Safedump never handles credentials
- Users choose their notification method
- Zero new dependencies
- Works offline
- Composable with existing tools
- No ongoing maintenance for Safedump

**Implementation:** ~30 lines in _capture.py. Add on_crash: str | Path | Callable | None to config.

**Change to roadmap:** Remove built-in SMTP/webhook notifications from v1.3. Add on_crash hook to v1.2 (it is trivial and more useful than filtering/stats).

---

## 5. Add Optional Report Compression

**Verdict: ACCEPT -- defer to v1.3**

Technical assessment:
- gzip is in stdlib. Implementation is ~20 lines.
- Transparent decompression in load_report() handles both .json and .json.gz.
- Filename convention: file.safedump.json.gz.
- Storage handles both transparently.

**Tradeoff:** Users who parse the reports directory directly need to handle .gz. CLI users are unaffected since safedump list and safedump view handle compression transparently.

**Why not v1.2:** v1.2 is already dense (HTML + server + filtering + doctor + foundation work). Compression adds no user-visible value until reports accumulate.

**Change to roadmap:** Move to v1.3. Add as configure(compress=True).

---

## 6. Introduce Crash Fingerprints Earlier

**Verdict: ACCEPT -- strongly agree. Move to v1.2 foundation.**

Fingerprints are not just for deduplication. They enable:
- Referencing crashes in GitHub issues: "I got crash a1b2c3d4"
- Correlating crashes across users
- Deduplication when it arrives (same fingerprint)
- Grouping in safedump stats

**Fingerprint formula:** SHA256 of exception_type || crash_site_file || crash_site_line. Deterministic and stable across runs. If code moves, the fingerprint changes -- which is correct, it is a different crash location.

**Implementation:** Add fingerprint to CrashReport. Compute in crash_handler after frame walking. Display in safedump list output. Expose via report.fingerprint property.

**Cost:** ~10 lines in _capture.py + ~5 lines in _types.py.

**Change to roadmap:** Add to v1.2 as a foundation task. It costs nothing and unlocks everything.

---

## 7. HTML Exports Must Be Completely Self-Contained

**Verdict: ACCEPT -- non-negotiable architectural constraint**

This is not a feature choice. It is a constraint that must be enforced in code review. Any external dependency in the HTML export is a bug.

**Implementation rules:**
- Zero external CSS (all inline or in style tag)
- Zero external JS (all inline in script tag)
- Zero external fonts (use system font stack)
- Zero images (CSS/Unicode icons only)
- Zero CDN references
- A test verifies the generated HTML contains no external URLs

The f-string template approach in the existing roadmap achieves this. Add the no-external-URLs test explicitly.

---

## 8. Plan Schema Migrations Now

**Verdict: ACCEPT -- most important technical debt item in this review**

Current state: _loader.py reads JSON, validates fields, and silently ignores unknown fields. There is no migration path. As the schema evolves, old reports become unreadable or silently produce wrong data.

**Proposed architecture:**

```python
MIGRATIONS = {
    1: _migrate_v1_to_v2,  # adds fingerprint field
    2: _migrate_v2_to_v3,  # adds compression flag
}


def load_report(path):
    data = json.loads(Path(path).read_text())
    version = data.pop("version", 1)
    for v in range(version, CURRENT_SCHEMA_VERSION):
        if v in MIGRATIONS:
            data = MIGRATIONS[v](data)
    data["version"] = CURRENT_SCHEMA_VERSION
    return CrashReport(**data)
```

**Why this must be done NOW:** Every release that changes the schema adds to migration debt. The first schema change (fingerprint, dedup fields, compression) should also introduce the migration framework -- even if there are no migrations yet.

**Change to roadmap:** Add "Schema migration framework" as a foundation task in v1.2, before any feature that modifies the report format.

---

## 9. Evaluate Plugin Timing

**Verdict: ACCEPT -- modify the order**

The roadmap has plugins and docs site in the same version (v2.0). The concern is valid: plugins should come after real users, not before.

**I agree, with nuance:** register_serializer() already exists and is frozen. That plugin category is validated. The question is whether formal entry-point discovery should be added before real plugin authors exist.

**Revised v2.0/v2.1 split:**

- v2.0: Documentation maturity + API freeze. MkDocs site, deprecation policy, stable object models. NO formal plugin discovery.
- v2.1: Plugin discovery via entry points, reference plugins, plugin development guide. Added only after:
  - Users explicitly request it
  - We have 3+ real-world use cases
  - The object model has been stable for one minor version

**Why this changes:** Premature API freezing is expensive. Once entry-point groups are published, changing them requires a major version bump. Waiting for real validation costs nothing.

---

## 10. Migrate from NamedTuple to Dataclass

**Verdict: ACCEPT -- with specific design**

CrashReport is currently a NamedTuple. NamedTuples are immutable (good) but not easily extensible (bad for forward compatibility) and lose type information during serialization/deserialization.

**Recommended design:**

```python
@dataclass(frozen=True, slots=True)
class CrashReport:
    version: int = CURRENT_SCHEMA_VERSION
    timestamp: str = ""
    fingerprint: str = ""
    exception: ExceptionSnapshot | None = None
    frames: tuple[FrameSnapshot, ...] = ()
    environment: EnvironmentSnapshot | None = None
    threads: tuple[ThreadSnapshot, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
```

**Key decisions:**
- frozen=True: preserves NamedTuple immutability for safety
- slots=True: memory efficiency (CrashReports are created once and saved)
- Default values for all fields: forward-compatible schema evolution
- metadata catch-all dict: extensibility without schema changes

**Impact on load_report:** Use explicit field construction with metadata passthrough, not CrashReport(**data).

**Change to roadmap:** Add to v1.2 as a tech-debt task before fingerprint and schema migration work.

---

## 11. Add Performance Benchmarks

**Verdict: ACCEPT -- post-v2.0**

Benchmarks are premature. The codebase is still changing actively. Benchmarks written now would need frequent updates.

**What to do instead:** Write a lightweight scripts/benchmark.py that measures capture time, serialization speed, and file size. Run manually during releases. Automate in CI only after v2.0 stabilization.

**Change to roadmap:** Move to v2.1.

---

## 12. Add Fuzz Testing

**Verdict: ACCEPT -- post-v2.0, lower priority than benchmarks**

Hypothesis is the right tool. Target areas: serializer (arbitrary Python objects), loader (malformed JSON), sanitizer (edge cases in redaction).

**Why post-v2.0:** Fuzz tests need a stable API and schema. The schema is still evolving (fingerprint, dedup, compression). Fuzz tests written now would need frequent churn.

**Change to roadmap:** Move to v2.1.

---

## 13. Consider Report Integrity

**Verdict: POSTPONE to post-v2.0 or later**

Hashes and signatures are valuable for verifying reports in incident response workflows. But no users have requested this, and the sharing workflow (HTML export + serve) doesn't exist yet.

**Recommendation:** Add a comment in _types.py noting that the fingerprint field (SHA256) is a foundation for future integrity features. Do not implement signing until users explicitly request it.

---

## 14. Expand Ecosystem Integrations

**Verdict: ACCEPT -- replace notification feature**

Instead of SMTP/webhook, integrate with tools developers already use:

| Integration | Value | Complexity |
|---|---|---|
| pytest -- auto-capture test failures | High | ~50 lines |
| Click/Typer -- capture CLI app crashes | Medium | ~30 lines |
| IPython -- capture notebook cell errors | Medium | ~40 lines |

**Why these are better than notifications:**
- Local-first (no network)
- Single-function integrations
- Make Safedump more useful immediately
- Position Safedump as a developer tool, not a monitoring service

**Change to roadmap:** Move to v1.3 replacing notification feature. pytest integration as P0, Click/Typer as P1.

---

## 15. Add safedump doctor Command

**Verdict: ACCEPT -- v1.2, high value, low cost**

Checks to include:
- Output directory is writable
- sys.excepthook points to Safedump
- No corrupted report files
- Python version compatibility
- Plugin loading status (when available)

**Implementation:** ~60 lines in _cli.py. Returns list of (check, status, message).

**Why v1.2:** Cheap, visible, builds user confidence. Helps debug configuration issues during the HTML/serve releases.

**Change to roadmap:** Add to v1.2 as P1.

---

## 16. Strengthen User-Driven Planning

**Verdict: ACCEPT -- process change, not code change**

**Recommendations:**
1. After every minor release, post a "What next?" GitHub Discussion
2. Track which features users actually ask for versus what we assumed
3. Add a needs-votes label for community upvoting
4. Review the roadmap quarterly based on actual feedback

**Specific concern:** v1.2 adds HTML export and serve. Users might want these, or they might want something completely different (VS Code extension, CI pipeline integration). We will not know until we ship v1.2 and ask.

---

## Hidden Technical Debt (Missed by Original Review)

### A. _capture.py needs splitting (422 lines)

Currently handles: frame walking, crash handler orchestration, hook install/uninstall, exception chain parsing, thread capture. Any change touches all these areas.

**Fix:** Split into _frame_walker.py, _hook_manager.py, and keep _capture.py as orchestration (~200 lines).

**Priority:** v1.2 foundation task.

### B. _capture.py has 18% test coverage

test_capture.py is 75 lines for 422 lines of source. This is the most critical module with the least coverage.

**Fix:** Add focused tests for _walk_traceback, _capture_frame, _capture_exception_chain, and crash_handler.

**Priority:** v1.2 incremental, done alongside each change.

### C. _cli.py has minimal test coverage

test_cli.py is 31 lines for 156 lines of source. Only view --json is tested.

**Fix:** Use pytest CliRunner or subprocess tests for each subcommand.

**Priority:** v1.2 incremental alongside new subcommands.

---

## Revised Version Timeline

```
v1.2.0   Week 1-2   Foundation:
                     - Schema migration framework
                     - CrashReport migration from NamedTuple to dataclass
                     - Renderer protocol
                     - Crash fingerprint
                     - Split _capture.py
                     Ship: HTML export, serve CLI, filtering, doctor command
                     Testing: incremental coverage on changed modules

v1.2.1   Week 3     Bug fixes from v1.2 feedback

v1.3.0   Week 4-6   Entropy detection (opt-in), deduplication,
                     report compression, on_crash hook,
                     pytest integration, Click/Typer integration

v1.3.1   Week 7     Bug fixes

v2.0.0   Week 8-11  Documentation site (MkDocs), API freeze,
                     deprecation policy, object model stabilization,
                     remove deprecated APIs

v2.0.1   Week 12    Bug fixes

v2.1.0   Week 13-16 Plugin API (entry-point discovery),
                     3 reference plugins (numpy, pandas, PIL),
                     plugin development guide, benchmarks,
                     fuzz testing

v2.1.1   Week 17    Bug fixes from plugin ecosystem feedback
```
