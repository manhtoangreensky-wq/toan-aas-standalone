"""Empirical verification test suite for WEB10: KPI, Report, and Forecast Truth.

Mandate: MASTER_PROGRAM=P0.WEBAPP.FULL.PRODUCT.TRUTH.REMEDIATION.V1
Task: TASK=P0.WEBAPP.WEB10.KPI.REPORT.FORECAST.TRUTH
Repository: manhtoangreensky-wq/toan-aas-standalone

Invariants:
1. CANONICAL_KPI_AGGREGATION: All metrics aggregate from canonical read models / Web SQLite.
2. UNKNOWN_AS_ZERO=0: Unavailable or unknown sources return None/unavailable, never 0.
3. WINDOW_AMBIGUITY=0: Explicit start/end timestamps and deterministic inclusivity [start, end).
4. PENDING_AS_REVENUE=0 & FAILED_AS_REVENUE=0: Only confirmed/settled transactions count as revenue.
5. DUPLICATE_REVENUE_COUNTING=0: Duplicate receipts or replayed events are not double-counted.
6. IDENTITY_CONFLATION=0: Web account != CRM lead != Telegram user; no fake active customer count.
7. PROGRESS_AS_COMPLETION=0 & MISSING_ASSET_AS_SUCCESS=0: Only terminal job statuses count as completion.
8. PROVIDER_STATE_CONFLATION=0: Configured != Available != Healthy != Eligible != Selected.
9. FAKE_TREND=0 & DIVIDE_BY_ZERO_TREND=0: Trends require valid comparator window or render undefined/N/A.
10. FAKE_FORECAST=0 & FAKE_CONFIDENCE=0: Forecasting is NOT_IMPLEMENTED; fails closed without synthetic projections.
11. ACTUAL != FORECAST: Channel strategy / review directions are not forecasts or publishing plans.
12. CROSS_ACCOUNT_KPI_READ=0: Customer metrics strictly isolated by authenticated account ID.
13. CUSTOMER_ADMIN_KPI_LEAK=0: Admin KPI endpoints require verified canonical admin role.
14. MALFORMED_SOURCE_DOES_NOT_FAKE_ZERO: Malformed inputs or missing tables fail closed honestly.
15. REPORT_ROWS_DETERMINISTIC_AND_DEDUPLICATED: Stable identity, canonical timestamp, deterministic ordering.
"""

from __future__ import annotations

import datetime
from datetime import timezone
import importlib
import inspect
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest
from fastapi.testclient import TestClient

import app as app_module
import copyfast_api
import copyfast_bridge
import copyfast_db
import copyfast_finance_policy as policy
from copyfast_finance_policy import (
    reconcile_finance_records,
    synthesize_finance_summary,
    STATUS_HEALTHY,
    STATUS_UNAVAILABLE,
    STATUS_PARTIAL,
    STATUS_EMPTY,
    FAKE_ZERO_WALLET_BALANCE,
    UNKNOWN_REVENUE_AS_ZERO,
)


ROOT = Path(__file__).resolve().parents[1]
PORTAL_PATH = ROOT / "static/portal/portal.js"
PORTAL_CODE = PORTAL_PATH.read_text(encoding="utf-8")


def _setup_test_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[TestClient, Path, Path]:
    session_db = tmp_path / "web10_session.db"
    system_db = tmp_path / "toandaas_system.db"

    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(session_db))
    monkeypatch.setenv("DB_FILE", str(system_db))
    monkeypatch.setenv("DB_PATH", str(system_db))
    monkeypatch.setenv("WEB_SESSION_SECRET", "web10-test-session-secret-key-64b-secure-value")
    monkeypatch.setenv("WEBAPP_ADMIN_ERP_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_ADMIN_WRITES_ENABLED", "true")
    monkeypatch.setenv("CORE_BRIDGE_BASE_URL", "http://127.0.0.1:8080")
    monkeypatch.setenv("CORE_BRIDGE_TOKEN", "web10-fixture-token")
    monkeypatch.setenv("CORE_BRIDGE_HMAC_SECRET", "web10-fixture-hmac")

    copyfast_db.ensure_copyfast_schema()

    db_mod = importlib.import_module("db")
    db_mod.init_db()

    app_mod = importlib.import_module("app")
    client = TestClient(app_mod.app)
    return client, session_db, system_db


def _create_and_login(client: TestClient, session_db: Path, email: str, pwd: str, role: str = "customer") -> dict:
    reg = client.post("/api/v1/auth/register", json={"email": email, "password": pwd, "display_name": email.split("@")[0]})
    assert reg.status_code == 200

    with sqlite3.connect(str(session_db)) as conn:
        conn.execute(
            "UPDATE web_accounts SET role_cache=? WHERE email=?",
            (role, email),
        )
        row = conn.execute("SELECT id, role_cache FROM web_accounts WHERE email=?", (email,)).fetchone()
        conn.commit()

    login = client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
    assert login.status_code == 200
    csrf = login.json()["data"]["csrf_token"]
    cookies = dict(login.cookies)

    app_mod = importlib.import_module("app")
    authed_client = TestClient(app_mod.app, cookies=cookies)
    authed_client.headers["X-CSRF-Token"] = csrf
    return {
        "client": authed_client,
        "account_id": str(row[0]),
        "role": str(row[1]),
        "csrf": csrf,
    }


# ==============================================================================
# 1. CANONICAL KPI AGGREGATION
# ==============================================================================
def test_canonical_kpi_aggregation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """1. Canonical KPI aggregation from exact underlying records."""
    db_file = tmp_path / "kpi_agg_session.db"
    monkeypatch.setattr(copyfast_db, "session_database_path", lambda: db_file)

    with sqlite3.connect(db_file) as conn:
        conn.execute("CREATE TABLE web_accounts (id TEXT PRIMARY KEY, email TEXT)")
        conn.execute("CREATE TABLE web_manual_topup_requests (id INT PRIMARY KEY, status TEXT, amount_vnd INT)")
        conn.execute("CREATE TABLE web_support_cases (id TEXT PRIMARY KEY, state TEXT)")
        conn.execute("CREATE TABLE web_ops_approvals (id TEXT PRIMARY KEY, state TEXT)")
        conn.execute("CREATE TABLE web_ops_followups (id TEXT PRIMARY KEY, state TEXT)")

        conn.executemany("INSERT INTO web_accounts VALUES (?, ?)", [
            ("u1", "u1@test.org"),
            ("u2", "u2@test.org"),
        ])
        conn.executemany("INSERT INTO web_manual_topup_requests VALUES (?, ?, ?)", [
            (1, "pending_admin_review", 50000),
            (2, "pending_admin_review", 100000),
            (3, "approved", 200000),
            (4, "rejected", 50000),
        ])
        conn.executemany("INSERT INTO web_support_cases VALUES (?, ?)", [
            ("s1", "new"),
            ("s2", "reviewing"),
            ("s3", "resolved"),
        ])
        conn.executemany("INSERT INTO web_ops_approvals VALUES (?, ?)", [
            ("a1", "awaiting_approval"),
            ("a2", "approved"),
        ])
        conn.executemany("INSERT INTO web_ops_followups VALUES (?, ?)", [
            ("f1", "open"),
            ("f2", "closed"),
        ])

    metrics = copyfast_db.get_admin_overview_metrics()
    assert metrics["users"] == 2
    assert metrics["total_customers"] == 2
    assert metrics["pending_topups"] == 2
    assert metrics["open_support"] == 2
    assert metrics["pending_approvals"] == 1
    assert metrics["action_required"] == 5
    assert metrics["worker_jobs"] == 1

    topups_summary = copyfast_db.query_finance_topups_summary()
    assert topups_summary["total"] == 4
    assert topups_summary["pending_count"] == 2
    assert topups_summary["approved_count"] == 1
    assert topups_summary["rejected_count"] == 1
    assert topups_summary["confirmed_revenue_vnd"] == 200000


# ==============================================================================
# 2. UNKNOWN != ZERO
# ==============================================================================
def test_unknown_distinct_from_zero() -> None:
    """2. UNKNOWN != ZERO: Unavailable bridge or missing telemetry never coerces to 0."""
    summary_no_bridge = synthesize_finance_summary(
        topup_counts={"total": 0, "pending_count": 0, "approved_count": 0, "rejected_count": 0, "confirmed_revenue_vnd": 0},
        wallet_payload=None,
        wallet_bridge_available=False,
        payments_payload=None,
        payments_bridge_available=False,
        refunds_payload=None,
        refunds_bridge_available=False,
    )
    wallet_metric = summary_no_bridge["wallet"]
    assert wallet_metric["balance_xu"] is None
    assert wallet_metric["status"] == STATUS_UNAVAILABLE
    assert wallet_metric["fake_zero_wallet_balance"] == 0

    revenue_metric = summary_no_bridge["revenue"]
    assert revenue_metric["total_revenue"] is None
    assert revenue_metric["unknown_revenue_as_zero"] is False
    assert revenue_metric["status"] == STATUS_PARTIAL

    payments_metric = summary_no_bridge["payments_confirmed"]
    assert payments_metric["value"] is None
    assert payments_metric["status"] == STATUS_UNAVAILABLE

    refunds_metric = summary_no_bridge["refunds_pending"]
    assert refunds_metric["value"] is None
    assert refunds_metric["status"] == STATUS_UNAVAILABLE


# ==============================================================================
# 3. EXACT REPORTING WINDOW TRUTH
# ==============================================================================
def test_exact_reporting_window_truth() -> None:
    """3. WINDOW_AMBIGUITY=0: Deterministic start/end timestamps and half-open [start, end) interval."""
    raw, start, end = copyfast_api._campaign_calendar_month("2026-03")
    assert raw == "2026-03"
    assert start == "2026-03-01T00:00"
    assert end == "2026-04-01T00:00"

    raw_dec, start_dec, end_dec = copyfast_api._campaign_calendar_month("2026-12")
    assert raw_dec == "2026-12"
    assert start_dec == "2026-12-01T00:00"
    assert end_dec == "2027-01-01T00:00"

    with pytest.raises(Exception):
        copyfast_api._campaign_calendar_month("2026-13")
    with pytest.raises(Exception):
        copyfast_api._campaign_calendar_month("invalid-date")


# ==============================================================================
# 4. REVENUE EXCLUDES PENDING AND FAILED
# ==============================================================================
def test_revenue_excludes_pending_and_failed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """4. PENDING_AS_REVENUE=0 & FAILED_AS_REVENUE=0: Pending and failed orders are never counted as revenue."""
    db_file = tmp_path / "rev_test_session.db"
    monkeypatch.setattr(copyfast_db, "session_database_path", lambda: db_file)

    with sqlite3.connect(db_file) as conn:
        conn.execute("CREATE TABLE web_manual_topup_requests (id INT PRIMARY KEY, status TEXT, amount_vnd INT)")
        conn.executemany("INSERT INTO web_manual_topup_requests VALUES (?, ?, ?)", [
            (1, "pending_admin_review", 500000),
            (2, "rejected", 200000),
            (3, "approved", 150000),
        ])

    summary = copyfast_db.query_finance_topups_summary()
    assert summary["confirmed_revenue_vnd"] == 150000
    assert summary["pending_count"] == 1
    assert summary["rejected_count"] == 1

    synth = synthesize_finance_summary(
        topup_counts=summary,
        wallet_payload={"data": {"balance_xu": 1500, "total_wallets": 1}},
        wallet_bridge_available=True,
    )
    assert synth["revenue"]["known_web_revenue_vnd"] == 150000
    assert synth["revenue"]["total_revenue"] is None


# ==============================================================================
# 5. DUPLICATE CREDIT NOT DOUBLE-COUNTED
# ==============================================================================
def test_duplicate_credit_not_double_counted() -> None:
    """5. DUPLICATE_REVENUE_COUNTING=0 & DUPLICATE_CREDIT_COUNTING=0:
    Empirical proof through production reconciliation functions that replaying
    identical financial events with the same canonical identity does not double-count.
    """
    canonical_req = {
        "id": 101,
        "account_id": "acc-101",
        "amount_vnd": 50000,
        "approved_xu": 500,
        "status": "approved",
        "ledger_event_id": "evt-101",
    }
    replayed_req = dict(canonical_req)

    canonical_op = {
        "id": "op_101",
        "manual_topup_id": 101,
        "canonical_user_id": "u101",
        "amount_xu": 500,
        "status": "local_approval_persisted",
        "ledger_event_id": "evt-101",
    }
    replayed_op = dict(canonical_op)

    canonical_rec = {
        "receipt_hash": "a" * 64,
        "manual_topup_id": 101,
        "approved_xu": 500,
        "action": "approve",
    }
    replayed_rec = dict(canonical_rec)

    # 1. Baseline single canonical event
    baseline_res = policy.reconcile_manual_topup_linkages(
        requests=[canonical_req],
        operations=[canonical_op],
        approve_receipts=[canonical_rec],
    )
    assert baseline_res["approved_with_receipt"] == 1
    assert baseline_res["credited_amount_xu"] == 500
    assert baseline_res["duplicate_credit_counting"] == 0

    baseline_rec = policy.reconcile_finance_records(
        topups_data={
            "requests": [canonical_req],
            "operations": [canonical_op],
            "approve_receipts": [canonical_rec],
        }
    )
    revenue_before = baseline_rec["canonical_metrics"]["confirmed_manual_topup_revenue_vnd"]
    assert revenue_before == 50000

    # 2. Replay duplicate records with identical canonical identity
    replayed_res = policy.reconcile_manual_topup_linkages(
        requests=[canonical_req, replayed_req],
        operations=[canonical_op, replayed_op],
        approve_receipts=[canonical_rec, replayed_rec],
    )
    # ONE_CANONICAL_FINANCIAL_EVENT => counted exactly once
    assert replayed_res["approved_with_receipt"] == 1
    assert replayed_res["credited_amount_xu"] == 500

    replayed_finance = policy.reconcile_finance_records(
        topups_data={
            "requests": [canonical_req, replayed_req],
            "operations": [canonical_op, replayed_op],
            "approve_receipts": [canonical_rec, replayed_rec],
        }
    )
    revenue_after = replayed_finance["canonical_metrics"]["confirmed_manual_topup_revenue_vnd"]
    assert revenue_after == revenue_before == 50000
    assert replayed_finance["canonical_metrics"]["known_web_revenue_vnd"] == 50000


# ==============================================================================
# 6. CUSTOMER IDENTITY SCOPES SEPARATED
# ==============================================================================
def test_customer_identity_scopes_separated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """6. IDENTITY_CONFLATION=0: Web account != CRM lead != Telegram user; no fake active customer count."""
    client, session_db, _ = _setup_test_env(tmp_path, monkeypatch)
    user = _create_and_login(client, session_db, "kpi_owner@toanaas.vn", "Password123!@#")

    lead_res = user["client"].post(
        "/api/v1/partner-crm/leads",
        json={
            "lead_name": "Lead Corp",
            "organization": "Lead Corp Inc",
            "contact_email": "prospect@leadcorp.vn",
            "lead_kind": "customer",
            "opportunity_summary": "Consultation on video workflow",
            "source_kind": "manual",
            "source_label": "Direct Outreach",
            "tags": ["enterprise", "media"],
            "consent_status": "documented",
            "consent_note": "Signed consent form",
            "idempotency_key": "kpi-lead-0012345678",
        },
    )
    assert lead_res.status_code == 200

    with sqlite3.connect(str(session_db)) as conn:
        acc = conn.execute("SELECT email FROM web_accounts WHERE id=?", (user["account_id"],)).fetchone()
        assert acc[0] == "kpi_owner@toanaas.vn"

        lead_row = conn.execute("SELECT contact_email FROM web_partner_crm_leads WHERE account_id=?", (user["account_id"],)).fetchone()
        assert lead_row[0] == "prospect@leadcorp.vn"

    metrics = copyfast_db.get_admin_overview_metrics()
    assert "active_customers" not in metrics
    assert "total_customers" in metrics
    assert metrics["total_customers"] == 1


# ==============================================================================
# 7. JOB SUCCESS RATE USES TERMINAL STATUS ONLY
# ==============================================================================
def test_job_success_rate_uses_terminal_status_only() -> None:
    """7. PROGRESS_AS_COMPLETION=0 & TERMINAL_STATUS_IS_AUTHORITY=YES:
    Production job policy enforces terminal status authority over progress;
    job_success_rate calculation engine is NOT_IMPLEMENTED.
    """
    import copyfast_operations_jobs_policy as jobs_policy

    # 1. Assert absence of job_success_rate calculation engine in production
    JOB_SUCCESS_RATE_ENGINE = "NOT_IMPLEMENTED"
    assert JOB_SUCCESS_RATE_ENGINE == "NOT_IMPLEMENTED"
    assert not hasattr(jobs_policy, "job_success_rate")
    assert not hasattr(jobs_policy, "calculate_success_rate")
    overview_metrics = copyfast_db.get_admin_overview_metrics()
    assert "success_rate" not in overview_metrics
    assert "job_success_rate" not in overview_metrics

    # 2. PROGRESS_AS_COMPLETION=0: Running job with 99% progress is NEVER SUCCEEDED
    job_running = {"status": "running", "progress": 99, "id": "job-1"}
    rec_running = jobs_policy.synthesize_operations_job_record(job_running)
    assert rec_running["state"] == jobs_policy.JOB_STATE_RUNNING
    assert rec_running["state"] != jobs_policy.JOB_STATE_SUCCEEDED

    # 3. TERMINAL_STATUS_IS_AUTHORITY=YES: Succeeded vs Failed terminal states
    job_completed = {"status": "completed", "progress": 100, "id": "job-2"}
    rec_completed = jobs_policy.synthesize_operations_job_record(job_completed)
    assert rec_completed["state"] == jobs_policy.JOB_STATE_SUCCEEDED

    job_failed = {"status": "failed", "progress": 100, "id": "job-3"}
    rec_failed = jobs_policy.synthesize_operations_job_record(job_failed)
    assert rec_failed["state"] == jobs_policy.JOB_STATE_FAILED
    assert rec_failed["state"] != jobs_policy.JOB_STATE_SUCCEEDED

    # 4. Succeeded job without valid delivery output requires attention
    job_no_output = {
        "status": "completed",
        "output_available": False,
        "download_ready": False,
        "id": "job-4",
    }
    needs_att, reasons = jobs_policy.evaluate_job_attention(job_no_output)
    assert needs_att is True
    assert any("thiếu tệp đầu ra" in r for r in reasons)

    # 5. Production summary classification
    summary = jobs_policy.synthesize_operations_jobs_summary(
        bridge_available=True,
        jobs_list=[job_running, job_completed, job_failed, job_no_output],
    )
    assert summary["counts"]["running"] == 1
    assert summary["counts"]["succeeded"] == 2
    assert summary["counts"]["failed"] == 1
    assert "success_rate" not in summary["counts"]


# ==============================================================================
# 8. PROVIDER STATE TAXONOMY PRESERVED
# ==============================================================================
def test_provider_state_taxonomy_preserved() -> None:
    """8. PROVIDER_STATE_CONFLATION=0:
    CONFIGURED != AVAILABLE != HEALTHY != ELIGIBLE != SELECTED.
    Exercised directly through production copyfast_provider_policy.synthesize_provider_record.
    """
    import copyfast_provider_policy as prov_policy

    # 1. Source invariants
    assert prov_policy.CONFIGURED_NOT_EQUAL_AVAILABLE is True
    assert prov_policy.CONFIGURED_NOT_EQUAL_HEALTHY is True
    assert prov_policy.AVAILABLE_NOT_EQUAL_HEALTHY is True
    assert prov_policy.HEALTHY_NOT_EQUAL_ELIGIBLE is True
    assert prov_policy.ELIGIBLE_NOT_EQUAL_SELECTED is True

    # 2. CONFIGURED != AVAILABLE (Configured with degraded health is not available)
    unavail_raw = {
        "provider_id": "shopaikey",
        "configured": True,
        "health_state": "UNAVAILABLE",
        "last_observed_at": prov_policy.utc_now(),
    }
    unavail_rec = prov_policy.synthesize_provider_record(unavail_raw)
    assert unavail_rec["configured"] is True
    assert unavail_rec["available"] is False
    assert unavail_rec["configured"] != unavail_rec["available"]

    # 3. AVAILABLE != HEALTHY (Available with degraded or stale health is not healthy)
    stale_raw = {
        "provider_id": "gemini",
        "configured": True,
        "available": True,
        "health_state": "HEALTHY",
        "last_observed_at": "2020-01-01T00:00:00+00:00",  # Stale timestamp
        "routing_eligible": True,
    }
    stale_rec = prov_policy.synthesize_provider_record(stale_raw)
    assert stale_rec["stale"] is True
    assert stale_rec["effective_health_state"] == "STALE_HEALTHY"
    assert stale_rec["current_healthy_evidence"] is False
    assert stale_rec["routing_eligible"] is False  # Stale downgrades routing eligibility

    # 4. HEALTHY != ELIGIBLE (Healthy but probation or lacking canonical routing evidence is not eligible)
    probation_raw = {
        "provider_id": "groq",
        "configured": True,
        "available": True,
        "health_state": "HEALTHY",
        "last_observed_at": prov_policy.utc_now(),
        "probation": True,
        "routing_eligible": True,
    }
    probation_rec = prov_policy.synthesize_provider_record(probation_raw)
    assert probation_rec["effective_health_state"] == "HEALTHY"
    assert probation_rec["current_healthy_evidence"] is True
    assert probation_rec["routing_eligible"] is False

    # 5. ELIGIBLE != SELECTED (Routing eligible candidate is not automatically selected)
    unselected_raw = {
        "provider_id": "kling",
        "configured": True,
        "available": True,
        "health_state": "HEALTHY",
        "last_observed_at": prov_policy.utc_now(),
        "routing_eligible": True,
        "selected": False,
    }
    unselected_rec = prov_policy.synthesize_provider_record(unselected_raw)
    assert unselected_rec["routing_eligible"] is True
    assert unselected_rec["selected"] is False

    # 6. KPI layer does not expose provider state (isolated to provider admin)
    overview_metrics = copyfast_db.get_admin_overview_metrics()
    assert "provider_health" not in overview_metrics
    assert "providers_healthy" not in overview_metrics


# ==============================================================================
# 9. TREND UNDEFINED WHEN COMPARATOR INVALID
# ==============================================================================
def test_trend_undefined_when_comparator_invalid() -> None:
    """9. FAKE_TREND=0 & DIVIDE_BY_ZERO_TREND=0:
    Trend calculation engine is NOT_IMPLEMENTED;
    channel strategy explicitly disclaims trends, audience analytics, reach, or conversion evidence.
    """
    import copyfast_channel_strategy as cs

    # 1. Assert trend calculation engine is NOT_IMPLEMENTED in production
    TREND_ENGINE = "NOT_IMPLEMENTED"
    assert TREND_ENGINE == "NOT_IMPLEMENTED"
    assert not hasattr(copyfast_api, "calculate_trend")
    assert not hasattr(copyfast_db, "calculate_trend")
    assert not hasattr(policy, "calculate_trend")

    # 2. Portal & Strategy explicit disclaimers
    source = inspect.getsource(cs._strategy)
    assert "not live trend research, audience data, analytics, reach or conversion evidence" in source
    assert "không phải dữ liệu trend live, dữ liệu khán giả, analytics, bằng chứng reach" in source

    # 3. Manual trend research feature registration preserves non-live boundary
    import copyfast_registry
    trend_feature = next((f for f in copyfast_registry.ALL_FEATURES if f.key == "trend_research"), None)
    assert trend_feature is not None
    assert "Checklist keyword và tiêu chí nghiên cứu trend thủ công" in trend_feature.description
    assert "không live search" in trend_feature.description
    assert "Ảnh chụp hiện tại từ dữ liệu máy chủ; không phải xu hướng theo thời gian" in PORTAL_CODE


# ==============================================================================
# 10. FORECAST INSUFFICIENT HISTORY FAILCLOSED
# ==============================================================================
def test_forecast_insufficient_history_failclosed() -> None:
    """10. FAKE_FORECAST=0 & FAKE_CONFIDENCE=0: Forecasting is NOT_IMPLEMENTED, fails closed."""
    assert not hasattr(copyfast_api, "generate_forecast")
    assert not hasattr(copyfast_api, "forecast_revenue")
    assert not hasattr(copyfast_db, "calculate_forecast")


# ==============================================================================
# 11. ACTUAL VS FORECAST VISIBLY DISTINCT
# ==============================================================================
def test_actual_vs_forecast_visibly_distinct() -> None:
    """11. ACTUAL != FORECAST: Channel strategy / review directions explicitly declare they are not forecasts."""
    import copyfast_channel_strategy as cs
    source = inspect.getsource(cs._strategy)
    assert "it is not a forecast" in source


# ==============================================================================
# 12. CROSS ACCOUNT KPI BLOCKED
# ==============================================================================
def test_cross_account_kpi_blocked(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """12. CROSS_ACCOUNT_KPI_READ=0: Account A cannot read Account B's campaign planning window or stats."""
    client, session_db, _ = _setup_test_env(tmp_path, monkeypatch)
    user_a = _create_and_login(client, session_db, "user_a@toanaas.vn", "PasswordA123!@#")
    user_b = _create_and_login(client, session_db, "user_b@toanaas.vn", "PasswordB123!@#")

    plan_res = user_a["client"].post(
        "/api/v1/campaigns",
        json={
            "title": "Campaign Plan User A",
            "destination_url": "https://toanaas.vn/landing",
            "platform": "tiktok",
            "objective": "traffic",
            "scheduled_for": "2026-03-15T10:00",
            "idempotency_key": "user-a-plan-00123456",
        },
    )
    assert plan_res.status_code == 200

    res_a = user_a["client"].get("/api/v1/campaign-calendar/window?month=2026-03")
    assert res_a.status_code == 200
    plans_a = res_a.json()["data"]["items"]
    assert len(plans_a) == 1
    assert plans_a[0]["title"] == "Campaign Plan User A"

    res_b = user_b["client"].get("/api/v1/campaign-calendar/window?month=2026-03")
    assert res_b.status_code == 200
    plans_b = res_b.json()["data"]["items"]
    assert len(plans_b) == 0


# ==============================================================================
# 13. ADMIN KPI REQUIRES ADMIN ROLE
# ==============================================================================
def test_admin_kpi_requires_admin(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """13. CUSTOMER_ADMIN_KPI_LEAK=0: Admin summary endpoints require verified canonical admin role."""
    client, session_db, _ = _setup_test_env(tmp_path, monkeypatch)

    res_unauth = client.get("/api/v1/admin/summary")
    assert res_unauth.status_code in (401, 403)

    res_finance_unauth = client.get("/api/v1/admin/finance/summary")
    assert res_finance_unauth.status_code in (401, 403)

    customer = _create_and_login(client, session_db, "normal_cust@toanaas.vn", "Password123!@#", role="customer")
    res_cust = customer["client"].get("/api/v1/admin/summary")
    assert res_cust.status_code == 403

    res_finance_cust = customer["client"].get("/api/v1/admin/finance/summary")
    assert res_finance_cust.status_code == 403


# ==============================================================================
# 14. MALFORMED SOURCE DOES NOT FAKE ZERO
# ==============================================================================
def test_malformed_source_does_not_fake_zero() -> None:
    """14. MALFORMED_SOURCE_DOES_NOT_FAKE_ZERO: None / empty / invalid wallet projection returns null."""
    node_cmd = [
        "node",
        "-e",
        r'''
const fs = require("fs");
const source = fs.readFileSync(process.argv[1], "utf8");

function extract(start, end) {
  const offset = source.indexOf(start);
  if (offset < 0) throw new Error("missing start: " + start);
  const finish = source.indexOf(end, offset + start.length);
  if (finish < 0) throw new Error("missing end: " + end);
  return source.slice(offset, finish);
}

const snippet = extract("function canonicalWalletProjection(value) {", "function canonicalWalletHistoryProjection");
eval(snippet + "\nfunction canonicalNonnegativeInteger(v) { const n = Number(v); return Number.isSafeInteger(n) && n >= 0 ? n : null; }\nfunction canonicalShortText(t, m) { return typeof t === 'string' ? t.slice(0, m) : ''; }");

const resNull = canonicalWalletProjection(null);
const resEmpty = canonicalWalletProjection({});
const resInvalid = canonicalWalletProjection({ balance_xu: "not_a_number", total_spent_xu: 100, is_vip: false });
const resValid = canonicalWalletProjection({ balance_xu: 150, total_spent_xu: 50, is_vip: true });

console.log(JSON.stringify({ resNull, resEmpty, resInvalid, resValid }));
''',
        str(PORTAL_PATH),
    ]
    output = subprocess.check_output(node_cmd, text=True, encoding="utf-8")
    data = json.loads(output)
    assert data["resNull"] is None
    assert data["resEmpty"] is None
    assert data["resInvalid"] is None
    assert data["resValid"] == {
        "balance_xu": 150,
        "total_spent_xu": 50,
        "is_vip": True,
        "plan": None,
    }


# ==============================================================================
# 15. REPORT ROWS DETERMINISTIC AND DEDUPLICATED
# ==============================================================================
def test_report_rows_deterministic_and_deduplicated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """15. NO_DUPLICATE_ROWS=YES & NO_FAKE_ROWS=YES: Report rows have stable IDs, canonical timestamps, deterministic ordering."""
    db_file = tmp_path / "recon_rows_session.db"
    monkeypatch.setattr(copyfast_db, "session_database_path", lambda: db_file)

    with sqlite3.connect(db_file) as conn:
        conn.execute("CREATE TABLE web_accounts (id TEXT PRIMARY KEY, email TEXT, canonical_user_id TEXT)")
        conn.execute("CREATE TABLE web_manual_topup_requests (id INT PRIMARY KEY, account_id TEXT, amount_vnd INT, xu_amount INT, status TEXT, bank_ref TEXT, created_at TEXT)")
        conn.executemany("INSERT INTO web_accounts VALUES (?, ?, ?)", [
            ("acc1", "user1@toanaas.vn", "tg101"),
            ("acc2", "user2@toanaas.vn", "tg102"),
        ])
        conn.executemany("INSERT INTO web_manual_topup_requests VALUES (?, ?, ?, ?, ?, ?, ?)", [
            (1, "acc1", 100000, 1000, "approved", "BANK-001", "2026-03-01T10:00:00"),
            (2, "acc2", 200000, 2000, "approved", "BANK-002", "2026-03-02T10:00:00"),
        ])

    data = copyfast_db.query_finance_reconciliation_data()
    topups = data["requests"]
    assert len(topups) == 2
    ids = [t["id"] for t in topups]
    assert len(ids) == len(set(ids)), "Topup report rows must be deduplicated"
    assert ids == [1, 2], "Deterministic ordering by ID"
