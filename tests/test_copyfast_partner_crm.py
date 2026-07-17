"""Focused safety contracts for the isolated Partner & Lead CRM router.

The router is intentionally mounted only in this test app until a separate
application/UI integration is approved.  These tests exercise the signed Web
account database alone: no Bot, bridge, provider, notification, wallet,
payment, referral or publishing runtime is loaded.
"""

from __future__ import annotations

import importlib
import json
from pathlib import Path
import sqlite3
import sys
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient


MODULES = ["copyfast_db", "copyfast_auth", "copyfast_partner_crm"]


def make_client(tmp_path, monkeypatch, *, enabled: bool = True) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "partner-crm-test.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "partner-crm-test-session-secret")
    monkeypatch.setenv("WEBAPP_PARTNER_CRM_ENABLED", "true" if enabled else "false")
    for name in ("APP_ENV", "ENVIRONMENT", "RAILWAY_ENVIRONMENT", "RAILWAY_VOLUME_MOUNT_PATH"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.delenv("CORE_BRIDGE_BASE_URL", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_TOKEN", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_HMAC_SECRET", raising=False)
    for name in MODULES:
        sys.modules.pop(name, None)
    auth = importlib.import_module("copyfast_auth")
    crm = importlib.import_module("copyfast_partner_crm")
    app = FastAPI()
    app.include_router(auth.router, prefix="/api/v1/auth")
    app.include_router(crm.router)
    return TestClient(app)


def login(client: TestClient, email: str) -> str:
    registered = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct-horse-battery-staple", "display_name": "CRM Owner"},
    )
    assert registered.status_code == 200
    return sign_in(client, email)


def sign_in(client: TestClient, email: str) -> str:
    signed_in = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert signed_in.status_code == 200
    return signed_in.json()["data"]["csrf_token"]


def lead_payload(key: str = "partner-crm-lead-create-0001", **overrides: Any) -> dict[str, Any]:
    value: dict[str, Any] = {
        "lead_name": "Nguyễn Minh An",
        "organization": "Studio Nền Tảng",
        "contact_email": "minh.an@example.com",
        "lead_kind": "partner",
        "opportunity_summary": "Cần trao đổi riêng về một gói nội dung và workflow phù hợp cho đội marketing nhỏ.",
        "source_kind": "inbound",
        "source_label": "Biểu mẫu Web tự nguyện",
        "tags": ["B2B", "Nội dung", "Ưu tiên"],
        "consent_status": "documented",
        "consent_note": "Đồng ý được lưu để đội ngũ tự review nội bộ.",
        "idempotency_key": key,
    }
    value.update(overrides)
    return value


def storage_counts(db_path: Path) -> dict[str, int]:
    tables = (
        "web_partner_crm_leads",
        "web_partner_crm_notes",
        "web_partner_crm_events",
        "web_idempotency",
        "web_audit_events",
    )
    with sqlite3.connect(db_path) as conn:
        return {
            table: int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            for table in tables
        }


def account_id_for_email(db_path: Path, email: str) -> str:
    with sqlite3.connect(db_path) as conn:
        row = conn.execute("SELECT id FROM web_accounts WHERE email=?", (email,)).fetchone()
    assert row is not None
    return str(row[0])


def seed_leads(
    db_path: Path,
    *,
    account_id: str,
    count: int,
    id_start: int,
    stage: str = "qualified",
) -> list[str]:
    """Seed local records only so the list API is tested at page boundaries.

    Creation validation is covered elsewhere.  Keeping this deterministic
    avoids 100+ mutation/audit requests in a focused read-pagination test.
    """

    lead_ids = [f"00000000-0000-4000-8000-{id_start + index:012d}" for index in range(count)]
    rows = []
    for index, lead_id in enumerate(lead_ids, start=1):
        timestamp = f"2026-07-16T12:00:00.{index:03d}+00:00"
        rows.append(
            (
                lead_id,
                account_id,
                f"Lead pagination {index}",
                f"Tổ chức {index}",
                f"lead-{index}@example.com",
                "partner" if index % 2 else "agency",
                f"Nhu cầu nội bộ có thứ tự {index} để kiểm tra phân trang.",
                "manual",
                "Seed kiểm thử",
                "[]",
                "documented",
                "Đã ghi nhận consent nội bộ.",
                stage,
                index,
                timestamp,
                timestamp,
                None,
            )
        )
    with sqlite3.connect(db_path) as conn:
        conn.executemany(
            """INSERT INTO web_partner_crm_leads
               (id, account_id, lead_name, organization, contact_email, lead_kind, opportunity_summary,
                source_kind, source_label, tags_json, consent_status, consent_note, stage, revision,
                created_at, updated_at, archived_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            rows,
        )
        conn.commit()
    return lead_ids


def assert_boundary(data: dict[str, Any], *, persisted: bool) -> None:
    assert data["execution"] == "web_native_partner_lead_crm_only"
    assert data["lead_persisted"] is persisted
    for key in (
        "telegram_state_changed",
        "bot_called",
        "bridge_called",
        "provider_called",
        "remote_lookup_called",
        "social_platform_called",
        "contacted",
        "notification_sent",
        "job_created",
        "wallet_mutated",
        "payment_started",
        "payout_created",
        "referral_ledger_changed",
        "promo_or_membership_changed",
        "publish_action_created",
    ):
        assert data[key] is False


def create_lead(client: TestClient, csrf: str, key: str = "partner-crm-lead-create-0001", **overrides: Any) -> dict[str, Any]:
    response = client.post(
        "/api/v1/partner-crm/leads",
        headers={"X-CSRF-Token": csrf},
        json=lead_payload(key, **overrides),
    )
    assert response.status_code == 200 and response.json()["ok"] is True
    assert_boundary(response.json()["data"], persisted=True)
    return response.json()["data"]["lead"]


def test_partner_crm_requires_signed_session_csrf_idempotency_and_redacts_receipts(tmp_path, monkeypatch):
    db_path = tmp_path / "partner-crm-test.db"
    raw = lead_payload()
    with make_client(tmp_path, monkeypatch) as client:
        assert client.post("/api/v1/partner-crm/leads", json=raw).status_code == 401
        csrf = login(client, "partner-crm-auth@example.com")
        assert client.post("/api/v1/partner-crm/leads", json=raw).status_code == 403

        created = client.post("/api/v1/partner-crm/leads", headers={"X-CSRF-Token": csrf}, json=raw)
        assert created.status_code == 200 and created.json()["ok"] is True
        body = created.json()
        assert body["status"] == "draft"
        assert_boundary(body["data"], persisted=True)
        lead = body["data"]["lead"]
        assert set(lead) == {"id", "revision", "stage"}
        assert lead["revision"] == 1 and lead["stage"] == "draft"

        replay = client.post("/api/v1/partner-crm/leads", headers={"X-CSRF-Token": csrf}, json=raw)
        assert replay.status_code == 200 and replay.json() == body
        collision = client.post(
            "/api/v1/partner-crm/leads",
            headers={"X-CSRF-Token": csrf},
            json=lead_payload(raw["idempotency_key"], organization="Một tổ chức khác hoàn toàn"),
        )
        assert collision.status_code == 409

    with sqlite3.connect(db_path) as conn:
        receipt = conn.execute(
            "SELECT response_json FROM web_idempotency WHERE scope LIKE 'web-partner-crm:%:lead:create'"
        ).fetchone()
        audit = conn.execute(
            "SELECT detail FROM web_audit_events WHERE action='web.partner_crm.lead.create'"
        ).fetchone()
    assert receipt is not None and audit is not None
    assert raw["lead_name"] not in str(receipt[0])
    assert raw["contact_email"] not in str(receipt[0])
    assert raw["opportunity_summary"] not in str(receipt[0])
    assert raw["lead_name"] not in str(audit[0])
    assert raw["contact_email"] not in str(audit[0])


def test_partner_crm_owner_scoped_crud_notes_stage_tags_and_consent(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        first_csrf = login(client, "partner-crm-owner@example.com")
        created = create_lead(client, first_csrf, "partner-crm-owner-create-0001")
        lead_id = created["id"]

        detail = client.get(f"/api/v1/partner-crm/leads/{lead_id}")
        assert detail.status_code == 200 and detail.json()["ok"] is True
        first = detail.json()["data"]["lead"]
        assert first["contact_email"] == "minh.an@example.com"
        assert first["tags"] == ["B2B", "Nội dung", "Ưu tiên"]

        updated_payload = lead_payload(
            "partner-crm-owner-update-0001",
            organization="Studio Nền Tảng Mới",
            tags=["B2B", "b2b", "Đã review"],
        )
        updated_payload["expected_revision"] = first["revision"]
        updated = client.patch(
            f"/api/v1/partner-crm/leads/{lead_id}",
            headers={"X-CSRF-Token": first_csrf},
            json=updated_payload,
        )
        assert updated.status_code == 200 and updated.json()["ok"] is True
        assert updated.json()["data"]["lead"]["revision"] == 2

        qualified = client.post(
            f"/api/v1/partner-crm/leads/{lead_id}/stage",
            headers={"X-CSRF-Token": first_csrf},
            json={"stage": "qualified", "expected_revision": 2, "idempotency_key": "partner-crm-owner-stage-0001"},
        )
        assert qualified.status_code == 200 and qualified.json()["data"]["lead"] == {"id": lead_id, "revision": 3, "stage": "qualified"}

        consent = client.post(
            f"/api/v1/partner-crm/leads/{lead_id}/consent",
            headers={"X-CSRF-Token": first_csrf},
            json={
                "consent_status": "withdrawn",
                "consent_note": "Lead yêu cầu chỉ lưu lịch sử nội bộ, không được chủ động liên hệ.",
                "expected_revision": 3,
                "idempotency_key": "partner-crm-owner-consent-0001",
            },
        )
        assert consent.status_code == 200 and consent.json()["data"]["lead"]["revision"] == 4

        note = client.post(
            f"/api/v1/partner-crm/leads/{lead_id}/notes",
            headers={"X-CSRF-Token": first_csrf},
            json={
                "body": "Đã kiểm tra nội bộ: cần chờ lead tự chủ động trao đổi tiếp.",
                "expected_revision": 4,
                "idempotency_key": "partner-crm-owner-note-0001",
            },
        )
        assert note.status_code == 200 and note.json()["ok"] is True
        assert note.json()["data"]["lead"]["revision"] == 5
        assert set(note.json()["data"]["note"]) == {"id", "created_at"}

        after = client.get(f"/api/v1/partner-crm/leads/{lead_id}").json()["data"]
        assert after["lead"]["organization"] == "Studio Nền Tảng Mới"
        assert after["lead"]["tags"] == ["B2B", "Đã review"]
        assert after["lead"]["consent_status"] == "withdrawn"
        assert len(after["notes"]) == 1
        assert {event["action"] for event in after["events"]} >= {
            "lead_created", "lead_updated", "stage_changed", "consent_recorded", "note_added",
        }

        second_csrf = login(client, "partner-crm-other@example.com")
        hidden = client.get(f"/api/v1/partner-crm/leads/{lead_id}")
        assert hidden.status_code == 200
        assert hidden.json()["error_code"] == "WEB_PARTNER_CRM_LEAD_NOT_FOUND"
        foreign_update = client.patch(
            f"/api/v1/partner-crm/leads/{lead_id}",
            headers={"X-CSRF-Token": second_csrf},
            json={**lead_payload("partner-crm-foreign-update-0001"), "expected_revision": 5},
        )
        assert foreign_update.status_code == 200
        assert foreign_update.json()["error_code"] == "WEB_PARTNER_CRM_LEAD_NOT_FOUND"
        own_list = client.get("/api/v1/partner-crm/leads")
        assert own_list.status_code == 200 and own_list.json()["data"]["items"] == []

        # A local Web manager can see only a redacted read-only directory.
        # Promote this separate test account in the signed-session database;
        # its existing session reloads role_cache on the next request.
        with sqlite3.connect(tmp_path / "partner-crm-test.db") as conn:
            conn.execute("UPDATE web_accounts SET role_cache='admin' WHERE email=?", ("partner-crm-other@example.com",))
            conn.commit()
        directory = client.get("/api/v1/partner-crm/manager/leads")
        assert directory.status_code == 200 and directory.json()["ok"] is True
        directory_data = directory.json()["data"]
        assert directory_data["cross_account_write_available"] is False
        assert directory_data["contact_detail_available"] is False
        assert directory_data["notes_available"] is False
        assert_boundary(directory_data, persisted=False)
        item = next(value for value in directory_data["items"] if value["stage"] == "qualified")
        assert item["stage"] == "qualified" and item["consent_status"] == "withdrawn"
        for private_key in ("lead_id", "owner_account_id", "owner_display_name", "lead_name", "organization", "contact_email", "opportunity_summary", "source_label", "tags", "consent_note", "notes"):
            assert private_key not in item
        # Manager visibility never bypasses the normal owner-scoped detail API.
        assert client.get(f"/api/v1/partner-crm/leads/{lead_id}").json()["error_code"] == "WEB_PARTNER_CRM_LEAD_NOT_FOUND"


def test_partner_crm_owner_list_paginates_101_records_without_cross_account_cursor_leakage(tmp_path, monkeypatch):
    """Owner pages remain scoped to the signed account at every offset."""

    db_path = tmp_path / "partner-crm-test.db"
    owner_email = "partner-crm-page-owner@example.com"
    other_email = "partner-crm-page-other@example.com"
    with make_client(tmp_path, monkeypatch) as client:
        login(client, owner_email)
        assert client.get("/api/v1/partner-crm/summary").status_code == 200
        owner_ids = set(
            seed_leads(
                db_path,
                account_id=account_id_for_email(db_path, owner_email),
                count=101,
                id_start=100_000,
            )
        )

        login(client, other_email)
        other_ids = set(
            seed_leads(
                db_path,
                account_id=account_id_for_email(db_path, other_email),
                count=2,
                id_start=200_000,
            )
        )
        other_page = client.get("/api/v1/partner-crm/leads?stage=all&limit=50&offset=0")
        assert other_page.status_code == 200 and other_page.json()["ok"] is True
        assert {item["id"] for item in other_page.json()["data"]["items"]} == other_ids
        assert other_page.json()["data"]["has_more"] is False
        assert other_page.json()["data"]["next_offset"] is None

        sign_in(client, owner_email)
        pages = []
        for offset, expected_count, has_more, next_offset in ((0, 50, True, 50), (50, 50, True, 100), (100, 1, False, None)):
            response = client.get(f"/api/v1/partner-crm/leads?stage=all&limit=50&offset={offset}")
            assert response.status_code == 200 and response.json()["ok"] is True
            data = response.json()["data"]
            assert len(data["items"]) == expected_count
            assert data["has_more"] is has_more
            assert data["next_offset"] == next_offset
            pages.append({item["id"] for item in data["items"]})

    assert all(page.isdisjoint(other_ids) for page in pages)
    assert pages[0].isdisjoint(pages[1]) and pages[0].isdisjoint(pages[2]) and pages[1].isdisjoint(pages[2])
    assert set().union(*pages) == owner_ids


def test_partner_crm_manager_directory_is_role_guarded_paginated_and_redacted(tmp_path, monkeypatch):
    """The directory pages only after the server confirms an admin role."""

    db_path = tmp_path / "partner-crm-test.db"
    owner_email = "partner-crm-directory-owner@example.com"
    manager_email = "partner-crm-directory-manager@example.com"
    with make_client(tmp_path, monkeypatch) as client:
        login(client, owner_email)
        assert client.get("/api/v1/partner-crm/summary").status_code == 200
        seed_leads(
            db_path,
            account_id=account_id_for_email(db_path, owner_email),
            count=101,
            id_start=300_000,
        )

        login(client, manager_email)
        denied = client.get("/api/v1/partner-crm/manager/leads?stage=all&limit=50&offset=0")
        assert denied.status_code == 403

        with sqlite3.connect(db_path) as conn:
            conn.execute("UPDATE web_accounts SET role_cache='admin' WHERE email=?", (manager_email,))
            conn.commit()

        pages = []
        for offset, expected_count, has_more, next_offset in ((0, 50, True, 50), (50, 50, True, 100), (100, 1, False, None)):
            response = client.get(f"/api/v1/partner-crm/manager/leads?stage=all&limit=50&offset={offset}")
            assert response.status_code == 200 and response.json()["ok"] is True
            data = response.json()["data"]
            assert len(data["items"]) == expected_count
            assert data["has_more"] is has_more
            assert data["next_offset"] == next_offset
            assert data["cross_account_write_available"] is False
            assert data["contact_detail_available"] is False
            assert data["notes_available"] is False
            assert_boundary(data, persisted=False)
            pages.append(data["items"])

    seen_revisions = {int(item["revision"]) for page in pages for item in page}
    assert seen_revisions == set(range(1, 102))
    for item in (value for page in pages for value in page):
        for private_key in (
            "id", "lead_id", "account_id", "owner_account_id", "owner_display_name", "lead_name",
            "organization", "contact_email", "opportunity_summary", "source_label", "tags", "consent_note", "notes",
        ):
            assert private_key not in item


def test_partner_crm_manager_directory_filters_stage_server_side_and_stays_redacted(tmp_path, monkeypatch):
    """Stage filtering remains an admin-only, redacted server query."""

    db_path = tmp_path / "partner-crm-test.db"
    owner_email = "partner-crm-filter-owner@example.com"
    manager_email = "partner-crm-filter-manager@example.com"
    with make_client(tmp_path, monkeypatch) as client:
        login(client, owner_email)
        assert client.get("/api/v1/partner-crm/summary").status_code == 200
        owner_id = account_id_for_email(db_path, owner_email)
        seed_leads(db_path, account_id=owner_id, count=2, id_start=510_000, stage="qualified")
        seed_leads(db_path, account_id=owner_id, count=3, id_start=520_000, stage="draft")

        login(client, manager_email)
        assert client.get("/api/v1/partner-crm/manager/leads?stage=qualified&limit=50&offset=0").status_code == 403
        with sqlite3.connect(db_path) as conn:
            conn.execute("UPDATE web_accounts SET role_cache='admin' WHERE email=?", (manager_email,))
            conn.commit()

        qualified = client.get("/api/v1/partner-crm/manager/leads?stage=qualified&limit=50&offset=0")
        assert qualified.status_code == 200 and qualified.json()["ok"] is True
        qualified_items = qualified.json()["data"]["items"]
        assert len(qualified_items) == 2
        assert {item["stage"] for item in qualified_items} == {"qualified"}

        draft = client.get("/api/v1/partner-crm/manager/leads?stage=draft&limit=50&offset=0")
        assert draft.status_code == 200 and draft.json()["ok"] is True
        draft_items = draft.json()["data"]["items"]
        assert len(draft_items) == 3
        assert {item["stage"] for item in draft_items} == {"draft"}

        combined = client.get("/api/v1/partner-crm/manager/leads?stage=all&limit=50&offset=0")
        assert combined.status_code == 200 and len(combined.json()["data"]["items"]) == 5
        for item in combined.json()["data"]["items"]:
            for private_key in ("id", "lead_id", "account_id", "lead_name", "organization", "contact_email", "notes"):
                assert private_key not in item

        invalid = client.get("/api/v1/partner-crm/manager/leads?stage=not-a-stage&limit=50&offset=0")
        assert invalid.status_code == 422


def test_partner_crm_pipeline_revision_and_archive_boundary(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "partner-crm-stage@example.com")
        lead = create_lead(client, csrf, "partner-crm-stage-create-0001")
        lead_id = lead["id"]

        invalid = client.post(
            f"/api/v1/partner-crm/leads/{lead_id}/stage",
            headers={"X-CSRF-Token": csrf},
            json={"stage": "proposal", "expected_revision": 1, "idempotency_key": "partner-crm-stage-invalid-0001"},
        )
        assert invalid.status_code == 200
        assert invalid.json()["error_code"] == "WEB_PARTNER_CRM_STAGE_TRANSITION"

        qualified = client.post(
            f"/api/v1/partner-crm/leads/{lead_id}/stage",
            headers={"X-CSRF-Token": csrf},
            json={"stage": "qualified", "expected_revision": 1, "idempotency_key": "partner-crm-stage-qualified-0001"},
        )
        assert qualified.status_code == 200 and qualified.json()["data"]["lead"]["revision"] == 2
        archived = client.post(
            f"/api/v1/partner-crm/leads/{lead_id}/stage",
            headers={"X-CSRF-Token": csrf},
            json={"stage": "archived", "expected_revision": 2, "idempotency_key": "partner-crm-stage-archive-0001"},
        )
        assert archived.status_code == 200 and archived.json()["data"]["lead"] == {"id": lead_id, "revision": 3, "stage": "archived"}

        denied_note = client.post(
            f"/api/v1/partner-crm/leads/{lead_id}/notes",
            headers={"X-CSRF-Token": csrf},
            json={"body": "Không được ghi vào lead archived.", "expected_revision": 3, "idempotency_key": "partner-crm-archived-note-0001"},
        )
        assert denied_note.status_code == 200
        assert denied_note.json()["error_code"] == "WEB_PARTNER_CRM_ARCHIVED"
        restored = client.post(
            f"/api/v1/partner-crm/leads/{lead_id}/stage",
            headers={"X-CSRF-Token": csrf},
            json={"stage": "draft", "expected_revision": 3, "idempotency_key": "partner-crm-stage-restore-0001"},
        )
        assert restored.status_code == 200 and restored.json()["data"]["lead"] == {"id": lead_id, "revision": 4, "stage": "draft"}
        stale = client.post(
            f"/api/v1/partner-crm/leads/{lead_id}/stage",
            headers={"X-CSRF-Token": csrf},
            json={"stage": "qualified", "expected_revision": 1, "idempotency_key": "partner-crm-stage-stale-0001"},
        )
        assert stale.status_code == 200
        assert stale.json()["error_code"] == "WEB_PARTNER_CRM_REVISION_CONFLICT"


def test_partner_crm_rejects_unsafe_schema_and_has_no_remote_or_money_surface(tmp_path, monkeypatch):
    db_path = tmp_path / "partner-crm-test.db"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "partner-crm-safety@example.com")
        headers = {"X-CSRF-Token": csrf}
        assert client.get("/api/v1/partner-crm/manager/leads").status_code == 403
        for index, overrides in enumerate((
            {"lead_name": "<script>alert(1)</script>"},
            {"opportunity_summary": "api_key=not-a-real-secret-value"},
            {"opportunity_summary": "Mã OTP 123456 không được lưu trong CRM"},
            {"contact_email": "not-an-email"},
            {"consent_status": "documented", "consent_note": ""},
            {"payout_amount": 100000},
            {"referral_code": "should-not-exist"},
        ), start=1):
            response = client.post(
                "/api/v1/partner-crm/leads",
                headers=headers,
                json=lead_payload(f"partner-crm-safety-{index:04d}", **overrides),
            )
            assert response.status_code == 422

        policy = client.get("/api/v1/partner-crm/policy")
        assert policy.status_code == 200 and policy.json()["ok"] is True
        policy_data = policy.json()["data"]
        assert policy_data["canonical_admin_directory_available"] is False
        assert_boundary(policy_data, persisted=False)

        create_lead(client, csrf, "partner-crm-safety-create-0001")

    with sqlite3.connect(db_path) as conn:
        tables = {str(row[0]) for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        counts = storage_counts(db_path)
    assert {"web_partner_crm_leads", "web_partner_crm_notes", "web_partner_crm_events"}.issubset(tables)
    assert counts["web_partner_crm_leads"] == 1
    assert counts["web_partner_crm_notes"] == 0
    assert not any("payos" in table.lower() or "wallet" in table.lower() or "payout" in table.lower() for table in tables)

    source = (Path(__file__).resolve().parents[1] / "copyfast_partner_crm.py").read_text(encoding="utf-8")
    for forbidden_import in (
        "import bot", "from bot", "import copyfast_bridge", "from copyfast_bridge",
        "import requests", "import httpx", "import urllib", "from urllib",
        "import affiliate_ops", "from affiliate_ops", "import erp_core", "from erp_core",
        "import PayOS", "from PayOS",
    ):
        assert forbidden_import not in source


def test_partner_crm_can_be_disabled_without_creating_a_canonical_admin_backdoor(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch, enabled=False) as client:
        csrf = login(client, "partner-crm-disabled@example.com")
        assert csrf
        guarded = client.get("/api/v1/partner-crm/policy")
        assert guarded.status_code == 503
        assert "WEBAPP_PARTNER_CRM_ENABLED" in guarded.text
