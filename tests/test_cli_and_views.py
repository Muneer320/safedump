# SPDX-FileCopyrightText: 2026 Muneer Alam
#
# SPDX-License-Identifier: MIT

"""In-process tests for the CLI commands, the renderers, the loader filters,
the web server endpoints, the JSON encoder and the pytest plugin."""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from pathlib import Path
from uuid import UUID

import pytest

import safedump
from safedump import _capture, _cli
from safedump._config import reset_config
from safedump._loader import clean_older_than, find_latest, format_value, list_reports, load_report

pytest_plugins = ["pytester"]


@pytest.fixture(autouse=True)
def _clean_state():
    reset_config()
    yield
    _capture.uninstall()
    reset_config()


@pytest.fixture()
def reports(tmp_path):
    """Three different crashes in tmp_path, returned newest last."""
    safedump.configure(output_dir=tmp_path)
    paths = []
    for exc in (ValueError("first problem"), KeyError("second"), ZeroDivisionError("third")):
        try:
            nested = {"items": [1, 2, 3], "label": "x"}  # noqa: F841
            raise exc
        except Exception as e:
            paths.append(safedump.capture_exception(e))
            time.sleep(0.02)
    return paths


def run_cli(*argv: str) -> None:
    old = sys.argv
    sys.argv = ["safedump", *argv]
    try:
        _cli.main()
    finally:
        sys.argv = old


# ── CLI ────────────────────────────────────────────────────────────────


def test_list_and_filters(reports, tmp_path, capsys):
    run_cli("--dir", str(tmp_path), "list")
    out = capsys.readouterr().out
    assert "Recent crash reports (3)" in out and "ZeroDivisionError" in out

    run_cli("--dir", str(tmp_path), "list", "--type", "keyerror")
    assert "KeyError" in capsys.readouterr().out

    run_cli("--dir", str(tmp_path), "list", "--search", "first problem", "--since", "1d")
    out = capsys.readouterr().out
    assert "ValueError" in out and "KeyError" not in out


def test_list_empty(tmp_path, capsys):
    run_cli("--dir", str(tmp_path), "list")
    assert "No crash reports found." in capsys.readouterr().out


def test_view_json_html_and_rich(reports, tmp_path, capsys):
    run_cli("--dir", str(tmp_path), "view", "--json", str(reports[0]))
    assert json.loads(capsys.readouterr().out)["exception"]["type"] == "ValueError"

    html_path = tmp_path / "report.html"
    run_cli("--dir", str(tmp_path), "view", "--html", str(html_path))
    assert "ZeroDivisionError" in html_path.read_text(encoding="utf-8")

    run_cli("--dir", str(tmp_path), "view")
    out = capsys.readouterr().out
    assert "ZeroDivisionError" in out and "Viewing:" in out


def test_view_errors(tmp_path, capsys):
    with pytest.raises(SystemExit):
        run_cli("--dir", str(tmp_path), "view")
    assert "No crash reports found" in capsys.readouterr().err
    with pytest.raises(SystemExit):
        run_cli("view", str(tmp_path / "missing.safedump.json"))
    bad = tmp_path / "bad.safedump.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(SystemExit):
        run_cli("view", str(bad))


def test_stats_clean_doctor_test(reports, tmp_path, capsys):
    run_cli("--dir", str(tmp_path), "stats")
    out = capsys.readouterr().out
    assert "Total crashes: 3 (in 3 report file(s))" in out and "By crash site" in out

    run_cli("--dir", str(tmp_path), "doctor", "--verbose")
    out = capsys.readouterr().out
    assert "[OK] Output directory" in out and "Report integrity" in out

    run_cli("--dir", str(tmp_path), "test")
    assert "Self-test passed" in capsys.readouterr().out

    old = time.time() - 40 * 86400
    os.utime(reports[0], (old, old))
    run_cli("--dir", str(tmp_path), "clean", "--older-than", "30")
    assert "Deleted 1 crash report(s)" in capsys.readouterr().out


def test_no_command_prints_help(capsys):
    with pytest.raises(SystemExit):
        run_cli()
    assert "commands" in capsys.readouterr().out


# ── renderers and formatting ───────────────────────────────────────────


def test_plain_text_renderer_without_rich(reports, monkeypatch, capsys):
    from safedump import _render

    monkeypatch.setattr(_render, "_get_rich", lambda: None, raising=False)
    _render.render(load_report(reports[0]))
    out = capsys.readouterr().out
    assert "ValueError" in out


def test_format_value():
    assert format_value("text") == "text"
    assert format_value({"a": [1, 2]}) == '{"a": [1, 2]}'
    assert format_value("y" * 50, max_chars=10) == "y" * 10 + "..."


# ── loader ─────────────────────────────────────────────────────────────


def test_loader_helpers(reports, tmp_path):
    assert find_latest(tmp_path) == reports[-1]
    assert find_latest(tmp_path / "nope") is None
    assert list_reports(tmp_path / "nope") == []
    assert len(list_reports(tmp_path, until="2000-01-01")) == 0
    assert len(list_reports(tmp_path, since="2000-01-01", count=2)) == 2
    with pytest.raises(ValueError):
        list_reports(tmp_path, since="last tuesday")
    assert clean_older_than(tmp_path / "nope", 1) == 0


def test_load_report_rejects_non_safedump_json(tmp_path):
    other = tmp_path / "x.safedump.json"
    other.write_text('{"hello": 1}', encoding="utf-8")
    with pytest.raises(ValueError):
        load_report(other)


def test_v1_report_from_2_0_still_loads(tmp_path):
    v1 = {
        "schema_version": 1,
        "safedump_version": "2.0.0",
        "exception": {"type": "ValueError", "message": "old"},
        "frames": [
            {
                "file": "a.py",
                "line": 1,
                "locals": {"x": {"type": "int", "value": "1"}},
                "is_crash_site": True,
            },
            {"file": "b.py", "line": 2, "locals": {}, "is_crash_site": False},
        ],
    }
    path = tmp_path / "old.safedump.json"
    path.write_text(json.dumps(v1), encoding="utf-8")
    data = load_report(path)
    assert data["schema_version"] == 2 and data["frames"][1]["is_crash_site"] is True


# ── web server endpoints ───────────────────────────────────────────────


def test_server_list_and_report_endpoints(reports, tmp_path):
    import http.client
    import threading
    from http.server import HTTPServer

    from safedump._server import SafedumpHandler, _build_index_html

    httpd = HTTPServer(("127.0.0.1", 0), SafedumpHandler)
    SafedumpHandler._reports_dir = tmp_path
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    port = httpd.server_address[1]

    def get(path):
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
        try:
            conn.request("GET", path)
            response = conn.getresponse()
            return response.status, response.read().decode("utf-8")
        finally:
            conn.close()

    try:
        status, body = get("/api/reports")
        assert status == 200 and len(json.loads(body)) == 3
        name = reports[0].name
        status, body = get(f"/api/reports/{name}")
        assert status == 200 and "ValueError" in body
        status, body = get(f"/api/reports/{name}/raw")
        assert status == 200 and json.loads(body)["exception"]["type"] == "ValueError"
        assert get("/api/reports/missing.safedump.json")[0] == 404
        assert get("/nothing")[0] == 404
        assert get("/")[0] == 200
        assert "Safedump Crash Reports" in _build_index_html()
    finally:
        httpd.shutdown()
        httpd.server_close()


# ── encoder (used for metadata) ────────────────────────────────────────


class Color(Enum):
    RED = 1


def test_metadata_types_are_encoded(tmp_path):
    def hook(report):
        report.metadata.update(
            {
                "when": datetime(2026, 1, 1, tzinfo=timezone.utc),
                "day": date(2026, 1, 2),
                "money": Decimal("1.50"),
                "id": UUID(int=1),
                "path": Path("a/b"),
                "blob": b"\x00\x01",
                "color": Color.RED,
                "tags": {"b", "a"},
                "pair": (1, 2),
                "obj": object(),
            }
        )
        return report

    safedump.configure(output_dir=tmp_path, before_capture=hook)
    try:
        raise ValueError("meta")
    except ValueError as e:
        data = load_report(safedump.capture_exception(e))
    meta = data["metadata"]
    assert meta["when"].startswith("2026-01-01") and meta["money"] == "1.50"
    assert meta["tags"] == ["a", "b"] and meta["pair"] == [1, 2] and meta["blob"] == "AAE="


# ── pytest plugin ──────────────────────────────────────────────────────


def test_pytest_plugin_captures_only_real_failures(pytester, tmp_path):
    out_dir = tmp_path / "reports"
    pytester.makeconftest(
        f"""
        import safedump
        safedump.configure(output_dir={str(out_dir)!r})
        pytest_plugins = ["safedump.integrations.pytest_plugin"]
        """
    )
    pytester.makepyfile(
        """
        import pytest

        def test_fails():
            value = 41
            assert value == 42

        def test_passes():
            assert True

        @pytest.mark.skip(reason="not now")
        def test_skipped():
            raise RuntimeError("never runs")

        @pytest.mark.xfail(reason="known bug")
        def test_xfail():
            raise RuntimeError("expected")
        """
    )
    result = pytester.runpytest_inprocess()
    result.assert_outcomes(failed=1, passed=1, skipped=1, xfailed=1)
    reports = list(out_dir.glob("*.safedump.json"))
    assert len(reports) == 1
    assert load_report(reports[0])["exception"]["type"] == "AssertionError"
