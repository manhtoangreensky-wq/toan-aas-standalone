"""Focused contract tests for Web-native Finance Operations Planning."""

from __future__ import annotations

from contextlib import contextmanager
import sqlite3

from fastapi import FastAPI
from fastapi.testclient import TestClient

import copyfast_finance_planning as finance


def _client(monkeypatch) -> tuple[TestClient, sqlite3.Connection]:
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.execute(
        """CREATE TABLE web_idempotency (
            scope TEXT NOT NULL, key TEXT NOT NULL, response_json TEXT NOT NULL,
            request_fingerprint TEXT NOT NULL, created_at TEXT NOT NULL,
            PRIMARY KEY(scope, key)
        )"""
    )

    @contextmanager
    def tx():
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise

    @contextmanager
    def read_tx():
        yield connection

    monkeypatch.setattr(finance, "transaction", tx)
    monkeypatch.setattr(finance, "read_transaction", read_tx)
    monkeypatch.setattr(finance, "ensure_copyfast_schema", lambda: None)
    monkeypatch.setattr(finance, "_record_audit", lambda *_args, **_kwargs: None)
    monkeypatch.setenv("WEBAPP_ADMIN_ERP_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_FINANCE_PLANNING_ENABLED", "true")

    app = FastAPI()
    app.include_router(finance.router)
    app.dependency_overrides[finance.require_admin] = lambda: {"id": "web-admin-a", "role": "admin"}
    app.dependency_overrides[finance.require_admin_csrf] = lambda: {"id": "web-admin-a", "role": "admin"}
    return TestClient(app), connection


def _budget_payload(*, key: str = "finance-budget-key-0001", amount: int = 2_500_000) -> dict:
    return {
        "period": "2026-07",
        "category": "infrastructure",
        "planned_vnd": amount,
        "note": "Dự trù hạ tầng Web trong tháng.",
        "confirm_budget": True,
        "idempotency_key": key,
    }


def _cost_payload(*, key: str = "finance-cost-key-00001", amount: int = 800_000) -> dict:
    return {
        "period": "2026-07",
        "planned_for": "2026-07-18",
        "category": "software",
        "planned_vnd": amount,
        "vendor_label": "Subscription nội bộ",
        "purpose": "Dự trù subscription cần review trước khi mua.",
        "confirm_plan": True,
        "idempotency_key": key,
    }


def test_budget_is_web_owned_idempotent_and_visible_in_summary(monkeypatch) -> None:
    client, _connection = _client(monkeypatch)
    payload = _budget_payload()

    first = client.post("/api/v1/admin/finance-planning/budgets", json=payload)
    replay = client.post("/api/v1/admin/finance-planning/budgets", json=payload)
    conflict_payload = {**payload, "planned_vnd": 2_600_000}
    conflict = client.post("/api/v1/admin/finance-planning/budgets", json=conflict_payload)
    summary = client.get("/api/v1/admin/finance-planning/summary?period=2026-07")
    listing = client.get("/api/v1/admin/finance-planning/budgets?period=2026-07")

    assert first.status_code == 200
    assert first.json()["status"] == "completed"
    budget = first.json()["data"]["budget"]
    assert budget["state"] == "active"
    assert budget["planned_vnd"] == 2_500_000
    assert first.json()["data"]["bot_called"] is False
    assert first.json()["data"]["payment_started"] is False
    assert first.json()["data"]["ledger_changed"] is False

    assert replay.status_code == 200
    # Replay receipts intentionally retain just opaque ID/state/revision.
    assert replay.json()["data"]["budget"] == {
        "id": budget["id"], "state": "active", "revision": 1
    }
    assert "planned_vnd" not in replay.json()["data"]["budget"]
    assert conflict.status_code == 409

    summary_data = summary.json()["data"]
    assert summary.status_code == 200
    assert summary_data["summary"]["budget_vnd"] == 2_500_000
    assert summary_data["summary"]["planned_vnd"] == 0
    assert summary_data["canonical_finance_read"] is False
    assert summary_data["payos_webhook_created"] is False
    assert listing.json()["data"]["items"][0]["id"] == budget["id"]


def test_cost_plan_requires_safe_text_and_server_revision_transition(monkeypatch) -> None:
    client, _connection = _client(monkeypatch)
    sensitive = _cost_payload(key="finance-cost-sensitive-01")
    sensitive["purpose"] = "Đính kèm TXID 123 để đối soát"
    rejected = client.post("/api/v1/admin/finance-planning/cost-plans", json=sensitive)
    assert rejected.status_code == 422
    assert "thanh toán" in str(rejected.json()["detail"]).lower()

    created = client.post("/api/v1/admin/finance-planning/cost-plans", json=_cost_payload())
    assert created.status_code == 200
    plan = created.json()["data"]["cost_plan"]
    assert plan["state"] == "draft"
    assert plan["revision"] == 1

    invalid = client.post(
        f"/api/v1/admin/finance-planning/cost-plans/{plan['id']}/state",
        json={"state": "approved", "expected_revision": 1, "confirm_change": True, "idempotency_key": "finance-cost-state-bad1"},
    )
    assert invalid.status_code == 200
    assert invalid.json()["ok"] is False
    assert invalid.json()["error_code"] == "WEB_FINANCE_PLANNING_STATE_CONFLICT"

    review = client.post(
        f"/api/v1/admin/finance-planning/cost-plans/{plan['id']}/state",
        json={"state": "review", "expected_revision": 1, "confirm_change": True, "idempotency_key": "finance-cost-state-review"},
    )
    assert review.status_code == 200
    assert review.json()["data"]["cost_plan"]["state"] == "review"
    assert review.json()["data"]["cost_plan"]["revision"] == 2

    stale = client.post(
        f"/api/v1/admin/finance-planning/cost-plans/{plan['id']}/state",
        json={"state": "approved", "expected_revision": 1, "confirm_change": True, "idempotency_key": "finance-cost-state-stale"},
    )
    assert stale.status_code == 200
    assert stale.json()["error_code"] == "WEB_FINANCE_PLANNING_REVISION_CONFLICT"

    approved = client.post(
        f"/api/v1/admin/finance-planning/cost-plans/{plan['id']}/state",
        json={"state": "approved", "expected_revision": 2, "confirm_change": True, "idempotency_key": "finance-cost-state-approve"},
    )
    assert approved.status_code == 200
    assert approved.json()["data"]["cost_plan"]["state"] == "approved"
    assert approved.json()["data"]["wallet_mutated"] is False
    assert approved.json()["data"]["refund_created"] is False


def test_finance_planning_filters_and_feature_gate_fail_closed(monkeypatch) -> None:
    client, _connection = _client(monkeypatch)
    client.post("/api/v1/admin/finance-planning/cost-plans", json=_cost_payload())

    invalid_state = client.get("/api/v1/admin/finance-planning/cost-plans?period=2026-07&state=processing")
    invalid_category = client.get("/api/v1/admin/finance-planning/cost-plans?period=2026-07&category=payos")
    listed = client.get("/api/v1/admin/finance-planning/cost-plans?period=2026-07&state=draft&category=software")

    assert invalid_state.status_code == 422
    assert invalid_category.status_code == 422
    assert listed.status_code == 200
    assert listed.json()["data"]["total"] == 1
    assert listed.json()["data"]["items"][0]["purpose"] == "Dự trù subscription cần review trước khi mua."

    monkeypatch.setenv("WEBAPP_FINANCE_PLANNING_ENABLED", "false")
    disabled = client.get("/api/v1/admin/finance-planning/policy")
    assert disabled.status_code == 503
    assert "tạm dừng" in disabled.json()["detail"].lower()


def test_budget_archive_restore_is_revisioned_and_never_changes_a_ledger(monkeypatch) -> None:
    client, _connection = _client(monkeypatch)
    created = client.post("/api/v1/admin/finance-planning/budgets", json=_budget_payload())
    assert created.status_code == 200
    budget = created.json()["data"]["budget"]

    archive_payload = {
        "state": "archived",
        "expected_revision": 1,
        "confirm_change": True,
        "idempotency_key": "finance-budget-archive-0001",
    }
    archived = client.post(
        f"/api/v1/admin/finance-planning/budgets/{budget['id']}/state",
        json=archive_payload,
    )
    replay = client.post(
        f"/api/v1/admin/finance-planning/budgets/{budget['id']}/state",
        json=archive_payload,
    )
    summary_after_archive = client.get("/api/v1/admin/finance-planning/summary?period=2026-07")

    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"
    assert archived.json()["data"]["budget"]["state"] == "archived"
    assert archived.json()["data"]["budget"]["revision"] == 2
    assert archived.json()["data"]["ledger_changed"] is False
    assert archived.json()["data"]["payment_started"] is False
    assert replay.status_code == 200
    assert replay.json()["data"]["budget"] == {
        "id": budget["id"], "state": "archived", "revision": 2
    }
    assert summary_after_archive.json()["data"]["summary"]["budget_vnd"] == 0

    restored = client.post(
        f"/api/v1/admin/finance-planning/budgets/{budget['id']}/state",
        json={
            "state": "active",
            "expected_revision": 2,
            "confirm_change": True,
            "idempotency_key": "finance-budget-restore-0001",
        },
    )
    assert restored.status_code == 200
    assert restored.json()["status"] == "active"
    assert restored.json()["data"]["budget"]["revision"] == 3

    archived_again = client.post(
        f"/api/v1/admin/finance-planning/budgets/{budget['id']}/state",
        json={
            "state": "archived",
            "expected_revision": 3,
            "confirm_change": True,
            "idempotency_key": "finance-budget-archive-0002",
        },
    )
    replacement = client.post(
        "/api/v1/admin/finance-planning/budgets",
        json=_budget_payload(key="finance-budget-replacement-001", amount=3_100_000),
    )
    blocked_restore = client.post(
        f"/api/v1/admin/finance-planning/budgets/{budget['id']}/state",
        json={
            "state": "active",
            "expected_revision": 4,
            "confirm_change": True,
            "idempotency_key": "finance-budget-restore-blocked",
        },
    )

    assert archived_again.status_code == 200
    assert replacement.status_code == 200
    assert blocked_restore.status_code == 200
    assert blocked_restore.json()["ok"] is False
    assert blocked_restore.json()["error_code"] == "WEB_FINANCE_PLANNING_BUDGET_EXISTS"
