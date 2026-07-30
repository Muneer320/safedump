# Installation

Safedump requires Python 3.9 or later. It has **zero required
dependencies** -- the core capture and CLI work out of the box.

## Standard Install

```bash
pip install safedump
```

This installs the core library with basic CLI support (plain text
output).

## With Terminal Viewer

For Rich-powered terminal output with syntax highlighting:

```bash
pip install safedump[view]
```

This adds the `rich` and `pygments` dependencies.

## Minimal Install

If you only need crash capture (no CLI):

```bash
pip install safedump --no-deps
```

## Verify Installation

```bash
safedump --version
```

Should print `safedump 1.3.0` (or later).

## Platform Support

| Platform | Status |
|---|---|
| Linux | Primary development platform |
| macOS | Fully supported |
| Windows | Verified on Windows 11 |
