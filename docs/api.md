# API Reference

## Public API (v1.0.0 — Stable)

Safedump exposes 11 public names. All other modules (prefixed with `_`) are private and may change without notice.

### `safedump.configure(**kwargs)`

Configure Safedump globally. Call before `install()`.

```python
def configure(
    *,
    preset: str | None = None,
    output_dir: str | Path = "~/.safedump",
    privacy_tier: int = 1,
    include_env_names: bool = True,
    include_argv: bool = False,
    max_string_length: int = 10000,
    max_collection_items: int = 100,
    max_depth: int = 5,
    redaction_rules: list[str | RedactionRule] | None = None,
    before_capture: Callable[[CrashReport], CrashReport | None] | None = None,
) -> None
```

**Presets:** `"production"`, `"development"`, `"debug"`, `"minimal"`

**Privacy Tiers:**
| Tier | Captures |
|---|---|
| 0 | Stack traces + exception info only |
| 1 (default) | Locals with mandatory redaction |
| 2 | Tier 1 + instance attributes, function arguments |
| 3 | Tier 2 + globals (redacted), env var names |
| 4 | Everything including env values. Never in production. |

---

### `safedump.install()`

Install crash hooks. Replaces `sys.excepthook`, `threading.excepthook`, `sys.unraisablehook`.

```python
def install() -> None
```

---

### `safedump.uninstall()`

Restore original Python exception hooks.

```python
def uninstall() -> None
```

---

### `safedump.capture_exception(exc=None, *, privacy_tier=None, output_dir=None)`

Manually capture an exception. Use in `except` blocks.

```python
def capture_exception(
    exc: BaseException | None = None,
    *,
    privacy_tier: int | None = None,
    output_dir: str | Path | None = None,
) -> Path | None
```

Returns the crash report file path, or `None` if the write failed.

---

### `safedump.test()`

Self-test — raises and captures a test exception.

```python
def test() -> Path | None
```

Raises `RuntimeError` if Safedump is not installed.

---

### `safedump.load_report(path)`

Load a crash report from disk.

```python
def load_report(path: str | Path) -> dict[str, Any]
```

Raises `FileNotFoundError` or `ValueError` on invalid input.

---

### `safedump.register_serializer(type_, handler)`

Register a custom serializer for a Python type.

```python
def register_serializer(type_: type, handler: Callable[[Any], Any]) -> None
```

Example:
```python
import numpy as np
safedump.register_serializer(np.ndarray, lambda a: a.tolist())
```

---

### `safedump.RedactionRule`

A custom secret redaction rule.

```python
class RedactionRule(NamedTuple):
    pattern: str          # Regex pattern
    replacement: str = "[REDACTED]"
    apply_to: str = "values"  # "values" | "names" | "both"
```

---

### `safedump.enable()` / `safedump.disable()`

Aliases for `install()` and `uninstall()`.

---

### `safedump.__version__`

Version string (e.g., `"1.0.0"`).
