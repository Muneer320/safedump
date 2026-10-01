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
- **Delete** -- `DELETE /api/reports/<filename>` with the per-run token
  printed at startup in the `X-Safedump-Token` header.

## Design Constraints

The server is intentionally minimal:

- **Localhost only by default** -- Binding elsewhere prints a warning.
- **No cross-origin access** -- No CORS headers are sent, so other sites
  open in your browser cannot read the API.
- **Host header checked** -- Requests must use the address the server is
  bound to. This blocks DNS-rebinding attacks.
- **Token for deletes** -- A random token is generated on every start.
- **Strict report names** -- Only `*.safedump.json[.gz]` names in the
  report directory are served, so `..` paths are rejected.
- **No sessions** -- Every request is stateless.
- **No JavaScript framework** -- Vanilla JS, no build step.
- **No database** -- Reads directly from the filesystem.
- **stdlib only** -- Built on `http.server`.

## Architecture

The server reuses the same `render_html()` function as the CLI
HTML export. The report list is served from a vanilla JS single-page
app embedded in the server module.
