"""Empirical verification test suite for P0.WEBAPP.WEB06: CUSTOMER CRM TRUTH.

Mandate: MASTER_PROGRAM=P0.WEBAPP.FULL.PRODUCT.TRUTH.REMEDIATION.V1
Task: TASK=P0.WEBAPP.WEB06.CUSTOMER.CRM.TRUTH
Mode: OWNER-GOVERNED, SOURCE_ONLY, AUDIT_FIRST, FIRST_RED_FIRST, ONE_BOUNDED_TASK

Invariants tested:
1. CUSTOMER_SEES_ONLY_OWN_LEADS: Customer sees only their own leads (CROSS_ACCOUNT_LEAD_READ=0).
2. FOREIGN_LEAD_HIDDEN_AND_BLOCKED: Foreign leads cannot be found via search or listed.
3. OWN_LEAD_DETAIL_TRUTHFUL: Customer can read full detail of own leads with canonical fields.
4. FOREIGN_LEAD_DETAIL_AND_MUTATION_BLOCKED: Foreign lead detail, patch, stage, note, and consent are blocked (CROSS_ACCOUNT_LEAD_READ=0, CROSS_ACCOUNT_LEAD_WRITE=0).
5. VALID_LEAD_CREATE: Valid lead creation persists draft lead, event, audit, and returns replayable receipt.
6. TAMPERED_OWNER_ACCOUNT_REJECTED: Server assigns canonical ownership; browser-supplied owner/account IDs are rejected (CLIENT_AUTHORITATIVE_ACCOUNT_ID=NO, CLIENT_AUTHORITATIVE_OWNER_ID=NO).
7. INVALID_CREATE_FAIL_CLOSED: Missing fields, invalid emails, invalid codes, markup, and secrets fail closed (INVALID_CREATE_FAKE_SUCCESS=0).
8. VALID_STAGE_UPDATE: Valid stage transitions succeed with optimistic concurrency and log events.
9. INVALID_STAGE_REJECTED: Invalid stage jumps and stale revisions are rejected (INVALID_STAGE_ACCEPTED=0).
10. EMPTY_CRM_TRUTHFUL: Empty durable state returns honest empty list without fake or demo leads (FAKE_CRM_ROW=0, FAKE_LEAD_COUNT=0).
11. BACKEND_STORE_FAILURE_TRUTHFUL: When CRM is disabled/unavailable, endpoints fail closed with 503 instead of faking success.
12. NO_FAKE_CRM_KPI_OR_COUNTS: Summary endpoint reflects exact SQLite counts; zero invented KPIs (FAKE_CRM_KPI=0).
13. NO_DEAD_CRM_CTA: Zero href='#' or href='javascript:*' in CRM; portal routes resolve truthfully; no CRM-to-admin leaks (DEAD_CRM_CTA=0, CRM_TO_ADMIN_ROUTE_LEAK=0).
14. NO_ACCOUNT_LEAD_IDENTITY_CONFLATION: Web Account != Lead != Contact; Telegram ID is never CRM owner (ACCOUNT_LEAD_IDENTITY_CONFLATION=0, TELEGRAM_ID_AS_CRM_OWNER=0).
15. NOTES_AND_ACTIVITY_DURABLE: Notes and activity log belong to exact lead/account and persist durably (FAKE_DURABLE_NOTE=0).
"""

from __future__ import annotations

import importlib
from pathlib import Path
import re
import sqlite3
import sys
from typing import Any
import uuid

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
PORTAL_JS_PATH = ROOT / "static" / "portal" / "portal.js"
COPYFAST_PAGES_PATH = ROOT / "copyfast_pages.py"

MODULES = [
    "app", "copyfast_db", "copyfast_auth", "copyfast_bridge", "copyfast_registry",
    "copyfast_native_read_models", "copyfast_api", "copyfast_projects", "copyfast_assets",
    "copyfast_project_packages", "copyfast_document_operations", "copyfast_image_runtime",
    "copyfast_image_operations", "copyfast_pages", "copyfast_partner_crm",
]


def make_client(tmp_path: Path, monkeypatch) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "web06-test.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "web06-test-session-secret-key-32chars!!")
    monkeypatch.setenv("WEBAPP_COPYFAST_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_PARTNER_CRM_ENABLED", "true")
    for name in (
        "APP_ENV", "ENVIRONMENT", "RAILWAY_ENVIRONMENT", "RAILWAY_VOLUME_MOUNT_PATH",
        "CORE_BRIDGE_BASE_URL", "CORE_BRIDGE_TOKEN", "CORE_BRIDGE_HMAC_SECRET",
    ):
        monkeypatch.delenv(name, raising=False)
    for name in MODULES:
        sys.modules.pop(name, None)
    return TestClient(importlib.import_module("app").app)


def register_and_login(client: TestClient, email: str, display_name: str | None = None) -> str:
    name = display_name or f"User {email}"
    registered = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "StrongPassword123!",
            "display_name": name,
        },
    )
    assert registered.status_code == 200, registered.text
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "StrongPassword123!"},
    )
    assert login.status_code == 200, login.text
    return login.json()["data"]["csrf_token"]


def create_lead_helper(
    client: TestClient,
    csrf: str,
    *,
    lead_name: str = "Cong ty Minh Khang",
    organization: str = "Minh Khang Co.",
    contact_email: str = "contact@minhkhang.vn",
    lead_kind: str = "customer",
    opportunity_summary: str = "Can tu van giai phap tu dong hoa content",
    source_kind: str = "manual",
    source_label: str = "Hoi thao tech",
    tags: list[str] | None = None,
    consent_status: str = "unknown",
    consent_note: str = "",
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    key = idempotency_key or f"crm-lead-{uuid.uuid4().hex[:16]}"
    res = client.post(
        "/api/v1/partner-crm/leads",
        headers={"X-CSRF-Token": csrf},
        json={
            "lead_name": lead_name,
            "organization": organization,
            "contact_email": contact_email,
            "lead_kind": lead_kind,
            "opportunity_summary": opportunity_summary,
            "source_kind": source_kind,
            "source_label": source_label,
            "tags": tags or ["tech", "enterprise"],
            "consent_status": consent_status,
            "consent_note": consent_note,
            "idempotency_key": key,
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body.get("ok") is True, body
    return body["data"]["lead"]


def test_own_leads_visible(tmp_path: Path, monkeypatch) -> None:
    """1. CUSTOMER_SEES_ONLY_OWN_LEADS: Account A sees only their own leads."""
    with make_client(tmp_path, monkeypatch) as client:
        csrf_a = register_and_login(client, "crm_user_a@example.com")
        lead_a1 = create_lead_helper(client, csrf_a, lead_name="Lead Alpha One", idempotency_key="crm-lead-a1-key-0001")
        lead_a2 = create_lead_helper(client, csrf_a, lead_name="Lead Alpha Two", idempotency_key="crm-lead-a2-key-0002")

        # Account A lists leads
        leads_res_a = client.get("/api/v1/partner-crm/leads").json()
        assert leads_res_a.get("ok") is True
        items_a = leads_res_a["data"]["items"]
        lead_ids_a = {item["id"] for item in items_a}
        assert lead_a1["id"] in lead_ids_a
        assert lead_a2["id"] in lead_ids_a

        # Account B registers and lists leads
        csrf_b = register_and_login(client, "crm_user_b@example.com")
        leads_res_b = client.get("/api/v1/partner-crm/leads").json()
        assert leads_res_b.get("ok") is True
        items_b = leads_res_b["data"]["items"]
        lead_ids_b = {item["id"] for item in items_b}

        # Verify zero cross-account read
        assert not any(lid in lead_ids_b for lid in lead_ids_a), (
            f"Cross-account lead read detected: User B saw User A leads! {lead_ids_b & lead_ids_a}"
        )


def test_foreign_lead_hidden_and_blocked(tmp_path: Path, monkeypatch) -> None:
    """2. FOREIGN_LEAD_HIDDEN_AND_BLOCKED: Account B cannot search or read Account A's lead."""
    with make_client(tmp_path, monkeypatch) as client:
        csrf_a = register_and_login(client, "crm_hidden_a@example.com")
        lead_a = create_lead_helper(
            client,
            csrf_a,
            lead_name="UniqueSecretCompanyAlpha",
            organization="AlphaOrg",
            idempotency_key="crm-lead-hidden-a-0001",
        )

        csrf_b = register_and_login(client, "crm_hidden_b@example.com")

        # Search query matching lead A's name returns nothing for Account B
        search_res = client.get("/api/v1/partner-crm/leads?q=UniqueSecretCompanyAlpha").json()
        assert search_res.get("ok") is True
        assert len(search_res["data"]["items"]) == 0

        # Direct GET on lead A's ID by Account B returns guarded not found
        get_res = client.get(f"/api/v1/partner-crm/leads/{lead_a['id']}")
        assert get_res.status_code == 200
        body = get_res.json()
        assert body.get("ok") is False
        assert body.get("error_code") == "WEB_PARTNER_CRM_LEAD_NOT_FOUND"


def test_own_lead_detail(tmp_path: Path, monkeypatch) -> None:
    """3. OWN_LEAD_DETAIL_TRUTHFUL: Account A can read full truthful lead detail."""
    with make_client(tmp_path, monkeypatch) as client:
        csrf_a = register_and_login(client, "crm_detail_a@example.com")
        lead_a = create_lead_helper(
            client,
            csrf_a,
            lead_name="Cong ty TNHH Song Hong",
            organization="Song Hong Media",
            contact_email="contact@songhong.vn",
            lead_kind="partner",
            opportunity_summary="Hop tac san xuat video ngan quy mo 50 clip",
            source_kind="inbound",
            source_label="Form lien he",
            tags=["media", "video"],
            consent_status="unknown",
            idempotency_key="crm-lead-detail-a-0001",
        )

        detail_res = client.get(f"/api/v1/partner-crm/leads/{lead_a['id']}")
        assert detail_res.status_code == 200
        body = detail_res.json()
        assert body.get("ok") is True
        data = body["data"]

        lead = data["lead"]
        assert lead["id"] == lead_a["id"]
        assert lead["lead_name"] == "Cong ty TNHH Song Hong"
        assert lead["organization"] == "Song Hong Media"
        assert lead["contact_email"] == "contact@songhong.vn"
        assert lead["lead_kind"] == "partner"
        assert lead["opportunity_summary"] == "Hop tac san xuat video ngan quy mo 50 clip"
        assert lead["source_kind"] == "inbound"
        assert lead["source_label"] == "Form lien he"
        assert lead["tags"] == ["media", "video"]
        assert lead["stage"] == "draft"
        assert lead["revision"] == 1
        assert lead["execution"] == "web_owned_partner_lead"
        assert lead["archived_at"] is None

        # Notes and events lists exist
        assert isinstance(data["notes"], list)
        assert isinstance(data["events"], list)
        assert len(data["events"]) >= 1
        assert data["events"][0]["action"] == "lead_created"


def test_foreign_lead_detail_blocked(tmp_path: Path, monkeypatch) -> None:
    """4. FOREIGN_LEAD_DETAIL_AND_MUTATION_BLOCKED: Account B cannot mutate Account A's lead."""
    with make_client(tmp_path, monkeypatch) as client:
        csrf_a = register_and_login(client, "crm_owner_a@example.com")
        lead_a = create_lead_helper(client, csrf_a, lead_name="Owner A Lead", idempotency_key="crm-lead-owner-a-0001")

        csrf_b = register_and_login(client, "crm_attacker_b@example.com")
        lead_id = lead_a["id"]

        # Detail blocked
        res_get = client.get(f"/api/v1/partner-crm/leads/{lead_id}").json()
        assert res_get.get("ok") is False
        assert res_get.get("error_code") == "WEB_PARTNER_CRM_LEAD_NOT_FOUND"

        # Update blocked
        res_patch = client.patch(
            f"/api/v1/partner-crm/leads/{lead_id}",
            headers={"X-CSRF-Token": csrf_b},
            json={
                "lead_name": "Tampered Name",
                "opportunity_summary": "Tampered summary",
                "expected_revision": 1,
                "idempotency_key": "crm-tamper-patch-0001",
            },
        ).json()
        assert res_patch.get("ok") is False
        assert res_patch.get("error_code") == "WEB_PARTNER_CRM_LEAD_NOT_FOUND"

        # Stage update blocked
        res_stage = client.post(
            f"/api/v1/partner-crm/leads/{lead_id}/stage",
            headers={"X-CSRF-Token": csrf_b},
            json={"stage": "qualified", "expected_revision": 1, "idempotency_key": "crm-tamper-stage-0001"},
        ).json()
        assert res_stage.get("ok") is False
        assert res_stage.get("error_code") == "WEB_PARTNER_CRM_LEAD_NOT_FOUND"

        # Note creation blocked
        res_note = client.post(
            f"/api/v1/partner-crm/leads/{lead_id}/notes",
            headers={"X-CSRF-Token": csrf_b},
            json={"body": "Hacked note", "expected_revision": 1, "idempotency_key": "crm-tamper-note-0001"},
        ).json()
        assert res_note.get("ok") is False
        assert res_note.get("error_code") == "WEB_PARTNER_CRM_LEAD_NOT_FOUND"

        # Consent update blocked
        res_consent = client.post(
            f"/api/v1/partner-crm/leads/{lead_id}/consent",
            headers={"X-CSRF-Token": csrf_b},
            json={"consent_status": "documented", "consent_note": "Falsified consent", "expected_revision": 1, "idempotency_key": "crm-tamper-consent-0001"},
        ).json()
        assert res_consent.get("ok") is False
        assert res_consent.get("error_code") == "WEB_PARTNER_CRM_LEAD_NOT_FOUND"


def test_valid_lead_create(tmp_path: Path, monkeypatch) -> None:
    """5. VALID_LEAD_CREATE: Valid creation persists draft lead with idempotency."""
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "crm_create@example.com")
        payload = {
            "lead_name": "Cong ty TNHH Khoi Sang",
            "organization": "Khoi Sang Tech",
            "contact_email": "khoisang@example.com",
            "lead_kind": "agency",
            "opportunity_summary": "Hop dong cung cap dich vu copywriter chuyen nghiep",
            "source_kind": "partner_intro",
            "source_label": "Gioi thieu tu anh Ba",
            "tags": ["agency", "copywriting"],
            "consent_status": "unknown",
            "idempotency_key": "crm-lead-valid-create-0001",
        }
        res = client.post("/api/v1/partner-crm/leads", headers={"X-CSRF-Token": csrf}, json=payload)
        assert res.status_code == 200
        body = res.json()
        assert body.get("ok") is True
        lead_receipt = body["data"]["lead"]
        assert lead_receipt["stage"] == "draft"
        assert lead_receipt["revision"] == 1
        assert body["data"]["execution"] == "web_native_partner_lead_crm_only"

        # Read back full detail to verify narrative persistence
        detail = client.get(f"/api/v1/partner-crm/leads/{lead_receipt['id']}").json()
        assert detail.get("ok") is True
        lead = detail["data"]["lead"]
        assert lead["lead_name"] == "Cong ty TNHH Khoi Sang"
        assert lead["organization"] == "Khoi Sang Tech"
        assert lead["contact_email"] == "khoisang@example.com"
        assert lead["lead_kind"] == "agency"
        assert lead["opportunity_summary"] == "Hop dong cung cap dich vu copywriter chuyen nghiep"

        # Replay with same idempotency key returns identical receipt
        replay_res = client.post("/api/v1/partner-crm/leads", headers={"X-CSRF-Token": csrf}, json=payload)
        assert replay_res.status_code == 200
        replay_body = replay_res.json()
        assert replay_body.get("ok") is True
        assert replay_body["data"]["lead"]["id"] == lead_receipt["id"]


def test_tampered_owner_account_rejected(tmp_path: Path, monkeypatch) -> None:
    """6. TAMPERED_OWNER_ACCOUNT_REJECTED: Server strictly assigns canonical ownership."""
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "crm_tamper_test@example.com")
        db_path = tmp_path / "web06-test.db"

        # Attempt to inject client-authoritative account_id or owner_id in body
        payload = {
            "lead_name": "Tampered Account Lead",
            "opportunity_summary": "Attempting to assign foreign account",
            "account_id": "foreign-fake-account-id",
            "owner_id": "foreign-fake-owner-id",
            "idempotency_key": "crm-lead-tamper-owner-0001",
        }
        res = client.post("/api/v1/partner-crm/leads", headers={"X-CSRF-Token": csrf}, json=payload)
        # Extra fields forbidden by Pydantic model_config extra="forbid" -> 422
        assert res.status_code == 422, f"Expected 422 Unprocessable Entity, got {res.status_code}: {res.text}"

        # Valid create assigns server-side account_id only
        valid_lead = create_lead_helper(client, csrf, lead_name="Honest Account Lead", idempotency_key="crm-lead-honest-owner-0001")
        with sqlite3.connect(db_path) as conn:
            row = conn.execute("SELECT account_id FROM web_partner_crm_leads WHERE id=?", (valid_lead["id"],)).fetchone()
            assert row is not None
            # Verified that account_id matches the authenticated user in web_accounts
            acc_row = conn.execute("SELECT id FROM web_accounts WHERE email=?", ("crm_tamper_test@example.com",)).fetchone()
            assert row[0] == acc_row[0]


def test_invalid_create_fail_closed(tmp_path: Path, monkeypatch) -> None:
    """7. INVALID_CREATE_FAIL_CLOSED: Invalid inputs fail closed with validation error."""
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "crm_invalid_inputs@example.com")

        def assert_invalid(payload: dict[str, Any]) -> None:
            res = client.post("/api/v1/partner-crm/leads", headers={"X-CSRF-Token": csrf}, json=payload)
            assert res.status_code == 422, f"Expected 422 for invalid payload {payload}, got {res.status_code}: {res.text}"

        base_valid = {
            "lead_name": "Valid Name",
            "opportunity_summary": "Valid opportunity narrative",
            "idempotency_key": "crm-lead-valid-key-000123",
        }

        # Missing / empty lead_name
        assert_invalid({**base_valid, "lead_name": ""})

        # Invalid email format
        assert_invalid({**base_valid, "contact_email": "not-an-email"})

        # Invalid lead_kind
        assert_invalid({**base_valid, "lead_kind": "unknown_lead_type"})

        # Invalid source_kind
        assert_invalid({**base_valid, "source_kind": "teleportation"})

        # Invalid consent_status
        assert_invalid({**base_valid, "consent_status": "unapproved"})

        # Documented consent without minimum 4 chars note
        assert_invalid({**base_valid, "consent_status": "documented", "consent_note": "no"})

        # Markup in opportunity_summary
        assert_invalid({**base_valid, "opportunity_summary": "<script>alert('pwn')</script>"})

        # Secret/token in opportunity_summary
        assert_invalid({**base_valid, "opportunity_summary": "api_key: sk-1234567890abcdef1234567890"})

        # Invalid idempotency key (too short)
        assert_invalid({**base_valid, "idempotency_key": "short"})


def test_valid_stage_update(tmp_path: Path, monkeypatch) -> None:
    """8. VALID_STAGE_UPDATE: Valid finite state transitions succeed and increment revision."""
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "crm_stage_valid@example.com")
        lead = create_lead_helper(client, csrf, lead_name="Stage Transition Lead", idempotency_key="crm-stage-lead-0001")
        lead_id = lead["id"]
        assert lead["stage"] == "draft"
        assert lead["revision"] == 1

        # draft -> qualified (revision 1 -> 2)
        res1 = client.post(
            f"/api/v1/partner-crm/leads/{lead_id}/stage",
            headers={"X-CSRF-Token": csrf},
            json={"stage": "qualified", "expected_revision": 1, "idempotency_key": "crm-stage-step-0001"},
        ).json()
        assert res1.get("ok") is True
        assert res1["data"]["lead"]["stage"] == "qualified"
        assert res1["data"]["lead"]["revision"] == 2

        # qualified -> proposal (revision 2 -> 3)
        res2 = client.post(
            f"/api/v1/partner-crm/leads/{lead_id}/stage",
            headers={"X-CSRF-Token": csrf},
            json={"stage": "proposal", "expected_revision": 2, "idempotency_key": "crm-stage-step-0002"},
        ).json()
        assert res2.get("ok") is True
        assert res2["data"]["lead"]["stage"] == "proposal"
        assert res2["data"]["lead"]["revision"] == 3

        # proposal -> won (revision 3 -> 4)
        res3 = client.post(
            f"/api/v1/partner-crm/leads/{lead_id}/stage",
            headers={"X-CSRF-Token": csrf},
            json={"stage": "won", "expected_revision": 3, "idempotency_key": "crm-stage-step-0003"},
        ).json()
        assert res3.get("ok") is True
        assert res3["data"]["lead"]["stage"] == "won"
        assert res3["data"]["lead"]["revision"] == 4

        # won -> archived (revision 4 -> 5)
        res4 = client.post(
            f"/api/v1/partner-crm/leads/{lead_id}/stage",
            headers={"X-CSRF-Token": csrf},
            json={"stage": "archived", "expected_revision": 4, "idempotency_key": "crm-stage-step-0004"},
        ).json()
        assert res4.get("ok") is True
        assert res4["data"]["lead"]["stage"] == "archived"
        assert res4["data"]["lead"]["revision"] == 5

        # Fetch detail to verify archived_at is populated
        archived_detail = client.get(f"/api/v1/partner-crm/leads/{lead_id}").json()
        assert archived_detail.get("ok") is True
        assert archived_detail["data"]["lead"]["stage"] == "archived"
        assert archived_detail["data"]["lead"]["archived_at"] is not None


def test_invalid_stage_rejected(tmp_path: Path, monkeypatch) -> None:
    """9. INVALID_STAGE_REJECTED: Illegal stage jumps and stale revisions are rejected."""
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "crm_stage_invalid@example.com")
        lead = create_lead_helper(client, csrf, lead_name="Invalid Stage Lead", idempotency_key="crm-inv-stage-0001")
        lead_id = lead["id"]

        # Illegal jump: draft -> won directly (not in allowable draft transitions)
        res_jump = client.post(
            f"/api/v1/partner-crm/leads/{lead_id}/stage",
            headers={"X-CSRF-Token": csrf},
            json={"stage": "won", "expected_revision": 1, "idempotency_key": "crm-stage-jump-0001"},
        ).json()
        assert res_jump.get("ok") is False
        assert res_jump.get("error_code") == "WEB_PARTNER_CRM_STAGE_TRANSITION"

        # Stale revision conflict: expected_revision=99
        res_stale = client.post(
            f"/api/v1/partner-crm/leads/{lead_id}/stage",
            headers={"X-CSRF-Token": csrf},
            json={"stage": "qualified", "expected_revision": 99, "idempotency_key": "crm-stage-stale-0001"},
        ).json()
        assert res_stale.get("ok") is False
        assert res_stale.get("error_code") == "WEB_PARTNER_CRM_REVISION_CONFLICT"

        # Invalid stage name
        res_bogus = client.post(
            f"/api/v1/partner-crm/leads/{lead_id}/stage",
            headers={"X-CSRF-Token": csrf},
            json={"stage": "exploded", "expected_revision": 1, "idempotency_key": "crm-stage-bogus-0001"},
        )
        assert res_bogus.status_code == 422


def test_empty_crm_truthful(tmp_path: Path, monkeypatch) -> None:
    """10. EMPTY_CRM_TRUTHFUL: Empty durable state returns honest empty list, zero demo rows."""
    with make_client(tmp_path, monkeypatch) as client:
        register_and_login(client, "crm_empty_user@example.com")
        res = client.get("/api/v1/partner-crm/leads").json()
        assert res.get("ok") is True
        data = res["data"]
        assert data["items"] == []
        assert data["has_more"] is False
        assert data["next_offset"] is None


def test_backend_store_failure_truthful(tmp_path: Path, monkeypatch) -> None:
    """11. BACKEND_STORE_FAILURE_TRUTHFUL: When disabled/failing, returns 503 instead of fake success."""
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "crm_disabled_test@example.com")

        # Disable Partner CRM via ENV
        monkeypatch.setenv("WEBAPP_PARTNER_CRM_ENABLED", "false")

        # GET leads returns 503 maintenance
        res_list = client.get("/api/v1/partner-crm/leads")
        assert res_list.status_code == 503
        assert "WEBAPP_PARTNER_CRM_ENABLED" in res_list.text

        # POST lead returns 503 maintenance
        res_create = client.post(
            "/api/v1/partner-crm/leads",
            headers={"X-CSRF-Token": csrf},
            json={"lead_name": "Test", "opportunity_summary": "Test", "idempotency_key": "crm-lead-disabled-0001"},
        )
        assert res_create.status_code == 503

        # GET summary returns 503
        res_summary = client.get("/api/v1/partner-crm/summary")
        assert res_summary.status_code == 503


def test_no_fake_crm_kpi_or_counts(tmp_path: Path, monkeypatch) -> None:
    """12. NO_FAKE_CRM_KPI_OR_COUNTS: Exact database counts returned, zero fabricated metrics."""
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "crm_counts_user@example.com")

        # Initially 0
        summary0 = client.get("/api/v1/partner-crm/summary").json()
        assert summary0.get("ok") is True
        assert summary0["data"]["total"] == 0
        assert all(count == 0 for count in summary0["data"]["by_stage"].values())

        # Create 2 leads: 1 in draft, 1 transitioned to qualified
        l1 = create_lead_helper(client, csrf, lead_name="Count Lead 1", idempotency_key="crm-count-lead-0001")
        l2 = create_lead_helper(client, csrf, lead_name="Count Lead 2", idempotency_key="crm-count-lead-0002")
        client.post(
            f"/api/v1/partner-crm/leads/{l2['id']}/stage",
            headers={"X-CSRF-Token": csrf},
            json={"stage": "qualified", "expected_revision": 1, "idempotency_key": "crm-count-stage-0001"},
        )

        summary1 = client.get("/api/v1/partner-crm/summary").json()
        assert summary1.get("ok") is True
        data = summary1["data"]
        assert data["total"] == 2
        assert data["by_stage"]["draft"] == 1
        assert data["by_stage"]["qualified"] == 1
        assert data["by_stage"]["won"] == 0
        assert data["by_stage"]["archived"] == 0

        # No invented metrics
        assert "revenue" not in data
        assert "conversion_rate" not in data
        assert "pipeline_value" not in data
        assert "growth_rate" not in data


def test_no_dead_crm_cta() -> None:
    """13. NO_DEAD_CRM_CTA: Zero dead links in portal.js; CRM routes resolve without 404."""
    content = PORTAL_JS_PATH.read_text(encoding="utf-8")

    # No dead hashes or javascript: voids in portal.js
    dead_hashes = list(re.finditer(r'href=["\']#["\']', content))
    assert len(dead_hashes) == 0, f"Found {len(dead_hashes)} dead href='#' in portal.js"
    dead_js = list(re.finditer(r'href=["\']javascript:[^"\']*["\']', content))
    assert len(dead_js) == 0, f"Found {len(dead_js)} dead javascript hrefs in portal.js"

    # Verify copyfast_pages render_portal handles CRM routes
    copyfast_pages = importlib.import_module("copyfast_pages")
    for route in ("/crm/leads", "/crm/leads/new", "/crm/consultations/new"):
        response = copyfast_pages.render_portal(route)
        assert response.status_code == 200, f"Route {route} failed with {response.status_code}"

    # Verify detail route with UUID
    detail_route = f"/crm/leads/{uuid.uuid4()}"
    response_detail = copyfast_pages.render_portal(detail_route)
    assert response_detail.status_code == 200, f"Detail route {detail_route} failed with {response_detail.status_code}"


def test_no_account_lead_identity_conflation(tmp_path: Path, monkeypatch) -> None:
    """14. NO_ACCOUNT_LEAD_IDENTITY_CONFLATION: Web Account != Lead != Contact; Telegram ID != CRM owner."""
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "account_owner@toanaas.com", display_name="Owner Display Name")
        db_path = tmp_path / "web06-test.db"

        # Create a lead with distinct contact information
        lead = create_lead_helper(
            client,
            csrf,
            lead_name="Target Prospect Company",
            contact_email="prospect_contact@external.org",
            idempotency_key="crm-conflation-lead-0001",
        )

        with sqlite3.connect(db_path) as conn:
            # Check web_accounts untouched
            acc = conn.execute("SELECT email, display_name FROM web_accounts WHERE email=?", ("account_owner@toanaas.com",)).fetchone()
            assert acc is not None
            assert acc[0] == "account_owner@toanaas.com"
            assert acc[1] == "Owner Display Name"

            # Check web_partner_crm_leads preserves lead-specific contact
            crm_lead = conn.execute("SELECT lead_name, contact_email FROM web_partner_crm_leads WHERE id=?", (lead["id"],)).fetchone()
            assert crm_lead is not None
            assert crm_lead[0] == "Target Prospect Company"
            assert crm_lead[1] == "prospect_contact@external.org"

        # Verify detail execution mode indicates web ownership, not Telegram
        detail = client.get(f"/api/v1/partner-crm/leads/{lead['id']}").json()
        assert detail["data"]["lead"]["execution"] == "web_owned_partner_lead"
        assert "telegram_id" not in detail["data"]["lead"]


def test_notes_and_activity_durable(tmp_path: Path, monkeypatch) -> None:
    """15. NOTES_AND_ACTIVITY_DURABLE: Notes and activity log belong to exact lead and persist."""
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "crm_notes_user@example.com")
        lead = create_lead_helper(client, csrf, lead_name="Note Target Lead", idempotency_key="crm-note-lead-0001")
        lead_id = lead["id"]

        # Add a note
        res_note = client.post(
            f"/api/v1/partner-crm/leads/{lead_id}/notes",
            headers={"X-CSRF-Token": csrf},
            json={
                "body": "Cuoc goi dau tien rat tich cuc, khach quan tam goi premium",
                "expected_revision": 1,
                "idempotency_key": "crm-note-create-0001",
            },
        ).json()
        assert res_note.get("ok") is True
        assert res_note["data"]["lead"]["revision"] == 2
        note_id = res_note["data"]["note"]["id"]

        # Fetch lead detail to verify note and event persisted
        detail = client.get(f"/api/v1/partner-crm/leads/{lead_id}").json()
        assert detail.get("ok") is True
        notes = detail["data"]["notes"]
        assert len(notes) == 1
        assert notes[0]["id"] == note_id
        assert notes[0]["body"] == "Cuoc goi dau tien rat tich cuc, khach quan tam goi premium"

        events = detail["data"]["events"]
        actions = [e["action"] for e in events]
        assert "note_added" in actions
        assert "lead_created" in actions
