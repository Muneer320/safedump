"""Local web server for browsing Safedump crash reports.

Usage: safedump serve [--port PORT] [--host HOST]

Bound to 127.0.0.1 by default for security. Warns if binding publicly.
Uses stdlib http.server -- no external dependencies.
"""

from __future__ import annotations

import contextlib
import json
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from safedump._config import get_config
from safedump._html_render import render_html
from safedump._loader import list_reports, load_report


class SafedumpHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the Safedump crash report browser."""

    # Shared reference set by the server factory
    _reports_dir: Path = Path()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"

        try:
            if path == "/":
                self._serve_index()
            elif path.startswith("/api/reports/"):
                self._serve_api_report(path)
            elif path == "/api/reports":
                self._serve_api_list()
            else:
                self._send_json(404, {"error": "Not found"})
        except Exception as e:
            self._send_json(500, {"error": str(e)})

    def do_DELETE(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/reports/"):
            self._delete_report(parsed.path)
        else:
            self._send_json(404, {"error": "Not found"})

    def _serve_index(self) -> None:
        """Serve the main HTML application."""
        html = _build_index_html()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def _serve_api_list(self) -> None:
        """Return JSON list of all reports."""
        reports = list_reports(self._reports_dir, count=9999)
        items = []
        for r in reports:
            try:
                data = load_report(r)
                items.append(
                    {
                        "path": str(r),
                        "name": r.name,
                        "timestamp": data.get("timestamp", ""),
                        "exception_type": data.get("exception", {}).get("type", "?"),
                        "exception_message": data.get("exception", {}).get("message", "")[:100],
                        "fingerprint": data.get("fingerprint", ""),
                    }
                )
            except Exception:
                items.append(
                    {
                        "path": str(r),
                        "name": r.name,
                        "timestamp": "",
                        "exception_type": "error",
                        "exception_message": "Could not load report",
                        "fingerprint": "",
                    }
                )
        self._send_json(200, items)

    def _serve_api_report(self, path: str) -> None:
        """Return HTML or JSON for a specific report."""
        # Extract the filename from /api/reports/<name>/raw or /api/reports/<name>
        parts = path.split("/")
        if len(parts) < 4:
            self._send_json(404, {"error": "Invalid report path"})
            return
        raw = len(parts) >= 5 and parts[4] == "raw"
        report_name = parts[3]

        report_path = self._reports_dir / report_name
        if not report_path.exists():
            self._send_json(404, {"error": "Report not found"})
            return

        try:
            data = load_report(report_path)
        except Exception as e:
            self._send_json(500, {"error": f"Could not load report: {e}"})
            return

        if raw:
            self._send_json(200, data)
        else:
            html = render_html(data)
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))

    def _delete_report(self, path: str) -> None:
        parts = path.split("/")
        if len(parts) < 4:
            self._send_json(404, {"error": "Invalid report path"})
            return
        report_name = parts[3]
        report_path = self._reports_dir / report_name
        if not report_path.exists():
            self._send_json(404, {"error": "Report not found"})
            return
        try:
            report_path.unlink()
            self._send_json(200, {"deleted": True})
        except OSError as e:
            self._send_json(500, {"error": str(e)})

    def _send_json(self, status: int, data: Any) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode("utf-8"))

    def log_message(self, format: str, *args: Any) -> None:
        sys.stderr.write(f"[safedump serve] {args[0]} {args[1]} {args[2]}\n")


def _build_index_html() -> str:
    """Build the single-page web app HTML."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Safedump Crash Reports</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
         background: #0d1117; color: #c9d1d9; padding: 20px; }
  h1 { font-size: 1.3em; margin-bottom: 16px; }
  .report { background: #161b22; border: 1px solid #30363d; border-radius: 6px;
            padding: 12px 16px; margin-bottom: 8px; cursor: pointer; }
  .report:hover { background: #1c2128; }
  .report .type { display: inline-block; background: #da3633; color: #fff;
                  padding: 2px 8px; border-radius: 3px; font-size: 0.8em; font-weight: 600; }
  .report .ts { color: #8b949e; font-size: 0.85em; margin-left: 8px; }
  .report .msg { color: #8b949e; font-size: 0.85em; margin-top: 4px; }
  .report .fp { font-family: monospace; font-size: 0.8em; color: #484f58; }
  #content { max-width: 800px; margin: 0 auto; }
  .empty { text-align: center; padding: 40px; color: #484f58; }
  .back { display: inline-block; margin-bottom: 12px; color: #58a6ff; cursor: pointer; }
  .delete { float: right; color: #da3633; cursor: pointer; font-size: 0.85em; }
  .loading { text-align: center; padding: 40px; color: #484f58; }
  #report-view { display: none; }
</style>
</head>
<body>
<div id="content">
<div id="list-view">
  <h1>Safedump Crash Reports</h1>
  <div id="report-list" class="loading">Loading...</div>
</div>
<div id="report-view">
  <span class="back" onclick="showList()">&larr; Back to list</span>
  <div id="report-detail"></div>
</div>
</div>
<script>
async function loadList() {
  const res = await fetch("/api/reports");
  const reports = await res.json();
  const el = document.getElementById("report-list");
  if (reports.length === 0) {
    el.innerHTML = '<div class="empty">No crash reports found.</div>';
    return;
  }
  el.innerHTML = reports.map(r =>
    '<div class="report" onclick="showReport(\\'' + r.name + '\\')">' +
    '<span class="type">' + esc(r.exception_type) + '</span>' +
    '<span class="ts">' + esc(r.timestamp.slice(0, 19)) + '</span>' +
    '<span class="fp"> ' + esc(r.fingerprint) + '</span>' +
    '<div class="msg">' + esc(r.exception_message) + '</div>' +
    '</div>'
  ).join("");
}
async function showReport(name) {
  document.getElementById("list-view").style.display = "none";
  document.getElementById("report-view").style.display = "block";
  document.getElementById("report-detail").innerHTML = '<div class="loading">Loading...</div>';
  const res = await fetch("/api/reports/" + encodeURIComponent(name));
  const html = await res.text();
  document.getElementById("report-detail").innerHTML = html;
}
function showList() {
  document.getElementById("list-view").style.display = "block";
  document.getElementById("report-view").style.display = "none";
  loadList();
}
function esc(s) { return (s || "").replace(/[&<>"]/g, function(m) {
  return {"&":"&amp;","<":"&lt;",">":"&gt;","\\"":"&quot;"}[m]; }); }
loadList();
</script>
</body>
</html>"""


def serve(host: str = "127.0.0.1", port: int = 4567) -> None:
    """Start the Safedump crash report web server.

    Args:
        host: Host to bind to (default: 127.0.0.1).
        port: Port to listen on (default: 4567).
    """
    reports_dir = get_config().output_dir

    # Try the requested port, fall back to subsequent ports
    for attempt in range(5):
        try:
            SafedumpHandler._reports_dir = reports_dir

            server = HTTPServer((host, port + attempt), SafedumpHandler)
            url = f"http://{host}:{port + attempt}"

            if host != "127.0.0.1":
                print(
                    f"Warning: Binding to {host} -- accessible from other machines.",
                    file=sys.stderr,
                )

            print(f"Safedump server started: {url}", file=sys.stderr)
            print(f"Reports directory: {reports_dir}", file=sys.stderr)

            # Try to open browser
            with contextlib.suppress(Exception):
                webbrowser.open(url)

            try:
                server.serve_forever()
            except KeyboardInterrupt:
                print("\nShutting down...", file=sys.stderr)
                server.shutdown()
                return

        except OSError:
            if attempt == 4:
                print(
                    f"Error: Could not find an available port (tried {port}-{port + 4}).",
                    file=sys.stderr,
                )
                sys.exit(1)
            continue
