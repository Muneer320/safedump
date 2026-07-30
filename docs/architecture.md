# Architecture

Safedump's architecture follows a linear pipeline:

```
Exception raised
      |
      v
Capture (crash_handler)
  - Walk traceback frames
  - Capture locals, environment, threads
  - Compute fingerprint
      |
      v
Sanitize (sanitize)
  - Denylist redaction (variable names)
  - Regex pattern detection (credentials)
  - Entropy-based detection (opt-in)
  - Custom user rules
      |
      v
Serialize (serialize)
  - Convert to JSON via SafedumpEncoder
  - Handle special types (set, deque, etc.)
  - Custom serializers via register_serializer()
      |
      v
Store (save)
  - Generate filename
  - Check for dedup (same fingerprint?)
  - Atomic write (tempfile + os.replace)
  - Optional gzip compression
      |
      v
Notify (on_crash hook)
  - User-defined callback with report path
```

## Module Layout

| Module | Responsibility |
|---|---|
| `_capture.py` | Crash handler, install/uninstall, capture_exception |
| `_frame_walker.py` | Traceback walking, frame/environment/thread capture |
| `_sanitize.py` | Secret detection and redaction |
| `_serialize.py` | JSON encoding with custom type support |
| `_storage.py` | File persistence, dedup, compression |
| `_loader.py` | Report loading, schema migration, listing, stats |
| `_html_render.py` | Self-contained HTML report generation |
| `_server.py` | Local web server (stdlib http.server) |
| `_render.py` | Rich terminal output |
| `_cli.py` | Command-line interface (argparse) |
| `_config.py` | Configuration storage and presets |
| `_types.py` | Data model classes and version constants |
| `watch.py` | Context manager for scoped monitoring |
| `logging_handler.py` | Python logging integration |

## Crash Pipeline

Each stage of the pipeline is wrapped in exception handlers.

- If **capture** fails, the original traceback is always preserved.
- If **sanitize** fails, the report is still saved (unredacted).
- If **save** fails, a fallback to the system temp directory is
  attempted.
- If **all** fails, Python's default exception handling applies.

## Schema Migration

Reports contain a `schema_version` field. When `load_report()` reads
a report, it checks the version and applies any pending migrations
sequentially. This ensures backward compatibility as the format
evolves.

## Fingerprint Generation

Fingerprints use SHA256 of `exception_type + message[:200] +
crash_file + crash_line`. This is stable across runs for the same
crash at the same location.
