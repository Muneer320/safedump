# Roadmap

## v1.1.0 — Community & Integration ✅ (Current)

- [x] Framework integration guides (Flask, FastAPI, Django)
- [x] `safedump view --json` flag
- [x] Capture-layer edge case tests (MemoryError, KeyboardInterrupt, SystemExit)
- [x] Friendly error when Rich is missing
- [x] Dynamic version via importlib.metadata

## v1.2 — Shareability

- [ ] HTML crash report export (`safedump view --html`)
- [ ] Local web server for browsing reports (`safedump serve`)
- [ ] Logging module integration (`SafedumpLogHandler`)
- [ ] Windows first-class support (CI runner, path handling)
- [ ] Entropy-based secret detection (opt-in)

## v1.3 — Ecosystem

- [ ] Context manager API (`with safedump.watch():`)
- [ ] Comprehensive documentation site (GitHub Pages / mkdocs)
- [ ] Plugin ecosystem documentation
- [ ] Performance benchmarks page

## v2.0 — Plugin Ecosystem

- [ ] Third-party serializer packages (numpy, pandas, PIL, etc.)
- [ ] Stable plugin API with discovery
- [ ] Community-contributed redaction rule packs
- [ ] Custom output formatters (HTML, Markdown, etc.)
