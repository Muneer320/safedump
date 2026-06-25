# Safedump

[![CI](https://github.com/Muneer320/safedump/actions/workflows/ci.yml/badge.svg)](https://github.com/Muneer320/safedump/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/safedump)](https://pypi.org/project/safedump/)
[![Python](https://img.shields.io/pypi/pyversions/safedump)](https://pypi.org/project/safedump/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> Local-first crash diagnostics for Python. Capture complete debugging context, redact secrets automatically, and inspect crashes offline — without ever touching the cloud.

---

## Why Safedump?

Python's traceback tells you WHERE your code crashed. It doesn't tell you WHY.

Safedump captures **everything you need to debug a crash** — local variables, exception chains, thread state, and environment context — and saves it as a structured, safe-to-share crash report.

```python
import safedump
safedump.install()

# Your application code here...
# When a crash happens, a crash report is saved automatically:
#   Crash report saved: ~/.safedump/crash-2026-06-25-123456-TypeError-a1b2c3d4.json
```

Then inspect it anytime:

```bash
$ safedump view
```

## Features

- 🔒 **Local-first** — zero cloud dependencies, zero telemetry, zero network calls
- 🤫 **Secret redaction** — passwords, tokens, and API keys are automatically scrubbed
- 📋 **Structured reports** — machine-readable JSON with versioned schema
- 🎨 **Beautiful terminal viewer** — inspect crashes with syntax highlighting
- 🧵 **Thread-aware** — captures crashes in worker threads, not just main
- 🔗 **Exception chains** — full `__cause__` and ExceptionGroup support
- 🐍 **Python 3.9–3.13** — works across all supported Python versions

## Installation

```bash
pip install safedump
```

For the terminal viewer:

```bash
pip install safedump[view]
```

## Quick Start

```python
import safedump
safedump.install()
# That's it. Every unhandled crash now produces a report.
```

Manual capture:

```python
try:
    result = dangerous_operation()
except Exception:
    path = safedump.capture_exception()
    print(f"Crash captured: {path}")
    raise  # still propagate
```

View reports:

```bash
$ safedump view              # latest crash
$ safedump view crash.json   # specific crash
$ safedump list              # recent crashes
$ safedump test              # verify installation
```

## Privacy

Safedump is designed for safe sharing. By default (privacy tier 1):

- ✅ Local variables captured with **mandatory redaction**
- ❌ Environment variable values **never captured**
- ❌ Command-line arguments **never captured**
- 🔒 Reports saved with `0600` permissions

Configure your privacy level:

```python
safedump.configure(privacy_tier=1)  # Default: locals + redaction
safedump.configure(privacy_tier=0)  # Minimal: stack traces only
```

See [docs/privacy.md](docs/privacy.md) for details.

## Documentation

- [API Reference](docs/api.md)
- [Architecture](docs/architecture.md)
- [Privacy Guide](docs/privacy.md)
- [Contributing](CONTRIBUTING.md)

## License

MIT © [Muneer Alam](https://github.com/Muneer320)
