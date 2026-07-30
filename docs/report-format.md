# Crash Report Format

Crash reports are JSON files with the extension `.safedump.json`
(or `.safedump.json.gz` when compression is enabled).

## File Naming

```
{timestamp}-{exception_type}-{hash}.safedump.json
```

Example: `2026-07-30-12-00-00-ValueError-a1b2c3d4.safedump.json`

The timestamp ensures chronological sorting. The hash provides
deduplication without revealing crash details.

## Schema Version

Every report includes a `schema_version` field. The current version
is **v1**. Old reports are automatically migrated forward when loaded
via `load_report()`.

## Top-Level Fields

| Field | Type | Description |
|---|---|---|
| `schema_version` | int | Report schema version (currently 1) |
| `safedump_version` | str | Version that captured this report |
| `fingerprint` | str | 12-char SHA256 crash identifier |
| `timestamp` | str | ISO-8601 capture time |
| `python_version` | str | Python version string |
| `platform` | str | OS platform (sys.platform) |
| `exception` | object | Exception details |
| `frames` | array | Stack frames (caller first) |
| `environment` | object | Runtime environment snapshot |
| `threads` | array | Thread state at capture time |
| `redactions` | array | Redaction audit trail |

## Exception Object

| Field | Type | Description |
|---|---|---|
| `type` | str | Exception class name (e.g. `ValueError`) |
| `message` | str | Exception message |
| `module` | str | Module where exception is defined |
| `is_explicitly_chained` | bool | Whether `__cause__` was set |
| `sub_exceptions` | array | Chained/grouped exceptions |

## Frame Object

| Field | Type | Description |
|---|---|---|
| `index` | int | Frame number (0 = crash site) |
| `file` | str | Source file path |
| `line` | int | Line number |
| `function` | str | Function name |
| `code_context` | array | Source lines around the crash site |
| `locals` | object | Local variables (name -> VariableSnapshot) |
| `is_crash_site` | bool | True for the crash frame |

## VariableSnapshot

| Field | Type | Description |
|---|---|---|
| `type` | str | Type name (e.g. `int`, `str`) |
| `value` | str | String representation |
| `is_truncated` | bool | True if value was truncated |
| `original_length` | int | Original length before truncation |

## Environment Object

| Field | Type | Description |
|---|---|---|
| `os_name` | str | `os.name` |
| `os_version` | str | `sys.platform` |
| `python_impl` | str | Python implementation |
| `python_path` | array | `sys.path` |
| `cwd` | str | Current working directory |
| `env_var_names` | array | Environment variable names (opt-in) |
| `argv` | array | Command-line arguments (opt-in) |

## Fingerprint

The `fingerprint` field is a 12-character hex string computed from:

```
SHA256(exception_type + exception_message[:200] + crash_file + crash_line)[:12]
```

This is stable across runs for the same crash in the same location.
Different crashes produce different fingerprints.
