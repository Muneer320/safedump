"""Self-contained HTML crash report renderer for Safedump.

Generates a single HTML file with no external dependencies.
Dark theme, collapsible frame sections, type badges, copy-JSON button.
"""

from __future__ import annotations

import html
import json
from typing import Any


def render_html(report: dict[str, Any]) -> str:
    """Render a crash report as a self-contained HTML page.

    Args:
        report: A crash report dict (as returned by load_report).

    Returns:
        An HTML string that can be saved to a .html file and opened
        in any browser. No external CSS, JS, fonts, or images.
    """
    exc = report.get("exception", {})
    env = report.get("environment", {})
    frames = report.get("frames", [])
    threads = report.get("threads", [])
    redactions = report.get("redactions", [])

    raw_json = html.escape(json.dumps(report, indent=2, ensure_ascii=False))
    exc_type = html.escape(exc.get("type", "Unknown"))
    exc_message = html.escape(exc.get("message", ""))
    exc_module = html.escape(exc.get("module", ""))
    timestamp = html.escape(report.get("timestamp", ""))
    fingerprint = html.escape(report.get("fingerprint", ""))
    occurrence_count = report.get("occurrence_count", 1)
    platform_name = html.escape(report.get("platform", ""))
    python_version = html.escape(report.get("python_version", ""))
    safedump_version = html.escape(report.get("safedump_version", ""))
    schema_version = report.get("schema_version", 0)

    frames_html = "\n".join(_render_frames(frames))
    threads_html = "\n".join(_render_threads(threads))
    redactions_html = "\n".join(_render_redactions(redactions))
    env_vars_html = _render_env_vars(env)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Crash Report — {exc_type}</title>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
    background: #0d1117; color: #c9d1d9; line-height: 1.6; padding: 20px;
  }}
  .container {{ max-width: 960px; margin: 0 auto; }}
  h1 {{ font-size: 1.5em; margin-bottom: 4px; }}
  h2 {{ font-size: 1.15em; margin: 20px 0 8px; color: #58a6ff; }}
  .meta {{ color: #8b949e; font-size: 0.85em; margin-bottom: 16px; }}
  .meta span {{ margin-right: 16px; }}
  .badge {{
    display: inline-block; padding: 2px 8px; border-radius: 3px;
    font-size: 0.8em; font-weight: 600; margin: 1px;
  }}
  .badge-error {{ background: #da3633; color: #fff; }}
  .badge-info {{ background: #1f6feb; color: #fff; }}
  .badge-warn {{ background: #d29922; color: #fff; }}
  .badge-type {{ background: #30363d; color: #c9d1d9; }}
  details {{ background: #161b22; border: 1px solid #30363d; border-radius: 6px;
             margin-bottom: 8px; }}
  details summary {{ padding: 10px 14px; cursor: pointer; font-family: "SF Mono", "Cascadia Code", "Fira Code", monospace; font-size: 0.85em; }}
  details summary:hover {{ background: #1c2128; }}
  .frame-body {{ padding: 10px 14px; border-top: 1px solid #30363d; }}
  .frame-body pre {{
    background: #0d1117; padding: 8px 12px; border-radius: 4px;
    overflow-x: auto; font-size: 0.82em; line-height: 1.45;
    font-family: "SF Mono", "Cascadia Code", "Fira Code", monospace;
  }}
  .var-table {{ width: 100%; border-collapse: collapse; font-size: 0.82em; }}
  .var-table th, .var-table td {{
    padding: 4px 8px; text-align: left; border-bottom: 1px solid #21262d;
  }}
  .var-table th {{ color: #8b949e; font-weight: 600; }}
  .code-context {{ margin: 8px 0; padding: 0; list-style: none; }}
  .code-context li {{ padding: 2px 12px; font-family: "SF Mono", "Cascadia Code", "Fira Code", monospace; font-size: 0.82em; }}
  .code-context .active {{ background: #da363333; border-left: 3px solid #da3633; }}
  .crash-site {{ color: #ff7b72; font-weight: 600; }}
  .thread {{ margin-bottom: 6px; }}
  .redaction {{ color: #d29922; font-size: 0.85em; }}
  .json-block {{ margin-top: 16px; }}
  .json-block pre {{
    background: #0d1117; padding: 12px; border-radius: 6px;
    overflow-x: auto; font-size: 0.78em; line-height: 1.4; max-height: 400px;
    font-family: "SF Mono", "Cascadia Code", "Fira Code", monospace;
  }}
  .copy-btn {{
    float: right; padding: 4px 12px; font-size: 0.8em;
    background: #21262d; color: #c9d1d9; border: 1px solid #30363d;
    border-radius: 4px; cursor: pointer;
  }}
  .copy-btn:hover {{ background: #30363d; }}
  .env-table {{ font-size: 0.85em; }}
  .env-table td {{ padding: 2px 8px; }}
  .footer {{ margin-top: 32px; color: #484f58; font-size: 0.78em; text-align: center; }}
  @media print {{
    body {{ background: #fff; color: #000; }}
    details {{ border: 1px solid #ccc; background: #f6f8fa; }}
    .json-block pre {{ background: #f6f8fa; }}
    .copy-btn {{ display: none; }}
    .badge-type {{ background: #e1e4e8; color: #000; }}
  }}
</style>
</head>
<body>
<div class="container">
<h1><span class="badge badge-error">{exc_type}</span></h1>
<p style="margin-bottom:4px">{exc_message}</p>
<div class="meta">
  <span>{timestamp}</span>
  <span>schema v{schema_version}</span>
  {f"<span>occurrence #{occurrence_count}</span>" if occurrence_count > 1 else ""}
  {f'<span class="badge badge-info">{fingerprint}</span>' if fingerprint else ""}
</div>
<div class="meta">
  <span>{platform_name}</span>
  <span>Python {python_version}</span>
  {f"<span>safedump {safedump_version}</span>" if safedump_version else ""}
  {f"<span>{exc_module}</span>" if exc_module else ""}
</div>

<h2>Stack Frames ({len(frames)})</h2>
{frames_html}

<h2>Environment</h2>
<details>
<summary>System Info</summary>
<div class="frame-body">
  <table class="env-table">
    <tr><td><strong>OS</strong></td><td>{html.escape(env.get("os_name", ""))} / {html.escape(env.get("os_version", ""))}</td></tr>
    <tr><td><strong>Python</strong></td><td>{html.escape(env.get("python_impl", ""))}</td></tr>
    <tr><td><strong>CWD</strong></td><td>{html.escape(env.get("cwd", ""))}</td></tr>
  </table>
</div>
</details>
{env_vars_html}

<h2>Threads ({len(threads)})</h2>
{threads_html}

{h2_redactions(redactions_html, redactions)}

<div class="json-block">
<h2>Raw Report</h2>
<button class="copy-btn" onclick="navigator.clipboard.writeText(document.getElementById('raw-json').textContent).then(() => this.textContent='Copied!').catch(() => this.textContent='Failed')">Copy JSON</button>
<pre id="raw-json">{raw_json}</pre>
</div>

<div class="footer">Generated by Safedump v{safedump_version}</div>
</div>
</body>
</html>"""


def _render_frames(frames: list[dict[str, Any]]) -> list[str]:
    """Render each frame as a collapsible details element."""
    parts = []
    for _i, frame in enumerate(frames):
        func = html.escape(frame.get("function", "<unknown>"))
        filepath = html.escape(frame.get("file", ""))
        line = frame.get("line", 0)
        is_crash = frame.get("is_crash_site", False)
        code_ctx = frame.get("code_context", [])
        locals_dict = frame.get("locals", {})

        site_marker = crash_marker(is_crash)
        summary = f"{site_marker}{func} &mdash; {filepath}:{line}"

        locals_rows = ""
        if locals_dict:
            rows = []
            for name, var in sorted(locals_dict.items()):
                var_type = html.escape(var.get("type", "?"))
                var_value = html.escape(var.get("value", ""))
                truncated = var.get("is_truncated", False)
                trunc_marker = (
                    ' <span class="badge badge-warn">truncated</span>' if truncated else ""
                )
                rows.append(
                    f"<tr><td>{html.escape(name)}</td>"
                    f'<td><span class="badge badge-type">{var_type}</span>{trunc_marker}</td>'
                    f'<td style="max-width:400px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{var_value}</td></tr>'
                )
            locals_rows = (
                '<table class="var-table"><tr><th>Variable</th><th>Type</th><th>Value</th></tr>'
                + "\n".join(rows)
                + "</table>"
            )

        code_lines = ""
        if code_ctx:
            ctx_lines = []
            for j, cl in enumerate(code_ctx):
                lineno = line - len(code_ctx) + j + 1
                active = " active" if lineno == line else ""
                ctx_lines.append(
                    f'<li class="code-context{active}"><span style="color:#484f58">{lineno}</span>  {html.escape(cl)}</li>'
                )
            code_lines = '<ul class="code-context">' + "\n".join(ctx_lines) + "</ul>"

        body = ""
        if code_lines or locals_rows:
            sections = []
            if code_lines:
                sections.append(code_lines)
            if locals_rows:
                sections.append(locals_rows)
            body = '<div class="frame-body">' + "\n".join(sections) + "</div>"

        parts.append(
            f"<details {'open' if is_crash else ''}>\n"
            f"<summary>{summary}</summary>\n"
            f"{body}\n"
            f"</details>"
        )
    return parts


def _render_threads(threads: list[dict[str, Any]]) -> list[str]:
    """Render thread information."""
    parts = []
    for t in threads:
        name = html.escape(t.get("name", ""))
        ident = t.get("ident")
        daemon = t.get("daemon", False)
        crashed = t.get("crashed", False)
        flags = []
        if daemon:
            flags.append("daemon")
        if crashed:
            flags.append('<span class="badge badge-error">crashed</span>')
        flag_str = " ".join(flags)
        parts.append(f'<div class="thread">Thread: {name} (id: {ident}) {flag_str}</div>')
    return parts


def _render_redactions(redactions: list[dict[str, Any]]) -> list[str]:
    """Render redaction records."""
    parts = []
    for r in redactions:
        location = html.escape(r.get("location", ""))
        reason = html.escape(r.get("reason", ""))
        rule = html.escape(r.get("rule", ""))
        parts.append(f'<div class="redaction">{location} &mdash; {reason} ({rule})</div>')
    return parts


def _render_env_vars(env: dict[str, Any]) -> str:
    """Render environment variables if present."""
    var_names = env.get("env_var_names", [])
    argv = env.get("argv")
    sections = []

    if var_names:
        names_str = ", ".join(html.escape(n) for n in sorted(var_names)[:50])
        if len(var_names) > 50:
            names_str += f", ... ({len(var_names) - 50} more)"
        sections.append(
            f"<details>\n<summary>Environment Variables ({len(var_names)})</summary>\n"
            f'<div class="frame-body"><pre style="font-size:0.82em">{names_str}</pre></div>\n'
            f"</details>"
        )

    if argv:
        argv_escaped = [html.escape(a) for a in argv]
        sections.append(
            f"<details>\n<summary>Command Line Arguments</summary>\n"
            f'<div class="frame-body"><pre style="font-size:0.82em">{" ".join(argv_escaped)}</pre></div>\n'
            f"</details>"
        )

    return "\n".join(sections)


def crash_marker(is_crash: bool) -> str:
    """Small marker for crash site."""
    if is_crash:
        return '<span class="crash-site">&#9656;</span> '
    return ""


def h2_redactions(redactions_html: str, redactions: list) -> str:
    """Conditionally render redactions section."""
    if not redactions:
        return ""
    return f"<h2>Redactions ({len(redactions)})</h2>\n{redactions_html}"
