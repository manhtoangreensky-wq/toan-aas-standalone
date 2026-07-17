"""Focused contract checks for the future short-lived Autopilot Cron tick."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from copyfast_autopilot_protocol import TICK_PATH, canonical_json, sign_tick, signature_material, valid_request_id


ROOT = Path(__file__).parents[1]
RUNNER_PATH = ROOT / "scripts" / "operations" / "run_autopilot_tick.py"


def _runner():
    spec = importlib.util.spec_from_file_location("autopilot_tick_runner_test", RUNNER_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_tick_signature_is_deterministic_and_binds_all_scheduler_audit_headers() -> None:
    body = canonical_json({"protocol_version": 1, "trigger": "railway_cron", "requested_at": "2026-07-14T00:00:00+00:00"})
    request_id = "123e4567-e89b-42d3-a456-426614174000"
    material = signature_material(
        method="POST", path=TICK_PATH, timestamp="2026-07-14T00:00:00+00:00", nonce="A" * 24,
        request_id=request_id, key_id="primary", body=body,
    )
    assert material.decode("utf-8").split("\n")[:6] == ["POST", TICK_PATH, "2026-07-14T00:00:00+00:00", "A" * 24, request_id, "primary"]
    signature = sign_tick(
        secret="s" * 32, timestamp="2026-07-14T00:00:00+00:00", nonce="A" * 24,
        request_id=request_id, key_id="primary", body=body,
    )
    assert len(signature) == 64
    assert signature == sign_tick(
        secret="s" * 32, timestamp="2026-07-14T00:00:00+00:00", nonce="A" * 24,
        request_id=request_id, key_id="primary", body=body,
    )
    assert signature != sign_tick(
        secret="s" * 32, timestamp="2026-07-14T00:00:01+00:00", nonce="A" * 24,
        request_id=request_id, key_id="primary", body=body,
    )
    assert signature != sign_tick(
        secret="s" * 32, timestamp="2026-07-14T00:00:00+00:00", nonce="A" * 24,
        request_id="123e4567-e89b-42d3-a456-426614174001", key_id="primary", body=body,
    )
    assert valid_request_id("01234567-89ab-4cde-8fab-0123456789ab") is True
    assert valid_request_id("browser-admin-id") is False


def test_tick_runner_fails_closed_for_missing_secret_or_untrusted_url(monkeypatch) -> None:
    runner = _runner()
    monkeypatch.delenv("WEBAPP_AUTOPILOT_TICK_SECRET", raising=False)
    monkeypatch.setenv("WEBAPP_AUTOPILOT_TICK_URL", "https://app.toanaas.vn/internal/v1/operations/tick")
    monkeypatch.setenv("WEBAPP_AUTOPILOT_TICK_ORIGIN", "https://app.toanaas.vn")
    with pytest.raises(runner.TickConfigurationError):
        runner.build_request()
    monkeypatch.setenv("WEBAPP_AUTOPILOT_TICK_SECRET", "s" * 32)
    monkeypatch.setenv("WEBAPP_AUTOPILOT_TICK_URL", "https://evil.example/elsewhere")
    with pytest.raises(runner.TickConfigurationError):
        runner.build_request()
    monkeypatch.setenv("WEBAPP_AUTOPILOT_TICK_URL", "https://evil.example/internal/v1/operations/tick")
    with pytest.raises(runner.TickConfigurationError):
        runner.build_request()
    monkeypatch.setenv("WEBAPP_AUTOPILOT_TICK_URL", "https://user:pass@app.toanaas.vn/internal/v1/operations/tick")
    with pytest.raises(runner.TickConfigurationError):
        runner.build_request()
    monkeypatch.setenv("WEBAPP_AUTOPILOT_TICK_URL", "https://app.toanaas.vn:8443/internal/v1/operations/tick")
    with pytest.raises(runner.TickConfigurationError):
        runner.build_request()


def test_tick_runner_uses_the_server_integer_budget_and_keeps_transport_margin(monkeypatch) -> None:
    runner = _runner()
    monkeypatch.setenv("WEBAPP_AUTOPILOT_MAX_RUN_SECONDS", "20")
    assert runner._timeout() == 25.0
    monkeypatch.setenv("WEBAPP_AUTOPILOT_MAX_RUN_SECONDS", "20.5")
    with pytest.raises(runner.TickConfigurationError):
        runner._timeout()
    monkeypatch.setenv("WEBAPP_AUTOPILOT_MAX_RUN_SECONDS", "26")
    with pytest.raises(runner.TickConfigurationError):
        runner._timeout()


def test_tick_runner_never_imports_web_app_bot_provider_or_payment_authorities() -> None:
    source = RUNNER_PATH.read_text(encoding="utf-8")
    for forbidden in (
        "import app", "from app", "import bot", "from bot", "copyfast_bridge", "PayOS", "import wallet", "from wallet",
        "import provider", "from provider",
        "sqlite3", "requests", "httpx",
    ):
        assert forbidden not in source
    assert '"X-Ops-Signature"' in source
    assert "ProxyHandler({})" in source
    assert "_RejectRedirect" in source
    assert "_opener().open(request, timeout=_timeout())" in source
