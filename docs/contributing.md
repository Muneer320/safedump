# Contributing

Thank you for your interest in contributing to Safedump!

## Development Setup

```bash
git clone https://github.com/Muneer320/safedump.git
cd safedump
pip install -e ".[dev]"
pre-commit install
```

## Running Tests

```bash
pytest                           # All tests
pytest -q                        # Quiet mode
pytest tests/test_capture.py     # Specific module
pytest -x                        # Stop on first failure
```

## Code Style

Safedump uses [ruff](https://github.com/astral-sh/ruff) for both
linting and formatting.

```bash
ruff check .      # Lint
ruff format .     # Format
```

## Type Checking

```bash
mypy src/safedump/ --strict
```

All code must pass strict mode type checking.

## Pull Request Process

1. Create a feature branch from `main`.
2. Make your changes with tests.
3. Run `pytest` and `mypy` locally.
4. Create a pull request with a clear description.
5. Ensure CI passes.

## Architecture

See [Architecture](architecture.md) for an overview of the module
layout and crash pipeline.

## Adding a New Redaction Pattern

Edit `src/safedump/_types.py` in the `DENYLIST_SUBSTRING_MATCH` set
or the `secret_patterns` property. Add corresponding tests in
`tests/test_sanitize.py`.

## Writing Integrations

Integrations live in `src/safedump/integrations/` as standalone
modules. Each integration should:

- Import only what it needs from Safedump.
- Never modify Safedump's global state.
- Be importable without side effects.
