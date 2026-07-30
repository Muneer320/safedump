"""Tests for the HTML crash report renderer."""

from __future__ import annotations

import re

from safedump._html_render import render_html


def _make_report(**overrides) -> dict:
    """Create a minimal crash report dict for testing."""
    report = {
        "schema_version": 1,
        "safedump_version": "1.1.0",
        "fingerprint": "a1b2c3d4e5f6",
        "timestamp": "2026-07-30T12:00:00",
        "python_version": "3.11.15",
        "platform": "linux",
        "exception": {
            "type": "ValueError",
            "message": "something went wrong",
            "module": "builtins",
            "is_explicitly_chained": False,
            "sub_exceptions": [],
        },
        "frames": [
            {
                "index": 0,
                "file": "/home/user/app.py",
                "line": 42,
                "function": "main",
                "code_context": ["    result = x / y", "    return result"],
                "locals": {
                    "x": {"type": "int", "value": "10", "is_truncated": False},
                    "y": {"type": "int", "value": "0", "is_truncated": False},
                },
                "is_crash_site": True,
            },
        ],
        "environment": {
            "os_name": "posix",
            "os_version": "linux",
            "python_impl": "CPython",
            "python_path": ["/usr/lib/python3.11"],
            "cwd": "/home/user",
            "env_var_names": ["PATH", "HOME"],
        },
        "threads": [
            {"name": "MainThread", "ident": 123456, "daemon": False, "crashed": True},
        ],
        "redactions": [
            {
                "location": "frames[0].locals.x",
                "reason": "matched denylist: 'api_key'",
                "rule": "variable_name_denylist",
            },
        ],
        "metadata": {},
    }
    report.update(overrides)
    return report


class TestHtmlRender:
    def test_renders_exception_type(self):
        report = _make_report()
        html = render_html(report)
        assert "ValueError" in html

    def test_renders_exception_message(self):
        report = _make_report()
        html = render_html(report)
        assert "something went wrong" in html

    def test_renders_fingerprint(self):
        report = _make_report()
        html = render_html(report)
        assert "a1b2c3d4e5f6" in html

    def test_renders_frame_function(self):
        report = _make_report()
        html = render_html(report)
        assert "main" in html

    def test_renders_frame_locals(self):
        report = _make_report()
        html = render_html(report)
        assert "x" in html
        assert "10" in html
        assert "y" in html

    def test_renders_thread_info(self):
        report = _make_report()
        html = render_html(report)
        assert "MainThread" in html

    def test_renders_redactions(self):
        report = _make_report()
        html = render_html(report)
        assert "matched denylist" in html

    def test_renders_environment(self):
        report = _make_report()
        html = render_html(report)
        assert "HOME" in html
        assert "PATH" in html

    def test_no_external_urls(self):
        """The generated HTML must not reference external resources."""
        report = _make_report()
        html = render_html(report)
        # Check for http://, https://, // in "src=" or "href=" contexts
        external_pattern = r'(src|href)\s*=\s*["\']https?://'
        matches = re.findall(external_pattern, html, re.IGNORECASE)
        assert not matches, f"Found external URLs in HTML: {matches}"
        # Also check no // without protocol (protocol-relative URLs)
        protocol_relative = re.findall(r'(src|href)\s*=\s*["\']//', html)
        assert not protocol_relative, "Found protocol-relative URLs in HTML"

    def test_doctype_declaration(self):
        report = _make_report()
        html = render_html(report)
        assert html.startswith("<!DOCTYPE html>")

    def test_html_contains_body(self):
        report = _make_report()
        html = render_html(report)
        assert "</body>" in html
        assert "</html>" in html

    def test_system_font_stack(self):
        """HTML should use system fonts, not external ones."""
        report = _make_report()
        html = render_html(report)
        assert "font-family: -apple-system" in html
        # No Google Fonts or external font references
        assert "fonts.googleapis.com" not in html
        assert "fonts.gstatic.com" not in html

    def test_no_cdn_references(self):
        report = _make_report()
        html = render_html(report)
        assert "cdn." not in html.lower()

    def test_print_css_present(self):
        report = _make_report()
        html = render_html(report)
        assert "@media print" in html

    def test_copy_json_button_present(self):
        report = _make_report()
        html = render_html(report)
        assert "Copy JSON" in html or "copy-btn" in html

    def test_handles_empty_locals(self):
        report = _make_report()
        report["frames"][0]["locals"] = {}
        html = render_html(report)
        assert "main" in html  # Still renders the frame

    def test_handles_no_frames(self):
        report = _make_report()
        report["frames"] = []
        html = render_html(report)
        assert "Stack Frames (0)" in html

    def test_handles_no_threads(self):
        report = _make_report()
        report["threads"] = []
        html = render_html(report)
        assert "Threads (0)" in html

    def test_html_escapes_special_chars(self):
        """Exception messages with HTML characters must be escaped."""
        report = _make_report()
        report["exception"]["message"] = "<script>alert('xss')</script>"
        html = render_html(report)
        assert "&lt;script&gt;" in html
        assert "<script>" not in html

    def test_handles_unicode(self):
        report = _make_report()
        report["exception"]["message"] = "error: 日本語 / emoji: 🚀"
        html = render_html(report)
        assert "日本語" in html or "emoji" in html
