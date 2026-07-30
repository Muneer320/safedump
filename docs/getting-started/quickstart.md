# Quick Start

## One-line Setup

```python
import safedump

safedump.install()
```

That's it. Every unhandled exception now produces a structured crash
report in `~/.safedump/`.

## View a Crash Report

```bash
safedump view
```

This shows the most recent crash with syntax highlighting (if Rich is
installed) or plain text.

## Export as HTML

```bash
safedump view --html report.html
# open report.html in any browser
```

The HTML file is completely self-contained -- no internet required.

## Manual Capture

```python
try:
    result = dangerous_operation()
except Exception:
    path = safedump.capture_exception()
    print(f"Crash captured: {path}")
    raise  # re-raise after capture
```

## List Recent Crashes

```bash
safedump list
```

## Filter by Exception Type

```bash
safedump list --type KeyError --since 7d
```

## Run a Self-Test

```bash
safedump test
```

This deliberately raises and captures a test exception to verify
Safedump is working.
