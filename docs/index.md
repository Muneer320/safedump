# Safedump

**Local-first crash diagnostics for Python.**

Capture complete debugging context when your application crashes:
local variables, exception chains, thread state, and environment --
then inspect it safely offline.

```python
import safedump

safedump.install()
# ... your application runs, crashes ...
# Crash report saved: ~/.safedump/crash-2026-06-25-123456-TypeError-a1b2c3.safedump.json
```

```console
$ safedump view
```

## Why Safedump?

Python's traceback tells you **where** your code crashed.
Safedump tells you **why** -- what the variables contained, which thread
was running, what the environment looked like, and what caused the
exception chain.

| Without Safedump | With Safedump |
|---|---|
| Ask the user to reproduce the crash | Read the crash report file |
| Add `print()` and redeploy | Variables already captured |
| Manually audit for secrets before sharing | Automatic redaction built in |
| Guess which thread from logs | Thread state captured at crash time |
| SSH in to check environment | Environment metadata in every report |

## Quick Start

```bash
pip install safedump[view]
```

```python
import safedump

safedump.install()
```

## CLI at a Glance

| Command | Description |
|---|---|
| `safedump view` | View the latest crash report (Rich terminal) |
| `safedump view --html` | Export as a self-contained HTML file |
| `safedump list --type KeyError` | Filter crash reports by type |
| `safedump stats` | Aggregate crash statistics |
| `safedump doctor` | Diagnose configuration issues |
| `safedump serve` | Start a local web browser UI |

## Design Principles

- **Local-first** -- Everything works offline. No accounts. No cloud.
- **Privacy-first** -- Secrets redacted before storage. Reports never
  leave your machine unless you share them.
- **Extensible** -- Custom serializers, redaction rules, and
  notification hooks without modifying core.
