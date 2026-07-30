# Python API

The public API is defined by `safedump.__all__`:

```python
__all__ = [
    "RedactionRule",
    "__version__",
    "capture_exception",
    "configure",
    "disable",
    "enable",
    "install",
    "load_report",
    "register_serializer",
    "test",
    "uninstall",
    "watch",
]
```

Everything not in `__all__` is internal and may change without notice.

## configure(**kwargs)

Configure Safedump globally. Call before `install()`.

```python
safedump.configure(
    preset="production",
    output_dir="~/.safedump",
    privacy_tier=1,
)
```

See [Configuration](getting-started/configuration.md) for full parameter
documentation.

## install()

Install Safedump crash hooks globally.

Replaces `sys.excepthook`, `threading.excepthook`, and
`sys.unraisablehook` with the Safedump crash handler. Safe to call
multiple times -- subsequent calls are no-ops.

```python
safedump.install()
```

## uninstall()

Restore the original Python exception hooks that were active before
`install()` was called. Safe to call multiple times.

## enable()

Alias for `install()`.

## disable()

Alias for `uninstall()`.

## capture_exception(exc=None, *, privacy_tier=None, output_dir=None)

Capture an exception and write a crash report. If `exc` is `None`,
captures the currently handled exception via `sys.exc_info()`.

```python
try:
    result = dangerous_operation()
except Exception:
    path = safedump.capture_exception()
    print(f"Crash captured: {path}")
    raise
```

**Returns:** Path to the crash report file, or `None` if the write
failed.

**Raises:** `RuntimeError` if no exception is available.

## watch(*, privacy_tier=None, output_dir=None) -> _Watch

Return a context manager that captures exceptions raised within its
block without installing global hooks. Exceptions are re-raised after
capture.

```python
with safedump.watch():
    dangerous_code()
```

## load_report(path) -> dict

Load a Safedump crash report as a Python dictionary. Supports both
`.safedump.json` and `.safedump.json.gz` files.

```python
report = safedump.load_report("crash.safedump.json")
print(report["exception"]["type"])
```

**Raises:** `FileNotFoundError`, `ValueError` (invalid format).

## test() -> Path | None

Self-test. Deliberately raises and captures a test exception.

```python
path = safedump.test()
```

**Raises:** `RuntimeError` if not installed.

## register_serializer(type_, handler)

Register a custom serializer for a Python type. The handler receives
an instance and must return a JSON-serializable value.

```python
import numpy as np

safedump.register_serializer(np.ndarray, lambda a: a.tolist())
```

## RedactionRule

A named tuple defining a custom redaction rule.

```python
rule = safedump.RedactionRule(
    pattern=r"\b\d{16}\b",  # 16-digit number
    replacement="[CARD-REDACTED]",
    apply_to="values",
)
```

Fields:

- `pattern` -- regex pattern to match
- `replacement` -- replacement text (default `[REDACTED]`)
- `apply_to` -- `"values"`, `"names"`, or `"both"`
