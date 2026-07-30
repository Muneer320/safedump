# CLI Reference

## safedump view

View a crash report in the terminal or export as HTML.

```bash
safedump view [file]                 # View latest or specific report
safedump view --json                 # Output raw JSON (pipe to jq)
safedump view --html [output.html]   # Export as self-contained HTML
```

If no file is specified, the most recent report is used.

## safedump list

List recent crash reports with optional filtering.

```bash
safedump list                            # Last 20 reports
safedump list --count 50                 # Last 50 reports
safedump list --type KeyError            # Filter by exception type
safedump list --since 7d                 # Reports from last 7 days
safedump list --since 2026-07-01         # Reports since date
safedump list --search "timeout"         # Search in type/message
```

Time filters accept ISO dates (`2026-07-01`) and human-readable
durations (`7d`, `24h`, `30m`).

## safedump stats

Show aggregate crash statistics.

```bash
safedump stats
```

Output includes total crash count, breakdown by exception type,
daily distribution, and top crash sites.

## safedump doctor

Diagnose common configuration issues.

```bash
safedump doctor                   # Quick check
safedump doctor --verbose         # Detailed diagnostics
```

Checks performed:

- Python version compatibility
- Output directory writability
- Exception hook installation status
- Crash report integrity
- Rich terminal viewer availability

## safedump serve

Start a local web server for browsing crash reports.

```bash
safedump serve                        # http://127.0.0.1:4567
safedump serve --port 8080            # Custom port
safedump serve --host 0.0.0.0         # Network accessible
```

The server is intentionally minimal (stdlib `http.server`).
No authentication, no sessions, no JavaScript framework.

## safedump clean

Delete old crash reports.

```bash
safedump clean --older-than 30   # Delete reports older than 30 days
```

## safedump test

Verify Safedump is working.

```bash
safedump test
```

Deliberately captures a test exception and writes a report.

## safedump --version

Print the Safedump version.

```bash
safedump --version
```
