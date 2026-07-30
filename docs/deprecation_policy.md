# Deprecation Policy

This document defines Safedump's commitment to backward compatibility
and the process for deprecating and removing features.

## Semantic Versioning

Safedump follows [Semantic Versioning 2.0.0](https://semver.org/).

- **Patch releases** (1.2.x) — bug fixes only, no breaking changes.
- **Minor releases** (1.x.0) — new features, deprecations, no breaking changes.
- **Major releases** (2.0.0) — breaking changes allowed.

## What is Public API?

The public API is defined by `safedump.__all__` in `__init__.py`:

- `RedactionRule`
- `capture_exception`
- `configure`
- `disable`
- `enable`
- `install`
- `load_report`
- `register_serializer`
- `test`
- `uninstall`
- `watch`

Everything else (modules prefixed with `_`, internal functions, test
utilities) is internal and may change without notice.

## CLI Commands

CLI subcommands follow the same versioning as the Python API.
Removing or renaming a command requires a major version bump.

## Deprecation Timeline

1. **Deprecation announced** — Function/documentation marked with
   `deprecated` and added to release notes. A `DeprecationWarning`
   is issued at runtime where feasible.
2. **Removal allowed** — After **one minor version** or **6 months**,
   the feature may be removed in the next major version.

| Phase | Timeline | Status |
|---|---|---|
| Deprecation warning | Minor release N | Users see warnings |
| Removal | Major release N+1 | Feature removed |

## Schema Evolution

The crash report schema uses a version number (`schema_version` field).

- **New optional fields** can be added in any release.
- **Removing or renaming fields** requires a major version bump.
- Old reports are automatically migrated forward (never backward).

## Exceptions

Deprecation policy may be bypassed for:

- Security fixes that cannot be applied otherwise.
- Bugs that make a feature permanently non-functional.
- Removing features that have never worked (documented as experimental).

These exceptions will be documented in release notes with clear
justification.

## Deprecation in Practice

When a function is deprecated:

1. The docstring gains a `.. deprecated::` directive.
2. A `DeprecationWarning` is emitted once on first call.
3. The CHANGELOG notes the deprecation.
4. After the deprecation period, the function is removed in a major release.
