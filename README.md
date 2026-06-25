# Safedump

<p align="center">
  <strong>Local-first crash diagnostics for Python.</strong><br>
  Capture full debugging context. Redact secrets automatically. Inspect crashes offline.
</p>

<p align="center">
  <a href="https://pypi.org/project/safedump/"><img src="https://img.shields.io/pypi/v/safedump" alt="PyPI"></a>
  <a href="https://github.com/Muneer320/safedump/actions/workflows/ci.yml"><img src="https://github.com/Muneer320/safedump/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://pypi.org/project/safedump/"><img src="https://img.shields.io/pypi/pyversions/safedump" alt="Python"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License"></a>
  <a href="https://github.com/Muneer320/safedump"><img src="https://img.shields.io/github/stars/Muneer320/safedump" alt="Stars"></a>
</p>

---

## What is Safedump?

Python's traceback tells you **where** your code crashed. Safedump tells you **why**.

When an exception occurs, Safedump captures the complete debugging context — local variables, exception chains, thread state, environment — and saves it as a structured, safe-to-share crash report. No cloud. No telemetry. No network calls. Ever.

```python
import safedump
safedump.install()
# ... your application runs, crashes ...
# Crash report saved: ~/.safedump/crash-2026-06-25-123456-TypeError-a1b2c3.json
```

Then inspect it anytime:

```bash
$ safedump view
```

## Why Safedump?

| Problem | Without Safedump | With Safedump |
|---|---|---|
| "It crashed on the server" | Ask user for logs, try to reproduce | Open the crash report file |
| "What were the variable values?" | Add print() statements, redeploy | Already captured in the report |
| "Can I share this crash safely?" | Manually audit for secrets first | Automatic redaction built in |
| "Which thread crashed?" | Guess from log timestamps | Thread state captured at crash time |
| "Works on my machine" | SSH in, check environment | Environment metadata in every report |

## How is it different?

| Feature | safedump | rich.traceback | stackprinter | Sentry SDK |
|---|---|---|---|---|
| **Local-first** | ✅ | ✅ | ✅ | ❌ (cloud) |
| **Offline crash reports** | ✅ (JSON files) | ❌ | ❌ | ❌ |
| **Secret redaction** | ✅ (built-in) | ❌ | ❌ | ✅ (configurable) |
| **CLI viewer** | ✅ | ✅ (terminal) | ❌ | ❌ |
| **Privacy tiers** | ✅ (0–4) | ❌ | ❌ | ❌ |
| **Plugin system** | ✅ | ❌ | ❌ | ✅ |
| **ExceptionGroup support** | ✅ | ❌ | ❌ | ✅ |
| **Cross-thread capture** | ✅ | ❌ | ❌ | ✅ |
| **Shareable reports** | ✅ | ❌ (plain text) | ❌ (plain text) | ✅ (cloud only) |

## Quick Start

### Installation

```bash
pip install safedump
```

For the terminal viewer:

```bash
pip install safedump[view]
```

### One-line setup

```python
import safedump
safedump.install()
```

That's it. Every unhandled exception now produces a crash report.

### What a crash report looks like

```
$ safedump view
╭───────────────────────────────── Exception ──────────────────────────────────╮
│ ZeroDivisionError: division by zero                                          │
╰──────────────────────────────────────────────────────────────────────────────╯
╭──────────────────────────────────────────────────────────────────────────────╮
│ main.py:42 in calculate                                                      │
╰──────────────────────────────────────────────────────────────────────────────╯
┏━━━━━━━━━━┳━━━━━━┳━━━━━━━┓
┃ Variable ┃ Type ┃ Value ┃
┡━━━━━━━━━━╇━━━━━━╇━━━━━━━┩
│ x        │ int  │ 42    │
│ y        │ int  │ 0     │
│ data     │ dict │ {...} │
└──────────┴──────┴───────┘
╭─────────────────────────────── Environment ────────────────────────────────╮
│ OS: linux | Python: 3.12.4 | Platform: linux | CWD: /app                   │
╰─────────────────────────────────────────────────────────────────────────────╯
```

### Manual capture

```python
try:
    result = dangerous_operation()
except Exception:
    path = safedump.capture_exception()
    print(f"Crash captured: {path}")  # share this file
    raise
```

## Features

### 🔒 Privacy First
- **Zero cloud** — no network calls, no telemetry, no accounts
- **Secret redaction** — passwords, tokens, and API keys automatically scrubbed
- **Privacy tiers** — configure exactly what gets captured
- **File permissions** — reports saved with `0600` (owner-only)

### 📋 Rich Debugging Context
- **Local variables** — values and types at every stack frame
- **Exception chains** — full `__cause__` + `ExceptionGroup` support
- **Thread state** — all threads captured, crashing thread highlighted
- **Environment** — OS, Python version, CWD, env var names

### 🎨 Developer Experience
- **One-line install** — `import safedump; safedump.install()`
- **Beautiful terminal viewer** — Rich-powered with syntax highlighting
- **CLI tools** — `view`, `list`, `clean`, `test`
- **Config presets** — `configure(preset="production")`

### 🔧 Extensible
- **Plugin system** — `register_serializer()` for custom types
- **Custom redaction** — `RedactionRule` for domain-specific scrubbing
- **`before_capture` hook** — pre-processing before report generation

## Configuration

```python
safedump.configure(
    preset="production",      # or "development", "debug", "minimal"
    output_dir="./crashes",   # where to save reports
    privacy_tier=1,           # 0=minimal, 1=default, 4=everything
)
```

## CLI Commands

```bash
safedump view                    # View latest crash report
safedump view crash.json         # View specific report
safedump list                    # List recent crashes
safedump list --count 10         # Last 10 crashes
safedump clean --older-than 30   # Delete reports older than 30 days
safedump test                    # Verify installation
```

## FAQ

**Does Safedump send data anywhere?**
No. Safedump is completely offline. It never makes network connections. Crash reports are stored locally on your filesystem.

**Is it safe to share crash reports?**
Yes (after review). By default, Safedump redacts variable names like `password`, `token`, and `secret`, and detects credential patterns (AWS keys, GitHub tokens, JWTs). The report includes a redaction audit trail. Still, always review before sharing publicly.

**What's the performance overhead?**
Zero during normal execution. Safedump only runs when an unhandled exception occurs. Crash capture takes <30ms for typical 20-frame tracebacks.

**What Python versions?**
3.9 through 3.13. Tested on all versions in CI.

**Can I use this in production?**
Yes. Use `configure(preset="production")` (privacy tier 1, no env capture, no argv). Safedump is designed to fail gracefully — if the handler itself crashes, the original traceback is always preserved.

## Supported Python Versions

| Python | Status |
|---|---|
| 3.9 | ✅ |
| 3.10 | ✅ |
| 3.11 | ✅ |
| 3.12 | ✅ |
| 3.13 | ✅ |

## Roadmap

- **v1.1** — HTML export, `safedump serve`, entropy-based redaction
- **v1.2** — Windows first-class support, logging integration
- **v1.3** — Framework guides (Flask, FastAPI, Django)
- **v2.0** — Plugin ecosystem, third-party type packages

See [ROADMAP.md](ROADMAP.md) for details.

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines.

## License

MIT © [Muneer Alam](https://github.com/Muneer320)
