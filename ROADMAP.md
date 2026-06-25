# Roadmap

## v0.1.0 — Core Capture & Viewing *(in development)*

- [ ] `safedump.install()` / `uninstall()` — crash hook management
- [ ] `safedump.capture_exception()` — manual capture for try/except blocks
- [ ] `safedump.configure()` — configuration with privacy tiers
- [ ] `safedump.test()` — self-test verification
- [ ] `safedump view` — Rich-powered terminal crash report viewer
- [ ] `safedump list` — list recent crash reports
- [ ] Secret redaction — variable name denylist + regex patterns
- [ ] JSON report format with versioned schema
- [ ] Python 3.9–3.13 support
- [ ] Atomic file writes with 0600 permissions

## v0.2.0 — Shareability

- [ ] HTML report export (with XSS protection)
- [ ] `safedump serve` — local web viewer
- [ ] Improved redaction with entropy detection
- [ ] `safedump clean --older-than` — report cleanup
- [ ] Environment variable name capture
- [ ] Windows production-quality support
- [ ] Configuration presets (`preset="production"`)
- [ ] `logging` module integration

## v0.3.0 — Ecosystem

- [ ] Plugin architecture (`register_serializer`, `register_redactor`)
- [ ] `safedump-numpy` — NumPy array support
- [ ] `safedump-pandas` — DataFrame support
- [ ] `safedump-pydantic` — Pydantic model support
- [ ] Community plugin contributions begin

## v0.5.0 — Production

- [ ] Framework documentation (Flask, FastAPI, Django)
- [ ] `sys.monitoring` support (Python 3.12+)
- [ ] Cross-thread stack capture
- [ ] Report HMAC signing
- [ ] Crash deduplication

## v1.0.0 — Stability

- [ ] Stable public API freeze
- [ ] Deprecation policy enforcement
- [ ] Complete documentation
- [ ] Plugin API freeze
- [ ] Semantic versioning from this point forward

## v2.0.0+ — Future (Undefined)

Framework integrations and broader ecosystem features will be reconsidered based on community feedback and maintainer capacity.
