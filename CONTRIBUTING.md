# Contributing to Safedump

Thank you for your interest in contributing to Safedump!

## Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md).

## Getting Started

### Prerequisites

- Python 3.9+
- Git

### Development Setup

```bash
git clone https://github.com/Muneer320/safedump.git
cd safedump
pip install -e ".[dev]"
```

### Running Tests

```bash
pytest                          # All tests
pytest tests/test_sanitize.py   # Specific module
pytest -x --ff                  # Fast-fail, failed first
```

### Code Quality

```bash
ruff check .                    # Linting
ruff format .                   # Formatting
mypy src/                       # Type checking
```

### Pre-commit

```bash
pre-commit install              # Install git hooks
pre-commit run --all-files      # Run all hooks manually
```

## Architecture

Safedump is a pipeline architecture with two execution contexts:

- **Hot path** (crash-time): `_capture` → `_sanitize` → `_serialize` → `_storage`
  - Runs inside exception handlers. Must never fail. Stdlib only.
- **Cold path** (post-crash): `_loader` → `_render` → `_cli`
  - Runs in CLI. Can use Rich. Can fail safely.

See [docs/architecture.md](docs/architecture.md) for the full design.

## Quick Contribution Guide

| You want to... | Look at... | Complexity |
|---|---|---|
| Add a secret pattern to redact | `src/safedump/_sanitize.py` — denylist | Easy |
| Add a crash test scenario | `tests/fixtures/` — copy an existing fixture | Easy |
| Fix a type serialization issue | `src/safedump/_serialize.py` — encoder | Medium |
| Add a new CLI flag | `src/safedump/_cli.py` — argparse | Medium |
| Improve frame capture | `src/safedump/_capture.py` — crash_handler | Hard |

## Module Map

All internal modules use the `_` prefix (Python convention for private). Contributors are welcome to modify these modules. Only `__init__.py` exports are the stable public API.

| Module | Purpose | Owner |
|---|---|---|
| `__init__.py` | Public API surface | Architect |
| `_types.py` | Data classes, constants, denylist | Architect |
| `_config.py` | Configuration validation | Architect |
| `_capture.py` | Frame walking, hook management | Senior Engineer |
| `_sanitize.py` | Secret redaction | Security Engineer |
| `_serialize.py` | JSON serialization | Senior Engineer |
| `_storage.py` | Atomic file I/O | Senior Engineer |
| `_loader.py` | Report loading | Senior Engineer |
| `_render.py` | Rich terminal output | Senior Engineer |
| `_cli.py` | CLI entry point | Senior Engineer |

## Pull Request Process

1. Create a branch: `feature/your-feature` or `fix/your-bug`
2. Write tests for your changes
3. Ensure `pytest`, `ruff check`, and `mypy src/` pass
4. Update documentation if you changed the public API
5. Submit a PR against `main`

### PR Checklist

- [ ] Tests pass on all Python versions (CI checks this)
- [ ] New code has tests
- [ ] Public API changes are documented in `docs/api.md`
- [ ] Hot path changes (`_capture`, `_sanitize`, `_serialize`, `_storage`) have been performance reviewed
- [ ] Security-sensitive changes (`_sanitize`, `_capture`) have been security reviewed

## Questions?

Open a [discussion](https://github.com/Muneer320/safedump/discussions) or ask in an issue.
