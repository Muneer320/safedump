# SPDX-FileCopyrightText: 2026 Muneer Alam
#
# SPDX-License-Identifier: MIT

"""Regression tests for behaviour the README promises.

Each test pins a bug that existed in 2.0.0: presets ignored, thread and
unraisable crashes lost, wrong crash-site frame, partial secret leaks
through truncation, custom rules not applied, compression breaking dedup,
privacy tiers having no effect, and the web server being readable cross-origin.
"""

from __future__ import annotations

import gzip
import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

import safedump
from safedump import _capture
from safedump._config import get_config, reset_config
from safedump._loader import compute_stats, list_reports, load_report

GH_TOKEN = "ghp_" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8S9t0"
AWS_KEY = "AKIA" + "ABCDEFGHIJKLMNOP"
STRIPE = "sk_live_" + "abcdefghijklmnopqrstuvwx"
JWT = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"


@pytest.fixture(autouse=True)
def _clean_state():
    reset_config()
    _capture.uninstall()
    yield
    _capture.uninstall()
    reset_config()


def _capture_in(tmp_path: Path, func, **kwargs) -> dict:
    try:
        func()
    except Exception as exc:
        path = safedump.capture_exception(exc, output_dir=tmp_path, **kwargs)
    assert path is not None
    return load_report(path)


def _leaks(text: str, secret: str, window: int = 9) -> bool:
    return any(secret[i : i + window] in text for i in range(len(secret) - window + 1))


# ── configuration ──────────────────────────────────────────────────────


def test_public_configure_applies_preset():
    safedump.configure(preset="debug")
    config = get_config()
    assert (config.privacy_tier, config.include_argv, config.max_depth) == (4, True, 50)


def test_safedump_dir_env_var_sets_default_output_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("SAFEDUMP_DIR", str(tmp_path / "reports"))
    reset_config()
    assert get_config().output_dir == tmp_path / "reports"
    safedump.configure(privacy_tier=1)
    assert get_config().output_dir == (tmp_path / "reports").resolve()


def test_capture_overrides_do_not_touch_global_config(tmp_path):
    safedump.configure(output_dir=tmp_path / "global", privacy_tier=1)

    def boom():
        raise ValueError("x")

    _capture_in(tmp_path / "override", boom, privacy_tier=0)
    assert get_config().privacy_tier == 1
    assert get_config().output_dir == (tmp_path / "global").resolve()


def test_before_capture_hook_runs_for_manual_capture(tmp_path):
    seen = []

    def hook(report):
        report.metadata["tag"] = "from-hook"
        seen.append(report.exception.type)
        return report

    safedump.configure(output_dir=tmp_path, before_capture=hook)

    def boom():
        raise KeyError("k")

    data = _capture_in(tmp_path, boom)
    assert seen == ["KeyError"] and data["metadata"]["tag"] == "from-hook"


# ── frames ─────────────────────────────────────────────────────────────


def _outer():
    return _middle()


def _middle():
    return _inner()


def _inner():
    marker = "inner-frame"  # noqa: F841
    raise RuntimeError("deep")


def test_crash_site_is_the_frame_that_raised(tmp_path):
    data = _capture_in(tmp_path, _outer)
    sites = [f for f in data["frames"] if f["is_crash_site"]]
    assert len(sites) == 1 and sites[0]["function"] == "_inner"
    assert sites[0] is data["frames"][-1]


def test_fingerprint_follows_the_raising_line_not_the_caller(tmp_path):
    def raise_a():
        raise RuntimeError("same")

    def raise_b():
        raise RuntimeError("same")

    def caller(fn):
        fn()

    a = _capture_in(tmp_path / "a", lambda: caller(raise_a))
    b = _capture_in(tmp_path / "b", lambda: caller(raise_b))
    assert a["fingerprint"] != b["fingerprint"]


def test_manual_capture_keeps_more_than_five_frames(tmp_path):
    def recurse(n):
        if n == 0:
            raise RecursionError("bottom")
        recurse(n - 1)

    data = _capture_in(tmp_path, lambda: recurse(20))
    assert len(data["frames"]) >= 21


def test_very_deep_traceback_keeps_the_innermost_frames(tmp_path):
    def recurse(n):
        if n == 0:
            raise RecursionError("bottom")
        recurse(n - 1)

    data = _capture_in(tmp_path, lambda: recurse(150))
    assert len(data["frames"]) == 100
    assert data["frames"][-1]["is_crash_site"] and data["frames"][-1]["locals"]["n"]["value"] == 0


# ── values, limits and redaction ───────────────────────────────────────


def test_locals_are_not_truncated_to_reprlib_defaults(tmp_path):
    def boom():
        text = "x" * 200  # noqa: F841
        items = list(range(50))  # noqa: F841
        raise ValueError("v")

    locals_ = _capture_in(tmp_path, boom)["frames"][-1]["locals"]
    assert locals_["text"]["value"] == "x" * 200
    assert locals_["items"]["value"] == list(range(50))


def test_max_string_length_truncates_after_redaction(tmp_path):
    safedump.configure(output_dir=tmp_path, max_string_length=100)

    def boom():
        # The token straddles the 100-character cut-off.
        blob = "a" * 80 + GH_TOKEN + " " + "-" * 200  # noqa: F841
        raise ValueError("v")

    data = _capture_in(tmp_path, boom)
    var = data["frames"][-1]["locals"]["blob"]
    assert var["is_truncated"] and len(var["value"]) <= 103
    assert not _leaks(json.dumps(data), GH_TOKEN)


def test_no_partial_secret_leaks_anywhere(tmp_path):
    def boom():
        plain = GH_TOKEN  # noqa: F841
        nested = {"service": {"creds": [AWS_KEY, {"note": f"use {STRIPE} for billing"}]}}  # noqa: F841
        header = f"Bearer {JWT}"  # noqa: F841
        raise ValueError(f"request failed with token {GH_TOKEN}")

    data = _capture_in(tmp_path, boom)
    text = json.dumps(data)
    for secret in (GH_TOKEN, AWS_KEY, STRIPE, JWT):
        assert not _leaks(text, secret), secret
    assert data["exception"]["message"] == "request failed with token [REDACTED]"
    assert (
        data["frames"][-1]["locals"]["nested"]["value"]["service"]["creds"][1]["note"]
        == "use [REDACTED] for billing"
    )


def test_denylisted_keys_inside_nested_dicts_are_redacted(tmp_path):
    def boom():
        settings = {"db": {"password": "hunter2-hunter2", "host": "localhost"}}  # noqa: F841
        raise ValueError("v")

    value = _capture_in(tmp_path, boom)["frames"][-1]["locals"]["settings"]["value"]
    assert value == {"db": {"password": "[REDACTED]", "host": "localhost"}}


def test_custom_rule_rewrites_exception_message_and_audit_is_truthful(tmp_path):
    safedump.configure(output_dir=tmp_path, redaction_rules=[r"acct-\d+"])

    def boom():
        raise ValueError("bad acct-12345 here")

    data = _capture_in(tmp_path, boom)
    assert data["exception"]["message"] == "bad [REDACTED] here"
    assert any(r["rule"] == "custom_rule" for r in data["redactions"])


def test_register_serializer_applies_to_locals(tmp_path):
    class Point:
        def __init__(self, x, y):
            self.x, self.y = x, y

    safedump.register_serializer(Point, lambda p: {"x": p.x, "y": p.y})

    def boom():
        pt = Point(3, 4)  # noqa: F841
        raise ValueError("v")

    assert _capture_in(tmp_path, boom)["frames"][-1]["locals"]["pt"]["value"] == {"x": 3, "y": 4}


# ── privacy tiers ──────────────────────────────────────────────────────

MODULE_SETTING = "module-level-value"


class _Account:
    def __init__(self):
        self.owner = "ada"
        self.api_key = "should-be-redacted"


def _crash_with_object():
    account = _Account()  # noqa: F841
    raise ValueError("tier test")


def test_tier_0_has_no_variable_or_environment_data(tmp_path):
    data = _capture_in(tmp_path, _crash_with_object, privacy_tier=0)
    assert all(not f["locals"] for f in data["frames"])
    assert data["environment"]["env_var_names"] == []
    assert data["frames"][-1]["code_context"]  # source lines are still there


def test_tier_1_has_locals_but_objects_stay_opaque(tmp_path):
    value = _capture_in(tmp_path, _crash_with_object, privacy_tier=1)["frames"][-1]["locals"][
        "account"
    ]["value"]
    assert isinstance(value, str) and "_Account" in value


def test_tier_2_expands_object_attributes_with_redaction(tmp_path):
    value = _capture_in(tmp_path, _crash_with_object, privacy_tier=2)["frames"][-1]["locals"][
        "account"
    ]["value"]
    assert value == {"__type__": "_Account", "owner": "ada", "api_key": "[REDACTED]"}


def test_tier_3_adds_crash_site_globals(tmp_path):
    frames = _capture_in(tmp_path, _crash_with_object, privacy_tier=3)["frames"]
    assert frames[-1]["globals"]["MODULE_SETTING"]["value"] == MODULE_SETTING
    assert "GH_TOKEN" in frames[-1]["globals"] and _leaks(json.dumps(frames), GH_TOKEN) is False
    assert all("globals" not in f for f in frames[:-1])


def test_tier_4_adds_env_values_with_secrets_redacted(tmp_path, monkeypatch):
    monkeypatch.setenv("SAFEDUMP_TEST_TOKEN", "abc-123-not-shown")
    monkeypatch.setenv("SAFEDUMP_TEST_PLAIN", "visible")
    monkeypatch.setenv("SAFEDUMP_TEST_URL", f"https://x/?k={GH_TOKEN}")
    env = _capture_in(tmp_path, _crash_with_object, privacy_tier=4)["environment"]
    assert env["env_var_values"]["SAFEDUMP_TEST_PLAIN"] == "visible"
    assert env["env_var_values"]["SAFEDUMP_TEST_TOKEN"] == "[REDACTED]"
    assert env["env_var_values"]["SAFEDUMP_TEST_URL"] == "https://x/?k=[REDACTED]"
    tier3_env = _capture_in(tmp_path / "tier3", _crash_with_object, privacy_tier=3)["environment"]
    assert tier3_env["env_var_values"] == {}


# ── storage: compression, dedup, loader ────────────────────────────────


def _same_crash():
    raise ValueError("same crash every time")


def test_compression_and_dedup_work_together(tmp_path):
    safedump.configure(output_dir=tmp_path, compress=True)
    paths = []
    for _ in range(3):
        try:
            _same_crash()
        except ValueError as exc:
            paths.append(safedump.capture_exception(exc))
    assert len(set(paths)) == 1 and paths[0].name.endswith(".safedump.json.gz")
    raw = paths[0].read_bytes()
    assert raw[:2] == bytes([0x1F, 0x8B])
    assert json.loads(gzip.decompress(raw))["occurrence_count"] == 3


def test_loader_filters_and_stats_include_compressed_reports(tmp_path):
    safedump.configure(output_dir=tmp_path, compress=True)
    for _ in range(2):
        try:
            _same_crash()
        except ValueError as exc:
            safedump.capture_exception(exc)
    assert len(list_reports(tmp_path, type_filter="ValueError")) == 1
    assert len(list_reports(tmp_path, search="every time")) == 1
    stats = compute_stats(tmp_path)
    assert stats["total"] == 2 and stats["reports"] == 1
    assert list(stats["by_site"]) and "test_regressions.py" in next(iter(stats["by_site"]))


# ── hooks (run in subprocesses so the real hooks fire) ─────────────────


def _run(script: str, tmp_path: Path) -> subprocess.CompletedProcess:
    code = textwrap.dedent(script).replace("OUT", repr(str(tmp_path)))
    return subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=60)


def test_thread_crash_is_captured_and_still_printed(tmp_path):
    result = _run(
        """
        import threading, safedump
        safedump.configure(output_dir=OUT)
        safedump.install()
        def work():
            payload = {"step": 3}
            raise ValueError("thread failure")
        t = threading.Thread(target=work, name="worker-1")
        t.start(); t.join()
        """,
        tmp_path,
    )
    reports = list(tmp_path.glob("*.safedump.json"))
    assert len(reports) == 1, result.stderr
    data = load_report(reports[0])
    assert data["exception"]["type"] == "ValueError"
    assert data["frames"][-1]["locals"]["payload"]["value"] == {"step": 3}
    assert [t["name"] for t in data["threads"] if t["crashed"]] == ["worker-1"]
    assert "Exception in thread worker-1" in result.stderr
    assert "TypeError" not in result.stderr


def test_unraisable_exception_is_captured(tmp_path):
    result = _run(
        """
        import gc, safedump
        safedump.configure(output_dir=OUT)
        safedump.install()
        class Leaky:
            def __del__(self):
                raise RuntimeError("from __del__")
        Leaky()
        gc.collect()
        """,
        tmp_path,
    )
    reports = list(tmp_path.glob("*.safedump.json"))
    assert len(reports) == 1, result.stderr
    assert load_report(reports[0])["exception"]["message"] == "from __del__"
    assert "from __del__" in result.stderr


def test_uninstall_restores_the_public_threading_hook():
    import threading

    original = threading.excepthook
    safedump.install()
    assert threading.excepthook is not original
    safedump.uninstall()
    assert threading.excepthook is original


# ── CLI ────────────────────────────────────────────────────────────────


def _cli(*args, env=None):
    full_env = dict(os.environ, **(env or {}))
    return subprocess.run(
        [sys.executable, "-m", "safedump", *args],
        capture_output=True,
        text=True,
        timeout=60,
        env=full_env,
    )


def test_cli_finds_reports_via_dir_flag_and_env_var(tmp_path):
    safedump.configure(output_dir=tmp_path)
    try:
        _same_crash()
    except ValueError as exc:
        safedump.capture_exception(exc)

    by_flag = _cli("--dir", str(tmp_path), "list")
    assert "ValueError" in by_flag.stdout, by_flag.stderr
    by_env = _cli("stats", env={"SAFEDUMP_DIR": str(tmp_path)})
    assert "Total crashes: 1" in by_env.stdout, by_env.stderr


# ── web server ─────────────────────────────────────────────────────────


@pytest.fixture()
def server(tmp_path):
    import threading
    from http.server import HTTPServer

    from safedump._server import SafedumpHandler

    safedump.configure(output_dir=tmp_path)
    try:
        _same_crash()
    except ValueError as exc:
        report = safedump.capture_exception(exc)
    httpd = HTTPServer(("127.0.0.1", 0), SafedumpHandler)
    port = httpd.server_address[1]
    SafedumpHandler._reports_dir = tmp_path
    SafedumpHandler._token = "test-token"
    SafedumpHandler._allowed_hosts = frozenset({f"127.0.0.1:{port}", f"localhost:{port}"})
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield port, report
    httpd.shutdown()
    httpd.server_close()
    SafedumpHandler._allowed_hosts = frozenset()
    SafedumpHandler._token = ""


def _request(port, method, path, headers=None):
    import http.client

    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    conn.request(method, path, headers=headers or {})
    try:
        response = conn.getresponse()
        body = response.read()
        return response.status, dict(response.getheaders()), body
    finally:
        conn.close()


def test_server_sends_no_cors_header(server):
    port, _ = server
    status, headers, _ = _request(port, "GET", "/api/reports")
    assert status == 200
    assert "Access-Control-Allow-Origin" not in headers


def test_server_rejects_foreign_host_headers(server):
    port, _ = server
    status, _, _ = _request(port, "GET", "/api/reports", {"Host": f"evil.example:{port}"})
    assert status == 403


def test_server_delete_requires_token_and_valid_name(server):
    port, report = server
    path = f"/api/reports/{report.name}"
    assert _request(port, "DELETE", path)[0] == 403
    assert _request(port, "DELETE", "/api/reports/..", {"X-Safedump-Token": "test-token"})[0] == 404
    assert _request(port, "GET", "/api/reports/..%2F..%2Fsecret.txt")[0] == 404
    assert _request(port, "DELETE", path, {"X-Safedump-Token": "test-token"})[0] == 200
    assert not report.exists()


# ── integrations ───────────────────────────────────────────────────────


def test_click_control_flow_exceptions_are_not_captured(tmp_path):
    from safedump.integrations.click_plugin import _is_click_control_flow

    exit_cls = type("Exit", (RuntimeError,), {"__module__": "click.exceptions"})
    assert _is_click_control_flow(exit_cls())
    assert not _is_click_control_flow(RuntimeError("real"))
