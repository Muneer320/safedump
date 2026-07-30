# Local Web Server

Safedump includes a minimal local web server for browsing crash
reports in the browser.

## Usage

```bash
safedump serve
```

Opens `http://127.0.0.1:4567` in your default browser.

## Options

```bash
safedump serve --port 8080          # Custom port
safedump serve --host 0.0.0.0       # Bind to all interfaces
```

## What it provides

- **Report list** -- Shows all crash reports sorted by time.
- **Individual report view** -- Full HTML report using the same
  renderer as `safedump view --html`.
- **Raw JSON endpoint** -- Access report data as JSON via
  `/api/reports/<filename>/raw`.
- **Delete** -- Delete reports via the API.

## Design Constraints

The server is intentionally minimal:

- **No authentication** -- Localhost only by default.
- **No sessions** -- Every request is stateless.
- **No JavaScript framework** -- Vanilla JS, no build step.
- **No database** -- Reads directly from the filesystem.
- **stdlib only** -- Built on `http.server`.

## Architecture

The server reuses the same `render_html()` function as the CLI
HTML export. The report list is served from a vanilla JS single-page
app embedded in the server module.
