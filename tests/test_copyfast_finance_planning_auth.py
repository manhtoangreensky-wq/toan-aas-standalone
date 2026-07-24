"""Runtime security checks for Finance Operations Planning.

The small unit-style planning tests override dependencies to focus on state
logic.  This suite instead mounts the real signed-Web auth router so the
Admin-only and CSRF boundaries are exercised before release.
"""

from __future__ import annotations

import ast
import importlib
from pathlib import Path
import sqlite3
import sys
import time
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient


MODULES = ["copyfast_db", "copyfast_auth", "copyfast_finance_planning"]
FULL_APP_MODULES = [
    "app",
    "copyfast_db",
    "copyfast_auth_throttle",
    "copyfast_auth",
    "copyfast_finance_planning",
]


def make_app(tmp_path, monkeypatch, *, finance_enabled: bool, erp_enabled: bool) -> tuple[FastAPI, Any, Path]:
    db_path = tmp_path / "finance-planning-auth.db"
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(db_path))
    monkeypatch.setenv("WEB_SESSION_SECRET", "finance-planning-auth-test-secret")
    monkeypatch.setenv("WEBAPP_FINANCE_PLANNING_ENABLED", "true" if finance_enabled else "false")
    monkeypatch.setenv("WEBAPP_ADMIN_ERP_ENABLED", "true" if erp_enabled else "false")
    for name in (
        "APP_ENV", "ENVIRONMENT", "RAILWAY_ENVIRONMENT", "RAILWAY_VOLUME_MOUNT_PATH",
        "CORE_BRIDGE_BASE_URL", "CORE_BRIDGE_TOKEN", "CORE_BRIDGE_HMAC_SECRET",
    ):
        monkeypatch.delenv(name, raising=False)
    for name in MODULES:
        sys.modules.pop(name, None)
    auth = importlib.import_module("copyfast_auth")
    finance = importlib.import_module("copyfast_finance_planning")
    app = FastAPI()
    app.include_router(auth.router, prefix="/api/v1/auth")
    app.include_router(finance.router)
    return app, finance, db_path


def make_full_app(tmp_path, monkeypatch) -> tuple[TestClient, Path, Any]:
    """Load the production middleware stack for body/rate regression checks."""

    db_path = tmp_path / "finance-planning-full-app.db"
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(db_path))
    monkeypatch.setenv("WEB_SESSION_SECRET", "finance-planning-full-app-session-secret")
    monkeypatch.setenv("WEBAPP_FINANCE_PLANNING_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_ADMIN_ERP_ENABLED", "true")
    for name in (
        "APP_ENV", "ENVIRONMENT", "RAILWAY_ENVIRONMENT", "RAILWAY_VOLUME_MOUNT_PATH",
        "CORE_BRIDGE_BASE_URL", "CORE_BRIDGE_TOKEN", "CORE_BRIDGE_HMAC_SECRET",
    ):
        monkeypatch.delenv(name, raising=False)
    for name in FULL_APP_MODULES:
        sys.modules.pop(name, None)
    app_module = importlib.import_module("app")
    # ``TestClient(app)`` outside a context manager does not execute the ASGI
    # lifespan.  Prepare the additive schema explicitly so the production
    # durable-auth throttle used to establish the signed admin session has its
    # opaque bucket table, while the test still exercises the real middleware.
    importlib.import_module("copyfast_db").ensure_copyfast_schema()
    app_module._auth_rate_windows.clear()
    return TestClient(app_module.app), db_path, app_module


def register(client: TestClient, email: str) -> str:
    registered = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "correct-horse-battery-staple",
            "display_name": "Finance Planning test account",
        },
    )
    assert registered.status_code == 200 and registered.json()["ok"] is True
    signed_in = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert signed_in.status_code == 200 and signed_in.json()["ok"] is True
    return str(signed_in.json()["data"]["csrf_token"])


def register_admin(client: TestClient, db_path: Path, email: str) -> str:
    register(client, email)
    with sqlite3.connect(db_path) as conn:
        row = conn.execute("SELECT id FROM web_accounts WHERE email=?", (email,)).fetchone()
        assert row is not None
        conn.execute("UPDATE web_accounts SET role_cache='admin' WHERE id=?", (str(row[0]),))
        conn.commit()
    signed_in = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert signed_in.status_code == 200 and signed_in.json()["ok"] is True
    return str(signed_in.json()["data"]["csrf_token"])


def budget_payload(key: str, *, note: str = "Dự trù hạ tầng Web nội bộ.") -> dict[str, Any]:
    return {
        "period": "2026-07",
        "category": "infrastructure",
        "planned_vnd": 1_500_000,
        "note": note,
        "confirm_budget": True,
        "idempotency_key": key,
    }


def _boundary(data: dict[str, Any]) -> None:
    assert data["execution"] == "web_native_finance_operations_planning"
    for key in (
        "canonical_finance_read", "canonical_finance_write", "bot_called", "bridge_called",
        "provider_called", "wallet_mutated", "payment_started", "payment_finalized",
        "payos_webhook_created", "refund_created", "ledger_changed", "tax_calculated",
        "report_exported", "notification_sent",
    ):
        assert data[key] is False


def test_finance_planning_requires_signed_admin_csrf_and_both_flags(tmp_path, monkeypatch) -> None:
    app, finance, db_path = make_app(tmp_path, monkeypatch, finance_enabled=False, erp_enabled=True)
    guest = TestClient(app)
    regular = TestClient(app)
    admin = TestClient(app)
    try:
        routes = {
            (route.path, method): {dependency.call for dependency in route.dependant.dependencies}
            for route in finance.router.routes
            for method in (route.methods or set())
        }
        for path in (
            "/api/v1/admin/finance-planning/policy",
            "/api/v1/admin/finance-planning/summary",
            "/api/v1/admin/finance-planning/budgets",
            "/api/v1/admin/finance-planning/cost-plans",
        ):
            assert finance.require_admin in routes[(path, "GET")]
        for path in (
            "/api/v1/admin/finance-planning/budgets",
            "/api/v1/admin/finance-planning/budgets/{budget_id}/state",
            "/api/v1/admin/finance-planning/cost-plans",
            "/api/v1/admin/finance-planning/cost-plans/{cost_plan_id}/state",
        ):
            assert finance.require_admin_csrf in routes[(path, "POST")]

        assert guest.get("/api/v1/admin/finance-planning/policy").status_code == 401
        regular_csrf = register(regular, "finance-regular@example.com")
        assert regular_csrf
        assert regular.get("/api/v1/admin/finance-planning/policy").status_code == 403

        csrf = register_admin(admin, db_path, "finance-admin@example.com")
        disabled = admin.get("/api/v1/admin/finance-planning/policy")
        assert disabled.status_code == 503
        assert "categories" not in disabled.text

        monkeypatch.setenv("WEBAPP_FINANCE_PLANNING_ENABLED", "true")
        monkeypatch.setenv("WEBAPP_ADMIN_ERP_ENABLED", "false")
        assert admin.get("/api/v1/admin/finance-planning/policy").status_code == 503

        monkeypatch.setenv("WEBAPP_ADMIN_ERP_ENABLED", "true")
        policy = admin.get("/api/v1/admin/finance-planning/policy")
        assert policy.status_code == 200 and policy.json()["ok"] is True
        _boundary(policy.json()["data"])
        assert policy.json()["data"]["manual_payment_evidence_accepted"] is False

        missing_csrf = admin.post(
            "/api/v1/admin/finance-planning/budgets",
            json=budget_payload("finance-auth-no-csrf-0001"),
        )
        assert missing_csrf.status_code == 403
        created = admin.post(
            "/api/v1/admin/finance-planning/budgets",
            headers={"X-CSRF-Token": csrf},
            json=budget_payload("finance-auth-csrf-0001"),
        )
        assert created.status_code == 200 and created.json()["ok"] is True
        _boundary(created.json()["data"])

        tree = ast.parse(Path(finance.__file__).read_text(encoding="utf-8"))
        imports = {
            module.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for module in ([alias.name for alias in node.names] if isinstance(node, ast.Import) else [node.module or ""])
            if module
        }
        assert not {"copyfast_bridge", "requests", "httpx", "payos", "bot"}.intersection(imports)
    finally:
        guest.close()
        regular.close()
        admin.close()


def test_finance_planning_dlp_rejects_credential_and_payment_proof_before_write(tmp_path, monkeypatch) -> None:
    app, _finance, db_path = make_app(tmp_path, monkeypatch, finance_enabled=True, erp_enabled=True)
    admin = TestClient(app)
    try:
        csrf = register_admin(admin, db_path, "finance-dlp-admin@example.com")
        for index, unsafe in enumerate((
            "password: 1234",
            "token: abcdefg",
            "IBAN DE89370400440532013000",
            "SWIFT/BIC DEUTDEFF",
            "VietQR merchant receipt",
            # Bare identifiers are still payment/account evidence even when a
            # user omits an explanatory keyword or label.
            "0123456789012345",
            "DE89370400440532013000",
        ), start=1):
            response = admin.post(
                "/api/v1/admin/finance-planning/budgets",
                headers={"X-CSRF-Token": csrf},
                json=budget_payload(f"finance-dlp-{index:04d}-request", note=unsafe),
            )
            assert response.status_code == 422
            assert response.status_code != 500
        for index, field_payload in enumerate((
            {"vendor_label": "0123 4567 8901 2345", "purpose": "Dự trù công cụ vận hành Web."},
            {"vendor_label": "Công cụ nội bộ", "purpose": "DE89 3704 0044 0532 0130 00"},
        ), start=1):
            response = admin.post(
                "/api/v1/admin/finance-planning/cost-plans",
                headers={"X-CSRF-Token": csrf},
                json={
                    "period": "2026-07",
                    "planned_for": "2026-07-18",
                    "category": "software",
                    "planned_vnd": 100_000,
                    "confirm_plan": True,
                    "idempotency_key": f"finance-dlp-cost-{index:04d}-request",
                    **field_payload,
                },
            )
            assert response.status_code == 422
            assert response.status_code != 500
        with sqlite3.connect(db_path) as conn:
            table = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='web_finance_planning_budgets'"
            ).fetchone()
            assert table is None or conn.execute("SELECT COUNT(*) FROM web_finance_planning_budgets").fetchone()[0] == 0
    finally:
        admin.close()


def test_finance_planning_full_app_enforces_body_and_fixed_rate_boundaries(tmp_path, monkeypatch) -> None:
    client, db_path, app_module = make_full_app(tmp_path, monkeypatch)
    try:
        csrf = register_admin(client, db_path, "finance-full-app-admin@example.com")
        oversized = client.post(
            "/api/v1/admin/finance-planning/budgets",
            headers={"X-CSRF-Token": csrf, "Content-Type": "application/json"},
            content=b'{"padding":"' + (b"x" * (16 * 1024)) + b'"}',
        )
        assert oversized.status_code == 413
        assert oversized.json()["error_code"] == "WEB_FINANCE_PLANNING_BODY_TOO_LARGE"
        assert oversized.headers["cache-control"] == "no-store, private"
        assert oversized.headers["cross-origin-resource-policy"] == "same-origin"
        _boundary(oversized.json()["data"])

        client_ip = "testclient"
        app_module._auth_rate_windows.clear()
        app_module._auth_rate_windows[f"finance-planning-read:{client_ip}"] = [time.monotonic()] * 120
        read_limited = client.get("/api/v1/admin/finance-planning/policy")
        assert read_limited.status_code == 429
        assert read_limited.json()["error_code"] == "AUTH_RATE_LIMITED"
        _boundary(read_limited.json()["data"])

        app_module._auth_rate_windows.clear()
        app_module._auth_rate_windows[f"finance-planning-write:{client_ip}"] = [time.monotonic()] * 20
        write_limited = client.post(
            "/api/v1/admin/finance-planning/budgets",
            headers={"X-CSRF-Token": csrf},
            json=budget_payload("finance-full-app-rate-write-0001"),
        )
        assert write_limited.status_code == 429
        assert write_limited.json()["error_code"] == "AUTH_RATE_LIMITED"
        _boundary(write_limited.json()["data"])
    finally:
        client.close()
