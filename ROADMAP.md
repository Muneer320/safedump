# Roadmap

## v1.0.0 — Stable API ✅ (Current)

- [x] Core crash capture + frame walking (Python 3.9–3.13)
- [x] Secret redaction (denylist + regex + custom rules)
- [x] Rich terminal viewer (`safedump view`)
- [x] CLI tools (`view`, `list`, `clean`, `test`)
- [x] Plugin architecture (`register_serializer`)
- [x] Config presets (`production`, `development`, `debug`, `minimal`)
- [x] Privacy tiers (0–4)
- [x] Cross-thread capture
- [x] `before_capture` hook
- [x] 67 tests, CI matrix 3.9–3.13
- [x] Stable API freeze — semver enforced

## v1.1 — Shareability

- [ ] HTML crash report export
- [ ] `safedump serve` — local web viewer
- [ ] Entropy-based secret detection (optional plugin)
- [ ] Report HMAC signing
- [ ] `safedump info` — display current configuration
- [ ] Windows first-class support

## v1.2 — Developer Experience

- [ ] `logging` module integration
- [ ] Context manager API (`with safedump.watch():`)
- [ ] Framework documentation (Flask, FastAPI, Django)
- [ ] Crash deduplication
- [ ] Performance improvements (pre-compiled regex)

## v1.3 — Ecosystem

- [ ] `safedump-numpy` — NumPy array support
- [ ] `safedump-pandas` — DataFrame support
- [ ] `safedump-pydantic` — Pydantic model support
- [ ] Community plugin contributions

## v2.0 — Maturity

- [ ] Plugin API freeze
- [ ] Internationalization
- [ ] Hosted documentation site
- [ ] Commercial support options (if community demand exists)

## Long-Term Vision

Safedump aims to become the default local crash recorder for Python — the tool developers reach for before `print()` debugging, before SSHing into servers, and before asking users "what were the variable values?"
