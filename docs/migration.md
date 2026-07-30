# Migration Guide

## Upgrading to v2.0

**No breaking changes.** v2.0 is a stabilization release. All v1.x
public APIs remain functional.

### Deprecations

None.

## Upgrading to v1.3

**No breaking changes.**

### What changed

- New optional `enable_entropy_detection` and `entropy_threshold`
  config parameters.
- New optional `compress` config parameter.
- New optional `on_crash` config parameter.
- New integration modules (`safedump.integrations.*`).
- Reports may now be saved as `.json.gz` when `compress=True`.

### Migration

All existing v1.x reports remain readable. No action required.

## Upgrading to v1.2

**No breaking changes.**

### What changed

- Reports now have a `schema_version` field (v1).
- Reports now have `fingerprint`, `occurrence_count`, `first_seen`,
  `last_seen` fields.
- `metadata` field type widened from `dict[str, str]` to `dict[str, Any]`.
- New CLI commands: `safedump doctor`, `safedump stats`, `safedump serve`.
- New CLI flags: `safedump view --html`, `safedump list --type/--since`.

### Migration

Old reports (no `schema_version`) are automatically migrated on
read. No action required.

## Upgrading to v1.1

**No breaking changes.**

### What changed

- Framework integration guides (Flask, FastAPI, Django).
- `safedump view --json` flag.
- Improved error handling for missing Rich.
- Dynamic version via `importlib.metadata`.

## Upgrading from v0.x

Reports from v0.x (pre-release) may not be forward-compatible with
v1.x. It is recommended to regenerate reports rather than relying on
migration of pre-release data.
