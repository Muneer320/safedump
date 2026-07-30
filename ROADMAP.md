# Roadmap

Current version: **v1.3.0** (July 2026)

## v1.2 — Foundation & Shareability ✅ *Released*
- Schema versioning + migration framework
- Crash fingerprint generation
- HTML crash report export (`safedump view --html`)
- CLI report filtering (`--type`, `--since`, `--search`)
- `safedump doctor`, `safedump stats`
- `safedump serve` local web server
- 172 tests, 11 commits

## v1.3 — Smart Detection ✅ *Released*
- Shannon entropy-based secret detection (opt-in)
- Crash report deduplication by fingerprint
- Optional gzip report compression
- `on_crash` notification hook
- pytest integration plugin
- Click/Typer integration (`@wrap_click()`)
- 181 tests, 6 commits

## v2.0 — Stabilization & Documentation 🎯 *In progress*
- Documentation site (MkDocs with GitHub Pages)
- API freeze and deprecation policy
- Security review and hardening
- Performance benchmarks
- Packaging and CI review
- Contributing experience improvements
- GitHub cleanup

## v2.1 — Plugin Ecosystem (Future)
- Plugin API via `importlib.metadata` entry points
- Reference first-party plugins (numpy, pandas, PIL)
- Fuzz testing with Hypothesis
- Automated benchmark CI

## Principles

- Every version must be backward compatible within the same major version.
- New features start as optional (opt-in or plugin).
- Documentation precedes community adoption.
- Breaking changes require a major version bump and deprecation cycle.
