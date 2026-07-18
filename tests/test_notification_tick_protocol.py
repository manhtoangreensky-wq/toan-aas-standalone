"""Focused safety contracts for the short-lived Inbox Automation Cron tick."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from urllib.request import Request

import pytest


ROOT = Path(__file__).parents[1]
RUNNER_PATH = ROOT / "scripts" / "notifications" / "run_notification_tick.py"


def _runner():
    spec = importlib.util.spec_from_file_location("notification_tick_runner_test", RUNNER_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _configure_valid_tick(monkeypatch) -> None:
    monkeypatch.setenv("WEBAPP_NOTIFICATION_TICK_SECRET", "n" * 32)
    monkeypatch.setenv("WEBAPP_NOTIFICATION_TICK_URL", "https://app.toanaas.vn/internal/v1/notifications/tick")
    monkeypatch.setenv("WEBAPP_NOTIFICATION_TICK_ORIGIN", "https://app.toanaas.vn")


def test_notification_tick_runner_fails_closed_for_missing_secret_or_untrusted_url(monkeypatch) -> None:
    runner = _runner()
    monkeypatch.delenv("WEBAPP_NOTIFICATION_TICK_SECRET", raising=False)
    monkeypatch.setenv("WEBAPP_NOTIFICATION_TICK_URL", "https://app.toanaas.vn/internal/v1/notifications/tick")
    monkeypatch.setenv("WEBAPP_NOTIFICATION_TICK_ORIGIN", "https://app.toanaas.vn")
    with pytest.raises(runner.TickConfigurationError):
        runner.build_request()

    monkeypatch.setenv("WEBAPP_NOTIFICATION_TICK_SECRET", "n" * 32)
    monkeypatch.setenv("WEBAPP_NOTIFICATION_TICK_URL", "https://evil.example/internal/v1/notifications/tick")
    with pytest.raises(runner.TickConfigurationError):
        runner.build_request()

    monkeypatch.setenv("WEBAPP_NOTIFICATION_TICK_URL", "https://app.toanaas.vn/elsewhere")
    with pytest.raises(runner.TickConfigurationError):
        runner.build_request()

    monkeypatch.setenv("WEBAPP_NOTIFICATION_TICK_URL", "https://user:pass@app.toanaas.vn/internal/v1/notifications/tick")
    with pytest.raises(runner.TickConfigurationError):
        runner.build_request()

    monkeypatch.setenv("WEBAPP_NOTIFICATION_TICK_URL", "https://app.toanaas.vn:8443/internal/v1/notifications/tick")
    with pytest.raises(runner.TickConfigurationError):
        runner.build_request()


def test_notification_tick_runner_pins_a_pure_origin_and_allows_local_http_only_when_explicit(monkeypatch) -> None:
    runner = _runner()
    _configure_valid_tick(monkeypatch)
    assert runner._tick_url() == "https://app.toanaas.vn/internal/v1/notifications/tick"

    monkeypatch.setenv("WEBAPP_NOTIFICATION_TICK_ORIGIN", "https://app.toanaas.vn/extra")
    with pytest.raises(runner.TickConfigurationError):
        runner._tick_url()

    monkeypatch.setenv("WEBAPP_NOTIFICATION_TICK_URL", "http://127.0.0.1/internal/v1/notifications/tick")
    monkeypatch.setenv("WEBAPP_NOTIFICATION_TICK_ORIGIN", "http://127.0.0.1")
    with pytest.raises(runner.TickConfigurationError):
        runner._tick_url()

    monkeypatch.setenv("WEBAPP_NOTIFICATION_ALLOW_INSECURE_LOCAL", "true")
    assert runner._tick_url() == "http://127.0.0.1/internal/v1/notifications/tick"


def test_notification_tick_runner_uses_the_server_integer_budget_and_keeps_transport_margin(monkeypatch) -> None:
    runner = _runner()
    monkeypatch.setenv("WEBAPP_NOTIFICATION_MAX_RUN_SECONDS", "20")
    assert runner._timeout() == 25.0
    monkeypatch.setenv("WEBAPP_NOTIFICATION_MAX_RUN_SECONDS", "20.5")
    with pytest.raises(runner.TickConfigurationError):
        runner._timeout()
    monkeypatch.setenv("WEBAPP_NOTIFICATION_MAX_RUN_SECONDS", "26")
    with pytest.raises(runner.TickConfigurationError):
        runner._timeout()


def test_notification_tick_runner_never_imports_web_app_bot_or_privileged_authorities() -> None:
    source = RUNNER_PATH.read_text(encoding="utf-8")
    for forbidden in (
        "import app", "from app", "import bot", "from bot", "copyfast_notification_center",
        "copyfast_db", "copyfast_bridge", "PayOS", "import wallet", "from wallet",
        "import provider", "from provider", "sqlite3", "requests", "httpx",
    ):
        assert forbidden not in source
    assert '"X-Notify-Signature"' in source
    assert "ProxyHandler({})" in source
    assert "_RejectRedirect" in source
    assert "_opener().open(request, timeout=_timeout())" in source


class _Response:
    def __init__(self, payload: dict[str, object], *, content_type: str = "application/json") -> None:
        self._payload = json.dumps(payload).encode("utf-8")
        self.headers = {"Content-Type": content_type}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> bool:
        return False

    def getcode(self) -> int:
        return 200

    def read(self, size: int) -> bytes:
        assert size > len(self._payload)
        return self._payload


class _Opener:
    def __init__(self, response: _Response) -> None:
        self.response = response
        self.calls: list[tuple[Request, float]] = []

    def open(self, request: Request, *, timeout: float):
        self.calls.append((request, timeout))
        return self.response


def _stub_signed_request(request_id: str) -> tuple[str, Request, str]:
    return (
        "https://app.toanaas.vn/internal/v1/notifications/tick",
        Request("https://app.toanaas.vn/internal/v1/notifications/tick", data=b"{}", method="POST"),
        request_id,
    )


def test_notification_tick_runner_accepts_only_a_matching_bounded_json_receipt(monkeypatch) -> None:
    runner = _runner()
    request_id = "123e4567-e89b-42d3-a456-426614174000"
    monkeypatch.setattr(runner, "build_request", lambda: _stub_signed_request(request_id))
    opener = _Opener(_Response({"ok": True, "status": "guarded", "data": {"request_id": request_id}}))
    monkeypatch.setattr(runner, "_opener", lambda: opener)
    monkeypatch.setattr(runner, "_timeout", lambda: 25.0)

    assert runner.invoke_once() == {"ok": True, "status": "guarded", "request_id": request_id}
    assert len(opener.calls) == 1
    assert opener.calls[0][1] == 25.0


def test_notification_tick_runner_rejects_a_response_with_a_different_request_id(monkeypatch) -> None:
    runner = _runner()
    request_id = "123e4567-e89b-42d3-a456-426614174000"
    monkeypatch.setattr(runner, "build_request", lambda: _stub_signed_request(request_id))
    monkeypatch.setattr(
        runner,
        "_opener",
        lambda: _Opener(_Response({"ok": True, "status": "completed", "data": {"request_id": "wrong-id"}})),
    )
    monkeypatch.setattr(runner, "_timeout", lambda: 25.0)

    with pytest.raises(RuntimeError, match="khớp request"):
        runner.invoke_once()
