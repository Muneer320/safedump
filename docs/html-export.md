# HTML Export

Safedump can generate self-contained HTML crash reports that work
in any browser without an internet connection.

## Basic Usage

```bash
safedump view --html report.html
```

This produces a single `.html` file containing the full crash report
with dark theme, collapsible stack frames, and type badges.

## Specify Output Path

```bash
safedump view --html ~/Desktop/crash-report.html
```

## HTML Features

- **Self-contained** -- Zero external dependencies. No CDN, no Google
  Fonts, no external CSS or JS. Works offline forever.
- **Dark theme** -- Designed for developer workflows.
- **Collapsible frames** -- Stack frames expand/collapse individually.
- **Crash site highlighting** -- The crash frame is expanded by
  default and marked in red.
- **Variable tables** -- Local variables shown with type badges and
  values.
- **Copy JSON button** -- One-click copy of the raw report.
- **Print-friendly CSS** -- Page prints cleanly with white background.
- **System font stack** -- No font downloads.

## Architecture

The HTML renderer is a pure function: `dict -> str`. It takes a
loaded crash report and returns an HTML string. The server and CLI
both reuse the same renderer -- there is no duplicated formatting
logic.
